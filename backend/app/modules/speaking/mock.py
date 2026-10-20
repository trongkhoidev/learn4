"""Mock session and turn routes."""

import datetime
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.ids import new_id
from app.db.session import get_db
from app.modules.speaking.common import normalize_student_name, prepare_audio, resolve_question
from app.modules.speaking.models import SpeakingMockSession, SpeakingTopic, SpeakingTurn
from app.modules.speaking.schemas import SpeakingMockSessionOut, SpeakingTurnOut
from app.modules.speaking import jobs
from app.modules.speaking.assessment.engine import grade_mock_session

router = APIRouter(prefix="/api/v1/speaking", tags=["speaking"])


@router.post("/mock-sessions", response_model=SpeakingMockSessionOut)
def start_mock_session(
    student_name: str = Form(...),
    topic_id: Optional[str] = Form(None),
    db: Session = Depends(get_db),
):
    if topic_id and not db.get(SpeakingTopic, topic_id):
        raise HTTPException(404, "Không tìm thấy chủ đề")
    session = SpeakingMockSession(
        id=new_id(),
        student_name=normalize_student_name(student_name),
        topic_id=topic_id,
        status="in_progress",
        current_part=1,
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


@router.get("/mock-sessions/{session_id}", response_model=SpeakingMockSessionOut)
def get_mock_session(session_id: str, db: Session = Depends(get_db)):
    session = db.get(SpeakingMockSession, session_id)
    if not session:
        raise HTTPException(404, "Không tìm thấy mock test")
    session.turns.sort(key=lambda turn: turn.sequence)
    return session


@router.post("/mock-sessions/{session_id}/turns", response_model=SpeakingTurnOut)
async def submit_mock_turn(
    session_id: str,
    part: int = Form(...),
    question_id: Optional[str] = Form(None),
    question_text: Optional[str] = Form(None),
    recognition_context: str = Form("", max_length=400),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    session = db.get(SpeakingMockSession, session_id)
    if not session:
        raise HTTPException(404, "Không tìm thấy mock test")
    if session.status != "in_progress":
        raise HTTPException(409, "Mock test đã kết thúc")
    if part not in (1, 2, 3):
        raise HTTPException(422, "Part không hợp lệ")
    _question, q_text = resolve_question(
        db, question_id, session.topic_id, question_text, part,
    )
    audio_path, audio_url = await prepare_audio(
        file, keep_for_job=True, max_seconds=125 if part == 2 else 95,
    )
    sequence = (db.query(func.max(SpeakingTurn.sequence)).filter(
        SpeakingTurn.session_id == session.id
    ).scalar() or 0) + 1
    turn = SpeakingTurn(
        id=new_id(),
        session_id=session.id,
        question_id=question_id,
        part=part,
        sequence=sequence,
        question_text=q_text,
        audio_url=audio_url,
        status="pending",
        result={"status": "pending", "recognition_context": recognition_context},
    )
    session.current_part = max(session.current_part, part)
    db.add(turn)
    db.commit()
    db.refresh(turn)
    jobs.enqueue_speaking(
        db,
        target_type="turn",
        target_id=turn.id,
        audio_path=audio_path,
        question_text=q_text,
        task_type=f"MOCK_PART{part}",
        tier="exam",
    )
    db.refresh(turn)
    return turn


@router.post("/mock-sessions/{session_id}/complete", response_model=SpeakingMockSessionOut)
def complete_mock_session(session_id: str, db: Session = Depends(get_db)):
    session = db.get(SpeakingMockSession, session_id)
    if not session:
        raise HTTPException(404, "Không tìm thấy mock test")
    turns = sorted(session.turns, key=lambda turn: turn.sequence)
    if any(turn.status in {"pending", "processing"} for turn in turns):
        raise HTTPException(409, "Hệ thống vẫn đang chấm một số câu trả lời")
    evidence_turns = [
        turn for turn in turns
        if (turn.result or {}).get("transcript")
        and (turn.result or {}).get("status") in {
            "scored", "partial", "needs_review", "insufficient_sample",
        }
    ]
    if not evidence_turns or {turn.part for turn in evidence_turns} != {1, 2, 3}:
        raise HTTPException(422, "Cần transcript có thể dùng làm evidence ở cả ba part")
    session.result = grade_mock_session([{
        "part": turn.part,
        "question_text": turn.question_text,
        "result": turn.result or {},
    } for turn in evidence_turns], tier="exam")
    session.overall = session.result.get("overall")
    session.status = "completed"
    session.completed_at = datetime.datetime.now(datetime.timezone.utc)
    db.commit()
    db.refresh(session)
    session.turns.sort(key=lambda turn: turn.sequence)
    return session
