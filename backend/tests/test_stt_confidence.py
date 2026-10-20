"""Phase 1 regression: Whisper decoding profile, missing-metric confidence,
uncertain spans, and conditional second-pass decoding."""

import shutil
import sys
import types
import wave

import pytest

from app.integrations.stt import recognition as stt_service
from app.integrations.stt.recognition import (
    _build_uncertain_spans,
    _decode_agreement,
    _recognition_signals,
    mean_avg_logprob,
)


def _w(word, start, end, prob):
    return {"word": word, "start": start, "end": end, "probability": prob}


class _FakeWord:
    def __init__(self, word, start, end, probability):
        self.word = word
        self.start = start
        self.end = end
        self.probability = probability


class _FakeSeg:
    def __init__(self, text, avg_logprob, no_speech_prob, compression_ratio, words):
        self.text = text
        self.start = 0.0
        self.end = 2.0
        self.avg_logprob = avg_logprob
        self.no_speech_prob = no_speech_prob
        self.compression_ratio = compression_ratio
        self.words = words


class _FakeModel:
    def __init__(self, passes):
        self.passes = passes
        self.calls = []

    def transcribe(self, audio_path, **kwargs):
        self.calls.append({"audio_path": audio_path, **kwargs})
        segs = self.passes[min(len(self.calls) - 1, len(self.passes) - 1)]
        return (s for s in segs), None


def _patch_selfhost(monkeypatch, model):
    monkeypatch.setattr(stt_service, "_load_model", lambda: model)
    monkeypatch.setattr(stt_service, "normalize_audio_to_wav", lambda p: p)


def test_recognition_signals_missing_metrics_penalized_not_perfect():
    # Groq-style segments without avg_logprob must NOT yield confidence 1.0.
    segments = [{"start": 0.0, "end": 1.0}]
    conf, hallu, missing = _recognition_signals(segments)
    assert conf < 0.6
    assert set(missing) == {"avg_logprob", "no_speech_prob", "compression_ratio"}


def test_recognition_signals_full_metrics_confident():
    segments = [{"avg_logprob": -0.05, "no_speech_prob": 0.01, "compression_ratio": 1.0}]
    conf, hallu, missing = _recognition_signals(segments)
    assert conf > 0.85
    assert missing == []
    assert hallu == 0.0


def test_recognition_signals_empty_segments():
    conf, hallu, missing = _recognition_signals([])
    assert conf < 0.6  # penalized, never confident on zero evidence
    assert missing != []


def test_mean_avg_logprob_missing_returns_none():
    assert mean_avg_logprob([]) is None
    assert mean_avg_logprob([{"no_speech_prob": 0.1}]) is None
    assert mean_avg_logprob([{"avg_logprob": -0.2}, {"no_speech_prob": 0.1}]) == pytest.approx(-0.2)


def test_uncertain_spans_schema_and_reasons():
    words = [
        _w("hello", 0.0, 0.4, 0.97),
        _w("mystery", 0.5, 0.9, 0.50),   # low_alignment_confidence
        _w("ghost", 1.0, 1.4, None),      # missing_word_confidence
        _w("supercalifragilistic", 1.5, 3.5, 0.99),  # abnormal_word_duration
    ]
    spans = _build_uncertain_spans(words)
    by_reason = {}
    for s in spans:
        assert set(("word", "start", "end", "confidence", "reason")) <= set(s)
        assert isinstance(s["confidence"], (int, float))
        by_reason.setdefault(s["reason"], []).append(s["word"])
    assert "mystery" in by_reason["low_alignment_confidence"]
    assert "ghost" in by_reason["missing_word_confidence"]
    assert "supercalifragilistic" in by_reason["abnormal_word_duration"]


def test_uncertain_spans_repetition_run():
    words = [_w("no", i * 0.3, i * 0.3 + 0.2, 0.95) for i in range(5)]
    spans = _build_uncertain_spans(words)
    assert any(s["reason"] == "repeated_sequence_needs_review" for s in spans)


def test_common_words_repeated_across_answer_are_not_flagged():
    words = [
        _w("I", 0.0, 0.1, 0.96), _w("like", 0.2, 0.4, 0.96),
        _w("the", 0.5, 0.6, 0.96), _w("park", 0.7, 0.9, 0.96),
        _w("and", 1.0, 1.1, 0.96), _w("I", 1.2, 1.3, 0.96),
        _w("like", 1.4, 1.6, 0.96), _w("the", 1.7, 1.8, 0.96),
        _w("trees", 1.9, 2.1, 0.96), _w("and", 2.2, 2.3, 0.96),
        _w("I", 2.4, 2.5, 0.96), _w("like", 2.6, 2.8, 0.96),
    ]
    assert _build_uncertain_spans(words) == []


