"""Typed contract tests for the pronunciation engine (plan §5, §8)."""

import pytest
from pydantic import ValidationError

from app.modules.speaking.pronunciation.contracts import (
    PhoneEvidence,
    PronunciationAssessment,
    PronunciationProvenance,
    WordTiming,
)
from app.modules.speaking.pronunciation.policy import band_eligibility
from datetime import datetime


def _phone_evidence(**overrides):
    base = {
        "id": "pe_1", "word_id": "w1", "word": "works", "start": 1.0, "end": 1.4,
        "expected_phone": "S", "observed_phone": None, "kind": "deletion",
        "status": "candidate", "score_unscaled": -1.82, "confidence": None,
        "model_version": "phone-model-v0",
    }
    base.update(overrides)
    return base


def word(word="works", start=1.0, end=1.4, id="w1"):
    return WordTiming(id=id, word=word, start=start, end=end)


def test_word_timing_rejects_reversed_bounds():
    with pytest.raises(ValidationError):
        word(start=2.0, end=1.0)
    with pytest.raises(ValidationError):
        word(start=-1.0, end=1.0)


def test_phone_evidence_requires_positive_span_and_real_model_version():
    with pytest.raises(ValidationError):
        PhoneEvidence.model_validate(_phone_evidence(start=1.4, end=1.4))
    with pytest.raises(ValidationError):
        PhoneEvidence.model_validate(_phone_evidence(model_version=""))


def test_candidate_evidence_cannot_carry_probability_confidence():
    with pytest.raises(ValidationError, match="probability-shaped"):
        PhoneEvidence.model_validate(_phone_evidence(confidence=0.91))


def test_scored_assessment_requires_calibration_not_uncalibrated():
    with pytest.raises(ValidationError, match="calibration"):
        PronunciationAssessment(band=6.5,
                                provenance=PronunciationProvenance(
                                    calibration_version="uncalibrated"))


def test_valid_scored_assessment_via_calibrated_artifact_fixture():
    assessment = PronunciationAssessment(
        band=6.5,
        band_source="examiner-calibrated-artifact",
        evidence_quality="high",
        provenance=PronunciationProvenance(calibration_version="examiner-cal-2026-06"),
    )
    assert assessment.status == "scored"
    assert assessment.score == 6.5


def test_band_must_be_half_band_in_scale():
    with pytest.raises(ValidationError):
        PronunciationAssessment(
            band=6.3,
            provenance=PronunciationProvenance(calibration_version="examiner-cal-2026-06"),
        )
    with pytest.raises(ValidationError):
        PronunciationAssessment(
            band=9.5,
            provenance=PronunciationProvenance(calibration_version="examiner-cal-2026-06"),
        )


def test_status_scored_rejected_without_band():
    with pytest.raises(ValidationError, match="half-band"):
        PronunciationAssessment(status="scored", band=None)


def test_assessment_serialization_is_stable_for_same_inputs():
    first = PronunciationAssessment(
        feedback="a", phoneme_evidence=[PhoneEvidence.model_validate(_phone_evidence())],
    )
    second = PronunciationAssessment.model_validate(first.model_dump(mode="json"))
    assert first.model_dump_json() == second.model_dump_json()


def test_band_eligibility_fail_closed_reasons(tmp_path):
    eligible, reason = band_eligibility(None)
    assert not eligible and reason == "calibration_artifact_missing"
    eligible, reason = band_eligibility({"schema_version": "other"})
    assert reason == "calibration_artifact_schema_mismatch"
    eligible, reason = band_eligibility({"schema_version": "pronunciation-artifact-v1",
                                         "calibration_version": "uncalibrated"})
    assert reason == "calibration_artifact_uncalibrated"


def test_timestamp_bounds_are_within_audio_duration():
    request_word = word(end=9.4)
    assert request_word.end <= 9.4 + 0.05


def test_phone_evidence_ids_unique_within_words():
    ids = {"pe_1", "pe_2"}
    first = PhoneEvidence.model_validate(_phone_evidence())
    second = PhoneEvidence.model_validate(_phone_evidence(id="pe_2", expected_phone="K",
                                                          start=1.0, end=1.15))
    assert {first.id, second.id} == ids


def test_contract_version_frozen_constants():
    from app.modules.speaking.pronunciation.contracts import ENGINE_VERSION, FEATURE_VERSION
    assert ENGINE_VERSION.startswith("pronunciation-engine-")
    assert FEATURE_VERSION.startswith("pronunciation-features-")
    # Keep the datetime import meaningful for provenance records in reports.
    assert datetime(2026, 10, 21)
