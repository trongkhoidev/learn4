from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from typing import List, Optional, Dict, Any, Literal
from datetime import datetime
from app.modules.speaking.assessment.contracts import ExaminerReview

class SpeakingQuestionBase(BaseModel):
    topic_id: Optional[str] = None
    part: int
    question_text: str
    cue_card: Optional[str] = None
    follow_up: Optional[str] = None

class SpeakingQuestionOut(SpeakingQuestionBase):
    id: str
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class SpeakingTopicBase(BaseModel):
    name: str
    description: Optional[str] = None

class SpeakingTopicOut(SpeakingTopicBase):
    id: str
    created_at: datetime
    questions: List[SpeakingQuestionOut] = []
    model_config = ConfigDict(from_attributes=True)

class PracticeSessionOut(BaseModel):
    id: str
    student_name: str
    topic_id: Optional[str] = None
    question_id: Optional[str] = None
    part_type: Optional[str] = None
    audio_url: Optional[str] = None
    transcript: Optional[str] = None
    result: Optional[Dict[str, Any]] = None
    score: Optional[float] = None
    created_at: datetime
    status: str = "pending"
    model_config = ConfigDict(from_attributes=True)

    @field_validator("result", mode="before")
    @classmethod
    def adapt_legacy_result(cls, value):
        return _adapt_result_field(value)

    @model_validator(mode="after")
    def align_score_with_nullable_result(self):
        if isinstance(self.result, dict) and self.result.get("schema_version") == "speaking-v3":
            self.score = self.result.get("overall")
        return self


class SpeakingTurnOut(BaseModel):
    id: str
    session_id: str
    question_id: Optional[str] = None
    part: int
    sequence: int
    question_text: str
    audio_url: Optional[str] = None
    transcript: Optional[str] = None
    result: Optional[Dict[str, Any]] = None
    score: Optional[float] = None
    status: str
    created_at: datetime
    completed_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)

    @field_validator("result", mode="before")
    @classmethod
    def adapt_legacy_result(cls, value):
        return _adapt_result_field(value)

    @model_validator(mode="after")
    def align_score_with_nullable_result(self):
        if isinstance(self.result, dict) and self.result.get("schema_version") == "speaking-v3":
            self.score = self.result.get("overall")
        return self


class SpeakingMockSessionOut(BaseModel):
    id: str
    student_name: str
    topic_id: Optional[str] = None
    status: str
    current_part: int
    result: Optional[Dict[str, Any]] = None
    overall: Optional[float] = None
    started_at: datetime
    completed_at: Optional[datetime] = None
    turns: List[SpeakingTurnOut] = Field(default_factory=list)
    model_config = ConfigDict(from_attributes=True)


class CriterionAssessment(BaseModel):
    status: Literal["scored", "partial", "insufficient_evidence", "needs_review", "failed"] = "insufficient_evidence"
    band: Optional[float] = None
    # `score` is retained as a nullable response alias for older clients.
    score: Optional[float] = None
    confidence: Optional[float] = None
    confidence_basis: str = "not_calibrated"
    feedback: Optional[str] = None
    errors: List[Dict[str, Any]] = Field(default_factory=list)
    evidence: List[Dict[str, Any]] = Field(default_factory=list)
    coverage_by_part: Dict[str, str] = Field(default_factory=dict)
    next_action_vi: Optional[str] = None
    examiner_review: Optional[ExaminerReview] = None
    reason: Optional[str] = None
    relevance: Optional[Literal["related", "weakly_related", "unrelated"]] = None
    features: Dict[str, Any] = Field(default_factory=dict)
    problem_words: List[Dict[str, Any]] = Field(default_factory=list)
    band_source: Optional[str] = None
    evidence_quality: Optional[str] = None
    prosody_features: Dict[str, Any] = Field(default_factory=dict)
    energy_features: Dict[str, Any] = Field(default_factory=dict)
    intelligibility: Dict[str, Any] = Field(default_factory=dict)
    phoneme_evidence: List[Dict[str, Any]] = Field(default_factory=list)
    alignment: Dict[str, Any] = Field(default_factory=dict)


class AssessmentMeta(BaseModel):
    score_type: Literal["diagnostic"] = "diagnostic"
    confidence_calibrated: bool = False
    rubric: str = "IELTS Speaking public band descriptors"
    disclaimer: str = (
        "AI diagnostic estimate; not an official IELTS score. "
        "Pronunciation requires audio-grounded evidence and human calibration."
    )
    scoring_version: Optional[str] = None
    stt_profile_version: Optional[str] = None
    calibration_version: str = "uncalibrated"
    rubric_version: Optional[str] = None
    asr_model: Optional[str] = None
    asr_fallback_used: Optional[bool] = None
    asr_fallback_reason: Optional[str] = None
    asr_latency_ms: Optional[float] = None
    llm_models: Dict[str, str] = Field(default_factory=dict)
    llm_provider: Optional[str] = None
    stt_provider: Optional[str] = None