def test_decode_agreement():
    assert _decode_agreement("hello world", "hello world") == 1.0
    assert _decode_agreement("", "") == 1.0
    assert _decode_agreement("hello", "") == 0.0
    assert _decode_agreement("a b c d", "w x y z") < 0.5


def test_selfhost_uses_fixed_ielts_english_profile(monkeypatch):
    segs = [_FakeSeg("hello world", -0.05, 0.01, 1.0,
                     [_FakeWord("hello", 0.0, 0.4, 0.97),
                      _FakeWord("world", 0.5, 0.9, 0.96)])]
    model = _FakeModel([segs])
    _patch_selfhost(monkeypatch, model)
    out = stt_service.transcribe_selfhost("dummy.webm")
    assert out["text"] == "hello world"
    assert len(model.calls) == 1  # confident: no second pass
    kw = model.calls[0]
    assert kw["language"] == "en"
    assert kw["task"] == "transcribe"
    assert kw["vad_filter"] is True
    assert kw["condition_on_previous_text"] is False
    assert kw["no_speech_threshold"] == 0.6
    assert kw["word_timestamps"] is True
    assert out["missing_metrics"] == []
    assert out["decode_agreement"] == 1.0
    assert out["uncertain_spans"] == out["low_conf_spans"]


def test_selfhost_second_pass_on_low_confidence(monkeypatch):
    monkeypatch.setattr(stt_service.settings, "stt_latency_profile", "balanced")
    low = [_FakeSeg("alpha beta gamma", -1.5, 0.2, 1.0,
                    [_FakeWord("alpha", 0.0, 0.4, 0.5),
                     _FakeWord("beta", 0.5, 0.9, 0.4),
                     _FakeWord("gamma", 1.0, 1.4, 0.6)])]
    different = [_FakeSeg("completely different words here", -0.4, 0.1, 1.0,
                          [_FakeWord("completely", 0.0, 0.5, 0.8)])]
    model = _FakeModel([low, different])
    _patch_selfhost(monkeypatch, model)
    out = stt_service.transcribe_selfhost("dummy.webm")
    assert len(model.calls) == 2  # doubtful first pass -> conditional re-decode
    assert len(out["nbest_texts"]) == 2
    assert out["decode_agreement"] < 0.70
    assert out["asr_confidence"] <= 0.50
    assert out["hallucination_risk"] >= 0.50
    assert out["text"] == "alpha beta gamma"  # first hypothesis kept, flagged


def test_selfhost_fast_profile_uses_one_smaller_beam_decode(monkeypatch):
    low = [_FakeSeg("alpha beta", -1.5, 0.2, 1.0, [
        _FakeWord("alpha", 0.0, 0.4, 0.5),
        _FakeWord("beta", 0.5, 0.9, 0.4),
    ])]
    model = _FakeModel([low])
    _patch_selfhost(monkeypatch, model)
    monkeypatch.setattr(stt_service.settings, "stt_latency_profile", "fast")
    monkeypatch.setattr(stt_service.settings, "whisper_fast_beam_size", 3)
    out = stt_service.transcribe_selfhost("dummy.webm")
    assert len(model.calls) == 1
    assert model.calls[0]["beam_size"] == 3
    assert out["decode_passes"] == 1
    assert out["latency_profile"] == "fast"


def test_groq_missing_metrics_stay_none_and_penalized(monkeypatch):
    class _Res:
        def model_dump(self):
            return {
                "text": "hello",
                "segments": [{
                    "start": 0.0, "end": 0.5,
                    "words": [{"word": "hello", "start": 0.0, "end": 0.5}],
                }],
            }

    fake_groq = types.ModuleType("groq")
    fake_groq.Groq = lambda **kwargs: types.SimpleNamespace(
        audio=types.SimpleNamespace(
            transcriptions=types.SimpleNamespace(create=lambda **kw: _Res())
        ),
        close=lambda: None,
    )
    monkeypatch.setitem(sys.modules, "groq", fake_groq)
    import os
    import tempfile

    fd, path = tempfile.mkstemp(suffix=".webm")
    os.close(fd)
    try:
        out = stt_service.transcribe_groq(path)
    finally:
        os.remove(path)
    assert out["segments"][0]["avg_logprob"] is None
    assert out["words"][0]["probability"] is None
    assert "avg_logprob" in out["missing_metrics"]
    assert out["asr_confidence"] < 0.6
    assert any(s["reason"] == "missing_word_confidence" for s in out["uncertain_spans"])


