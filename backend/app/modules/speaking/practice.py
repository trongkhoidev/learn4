"""Practice submission, history, and progress routes."""

import datetime
from typing import List, Optional
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy import desc, func
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool

from app.core.config import settings
from app.core.ids import new_id
from app.db.session import get_db
from app.modules.speaking.common import normalize_student_name, student_name_key, prepare_audio, resolve_question
from app.modules.speaking.models import PracticeSession, SpeakingQuestion, SpeakingTopic
from app.modules.speaking.schemas import PracticeSessionOut, SpeakingQuestionOut, SpeakingTopicOut, TranscriptReviewDecision
from app.modules.speaking.assessment.contracts import _validate_reference, RaterContractError
from app.modules.speaking import jobs
from app.modules.speaking.assessment.engine import grade_speaking

router = APIRouter(prefix="/api/v1/speaking", tags=["speaking"])


@router.get("/topics", response_model=List[SpeakingTopicOut])
def get_topics(db: Session = Depends(get_db)):
    return db.query(SpeakingTopic).all()


@router.get("/questions", response_model=List[SpeakingQuestionOut])
def get_questions(topic_id: Optional[str] = None, part: Optional[int] = None, db: Session = Depends(get_db)):
    query = db.query(SpeakingQuestion)
    if topic_id:
        query = query.filter(SpeakingQuestion.topic_id == topic_id)
    if part:
        query = query.filter(SpeakingQuestion.part == part)
    return query.order_by(SpeakingQuestion.part, SpeakingQuestion.created_at).all()


