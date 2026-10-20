from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.ids import new_id
from app.db.base import Base


class Assignment(Base):
    __tablename__ = "assignments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    class_id: Mapped[str] = mapped_column(String(36), ForeignKey("classes.id"), index=True, nullable=False)
    skill: Mapped[str] = mapped_column(String, nullable=False)
    title: Mapped[str] = mapped_column(String, nullable=False)
    question_count: Mapped[int] = mapped_column(Integer, default=0)
    content_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    content_file_url: Mapped[str | None] = mapped_column(String, nullable=True)
    audio_url: Mapped[str | None] = mapped_column(String, nullable=True)
    answer_key: Mapped[list | None] = mapped_column(JSON, nullable=True)
    speaking_parts: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    writing_task_type: Mapped[str | None] = mapped_column(String, nullable=True)
    min_words: Mapped[int | None] = mapped_column(Integer, nullable=True)
    deadline: Mapped[object | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[object] = mapped_column(DateTime(timezone=True), server_default=func.now())