def test_normalize_audio_to_wav_mono_16k(tmp_path):
    if shutil.which("ffmpeg") is None:
        pytest.skip("ffmpeg not available")
    from app.integrations.audio.processor import normalize_audio_to_wav

    src = tmp_path / "src.wav"
    import array

    stereo = array.array("h")
    for t in range(4410):
        v = int(8000 * (t % 100) / 100)
        stereo.append(v)
        stereo.append(-v)
    with wave.open(str(src), "wb") as wf:
        wf.setnchannels(2)
        wf.setsampwidth(2)
        wf.setframerate(44100)
        wf.writeframes(stereo.tobytes())
    out = normalize_audio_to_wav(src, tmp_path / "norm.wav")
    with wave.open(out, "rb") as wf:
        assert wf.getnchannels() == 1
        assert wf.getframerate() == 16000
        assert wf.getsampwidth() == 2


def test_model_is_loaded_once_across_threads(monkeypatch):
    from concurrent.futures import ThreadPoolExecutor
    import threading

    created = []
    start = threading.Barrier(4)
    model = object()

    def constructor(*args, **kwargs):
        assert stt_service._model_lock.locked()
        created.append(kwargs)
        return model

    monkeypatch.setattr(stt_service, "_model", None)
    monkeypatch.setattr(stt_service, "_model_error", None)
    monkeypatch.setitem(sys.modules, "faster_whisper", types.SimpleNamespace(WhisperModel=constructor))

    def load():
        start.wait(timeout=5)
        return stt_service._load_model()

    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(lambda _: load(), range(4)))
    assert all(result is model for result in results)
    assert len(created) == 1
    assert created[0]["num_workers"] == 1
    assert created[0]["cpu_threads"] == stt_service.settings.whisper_cpu_threads


def test_model_import_failure_is_recorded(monkeypatch):
    monkeypatch.setattr(stt_service, "_model", None)
    monkeypatch.setattr(stt_service, "_model_error", None)
    monkeypatch.setitem(sys.modules, "faster_whisper", None)
    with pytest.raises(ModuleNotFoundError):
        stt_service._load_model()
    assert stt_service._model_error == "ModuleNotFoundError"


@pytest.mark.parametrize(
    "provider,preload,error,key,loaded,ready",
    [
        ("selfhost", True, None, "", False, False),
        ("selfhost", False, None, "", False, True),
        ("selfhost", True, None, "", True, True),
        ("selfhost", False, "ImportError", "", False, False),
        ("auto", True, "ImportError", "configured", False, True),
        ("auto", True, "ImportError", "", False, False),
        ("groq", False, "ImportError", "configured", False, True),
        ("groq", False, None, "", False, False),
        ("mock", False, None, "", False, True),
    ],
)
def test_readiness_reflects_preload_and_fallback(monkeypatch, provider, preload, error, key, loaded, ready):
    monkeypatch.setattr(stt_service.settings, "stt_provider", provider)
    monkeypatch.setattr(stt_service.settings, "whisper_preload", preload)
    monkeypatch.setattr(stt_service.settings, "groq_api_key", key)
    monkeypatch.setattr(stt_service, "_model", object() if loaded else None)
    monkeypatch.setattr(stt_service, "_model_error", error)
    state = stt_service.readiness()
    assert state["ready"] is ready
    assert state["model_loaded"] is loaded
    assert state["fallback_available"] is (provider == "auto" and bool(key))


@pytest.mark.parametrize("provider,key,raises", [
    ("auto", "configured", False), ("auto", "", True), ("selfhost", "configured", True),
])
def test_preload_failure_only_tolerated_with_auto_fallback(monkeypatch, provider, key, raises):
    monkeypatch.setattr(stt_service.settings, "stt_provider", provider)
    monkeypatch.setattr(stt_service.settings, "groq_api_key", key)

    def fail():
        raise RuntimeError("model unavailable")

    monkeypatch.setattr(stt_service, "_load_model", fail)
    if raises:
        with pytest.raises(RuntimeError):
            stt_service.preload()
    else:
        stt_service.preload()


def test_busy_local_model_falls_back_without_loading(monkeypatch):
    monkeypatch.setattr(stt_service.settings, "stt_provider", "auto")
    monkeypatch.setattr(stt_service.settings, "stt_local_wait_seconds", 0)
    monkeypatch.setattr(stt_service.settings, "groq_api_key", "configured")
    monkeypatch.setattr(stt_service, "transcribe_groq", lambda _: {"text": "fallback", "provider": "groq"})
    with stt_service._decode_lock:
        result = stt_service.transcribe("unused.wav")
    assert result["fallback_used"] is True
    assert result["fallback_reason"] == "TimeoutError"
    assert result["provider"] == "groq"
    assert result["latency_ms"] >= 0


def test_busy_selfhost_does_not_call_remote(monkeypatch):
    monkeypatch.setattr(stt_service.settings, "stt_provider", "selfhost")
    monkeypatch.setattr(stt_service.settings, "stt_local_wait_seconds", 0)
    with stt_service._decode_lock, pytest.raises(TimeoutError, match="busy"):
        stt_service.transcribe("unused.wav")


