import json
from datetime import datetime

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.core.access import verify_teacher
from app.core.ids import new_id
from app.db.session import get_db
from app.integrations.storage.blob import blob_service
from app.modules.assignments.models import Assignment
from app.modules.assignments.schemas import AssignmentOut, AssignmentWithKey
from app.modules.assignments.use_cases import delete_assignment_record
from app.modules.classes.models import Class

router = APIRouter(prefix="/api/v1", tags=["assignments"])


def _parse_json(value: str | None):
    if not value:
        return None
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        raise HTTPException(422, "JSON không hợp lệ")


def _parse_deadline(value: str | None):
    if not value:
        return None
    return datetime.fromisoformat(value)


@router.post("/assignments", response_model=AssignmentWithKey, dependencies=[Depends(verify_teacher)])
def create_assignment(
    class_id: str = Form(...),
    skill: str = Form(...),
    title: str = Form(...),
    question_count: int = Form(0),
    content_text: str | None = Form(None),
    answer_key: str | None = Form(None),
    speaking_parts: str | None = Form(None),
    writing_task_type: str | None = Form(None),
    min_words: int | None = Form(None),
    deadline: str | None = Form(None),
    content_file: UploadFile | None = File(None),
    audio_file: UploadFile | None = File(None),
    db: Session = Depends(get_db),
):
    if not db.get(Class, class_id):
        raise HTTPException(404, "Lớp không tồn tại")
    assignment = Assignment(
        id=new_id(),
        class_id=class_id,
        skill=skill,
        title=title,
        question_count=question_count,
        content_text=content_text,
        answer_key=_parse_json(answer_key),
        speaking_parts=_parse_json(speaking_parts),
        writing_task_type=writing_task_type,
        min_words=min_words,
        deadline=_parse_deadline(deadline),
    )
    if content_file:
        key = f"assignments/{assignment.id}/content"
        assignment.content_file_url = blob_service.upload_bytes(
            key, content_file.file.read(), content_file.content_type or "application/octet-stream"
        )
    if audio_file:
        key = f"assignments/{assignment.id}/audio"
        assignment.audio_url = blob_service.upload_bytes(
            key, audio_file.file.read(), audio_file.content_type or "application/octet-stream"
        )
    db.add(assignment)
    db.commit()
    db.refresh(assignment)
    return assignment


@router.get("/classes/{class_id}/assignments", response_model=list[AssignmentOut])
def list_assignments(class_id: str, db: Session = Depends(get_db)):
    return (
        db.query(Assignment)
        .filter(Assignment.class_id == class_id)
        .order_by(Assignment.created_at.desc())
        .all()
    )


@router.get("/assignments/{assignment_id}", response_model=AssignmentOut)
def get_assignment(assignment_id: str, db: Session = Depends(get_db)):
    assignment = db.get(Assignment, assignment_id)
    if not assignment:
        raise HTTPException(404, "Không tìm thấy bài tập")
    return assignment


@router.get("/teacher/assignments/{assignment_id}", response_model=AssignmentWithKey, dependencies=[Depends(verify_teacher)])
def get_teacher_assignment(assignment_id: str, db: Session = Depends(get_db)):
    assignment = db.get(Assignment, assignment_id)
    if not assignment:
        raise HTTPException(404, "Không tìm thấy bài tập")
    return assignment


@router.patch("/assignments/{assignment_id}", response_model=AssignmentWithKey, dependencies=[Depends(verify_teacher)])
def update_assignment(
    assignment_id: str,
    title: str | None = Form(None),
    question_count: int | None = Form(None),
    content_text: str | None = Form(None),
    answer_key: str | None = Form(None),
    speaking_parts: str | None = Form(None),
    writing_task_type: str | None = Form(None),
    min_words: int | None = Form(None),
    deadline: str | None = Form(None),
    content_file: UploadFile | None = File(None),
    audio_file: UploadFile | None = File(None),
    db: Session = Depends(get_db),
):
    assignment = db.get(Assignment, assignment_id)
    if not assignment:
        raise HTTPException(404, "Không tìm thấy bài tập")
    
    if title is not None:
        assignment.title = title
    if question_count is not None:
        assignment.question_count = question_count
    if content_text is not None:
        assignment.content_text = content_text
    if answer_key is not None:
        assignment.answer_key = _parse_json(answer_key)
    if speaking_parts is not None:
        assignment.speaking_parts = _parse_json(speaking_parts)
    if writing_task_type is not None:
        assignment.writing_task_type = writing_task_type
    if min_words is not None:
        assignment.min_words = min_words
    if deadline is not None:
        assignment.deadline = _parse_deadline(deadline)
        
    if content_file:
        key = f"assignments/{assignment.id}/content"
        assignment.content_file_url = blob_service.upload_bytes(
            key, content_file.file.read(), content_file.content_type or "application/octet-stream"
        )
    if audio_file:
        key = f"assignments/{assignment.id}/audio"
        assignment.audio_url = blob_service.upload_bytes(
            key, audio_file.file.read(), audio_file.content_type or "application/octet-stream"
        )
    
    db.commit()
    db.refresh(assignment)
    return assignment


@router.delete("/assignments/{assignment_id}", dependencies=[Depends(verify_teacher)])
def delete_assignment(assignment_id: str, db: Session = Depends(get_db)):
    if not delete_assignment_record(assignment_id, db):
        raise HTTPException(404, "Không tìm thấy bài tập")
    return {"ok": True}
