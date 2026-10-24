"""P7 shadow wiring: readiness probe + worker flow stay bandless offline."""

from app.core.config import settings
from app.core import bootstrap
from app.modules.speaking.pronunciation import engine as engine_module


def test_readiness_disabled_is_healthy(monkeypatch):
    monkeypatch.setattr(settings, "pronunciation_mode", "disabled")
    state = engine_module.capability_readiness()
    assert state == {"mode": "disabled", "ready": True, "state": "disabled"}


def test_bootstrap_readiness_has_informational_pronunciation_disabled(monkeypatch):
    monkeypatch.setattr(settings, "pronunciation_mode", "disabled")
    bootstrap_state = bootstrap.readiness()
    assert bootstrap_state["pronunciation"]["mode"] == "disabled"
    assert bootstrap_state["pronunciation"]["ready"] is True
    # pronunciation never gates the core readiness decision
    for key in ("stt", "llm", "queue"):
        assert key in bootstrap_state


def test_readiness_shadow_degrades_without_phone_model(monkeypatch):
    monkeypatch.setattr(settings, "pronunciation_mode", "shadow")
    monkeypatch.setattr(settings, "pronunciation_phone_model", "none")
    monkeypatch.setattr(settings, "pronunciation_phone_model_manifest", None)
    state = engine_module.capability_readiness()
    assert state["ready"] is True
    assert state["state"] == "degraded_prosody_only"


def test_readiness_enabled_fails_closed_without_artifact(monkeypatch):
    monkeypatch.setattr(settings, "pronunciation_mode", "enabled")
    monkeypatch.setattr(settings, "pronunciation_artifact_path", None)
    state = engine_module.capability_readiness()
    assert state["ready"] is False
    assert state["state"] == "artifact_missing_or_invalid"
    assert state["failure_reason"] == "calibration_artifact_missing"


def test_shadow_assessment_flow_stays_bandless(monkeypatch):
    import math
    from array import array

    from app.modules.speaking.pronunciation import audio_features
    import app.modules.speaking.pronunciation.engine as engine_module
    from app.modules.speaking.pronunciation.contracts import PronunciationRequest
    from app.modules.speaking.pronunciation.engine import ShadowPronunciationEngine

    samples = [int(9000 * math.sin(2 * math.pi * 180 * t / 16000)) for t in range(32000)]
    pcm = audio_features.PcmAudio(array("h", samples), 16000, 2.0)
    monkeypatch.setattr(
        engine_module.audio_features, "load_pcm_mono_16k", lambda path: pcm,
    )
    shadow = ShadowPronunciationEngine()
    request = PronunciationRequest(
        audio_path="x.wav", transcript="a calm works",
        words=[], asr_uncertain_word_ids=[], asr_confidence=0.9,
    )
    result = shadow.assess(request)
    assert result.band is None
    assert result.shadow is True
    assert "no_word_timings" in result.quality_gates["missing_reasons"]
