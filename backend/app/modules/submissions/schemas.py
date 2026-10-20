from datetime import datetime

from pydantic import BaseModel, ConfigDict


class SubmitRequest(BaseModel):
    student_name: str
    answers: list[str] | None = None
    essay_text: str | None = None


class SubmissionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    assignment_id: str
    student_name: str
    answers: list | None = None
    audio_url: str | None = None
    transcript: str | None = None
    essay_text: str | None = None
    image_url: str | None = None
    result: dict | None = None
    score: float | None = None
    status: str
    submitted_at: datetime


class GradeUpdate(BaseModel):
    score: float | None = None
    result: dict | None = None
    status: str | None = None


class RosterEntry(SubmissionOut):
    assignment_title: str | None = None
