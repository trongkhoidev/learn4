"""Regression tests for the nullable, evidence-linked Speaking contract."""

from datetime import datetime, timezone
from unittest.mock import patch

import pytest

from app.core.config import settings
from app.modules.speaking.schemas import PracticeSessionOut, SpeakingAssessmentResult
from app.modules.speaking.assessment import raters as llm_service
from app.modules.speaking.assessment.engine import grade_speaking
from app.modules.speaking.assessment.contracts import RaterContractError, validate_rater_result


def test_mock_result_matches_typed_partial_contract(monkeypatch):
    monkeypatch.setattr(settings, "stt_provider", "mock")
    monkeypatch.setattr(settings, "llm_provider", "mock")
    with patch("app.modules.speaking.assessment.engine.budget.record"):
        result = grade_speaking("dummy.webm", "Describe a topic", "PART 1")

    parsed = SpeakingAssessmentResult.model_validate(result)
    assert parsed.schema_version == "speaking-v3"
    assert parsed.status == "partial"
    assert parsed.overall is None
    assert parsed.pronun.band is None
    assert parsed.pronun.status == "insufficient_evidence"
    assert parsed.fluency.band is not None
    assert parsed.assessment_meta.score_type == "diagnostic"
    assert parsed.assessment_meta.confidence_calibrated is False
    assert parsed.assessment_meta.asr_model == "mock"
    assert parsed.assessment_meta.asr_latency_ms >= 0
    for criterion in (parsed.pronun, parsed.fluency, parsed.grammar, parsed.vocab):
        assert criterion.feedback
        assert criterion.next_action_vi
    assert parsed.color_coded_transcript[0]["id"] == "w1"
    assert parsed.color_coded_transcript[0]["start"] == 0.0


def test_fallback_metadata_survives_typed_contract():
    from app.modules.speaking.assessment.engine import _assessment_meta
    from app.modules.speaking.schemas import AssessmentMeta

    parsed = AssessmentMeta.model_validate(_assessment_meta({
        "provider": "groq", "model": "fallback-model", "fallback_used": True,
        "fallback_reason": "TimeoutError", "latency_ms": 30123.45,
    }))
    assert parsed.stt_provider == "groq"
    assert parsed.asr_model == "fallback-model"
    assert parsed.asr_fallback_used is True
    assert parsed.asr_fallback_reason == "TimeoutError"
    assert parsed.asr_latency_ms == 30123.45


def test_edge_status_results_match_typed_contract(monkeypatch):
    cases = [
        ({"text": "", "words": [], "segments": []}, "cant_hear"),
        ({
            "text": "hello there", "words": [],
            "segments": [{"avg_logprob": -0.1, "no_speech_prob": 0.1, "compression_ratio": 1.0}],
            "asr_confidence": 0.9, "hallucination_risk": 0.0, "low_conf_spans": [],
            "provider": "mock", "model": "mock", "decode_profile": "test",
        }, "insufficient_sample"),
    ]
    monkeypatch.setattr(settings, "stt_provider", "mock")
    monkeypatch.setattr(settings, "llm_provider", "mock")
    for stt_result, expected_status in cases:
        with patch("app.modules.speaking.assessment.engine.stt_service.transcribe", return_value=stt_result):
            result = grade_speaking("dummy.webm", "Describe a topic", "PART 1")
        parsed = SpeakingAssessmentResult.model_validate(result)
        assert parsed.status == expected_status
        assert parsed.overall is None


def test_missing_provider_returns_failed_without_transcript(monkeypatch):
    monkeypatch.setattr(settings, "stt_provider", "groq")
    monkeypatch.setattr(settings, "llm_provider", "groq")
    monkeypatch.setattr(settings, "groq_api_key", "")
    with patch("app.modules.speaking.assessment.engine.stt_service.transcribe") as transcribe:
        result = grade_speaking("dummy.webm", "Question", "PART 1")
    transcribe.assert_not_called()
    assert result["status"] == "failed"
    assert result["transcript"] == ""
    assert result["overall"] is None
    assert result["assessment_meta"]["llm_provider"] == "groq"


def test_rater_evidence_cannot_overlap_uncertain_words():
    response = {
        "criterion": "grammatical_range_accuracy", "status": "scored", "band": 6.0,
        "feedback_vi": "Có một lỗi ngữ pháp.",
        "evidence": [{"quote": "go", "word_ids": ["w1"]}],
        "errors": [], "next_action_vi": "Luyện thì quá khứ.",
    }
    with pytest.raises(RaterContractError, match="ASR-uncertain"):
        validate_rater_result(
            response, "grammatical_range_accuracy", [{"id": "w1", "word": "go"}],
            [{"word_id": "w1", "word": "go"}],
        )


def test_rater_repair_receives_all_quote_mismatches_with_expected_source_text():
    payload = {
        "criterion": "lexical_resource", "status": "scored", "band": 6.0,
        "evidence": [
            {"quote": "quiet", "word_ids": ["w1"]},
            {"quote": "garden", "word_ids": ["w2"]},
        ],
    }
    words = [{"id": "w1", "word": "peaceful"}, {"id": "w2", "word": "park"}]
    with pytest.raises(RaterContractError) as error:
        validate_rater_result(payload, "lexical_resource", words, [])
    diagnostic = str(error.value)
    assert 'evidence[0]' in diagnostic and '"peaceful"' in diagnostic
    assert 'evidence[1]' in diagnostic and '"park"' in diagnostic


def test_invalid_json_is_retried_once_then_rejected(monkeypatch):
    responses = iter(["not json", "still not json"])
    calls = []

    def complete(_model, messages, max_tokens=900):
        calls.append(messages)
        return next(responses)

    monkeypatch.setattr(llm_service, "_complete", complete)
    words = [{"id": "w1", "word": "I", "text": "I"}]
    with pytest.raises(ValueError, match="one retry"):
        llm_service._request_rater(
            "grammatical_range_accuracy",
            {"criterion": "grammatical_range_accuracy", "scope": "practice_answer"},
            words=words, uncertain_spans=[], model="fake",
        )
    assert len(calls) == 2


def test_legacy_history_adapter_keeps_only_supported_bands():
    session = PracticeSessionOut.model_validate({
        "id": "history-1", "student_name": "Student",
        "score": 6.5,
        "created_at": datetime.now(timezone.utc),
        "result": {
            "status": "scored", "overall": 6.5, "transcript": "I go yesterday",
            "fluency": {"score": 6.5}, "vocab": {"score": 6.0},
            "grammar": {"score": 5.5},
            "pronun": {"score": 7.0, "band_source": "llm_only_pending_alignment", "phoneme_evidence": []},
        },
    })
    assert session.result["schema_version"] == "speaking-v3"
    assert session.result["pronun"]["band"] is None
    assert session.result["overall"] is None
    assert session.result["status"] == "partial"
    assert session.score is None


def test_invalid_word_timestamps_are_not_exposed_for_playback():
    from app.modules.speaking.assessment.engine import _as_words

    words, reasons = _as_words(
        [{"word": "hello", "start": 1.0, "end": 2.1, "probability": 0.9}],
        "hello", 2.0, allow_unverified_mock=False,
    )
    assert words[0]["start"] is None
    assert words[0]["end"] is None
    assert "word_timing_missing_or_out_of_audio_bounds" in reasons
