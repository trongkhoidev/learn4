import base64
import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.access import verify_teacher
from app.core.background import run_in_background
from app.core.config import settings
from app.db.session import SessionLocal, get_db
from app.integrations.ocr.provider import transcribe_image
from app.integrations.storage.blob import blob_service
from app.modules.assignments.models import Assignment
from app.modules.speaking import jobs
from app.modules.submissions.grading import grade_answers
from app.modules.submissions.models import Submission
from app.modules.submissions.schemas import GradeUpdate, RosterEntry, SubmissionOut
from app.modules.writing.assessment import grade_writing

router = APIRouter(prefix="/api/v1", tags=["submissions"])


def _parse_json(value: str | None):
    if not value:
        return None
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        raise HTTPException(422, "JSON không hợp lệ")


def _save_audio(submission_id: str, upload: UploadFile) -> tuple[str, str]:
    suffix = os.path.splitext(upload.filename or "")[1] or ".webm"
    data = upload.file.read()
    storage = Path(settings.storage_dir) / "audio"
    storage.mkdir(parents=True, exist_ok=True)
    local_path = storage / f"{submission_id}{suffix}"
    local_path.write_bytes(data)
    url = blob_service.upload_bytes(f"audio/{submission_id}{suffix}", data, upload.content_type or "audio/webm")
    return str(local_path), url


def _finish_writing(submission_id: str, task_type: str, question: str, essay: str, image_b64: str | None = None, mime: str = "image/jpeg"):
    db = SessionLocal()
    try:
        if image_b64:
            essay = transcribe_image(image_b64, mime)
            sub = db.get(Submission, submission_id)
            if sub:
                sub.essay_text = essay
                db.commit()
                
        result = grade_writing(task_type, question, essay)
        sub = db.get(Submission, submission_id)
        if sub:
            sub.result = result
            sub.score = result.get("overall")
            sub.status = "graded"
            db.commit()
    except Exception as exc:
        db.rollback()
        sub = db.get(Submission, submission_id)
        if sub:
            sub.status = "graded"
            sub.result = {"error": str(exc)}
            db.commit()
    finally:
        db.close()


@router.post("/assignments/{assignment_id}/submit", response_model=SubmissionOut)
def submit(
    assignment_id: str,
    student_name: str = Form(...),
    answers: str | None = Form(None),
    essay_text: str | None = Form(None),
    question: str | None = Form(None),
    task_type: str | None = Form(None),
    image_file: UploadFile | None = File(None),
    audio_file: UploadFile | None = File(None),
    db: Session = Depends(get_db),
):
    assignment = db.get(Assignment, assignment_id)
    if not assignment:
        raise HTTPException(404, "Không tìm thấy bài tập")

    if assignment.deadline:
        deadline = assignment.deadline
        if deadline.tzinfo is None:
            deadline = deadline.replace(tzinfo=timezone.utc)
        if datetime.now(timezone.utc) > deadline:
            raise HTTPException(400, "Bài tập đã quá hạn nộp")

    student_name = " ".join(student_name.strip().lower().split())
    if not student_name:
        raise HTTPException(422, "Tên học viên không hợp lệ")

    if settings.daily_submit_limit_per_student > 0:
        today = datetime.now(timezone.utc).date().isoformat()
        count = (
            db.query(func.count())
            .select_from(Submission)
            .filter(
                Submission.student_name == student_name,
                func.date(Submission.submitted_at) == today,
            )
            .scalar()
        )
        if count >= settings.daily_submit_limit_per_student:
            raise HTTPException(429, "Đã đạt giới hạn số lần nộp trong ngày")

    sub = Submission(
        id=str(uuid.uuid4()),
        assignment_id=assignment_id,
        student_name=student_name,
        status="pending",
    )

    if assignment.skill in ("reading", "listening"):
        answers_list = _parse_json(answers)
        sub.answers = answers_list
        if assignment.answer_key:
            grade = grade_answers(answers_list, assignment.answer_key)
            sub.score = grade["score"]
            sub.result = grade
            sub.status = "graded"
        db.add(sub)
        db.commit()
        db.refresh(sub)
        return sub

    if assignment.skill == "speaking":
        if not audio_file:
            raise HTTPException(422, "Speaking cần file audio")
        local_path, url = _save_audio(sub.id, audio_file)
        sub.audio_url = url
        db.add(sub)
        db.commit()
        db.refresh(sub)
        question_text = question or (assignment.speaking_parts or {}).get("part1", "")
        part_type = task_type or "PART 1"
        tier = "exam" if (assignment.speaking_parts or {}).get("is_mock") else "practice"
        jobs.enqueue_speaking(
            db,
            target_type="submission",
            target_id=sub.id,
            audio_path=local_path,
            question_text=question_text,
            task_type=part_type,
            tier=tier,
        )
        return sub

    if assignment.skill == "writing":
        essay = essay_text or ""
        image_b64 = None
        mime = "image/jpeg"
        if image_file:
            data = image_file.file.read()
            mime = image_file.content_type or "image/jpeg"
            image_b64 = base64.b64encode(data).decode()
            sub.image_url = blob_service.upload_bytes(f"writing/{sub.id}.jpg", data, mime)
        sub.essay_text = essay
        db.add(sub)
        db.commit()
        db.refresh(sub)
        run_in_background(
            _finish_writing,
            sub.id,
            assignment.writing_task_type or "task2",
            assignment.content_text or "",
            essay,
            image_b64,
            mime,
        )
        return sub

    raise HTTPException(422, "Skill không hợp lệ")


@router.get("/assignments/{assignment_id}/submissions", response_model=list[SubmissionOut], dependencies=[Depends(verify_teacher)])
def list_submissions(assignment_id: str, db: Session = Depends(get_db)):
    return (
        db.query(Submission)
        .filter(Submission.assignment_id == assignment_id)
        .order_by(Submission.submitted_at.desc())
        .all()
    )


@router.get("/submissions/{submission_id}", response_model=SubmissionOut)
def get_submission(submission_id: str, db: Session = Depends(get_db)):
    sub = db.get(Submission, submission_id)
    if not sub:
        raise HTTPException(404, "Không tìm thấy bài nộp")
    return sub


@router.patch("/submissions/{submission_id}", response_model=SubmissionOut, dependencies=[Depends(verify_teacher)])
def patch_submission(submission_id: str, payload: GradeUpdate, db: Session = Depends(get_db)):
    sub = db.get(Submission, submission_id)
    if not sub:
        raise HTTPException(404, "Không tìm thấy bài nộp")
    if payload.score is not None:
        sub.score = payload.score
    if payload.result is not None:
        sub.result = payload.result
    if payload.status is not None:
        sub.status = payload.status
    db.commit()
    db.refresh(sub)
    return sub


@router.get("/classes/{class_id}/roster", response_model=list[RosterEntry])
def roster(class_id: str, name: str, db: Session = Depends(get_db)):
    normalized_name = " ".join(name.strip().lower().split())
    results = (
        db.query(Submission, Assignment.title)
        .join(Assignment, Submission.assignment_id == Assignment.id)
        .filter(Assignment.class_id == class_id, Submission.student_name == normalized_name)
        .order_by(Submission.submitted_at.desc())
        .all()
    )
    roster_entries = []
    for sub, title in results:
        sub_dict = SubmissionOut.model_validate(sub).model_dump()
        sub_dict["assignment_title"] = title
        roster_entries.append(RosterEntry(**sub_dict))
    return roster_entries
