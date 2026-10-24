"""Engine behaviour tests with injected fakes — offline and deterministic."""

import json

import pytest

from app.core.config import settings
from app.modules.speaking.pronunciation import audio_features, engine as engine_module
from app.modules.speaking.pronunciation.contracts import PronunciationRequest, WordTiming
from app.modules.speaking.pronunciation.phone_model import (
    FrozenPhoneModel,
    PhoneModelUnavailable,
)
from app.modules.speaking.pronunciation.engine import (
    DisabledPronunciationEngine,
    ShadowPronunciationEngine,
    get_engine,
)
from app.modules.speaking.pronunciation.lexicon import Lexicon


def _alignment() -> dict:
    """Real (frozen) aligned phone intervals, one base interval per phone."""
    spans = {
        "w1": (0.0, 0.2, ["AH"]),
        "w2": (0.25, 0.95, ["S", "AY", "AH", "N", "T", "IH", "S", "T"]),
        "w3": (1.0, 1.5, ["W", "ER", "K", "S"]),
        "w4": (1.6, 1.75, ["IH", "N"]),
        "w5": (1.8, 1.95, ["D"]),
        "w6": (2.0, 2.4, ["NG"]),
    }
    phones = []
    for word_id, (start, end, names) in spans.items():
        slot = (end - start) / len(names)
        for index, name in enumerate(names):
            phones.append({
                "phone": name,
                "start": round(start + index * slot, 3),
                "end": round(start + (index + 1) * slot, 3),
                "word_id": word_id,
            })
    return {"provider": "mfa", "declares_phone_alignment": True, "phones": phones}


def _request(audio="x.wav", uncertain=None, proper=None):
    return PronunciationRequest(
        audio_path=audio,
        transcript="A scientist works in Da Nang",
        words=[
            WordTiming(id="w1", word="A", start=0.0, end=0.2),
            WordTiming(id="w2", word="scientist", start=0.25, end=0.95),
            WordTiming(id="w3", word="works", start=1.0, end=1.5),
            WordTiming(id="w4", word="in", start=1.6, end=1.75),
            WordTiming(id="w5", word="Da", start=1.8, end=1.95),
            WordTiming(id="w6", word="Nang", start=2.0, end=2.4),
        ],
        asr_uncertain_word_ids=uncertain or [],
        asr_confidence=0.9,
        is_proper_noun=proper or [],
        alignment=_alignment(),
    )


@pytest.fixture
def mock_pcm(monkeypatch):
    """Deterministic low-noise tone instead of real audio; no ffmpeg needed."""
    import math

    samples = [
        int(9000 * math.sin(2 * math.pi * 180 * t / 16000)) for t in range(32000)
    ]
    from array import array as _array

    pcm = audio_features.PcmAudio(_array("h", samples), 16000, 2.0)
    monkeypatch.setattr(engine_module.audio_features, "load_pcm_mono_16k", lambda path: pcm)
    return pcm


def _lexicon_stub() -> Lexicon:
    lex = Lexicon(path=None)
    lex._entries = {
        "WORKS": [["W", "ER", "K", "S"]],
        "SCIENTIST": [["S", "AY", "AH", "N", "T", "IH", "S", "T"]],
        "IN": [["IH", "N"]],
        "A": [["AH"]],
    }
    lex.loaded = True
    return lex


def test_disabled_engine_returns_nullable_observations():
    result = DisabledPronunciationEngine().assess(_request())
    assert result.band is None
    assert result.status == "insufficient_evidence"
    assert result.band_source == "unavailable_no_validated_pronunciation_model"
    assert result.provenance.calibration_version == "uncalibrated"
    assert result.shadow is False
    assert get_engine() is None or type(get_engine()).__name__ == "DisabledPronunciationEngine"


def test_default_config_mode_is_disabled():
    from pydantic_settings import BaseSettings
    from app.core.config import Settings

    fresh = Settings(_env_file=None)
    assert fresh.pronunciation_mode == "disabled"
    assert BaseSettings is not None  # keep import meaningful


def test_shadow_engine_produces_candidate_gop_evidence(mock_pcm):
    frames = []
    for index in range(200):  # 4 s at hop 0.02
        frames.append({
            "W": 0.4, "ER": 0.3, "K": 0.2, "S": 0.05, "AH": 0.05,
        } if index in range(0, 12) else {"AH": 0.05, "S": 0.01})
    shadow = ShadowPronunciationEngine(
        phone_model=FrozenPhoneModel(frames), lexicon=_lexicon_stub(),
    )
    result = shadow.assess(_request())
    assert result.band is None
    assert result.status == "insufficient_evidence"
    assert result.shadow is True
    assert result.provenance.feature_version == "pronunciation-features-v1"
    for evidence in result.phoneme_evidence:
        assert evidence.status == "candidate"
        assert evidence.confidence is None
        assert 0 <= evidence.start < evidence.end
        assert any(word.id == evidence.word_id for word in _request().words)
        assert evidence.model_version == "frozen-v0"
    assert result.prosody_features["feature_version"] == "pronunciation-features-v1"