def test_lazy_decode_failure_releases_lock_and_temporary_audio(monkeypatch, tmp_path):
    original = tmp_path / "original.webm"
    normalized = tmp_path / "normalized.wav"
    original.write_bytes(b"original")
    normalized.write_bytes(b"normalized")

    def transcribe(*args, **kwargs):
        def segments():
            assert stt_service._decode_lock.locked()
            raise RuntimeError("lazy decoder failure")
            yield  # Model starts inference only when its iterator is consumed.
        return segments(), None

    monkeypatch.setattr(stt_service, "_load_model", lambda: types.SimpleNamespace(transcribe=transcribe))
    monkeypatch.setattr(stt_service, "normalize_audio_to_wav", lambda _: str(normalized))
    with pytest.raises(RuntimeError, match="lazy decoder"):
        stt_service.transcribe_selfhost(original)
    assert not stt_service._decode_lock.locked()
    assert not normalized.exists()
    assert original.read_bytes() == b"original"


def test_groq_timeout_and_client_closed_on_failure(monkeypatch, tmp_path):
    created, closed = [], []

    def fail(**kwargs):
        raise TimeoutError("remote timeout")

    def client(**kwargs):
        created.append(kwargs)
        return types.SimpleNamespace(
            audio=types.SimpleNamespace(transcriptions=types.SimpleNamespace(create=fail)),
            close=lambda: closed.append(True),
        )

    monkeypatch.setitem(sys.modules, "groq", types.SimpleNamespace(Groq=client))
    source = tmp_path / "source.wav"
    source.write_bytes(b"audio")
    with pytest.raises(TimeoutError):
        stt_service.transcribe_groq(source)
    assert created[0]["timeout"] == stt_service.settings.stt_remote_timeout_seconds
    assert created[0]["max_retries"] == 0
    assert closed == [True]


def test_normalization_timeout_cleans_temporary_output(monkeypatch, tmp_path):
    import subprocess
    from pathlib import Path
    from app.integrations.audio import processor

    output_paths = []

    def timeout(cmd, **kwargs):
        assert kwargs["timeout"] == processor.settings.audio_process_timeout_seconds
        output_paths.append(Path(cmd[-1]))
        raise subprocess.TimeoutExpired(cmd, kwargs["timeout"])

    monkeypatch.setattr(processor.subprocess, "run", timeout)
    source = tmp_path / "source.webm"
    source.write_bytes(b"original")
    with pytest.raises(subprocess.TimeoutExpired):
        processor.normalize_audio_to_wav(source)
    assert len(output_paths) == 1
    assert not output_paths[0].exists()
    assert source.read_bytes() == b"original"


def test_normalization_rejects_overwriting_original(tmp_path):
    from app.integrations.audio.processor import normalize_audio_to_wav

    source = tmp_path / "source.wav"
    source.write_bytes(b"original")
    with pytest.raises(ValueError, match="differ"):
        normalize_audio_to_wav(source, source)
    assert source.read_bytes() == b"original"


@pytest.mark.parametrize("field,value", [
    ("stt_provider", "typo"), ("whisper_cpu_threads", 0),
    ("stt_local_wait_seconds", -1), ("stt_remote_timeout_seconds", 0),
    ("audio_process_timeout_seconds", float("nan")),
])
def test_invalid_runtime_settings_fail_fast(field, value):
    from pydantic import ValidationError
    from app.core.config import Settings

    with pytest.raises(ValidationError):
        Settings(_env_file=None, **{field: value})


def test_names_are_passed_to_whisper_and_sparse_uncertainty_triggers_redecode(monkeypatch):
    monkeypatch.setattr(stt_service.settings, "stt_latency_profile", "balanced")
    tokens = ['I', 'live', 'in', 'Ghana', 'and', 'I', 'love', 'my', 'hometown']
    first = [_FakeSeg(' '.join(tokens), -.05, .01, 1.0, [
        _FakeWord(token, i*.3, i*.3+.2, .5 if token == 'Ghana' else .97)
        for i, token in enumerate(tokens)
    ])]
    second_tokens = ['I', 'study', 'in', 'Da', 'Nang', 'and', 'I', 'love', 'my', 'hometown']
    second = [_FakeSeg(' '.join(second_tokens), -.05, .01, 1.0, [])]
    model = _FakeModel([first, second])
    _patch_selfhost(monkeypatch, model)
    result = stt_service.transcribe_selfhost('dummy.webm', keyterms=['Đà Nẵng', 'Quảng Trị'])
    assert len(model.calls) == 2
    assert all(call['hotwords'] == 'Đà Nẵng, Quảng Trị' for call in model.calls)
    assert result['text'] == ' '.join(tokens)
    assert any(span['word'] == 'live' and span['reason'] == 'decode_disagreement'
               for span in result['uncertain_spans'])
    assert result['nbest_texts'][1] == ' '.join(second_tokens)