@router.post("/practice", response_model=PracticeSessionOut)
async def submit_practice(
    student_name: str = Form(...),
    topic_id: Optional[str] = Form(None),
    question_id: Optional[str] = Form(None),
    question_text: Optional[str] = Form(None),
    part_type: Optional[str] = Form(None),
    async_processing: bool = Form(settings.speaking_async_default),
    recognition_context: str = Form("", max_length=400),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    student_name = normalize_student_name(student_name)
    _question, q_text = resolve_question(db, question_id, topic_id, question_text)
    effective_part_type = part_type or "PART 2"
    answer_limit = 125 if "PART 2" in effective_part_type.upper() else 95
    audio_path, audio_url = await prepare_audio(
        file, keep_for_job=async_processing, max_seconds=answer_limit,
    )
    session = PracticeSession(
        id=new_id(),
        student_name=student_name,
        topic_id=topic_id,
        question_id=question_id,
        part_type=effective_part_type,
        audio_url=audio_url,
        result={"status": "pending", "recognition_context": recognition_context} if async_processing else None,
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    if async_processing:
        jobs.enqueue_speaking(
            db,
            target_type="practice",
            target_id=session.id,
            audio_path=audio_path,
            question_text=q_text,
            task_type=session.part_type,
            tier="practice",
        )
        db.refresh(session)
        return session

    try:
        try:
            result = await run_in_threadpool(
                grade_speaking, audio_path, q_text, session.part_type,
                recognition_context=recognition_context,
            )
        except Exception as exc:
            raise HTTPException(500, f"Scoring failed: {exc}")
        result.setdefault("assessment_meta", {})
        result["assessment_meta"].update({
            "scoring_version": settings.scoring_version,
            "stt_profile_version": settings.stt_profile_version,
        })
        session.transcript = result.get("transcript", "")
        session.result = result
        session.score = result.get("overall", 0.0)
        db.commit()
        db.refresh(session)
        return session
    finally:
        Path(audio_path).unlink(missing_ok=True)


@router.get("/practice/{session_id}", response_model=PracticeSessionOut)
def get_practice(session_id: str, db: Session = Depends(get_db)):
    session = db.get(PracticeSession, session_id)
    if not session:
        raise HTTPException(404, "Không tìm thấy lượt luyện nói")
    return session


@router.patch("/practice/{session_id}/transcript-review", response_model=PracticeSessionOut)
def update_transcript_review(session_id: str, decision: TranscriptReviewDecision, db: Session = Depends(get_db)):
    session = db.get(PracticeSession, session_id)
    if not session or student_name_key(session.student_name) != student_name_key(decision.student_name):
        raise HTTPException(404, "Không tìm thấy lượt luyện nói của bạn")
    result = dict(session.result or {})
    if result.get("schema_version") != "speaking-v3" or session.status in {"pending", "processing"}:
        raise HTTPException(409, "Chờ kết quả phân tích trước khi đối chiếu transcript")
    words = result.get("color_coded_transcript") or []
    by_id = {word["id"]: word for word in words}
    quote = " ".join(by_id.get(word_id, {}).get("word", "") for word_id in decision.word_ids)
    try:
        _validate_reference(quote, decision.word_ids, by_id, set(), "learner review")
    except RaterContractError:
        raise HTTPException(422, "Đoạn đối chiếu không khớp transcript gốc") from None
    review = dict(result.get("transcript_review") or {"status": "ready", "keyterms": []})
    suggestions = [dict(item) for item in review.get("suggestions", [])]
    existing = next((item for item in suggestions if item["word_ids"] == decision.word_ids), None)
    if any(set(item["word_ids"]).intersection(decision.word_ids) and item is not existing for item in suggestions):
        raise HTTPException(409, "Đoạn này đã thuộc một mục đối chiếu khác")
    replacement = decision.replacement.strip()
    if decision.action == "accepted" and not replacement:
        raise HTTPException(422, "Nhập từ bạn xác nhận đã nói")
    if not existing:
        if decision.action == "dismissed":
            raise HTTPException(422, "Không tìm thấy gợi ý cần bỏ qua")
        if len(suggestions) >= 20:
            raise HTTPException(422, "Đã đạt giới hạn 20 mục đối chiếu cho bản ghi")
        existing = {"quote": quote, "word_ids": decision.word_ids,
                    "replacement": replacement, "kind": "possible_mishearing",
                    "source": "learner_supplied", "reason_vi": "Bạn đã nghe lại và xác nhận cách ghi."}
        suggestions.append(existing)
    existing.update(status=decision.action,
                    confirmed_text=replacement if decision.action == "accepted" else None)
    review.update(status="ready", suggestions=suggestions)
    result["transcript_review"] = review
    # Preserve raw ASR, timing and assessment. A learner's intended wording does
    # not establish what was audible or retroactively change an IELTS estimate.
    session.result = result
    db.commit()
    db.refresh(session)
    return session


@router.get("/history", response_model=List[PracticeSessionOut])
def get_history(student_name: str, db: Session = Depends(get_db)):
    return db.query(PracticeSession).filter(
        func.lower(PracticeSession.student_name) == student_name_key(student_name)
    ).order_by(desc(PracticeSession.created_at)).all()


@router.get("/progress")
def get_progress(student_name: str, db: Session = Depends(get_db)):
    sessions = db.query(PracticeSession).filter(
        func.lower(PracticeSession.student_name) == student_name_key(student_name),
    ).order_by(desc(PracticeSession.created_at)).all()
    if not sessions:
        return {"estimated_band": None, "streak": 0}
    normalized = [PracticeSessionOut.model_validate(session) for session in sessions]
    scored = [
        session.result for session in normalized
        if session.result and session.result.get("status") == "scored"
        and session.result.get("overall") is not None
    ]
    scores = [session["overall"] for session in scored[:7]]
    estimated_band = sum(scores) / len(scores) if scores else None
    streak = 0
    current = datetime.date.today()
    dates = sorted({s.created_at.date() for s in sessions if s.created_at}, reverse=True)
    for date in dates:
        if date == current or date == current - datetime.timedelta(days=1):
            streak += 1
            current = date
        else:
            break
    return {"estimated_band": round(estimated_band, 1) if estimated_band is not None else None, "streak": streak}