def _legacy_criterion(value: dict | None, *, status: str) -> dict:
    old = value if isinstance(value, dict) else {}
    band = old.get("band", old.get("score"))
    source = old.get("band_source")
    if source == "llm_only_pending_alignment" or status != "scored":
        band = None
    try:
        band = float(band) if band is not None else None
    except (TypeError, ValueError):
        band = None
    criterion_status = "scored" if band is not None else "insufficient_evidence"
    return {
        **old,
        "status": criterion_status,
        "band": band,
        "score": band,
        "confidence": None,
        "confidence_basis": old.get("confidence_basis", "legacy_unverified"),
        "evidence": old.get("evidence", []),
    }


def _adapt_legacy_result(value: dict) -> dict:
    """Expose old persisted JSON through the current nullable Speaking contract."""
    if value.get("schema_version") == "speaking-v3":
        return value
    old_status = value.get("status", "failed")
    if old_status in {"pending", "processing"}:
        return value
    status = old_status if old_status in {
        "scored", "partial", "cant_hear", "insufficient_sample", "needs_review", "failed",
    } else ("partial" if old_status == "off_topic" else "failed")
    aliases = {
        "fluency_coherence": "fluency",
        "lexical_resource": "vocab",
        "grammatical_range_accuracy": "grammar",
        "pronunciation": "pronun",
    }
    criteria = {
        key: _legacy_criterion(value.get(alias), status=old_status)
        for key, alias in aliases.items()
    }
    if not all(criteria[key].get("band") is not None for key in aliases):
        overall = None
        if status == "scored":
            status = "partial"
    else:
        overall = value.get("overall")
    words = []
    for index, word in enumerate(value.get("color_coded_transcript") or [], start=1):
        words.append({
            **word,
            "id": word.get("id", f"w{index}"),
            "start": word.get("start"),
            "end": word.get("end"),
            "asr_probability": word.get("asr_probability"),
            "asr_probability_calibrated": False,
            "uncertain": bool(word.get("uncertain", False)),
        })
    meta = dict(value.get("assessment_meta") or {})
    meta.setdefault("rubric_version", "legacy_unknown")
    return {
        **value,
        "schema_version": "speaking-v3",
        "scope": "practice_answer",
        "score_type": "diagnostic",
        "status": status,
        "overall": overall,
        "criteria": criteria,
        "pronun": criteria["pronunciation"],
        "fluency": criteria["fluency_coherence"],
        "grammar": criteria["grammatical_range_accuracy"],
        "vocab": criteria["lexical_resource"],
        "transcription": {
            "text": value.get("transcript", ""),
            "words": words,
            "calibrated": False,
        },
        "color_coded_transcript": words,
        "assessment_meta": meta,
        "provenance": value.get("provenance") or {},
        "coaching_flags": ["off_topic"] if old_status == "off_topic" else [],
    }


class SpeakingAssessmentResult(BaseModel):
    schema_version: Literal["speaking-v3"] = "speaking-v3"
    scope: Literal["practice_answer", "mock_session"] = "practice_answer"
    score_type: Literal["diagnostic"] = "diagnostic"
    status: Literal["scored", "partial", "cant_hear", "insufficient_sample", "needs_review", "failed"]
    transcript: str = ""
    noise: Optional[str] = None
    is_relevant: Optional[bool] = None
    overall: Optional[float] = None
    criteria: Dict[str, CriterionAssessment] = Field(default_factory=dict)
    pronun: CriterionAssessment
    fluency: CriterionAssessment
    grammar: CriterionAssessment
    vocab: CriterionAssessment
    color_coded_transcript: List[Dict[str, Any]] = Field(default_factory=list)
    uncertain_spans: List[Dict[str, Any]] = Field(default_factory=list)
    review_reasons: List[str] = Field(default_factory=list)
    coaching_flags: List[str] = Field(default_factory=list)
    transcription: Dict[str, Any] = Field(default_factory=dict)
    provenance: Dict[str, Any] = Field(default_factory=dict)
    assessment_meta: AssessmentMeta = Field(default_factory=AssessmentMeta)
    error: Optional[str] = None


def _adapt_result_field(value):
    if isinstance(value, dict):
        return _adapt_legacy_result(value)
    return value