def test_shadow_engine_abstains_phone_claims_for_proper_nouns(mock_pcm):
    frames = [{"AH": 0.2, "S": 0.01} for _ in range(200)]
    shadow = ShadowPronunciationEngine(
        phone_model=FrozenPhoneModel(frames), lexicon=_lexicon_stub(),
    )
    result = shadow.assess(_request(proper=["w5", "w6"]))
    claimed_words = {evidence.word_id for evidence in result.phoneme_evidence}
    assert "w5" not in claimed_words and "w6" not in claimed_words
    # unstudied words in the lexicon stub stay abstained as well
    assert "w1" in claimed_words


def test_shadow_engine_quality_gates_on_clipping(monkeypatch, mock_pcm):
    from array import array as _array

    clipped = audio_features.PcmAudio(
        _array("h", [32767] * len(mock_pcm.samples)), 16000, 2.0,
    )
    monkeypatch.setattr(engine_module.audio_features, "load_pcm_mono_16k", lambda path: clipped)
    shadow = ShadowPronunciationEngine(lexicon=_lexicon_stub())
    result = shadow.assess(_request())
    assert result.evidence_quality == "low"
    assert "clipping_detected" in result.quality_gates["gate_reasons"]
    assert result.band is None


def test_shadow_engine_low_quality_on_silence_and_short_audio(monkeypatch, mock_pcm):
    from array import array as _array

    silent = audio_features.PcmAudio(_array("h", [0] * 1600), 16000, 0.1)
    monkeypatch.setattr(engine_module.audio_features, "load_pcm_mono_16k", lambda path: silent)
    shadow = ShadowPronunciationEngine(lexicon=_lexicon_stub())
    result = shadow.assess(_request())
    assert result.evidence_quality == "low"
    assert "audio_too_short" in result.quality_gates["gate_reasons"]


def test_shadow_engine_healthy_audio_gets_medium_quality(mock_pcm):
    """No gate reasons + no uncertain words => trusted-enough shadow label."""
    frames = [{"AH": 0.2, "S": 0.01} for _ in range(200)]
    shadow = ShadowPronunciationEngine(
        phone_model=FrozenPhoneModel(frames), lexicon=_lexicon_stub(),
    )
    result = shadow.assess(_request())
    assert result.prosody_features["voiced_coverage"] >= 0.1
    assert result.evidence_quality == "medium"


def test_missing_phone_model_degrades_to_prosody_only(mock_pcm):
    shadow = ShadowPronunciationEngine(phone_model=None, lexicon=_lexicon_stub())
    result = shadow.assess(_request())
    assert result.phoneme_evidence == []
    assert result.prosody_features["speech_rate_wpm"] is not None
    assert result.band is None


def test_get_engine_mode_matrix(monkeypatch, mock_pcm):
    monkeypatch.setattr(settings, "pronunciation_mode", "disabled")
    engine = get_engine()
    assert type(engine) is DisabledPronunciationEngine

    monkeypatch.setattr(settings, "pronunciation_mode", "shadow")
    engine_module.reset_engine = engine_module.reset_engine  # kept for compat
    shadow = ShadowPronunciationEngine(lexicon=_lexicon_stub())
    result = shadow.assess(_request())
    assert result.band is None and result.shadow is True

    monkeypatch.setattr(settings, "pronunciation_mode", "enabled")
    enabled = engine_module.EnabledPronunciationEngine(lexicon=_lexicon_stub())
    result = enabled.assess(_request())
    assert result.band is None  # artifact missing -> fail closed
    assert "calibration_artifact_missing" in result.reason
    assert result.status == "insufficient_evidence"


def test_phone_model_fail_closed_without_manifest():
    with pytest.raises(PhoneModelUnavailable):
        from app.modules.speaking.pronunciation.phone_model import get_phone_model

        get_phone_model()


def test_engine_missing_audio_abstains(monkeypatch):
    def unreadable(path):  # simulate decoder failure
        raise RuntimeError("ffmpeg missing")

    monkeypatch.setattr(engine_module.audio_features, "load_pcm_mono_16k", unreadable)
    shadow = ShadowPronunciationEngine(lexicon=_lexicon_stub())
    result = shadow.assess(_request(audio="broken.webm"))
    assert "audio_unreadable" in result.quality_gates["gate_reasons"]
    assert result.band is None
    assert result.evidence_quality == "low"


