"""Phase 2 regression: audio-grounded pronunciation evidence layer."""

import wave

from app.modules.speaking.pronunciation.service import (
    analyze_prosody,
    analyze_waveform_energy,
    assess_pronunciation,
    decide_evidence_quality,
    filter_problem_words,
    intelligibility_proxy,
)


def _w(word, start, end):
    return {"word": word, "start": start, "end": end, "probability": 0.95}


def test_prosody_features_from_timestamps():
    words = [_w("a", 0.0, 0.3), _w("b", 0.4, 0.7), _w("c", 1.5, 1.8), _w("d", 1.9, 2.2)]
    feats = analyze_prosody(words, 2.2)
    assert feats["coverage"] == 1.0
    assert feats["speech_rate_wpm"] == round(4 / 2.2 * 60, 1)
    assert feats["long_pauses"] == 0  # 0.8s gap is a pause but not "long"
    assert feats["pause_ratio"] > 0.0
    assert feats["rhythm_cv"] >= 0.0


def test_prosody_empty_or_missing_timing():
    assert analyze_prosody([], 0.0)["coverage"] == 0.0
    assert analyze_prosody([{"word": "x"}], 1.0)["coverage"] == 0.0


def test_filter_problem_words_drops_hallucinated_claims_and_relabels():
    claims = [
        {"heard": "ship", "intended": "sheep", "type": "pronun"},
        {"heard": "banana", "intended": "bandana", "type": "pronun"},  # not in transcript
        "world",
    ]
    uncertain = [{"word": "ship", "reason": "low_alignment_confidence"}]
    kept = filter_problem_words(claims, "I saw a ship in the world", uncertain)
    heard = [p["heard"] if isinstance(p, dict) else p for p in kept]
    assert "banana" not in heard  # LLM hallucination guard
    ship = next(p for p in kept if p["heard"] == "ship")
    assert ship["type"] == "asr_uncertain"  # recognizer doubted it
    world = next(p for p in kept if p["heard"] == "world")
    assert world["type"] == "pronun"


def test_intelligibility_proxy():
    intel = intelligibility_proxy("hello world foo", [], 0.0)
    assert intel["score"] == 1.0
    intel = intelligibility_proxy(
        "hello world foo", [{"word": "world", "reason": "low_alignment_confidence"}], 0.0
    )
    assert 0.0 < intel["score"] < 1.0
    assert intel["uncertain_word_ratio"] > 0.0


def test_decide_evidence_quality():
    assert decide_evidence_quality(0.5, False, 0.9, 1.0) == "low"
    assert decide_evidence_quality(0.9, True, 0.9, 1.0) == "low"
    assert decide_evidence_quality(0.7, False, 0.9, 1.0) == "medium"
    assert decide_evidence_quality(0.95, False, 0.95, 1.0) == "high"


def test_pronunciation_band_is_null_without_validated_engine():
    words = [_w("hello", 0.0, 0.4), _w("world", 0.5, 0.9)]
    out = assess_pronunciation(
        audio_path=None,
        transcript="hello world",
        words=words,
        uncertain_spans=[],
        asr_confidence=0.9,
        hallucination_risk=0.0,
        total_duration_s=1.0,
        llm_band=6.5,
        llm_problem_words=[{"heard": "world", "intended": "word", "type": "pronun"}],
    )
    assert out["band"] is None
    assert out["band_source"] == "unavailable_no_validated_pronunciation_model"
    assert out["phoneme_evidence"] == []  # no forced alignment yet
    assert out["confidence"] is None
    assert out["problem_words"] == []
    assert out["prosody_features"]["coverage"] == 1.0
    assert "stress_contrast" not in out["prosody_features"]


def test_pronunciation_feedback_distinguishes_asr_review_from_sound_errors():
    words = [_w("hello", 0.0, 0.4), _w("world", 1.6, 1.9)]
    result = assess_pronunciation(
        transcript="hello world", words=words,
        uncertain_spans=[{"word_id": "w2", "word": "world"}],
        total_duration_s=1.9, asr_confidence=0.8,
    )
    assert result["band"] is None
    assert "1/2" in result["feedback"]
    assert "1 khoảng nghỉ" in result["feedback"]
    assert "chưa xác nhận lỗi phát âm" in result["feedback"]
    assert result["next_action_vi"]
    assert result["phoneme_evidence"] == []


def test_pronunciation_feedback_does_not_invent_timing_when_missing():
    result = assess_pronunciation(transcript="hello world", words=[], total_duration_s=0)
    assert "chưa đủ" in result["feedback"].lower()
    assert result["next_action_vi"]
    assert result["band"] is None


def _valid_artifact(tmp_path):
    import json

    from scripts.pronunciation.export_artifact import artifact_checksum

    artifact = {
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
    artifact["checksums"] = {"artifact": artifact_checksum(artifact)}
    path = tmp_path / "artifact.json"
    path.write_text(json.dumps(artifact, sort_keys=True), encoding="utf-8")
    return str(path)


def test_facade_passes_scored_band_from_enabled_engine(monkeypatch, tmp_path):
    """Spec 4: enabled mode has a real runtime path artifact -> band -> result."""
    import math
    from array import array

    from app.modules.speaking.pronunciation import audio_features as audio_module
    from app.core.config import settings

    artifact_path = _valid_artifact(tmp_path)
    monkeypatch.setattr(settings, "pronunciation_mode", "enabled")
    monkeypatch.setattr(settings, "pronunciation_artifact_path", artifact_path)
    monkeypatch.setattr(settings, "pronunciation_aligner", "none")

    samples = [int(9000 * math.sin(2 * math.pi * 180 * t / 16000))
               for t in range(32000)]
    pcm = audio_module.PcmAudio(array("h", samples), 16000, 2.0)
    monkeypatch.setattr(audio_module, "load_pcm_mono_16k", lambda path: pcm)

    words = [_w("hello", 0.0, 0.4), _w("world", 0.5, 0.9)]
    out = assess_pronunciation(
        audio_path="storage/mock.webm",
        transcript="hello world",
        words=words,
        uncertain_spans=[],
        asr_confidence=0.9,
        hallucination_risk=0.0,
        total_duration_s=1.0,
    )
    expected = 6.0 if 2.0 * (out["prosody_features"]["voiced_coverage"] - 0.2) / 0.1 >= 1.0 else 5.0
    assert out["band"] == expected
    assert out["band_source"] == "examiner_calibrated_artifact"
    assert out["confidence"] is None
    assert out["reason"] is None
    # no aligner configured: no decode, and the alignment block stays honest
    assert out["alignment"]["provider"] == "none"


def _write_wav(path, samples, sr=16000):
    import array

    data = array.array("h", (max(-32768, min(32767, int(v))) for v in samples))
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(data.tobytes())


def test_waveform_energy_silence_vs_tone(tmp_path):
    silence = tmp_path / "sil.wav"
    tone = tmp_path / "tone.wav"
    _write_wav(silence, [0] * 16000)
    import math

    _write_wav(tone, [9000 * math.sin(2 * math.pi * 440 * t / 16000) for t in range(16000)])
    s = analyze_waveform_energy(str(silence))
    t = analyze_waveform_energy(str(tone))
    assert s["low_energy_ratio"] > 0.9
    assert t["low_energy_ratio"] < 0.2


def test_waveform_energy_unreadable_returns_empty(tmp_path):
    bad = tmp_path / "bad.webm"
    bad.write_bytes(b"not a wav file")
    assert analyze_waveform_energy(str(bad)) == {}
    assert analyze_waveform_energy(None) == {}
    assert analyze_waveform_energy("/nonexistent/file.wav") == {}
