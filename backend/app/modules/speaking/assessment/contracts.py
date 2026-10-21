"""Strict JSON contract for transcript-grounded IELTS criterion raters."""

import json
import re
import unicodedata
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class Evidence(BaseModel):
    model_config = ConfigDict(extra="forbid")

    quote: str = Field(min_length=1, max_length=500)
    word_ids: list[str] = Field(min_length=1)


class GrammarError(BaseModel):
    model_config = ConfigDict(extra="forbid")

    quote: str = Field(min_length=1, max_length=300)
    word_ids: list[str] = Field(min_length=1)
    correction: str = Field(min_length=1, max_length=300)
    reason_vi: str = Field(min_length=1, max_length=500)
    error_or_improvement: Literal["error", "optional_improvement"]


class ExaminerObservation(Evidence):
    kind: Literal["strength", "limitation", "error", "optional_improvement"]
    explanation_vi: str = Field(min_length=1, max_length=360)
    suggestion: str | None = Field(default=None, max_length=300)


class ExaminerReview(BaseModel):
    model_config = ConfigDict(extra="forbid")

    band_reason_vi: str = Field(min_length=1, max_length=500)
    next_band_gap_vi: str = Field(min_length=1, max_length=360)
    observations: list[ExaminerObservation] = Field(min_length=1, max_length=3)


class CriterionRaterResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    criterion: Literal[
        "fluency_coherence", "lexical_resource", "grammatical_range_accuracy", "pronunciation",
    ]
    status: Literal["scored", "insufficient_evidence", "needs_review", "failed"]
    band: float | None = None
    feedback_vi: str = Field(default="", max_length=2000)
    evidence: list[Evidence] = Field(default_factory=list)
    errors: list[GrammarError] = Field(default_factory=list)
    next_action_vi: str = Field(default="", max_length=500)
    examiner_review: ExaminerReview | None = None
    relevance: Literal["related", "weakly_related", "unrelated"] | None = None
    coverage_by_part: dict[Literal["1", "2", "3"], Literal["sufficient", "limited", "missing"]] = Field(default_factory=dict)

    @field_validator("band")
    @classmethod
    def validate_band(cls, value):
        if value is None:
            return value
        if not 0 <= value <= 9 or abs(value * 2 - round(value * 2)) > 1e-8:
            raise ValueError("band must be a half-band from 0 to 9")
        return float(value)

    @model_validator(mode="after")
    def validate_status_band(self):
        if (self.status == "scored") != (self.band is not None):
            raise ValueError("only scored results may contain a band")
        if self.status == "scored" and not self.evidence:
            raise ValueError("scored results require transcript evidence")
        return self


class RaterContractError(ValueError):
    pass


def _normalized_quote(value: str) -> str:
    normalized = unicodedata.normalize("NFC", value).casefold().replace("’", "'")
    return " ".join(re.findall(r"[^\W_]+(?:'[^\W_]+)*", normalized))


def _validate_reference(quote: str, word_ids: list[str], by_id: dict, uncertain_ids: set, label: str):
    if len(set(word_ids)) != len(word_ids):
        raise RaterContractError(f"{label} repeats a word ID")
    missing = [word_id for word_id in word_ids if word_id not in by_id]
    if missing:
        raise RaterContractError(f"{label} references unknown word IDs: {missing}")
    positions = {word_id: index for index, word_id in enumerate(by_id)}
    indices = [positions[word_id] for word_id in word_ids]
    if indices != list(range(indices[0], indices[0] + len(indices))):
        raise RaterContractError(f"{label} must cite contiguous words in transcript order")
    turn_ids = {word_id.split("_w")[0] for word_id in word_ids if re.match(r"^t\d+_w\d+$", word_id)}
    if len(turn_ids) > 1:
        raise RaterContractError(f"{label} must cite contiguous words within one turn")
    expected = " ".join(str(by_id[word_id].get("word") or by_id[word_id].get("text", "")) for word_id in word_ids)
    if _normalized_quote(quote) != _normalized_quote(expected):
        raise RaterContractError(
            f"{label} quote does not match its word IDs {word_ids}; "
            f"expected exact quote {json.dumps(expected, ensure_ascii=False)}"
        )
    if uncertain_ids.intersection(word_ids):
        raise RaterContractError(f"{label} overlaps an ASR-uncertain word")


def validate_rater_result(payload: dict, criterion: str, words: list, uncertain_spans: list) -> CriterionRaterResult:
    """Validate JSON shape and ensure every claim points to heard, certain words."""
    result = CriterionRaterResult.model_validate(payload)
    if result.criterion != criterion:
        raise RaterContractError("criterion does not match the request")

    by_id = {str(word["id"]): word for word in words if word.get("id")}
    uncertain_ids = {
        str(span.get("word_id")) for span in uncertain_spans
        if span.get("word_id") is not None
    }
    violations = []
    observations = result.examiner_review.observations if result.examiner_review else []
    for label, references in (("evidence", result.evidence), ("errors", result.errors), ("observations", observations)):
        for index, reference in enumerate(references):
            try:
                _validate_reference(reference.quote, reference.word_ids, by_id, uncertain_ids, f"{label}[{index}]")
            except RaterContractError as exc:
                violations.append(str(exc))
    if result.criterion != "grammatical_range_accuracy" and result.errors:
        violations.append("only the grammar rater may return grammar errors")
    for observation in observations:
        if observation.kind in {"error", "optional_improvement"} and not (observation.suggestion or "").strip():
            violations.append("error and optional_improvement observations require a concrete suggestion")
        if observation.kind == "error" and result.criterion == "fluency_coherence":
            violations.append("fluency observations describe delivery or coherence limitations, not language errors")
    for error in result.errors:
        if _normalized_quote(error.quote) == _normalized_quote(error.correction):
            violations.append("grammar correction must change the quoted text")
    if violations:
        raise RaterContractError("; ".join(violations))
    return result
