from sqlalchemy import DateTime, JSON, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.ids import new_id
from app.db.base import Base


class Topic(Base):
    __tablename__ = "topics"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    name: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[object] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Question(Base):
    __tablename__ = "questions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    topic_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    part: Mapped[int] = mapped_column(nullable=False, default=1)
    question_text: Mapped[str] = mapped_column(String, nullable=False)
    cue_card: Mapped[str | None] = mapped_column(String, nullable=True)
    follow_up: Mapped[str | None] = mapped_column(String, nullable=True)


class ExamSet(Base):
    __tablename__ = "exam_sets"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    name: Mapped[str] = mapped_column(String, nullable=False)
    questions: Mapped[list | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[object] = mapped_column(DateTime(timezone=True), server_default=func.now())
