from sqlalchemy import DateTime, JSON, String, Integer, Float, ForeignKey, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import List, Optional

from app.core.ids import new_id
from app.db.base import Base

class SpeakingTopic(Base):
    __tablename__ = "speaking_topics"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    created_at: Mapped[object] = mapped_column(DateTime(timezone=True), server_default=func.now())

    questions: Mapped[List["SpeakingQuestion"]] = relationship("SpeakingQuestion", back_populates="topic")

class SpeakingQuestion(Base):
    __tablename__ = "speaking_questions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    topic_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("speaking_topics.id"), nullable=True)
    part: Mapped[int] = mapped_column(Integer, default=1)
    question_text: Mapped[str] = mapped_column(String, nullable=False)
    cue_card: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    follow_up: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    created_at: Mapped[object] = mapped_column(DateTime(timezone=True), server_default=func.now())

    topic: Mapped[Optional["SpeakingTopic"]] = relationship("SpeakingTopic", back_populates="questions")

class PracticeSession(Base):
    __tablename__ = "practice_sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    student_name: Mapped[str] = mapped_column(String, nullable=False, index=True)
    topic_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("speaking_topics.id"), nullable=True)
    question_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("speaking_questions.id"), nullable=True)
    audio_url: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    transcript: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    result: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    part_type: Mapped[Optional[str]] = mapped_column(String, nullable=True) # 'PRACTICE', 'MOCK_PART1', 'MOCK_PART2', 'MOCK_PART3'
    created_at: Mapped[object] = mapped_column(DateTime(timezone=True), server_default=func.now())

    @property
    def status(self) -> str:
        return (self.result or {}).get("status", "pending")


class SpeakingMockSession(Base):
    __tablename__ = "speaking_mock_sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    student_name: Mapped[str] = mapped_column(String, nullable=False, index=True)
    topic_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("speaking_topics.id"), nullable=True)
    status: Mapped[str] = mapped_column(String, default="in_progress", index=True)
    current_part: Mapped[int] = mapped_column(Integer, default=1)
    result: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    overall: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    started_at: Mapped[object] = mapped_column(DateTime(timezone=True), server_default=func.now())
    completed_at: Mapped[Optional[object]] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[object] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    turns: Mapped[List["SpeakingTurn"]] = relationship(
        "SpeakingTurn", back_populates="session", cascade="all, delete-orphan",
    )


class SpeakingTurn(Base):
    __tablename__ = "speaking_turns"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    session_id: Mapped[str] = mapped_column(String(36), ForeignKey("speaking_mock_sessions.id"), index=True)
    question_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("speaking_questions.id"), nullable=True)
    part: Mapped[int] = mapped_column(Integer, nullable=False)
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    question_text: Mapped[str] = mapped_column(Text, nullable=False)
    audio_url: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    transcript: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    result: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    status: Mapped[str] = mapped_column(String, default="pending", index=True)
    created_at: Mapped[object] = mapped_column(DateTime(timezone=True), server_default=func.now())
    completed_at: Mapped[Optional[object]] = mapped_column(DateTime(timezone=True), nullable=True)

    session: Mapped["SpeakingMockSession"] = relationship("SpeakingMockSession", back_populates="turns")


class SpeakingAssessmentJob(Base):
    __tablename__ = "speaking_assessment_jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    target_type: Mapped[str] = mapped_column(String, nullable=False)  # practice | turn
    target_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    audio_path: Mapped[str] = mapped_column(Text, nullable=False)
    question_text: Mapped[str] = mapped_column(Text, nullable=False)
    task_type: Mapped[str] = mapped_column(String, nullable=False)
    tier: Mapped[str] = mapped_column(String, default="practice")
    status: Mapped[str] = mapped_column(String, default="pending", index=True)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[object] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[object] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

