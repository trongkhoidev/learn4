import httpx
import pytest

from app.integrations.stt import cloud
from app.integrations.stt import recognition


class FakeClient:
    def __init__(self, payload, captured, **kwargs):
        self.payload = payload
        self.captured = captured
        self.captured["client"] = kwargs

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return None

    def post(self, url, **kwargs):
        self.captured.update(url=url, request=kwargs)
        return httpx.Response(200, json=self.payload, request=httpx.Request("POST", url))


def test_deepgram_adapter_preserves_word_confidence_and_repeated_keyterms(monkeypatch, tmp_path):
    payload = {
        "metadata": {"duration": 1.1, "request_id": "dg-1"},
        "results": {"channels": [{"alternatives": [{
            "transcript": "I live in Quảng Trị.", "confidence": .91,
            "words": [
                {"word": "i", "punctuated_word": "I", "start": 0, "end": .2, "confidence": .99},
                {"word": "quang tri", "punctuated_word": "Quảng Trị.", "start": .5, "end": 1.1, "confidence": .82},
            ],
        }]}]},
    }
    captured = {}
    monkeypatch.setattr(cloud.settings, "deepgram_api_key", "secret")
    monkeypatch.setattr(cloud.httpx, "Client", lambda **kwargs: FakeClient(payload, captured, **kwargs))
    audio = tmp_path / "answer.webm"
    audio.write_bytes(b"audio")
    result = cloud.transcribe_deepgram(audio, keyterms=["Quảng Trị", "Đà Nẵng"])
    assert result["provider"] == "deepgram"
    assert result["provider_confidence"] == pytest.approx(.91)
    assert result["words"][-1]["word"] == "Quảng Trị."
    params = captured["request"]["params"]
    assert ("keyterm", "Quảng Trị") in params and ("keyterm", "Đà Nẵng") in params


def test_elevenlabs_adapter_keeps_verbatim_mode_and_skips_spacing(monkeypatch, tmp_path):
    payload = {
        "text": "I am still studying.", "language_code": "en", "language_probability": .98,
        "words": [
            {"text": "I", "start": 0, "end": .1, "type": "word", "logprob": -.01},
            {"text": " ", "start": .1, "end": .12, "type": "spacing", "logprob": 0},
            {"text": "am", "start": .12, "end": .3, "type": "word", "logprob": -.05},
        ],
    }
    captured = {}
    monkeypatch.setattr(cloud.settings, "elevenlabs_api_key", "secret")
    monkeypatch.setattr(cloud.httpx, "Client", lambda **kwargs: FakeClient(payload, captured, **kwargs))
    audio = tmp_path / "answer.webm"
    audio.write_bytes(b"audio")
    result = cloud.transcribe_elevenlabs(audio, keyterms=["Quảng Trị"])
    assert [word["word"] for word in result["words"]] == ["I", "am"]
    assert result["provider_confidence"] > .9
    form = captured["request"]["files"]
    assert ("no_verbatim", (None, "false")) in form
    assert ("keyterms", (None, "Quảng Trị")) in form


def _result(provider, text, confidence=.9):
    return {
        "text": text,
        "words": [
            {"word": token, "start": index * .2, "end": index * .2 + .15, "probability": confidence}
            for index, token in enumerate(text.split())
        ],
        "segments": [{"start": 0, "end": 1, "avg_logprob": -.05,
                      "no_speech_prob": .01, "compression_ratio": 1}],
        "asr_confidence": confidence, "hallucination_risk": 0,
        "missing_metrics": [], "nbest_texts": [text], "provider": provider,
        "model": provider + "-model", "latency_ms": 10,
    }


def test_medoid_uses_cross_provider_agreement_instead_of_raw_confidence():
    hypotheses = [
        _result("deepgram", "I study in Da Nang", .7),
        _result("elevenlabs", "I study in Da Nang", .8),
        _result("selfhost", "I still in Ghana", .99),
    ]
    selected, agreement = recognition._select_transcript_medoid(
        hypotheses, ["deepgram", "elevenlabs", "selfhost"],
    )
    assert selected["provider"] == "deepgram"
    assert agreement > .6


def test_ensemble_survives_one_provider_failure_and_marks_disagreement(monkeypatch):
    monkeypatch.setattr(recognition, "_available_ensemble_providers",
                        lambda: ["deepgram", "elevenlabs", "selfhost"])
    monkeypatch.setattr(recognition.settings, "stt_ensemble_min_providers", 2)

    def run(provider, _audio, _keyterms):
        if provider == "selfhost":
            raise TimeoutError("busy")
        text = "I study in Da Nang" if provider == "deepgram" else "I still in Da Nang"
        return _result(provider, text)

    monkeypatch.setattr(recognition, "_provider_transcribe", run)
    result = recognition.transcribe_ensemble("answer.webm", keyterms=["Đà Nẵng"])
    assert result["provider"] == "ensemble"
    assert result["fallback_used"] is True
    assert result["provider_errors"] == {"selfhost": "TimeoutError"}
    assert set(result["providers_succeeded"]) == {"deepgram", "elevenlabs"}
    assert any(span["reason"] == "decode_disagreement" for span in result["uncertain_spans"])


def test_ensemble_requires_configured_quorum(monkeypatch):
    monkeypatch.setattr(recognition, "_available_ensemble_providers", lambda: ["selfhost"])
    monkeypatch.setattr(recognition.settings, "stt_ensemble_min_providers", 2)
    with pytest.raises(RuntimeError, match="needs 2"):
        recognition.transcribe_ensemble("answer.webm")
