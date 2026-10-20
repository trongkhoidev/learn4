from datetime import datetime

from pydantic import BaseModel, ConfigDict


class AssignmentCreate(BaseModel):
    class_id: str
    skill: str
    title: str
    question_count: int = 0
    content_text: str | None = None
    answer_key: list[str] | None = None
    speaking_parts: dict | None = None
    writing_task_type: str | None = None
    min_words: int | None = None
    deadline: datetime | None = None


class AssignmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    class_id: str
    skill: str
    title: str
    question_count: int
    content_text: str | None = None
    content_file_url: str | None = None
    audio_url: str | None = None
    speaking_parts: dict | None = None
    writing_task_type: str | None = None
    min_words: int | None = None
    deadline: datetime | None = None
    created_at: datetime


class AssignmentWithKey(AssignmentOut):
    answer_key: list | None = None


class AssignmentUpdate(BaseModel):
    title: str | None = None
    question_count: int | None = None
    content_text: str | None = None
    answer_key: list[str] | None = None
    speaking_parts: dict | None = None
    writing_task_type: str | None = None
    min_words: int | None = None
    deadline: datetime | None = None

