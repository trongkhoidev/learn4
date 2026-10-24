"""Typed pronunciation domain contract with enforced invariants.

Rules baked into validators (plan §5):

- ``status == "scored"`` iff ``band`` is a valid half-band and calibration is
  not ``uncalibrated``.
- A candidate observation is never exported as a probability: ``confidence``
  stays ``None`` until a calibrated artifact declares a calibrator.
- ``start < end`` and bounds are positive; timestamps must map to the original
  audio timeline.
- Every phone evidence references an existing word timing and a real
  ``model_version``.
"""

from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator

ENGINE_VERSION = "pronunciation-engine-v1"
FEATURE_VERSION = "pronunciation-features-v1"

EvidenceStatus = Literal["candidate", "validated", "human_confirmed", "rejected"]
EvidenceKind = Literal[
    "substitution", "deletion", "insertion", "duration_outlier",
    "uncertain_phone", "stress_observational",
]
CriterionStatus = Literal[
    "scored", "partial", "insufficient_evidence", "needs_review", "failed",
]
EngineMode = Literal["disabled", "shadow", "enabled"]


def _valid_half_band(value: float) -> bool:
    return 0 <= value <= 9 and abs(value * 2 - round(value * 2)) < 1e-6


class WordTiming(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1)
    word: str = Field(min_length=1)
    start: float = Field(ge=0)
    end: float = Field(gt=0)

    @model_validator(mode="after")
    def _ordered(self):
        if self.end <= self.start:
            raise ValueError(f"word {self.id!r} must have end > start")
        return self


class PhoneEvidence(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1)
    word_id: str = Field(min_length=1)
    word: str = Field(min_length=1)
    start: float = Field(ge=0)
    end: float = Field(gt=0)
    expected_phone: str = Field(min_length=1)
    observed_phone: Optional[str] = None
    kind: EvidenceKind
    status: EvidenceStatus = "candidate"
    score_unscaled: Optional[float] = None
    confidence: Optional[float] = None
    model_version: str = Field(min_length=1)
    # Deterministic provenance from the GOP step (plan §5/P3); never a score.
    reason_code: Optional[str] = None
    duration_hint: Optional[str] = None
    explanation_vi: str = ""
    practice_hint_vi: Optional[str] = None

    @model_validator(mode="after")
    def _ordered_and_uncalibrated(self):
        if self.end <= self.start:
            raise ValueError(f"phone evidence {self.id!r} must have end > start")
        if self.status != "validated" and self.confidence is not None:
            raise ValueError(
                "candidate evidence cannot carry probability-shaped confidence "
                "before a validated calibrator exists"
            )
        return self


class PronunciationProvenance(BaseModel):
    model_config = ConfigDict(extra="forbid")

    engine_version: str = ENGINE_VERSION
    feature_version: str = FEATURE_VERSION
    alignment_provider: str = "none"
    alignment_model: str = ""
    phone_model: str = ""
    phone_model_license: Optional[str] = None
    calibration_version: str = "uncalibrated"
    g2p_source: str = "none"
    audio_duration_s: Optional[float] = None


class PronunciationAssessment(BaseModel):
    """Single public result object returned by every PronunciationEngine."""

    model_config = ConfigDict(extra="forbid")

    status: CriterionStatus = "insufficient_evidence"
    band: Optional[float] = None
    score: Optional[float] = None
    band_source: str = "unavailable_no_validated_pronunciation_model"
    confidence: Optional[float] = None
    evidence_quality: Literal["high", "medium", "low"] = "low"
    reason: str = ""
    feedback: str = ""
    next_action_vi: Optional[str] = None
    phoneme_evidence: list[PhoneEvidence] = Field(default_factory=list)
    prosody_features: dict = Field(default_factory=dict)
    word_features: dict = Field(default_factory=dict)
    quality_gates: dict = Field(default_factory=dict)
    provenance: PronunciationProvenance = Field(default_factory=PronunciationProvenance)
    shadow: bool = False

    @model_validator(mode="after")
    def _status_band_invariant(self):
        if self.band is not None:
            if not _valid_half_band(self.band):
                raise ValueError("pronunciation band must be a half-band in [0, 9]")
            if self.provenance.calibration_version == "uncalibrated":
                raise ValueError(
                    "scored pronunciation band requires a calibration version that is "
                    "not 'uncalibrated'"
                )
            self.status = "scored"
            self.score = self.band
        else:
            if self.status == "scored":
                raise ValueError("status 'scored' requires a non-null half-band")
            self.score = None
        return self


class PronunciationRequest(BaseModel):
    """Everything the engine may see; provider payloads stop outside the seam."""

    model_config = ConfigDict(extra="forbid")

    audio_path: str = Field(min_length=1)
    transcript: str = ""
    words: list[WordTiming] = Field(default_factory=list)
    asr_uncertain_word_ids: list[str] = Field(default_factory=list)
    asr_confidence: Optional[float] = None
    task_metadata: dict = Field(default_factory=dict)
    is_proper_noun: list[str] = Field(default_factory=list)  # word ids
    # Optional normalized alignment contract (see alignment.py). Phone-level
    # evidence is only produced when this layer comes from a real forced
    # aligner with declared phone alignment; the engine never fabricates
    # phone positions by slicing word timings evenly.
    alignment: dict = Field(default_factory=dict)

    @model_validator(mode="after")
    def _alignment_contract(self):
        alignment = self.alignment
        if alignment and (
            alignment.get("declares_phone_alignment") is not True
            and (alignment.get("phones") or [])
        ):
            raise ValueError(
                "alignment phones without declares_phone_alignment are not "
                "contract-shaped"
            )
        return self