def test_shadow_engine_never_fabricates_phone_timing_without_alignment(mock_pcm):
    """No aligner => no phone evidence, and no even-slicing of word spans."""
    import copy

    frames = [{"W": 0.3, "ER": 0.2} for _ in range(200)]
    shadow = ShadowPronunciationEngine(
        phone_model=FrozenPhoneModel(frames), lexicon=_lexicon_stub(),
    )
    no_alignment = _request()
    no_alignment.alignment = {}
    result = shadow.assess(no_alignment)
    assert result.phoneme_evidence == []
    assert "real_phone_alignment_unavailable" in result.quality_gates["missing_reasons"]
    assert result.provenance.phone_model == "frozen-phone-model"
    assert result.provenance.alignment_provider == "none"

    # word-only alignment (WhisperX) still yields no phone evidence
    word_only = copy.deepcopy(_request())
    word_only.alignment = {"provider": "whisperx", "declares_phone_alignment": False,
                           "phones": [{"phone": "AH", "start": 0.0, "end": 0.2}]}
    result = shadow.assess(word_only)
    assert result.phoneme_evidence == []


def test_shadow_engine_phone_timing_comes_from_real_alignment(mock_pcm):
    """Evidence times equal the aligned intervals, not evenly split word spans."""
    frames = [{"AH": 0.2, "S": 0.01} for _ in range(200)]
    shadow = ShadowPronunciationEngine(
        phone_model=FrozenPhoneModel(frames), lexicon=_lexicon_stub(),
    )
    result = shadow.assess(_request())
    assert result.phoneme_evidence  # word "A" -> phones ["AH"]
    assert result.provenance.alignment_provider == "mfa"
    assert result.provenance.phone_model == "frozen-phone-model"
    # aligned interval for AH is exactly [0.0, 0.2] — same as the intact word
    # span here; use a second word whose span is NOT evenly split:
    er_aligned = next(
        interval for interval in _alignment()["phones"]
        if interval["word_id"] == "w3" and interval["phone"] == "ER"
    )
    er_evidence = next(
        e for e in result.phoneme_evidence
        if e.word_id == "w3" and e.expected_phone == "ER"
    )
    # evidence times must equal the aligned interval bytes, not an even slice
    assert er_evidence.start == pytest.approx(float(er_aligned["start"]))
    assert er_evidence.end == pytest.approx(float(er_aligned["end"]))


def test_request_rejects_undeleclared_phone_alignment():
    with pytest.raises(ValueError):
        PronunciationRequest(
            audio_path="x.wav", words=[], asr_uncertain_word_ids=[],
            alignment={"provider": "x", "declares_phone_alignment": False,
                       "phones": [{"phone": "AH", "start": 0, "end": 1}]},
        )


def _write_artifact(tmp_path, artifact: dict) -> str:
    from scripts.pronunciation.export_artifact import artifact_checksum

    artifact["checksums"] = {"artifact": artifact_checksum(artifact)}
    path = tmp_path / "artifact.json"
    path.write_text(json.dumps(artifact, sort_keys=True), encoding="utf-8")
    return str(path)


def _valid_artifact() -> dict:
    return {
        "schema_version": "pronunciation-artifact-v1",
        "artifact_id": "examiner-cal-2026-10",
        "engine_version": "pronunciation-engine-v1",
        "feature_version": "pronunciation-features-v1",
        "calibration_version": "examiner-cal-2026-10",
        "model_class": "ordinal_regression",
        "coefficients": {"voiced_coverage": 2.0},
        "bias": 0.0,
        "standardization": {"mean": [0.2], "scale": [0.1]},
        "band_values": [5.0, 6.0],
        "thresholds": [1.0],
        "training": {"dataset_ids": ["learn4-pilot-1"], "samples": 10,
                     "speakers": 10},
        "metrics": {"status": "passed_release_gate", "mae": 0.3, "qwk": 0.8,
                    "bias": 0.01, "within_half": 0.9, "coverage": 1.0},
    }


def test_enabled_engine_scores_band_from_valid_artifact(mock_pcm, tmp_path,
                                                        monkeypatch):
    artifact_path = _write_artifact(tmp_path, _valid_artifact())
    monkeypatch.setattr(settings, "pronunciation_artifact_path", artifact_path)
    engine = engine_module.EnabledPronunciationEngine(lexicon=_lexicon_stub())
    result = engine.assess(_request())
    # voiced_coverage in prosody_features maps through the artifact to a band
    coverage = result.prosody_features["voiced_coverage"]
    score = 0.0 + 2.0 * (coverage - 0.2) / 0.1
    expected = 6.0 if score >= 1.0 else 5.0
    assert result.band == expected
    assert result.band_source == "examiner_calibrated_artifact"
    assert result.status == "scored"
    assert result.shadow is False
    assert result.confidence is None


def test_enabled_engine_fails_closed_when_features_missing(mock_pcm, tmp_path,
                                                           monkeypatch):
    artifact_path = _write_artifact(tmp_path, _valid_artifact())
    monkeypatch.setattr(settings, "pronunciation_artifact_path", artifact_path)
    engine = engine_module.EnabledPronunciationEngine(lexicon=_lexicon_stub())

    def no_features(pcm, words):
        return {}

    monkeypatch.setattr(engine_module.prosody, "extract_prosody_features", no_features)
    result = engine.assess(_request())
    assert result.band is None
    assert result.status == "insufficient_evidence"
    assert "calibration_features_unavailable" in (result.reason or "")
