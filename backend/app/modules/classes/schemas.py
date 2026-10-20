from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ClassCreate(BaseModel):
    name: str
    level: str = "General English B1"
    teacher_note: str | None = None


class ClassOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    level: str = "General English B1"
    share_code: str
    teacher_note: str | None = None
    created_at: datetime


class JoinRequest(BaseModel):
    code: str


class ClassUpdate(BaseModel):
    name: str | None = None
    level: str | None = None
    teacher_note: str | None = None
