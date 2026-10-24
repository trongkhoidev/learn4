"""P0 regression: no Pronunciation band may be inferred from ASR confidence.

Real-provider decodes with high or low confidence and no calibrated
pronunciation artifact must always produce a nullable Pronunciation criterion;
client code must never recompute Overall from language bands alone.
"""

from datetime import datetime, timezone
from unittest.mock import patch

import pytest

from app.core.config import settings
from app.modules.speaking.assessment.engine import grade_mock_session, grade_speaking
from app.modules.speaking.schemas import PracticeSessionOut, SpeakingTurnOut


def _stt_payload(asr_confidence):
    return {
        "text": "I have been working in Da Nang for five years",
        "words": [
            {"word": "I", "start": 0.0, "end": 0.2, "probability": asr_confidence},
            {"word": "have", "start": 0.25, "end": 0.45, "probability": asr_confidence},
            {"word": "been", "start": 0.5, "end": 0.7, "probability": asr_confidence},
            {"word": "working", "start": 0.75, "end": 1.2, "probability": asr_confidence},
            {"word": "in", "start": 1.25, "end": 1.4, "probability": asr_confidence},
            {"word": "Da", "start": 1.45, "end": 1.6, "probability": asr_confidence},
            {"word": "Nang", "start": 1.65, "end": 1.9, "probability": asr_confidence},
            {"word": "for", "start": 1.95, "end": 2.1, "probability": asr_confidence},
            {"word": "five", "start": 2.15, "end": 2.35, "probability": asr_confidence},
            {"word": "years", "start": 2.4, "end": 2.7, "probability": asr_confidence},
        ],
        "segments": [{"start": 0.0, "end": 2.7, "avg_logprob": -0.1, "no_speech_prob": 0.01,
                      "compression_ratio": 1.0}],
        "asr_confidence": asr_confidence,
        "hallucination_risk": 0.0,
        "low_conf_spans": [],
        "uncertain_spans": [],
        "nbest_texts": ["I have been working in Da Nang for five years"],
        "decode_agreement": 1.0,
        "provider": "groq",
        "model": "whisper-large-v3-turbo",
        "decode_profile": "test",
        "latency_ms": 12.0,
    }


@pytest.mark.parametrize("asr_confidence", [0.1, 0.5, 0.9])
def test_real_provider_confidence_never_creates_pronunciation_band(monkeypatch, asr_confidence):
    monkeypatch.setattr(settings, "stt_provider", "groq")
    monkeypatch.setattr(settings, "groq_api_key", "configured")
    monkeypatch.setattr(settings, "llm_provider", "mock")
    with patch("app.modules.speaking.assessment.engine.stt_service.transcribe",
               return_value=_stt_payload(asr_confidence)), \
         patch("app.modules.speaking.assessment.engine.probe_audio_duration", return_value=2.7), \
         patch("app.modules.speaking.assessment.engine.budget.record"):
        result = grade_speaking("dummy.webm", "Where do you work?", "PART 1")

    assert result["criteria"]["pronunciation"]["band"] is None
    assert result["criteria"]["pronunciation"]["status"] != "scored"
    assert result["pronun"]["band"] is None
    assert result["pronun"]["band_source"] == "unavailable_no_validated_pronunciation_model"
    assert result["overall"] is None
    assert result["status"] == "partial"
    assert result["assessment_meta"]["calibration_version"] == "uncalibrated"


def test_mock_session_never_averages_turn_bands_or_defaults_6_5(monkeypatch):
    monkeypatch.setattr(settings, "llm_provider", "mock")
    monkeypatch.setattr(settings, "calibration_version", "uncalibrated")
    legacy_turn = {  # old payload with an untrusted pronunciation band source
        "schema_version": "speaking-v3", "status": "partial", "transcript": "I like parks",
        "overall": None,
        "pronun": {"status": "scored", "band": 6.5, "score": 6.5,
                   "band_source": "asr_confidence"},
        "fluency": {"status": "scored", "band": 6.5, "score": 6.5},
        "grammar": {"status": "scored", "band": 6.0, "score": 6.0},
        "vocab": {"status": "scored", "band": 6.5, "score": 6.5},
        "color_coded_transcript": [{"id": "w1", "word": "I"}, {"id": "w2", "word": "like"},
                                   {"id": "w3", "word": "parks"}],
        "uncertain_spans": [],
    }
    result = grade_mock_session([
        {"part": 1, "question_text": "Do you like parks?", "result": legacy_turn},
        {"part": 2, "question_text": "Describe a park", "result": legacy_turn},
        {"part": 3, "question_text": "Why are parks important?", "result": legacy_turn},
    ], tier="exam")
    pron = result["criteria"]["pronunciation"]
    assert pron["band"] is None
    assert pron["status"] != "scored"
    assert result["overall"] is None
    assert result["status"] == "partial"


def test_legacy_session_adapter_invalidates_untrusted_pronunciation_bands():
    for source in ("asr_confidence", "acoustic_confidence_and_prosody_calibration",
                   None, "unknown_legacy_source"):
        session = PracticeSessionOut.model_validate({
            "id": "history-2", "student_name": "Student", "score": 6.5,
            "created_at": datetime.now(timezone.utc),
            "result": {
                "status": "scored", "overall": 6.5, "transcript": "I go yesterday",
                "fluency": {"score": 6.5}, "vocab": {"score": 6.0},
                "grammar": {"score": 5.5},
                "pronun": {"score": 7.0, "band_source": source},
            },
        })
        pron = session.result["pronun"]
        assert pron["band"] is None
        assert pron["status"] != "scored"
        assert session.result["overall"] is None
        assert session.result["status"] == "partial"
        assert session.score is None


def test_legacy_turn_adapter_invalidates_untrusted_pronunciation_bands():
    turn = SpeakingTurnOut.model_validate({
        "id": "turn-1", "session_id": "s1", "part": 1, "sequence": 1,
        "question_text": "Q", "status": "completed", "score": 6.5,
        "created_at": datetime.now(timezone.utc),
        "result": {
            "status": "scored", "overall": 6.5, "transcript": "I go yesterday",
            "fluency": {"score": 6.5}, "vocab": {"score": 6.0},
            "grammar": {"score": 5.5},
            "pronun": {"score": 7.0, "band_source": "asr_confidence"},
        },
    })
    assert turn.result["pronun"]["band"] is None
    assert turn.result["overall"] is None


def test_pronunciation_band_source_policy_rejects_untrusted_sources():
    from app.modules.speaking.pronunciation.policy import is_trusted_pronunciation_band_source

    assert is_trusted_pronunciation_band_source("asr_confidence") is False
    assert is_trusted_pronunciation_band_source("llm_only_pending_alignment") is False
    assert is_trusted_pronunciation_band_source(
        "acoustic_confidence_and_prosody_calibration") is False
    assert is_trusted_pronunciation_band_source(None) is False
