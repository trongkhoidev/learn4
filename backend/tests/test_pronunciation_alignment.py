"""P2 alignment contract tests — offline, no aligner binaries required."""

import json
import subprocess
from pathlib import Path

import pytest

from app.core.config import settings
from app.modules.speaking.pronunciation import alignment


# --- normalize_alignment ------------------------------------------------------

MFA_RESULT = {
    "status": "aligned",
    "provider": "mfa",
    "raw": {"phones": {"utt001": [
        {"phone": "AH_s3", "start": 0.0, "end": 0.2},
        {"phone": "S_s1", "start": 0.2, "end": 0.35},
        {"phone": "bad", "start": 0.4, "end": 0.2},  # end<=start: dropped
    ]}},
    "words": [
        {"word": "A", "start": 0.0, "end": 0.2},
        {"text": "scientist", "start": 0.25, "end": 0.95},
        {"word": "inverted", "start": 1.0, "end": 1.0},   # invalid timing
        {"word": "negative", "start": -0.5, "end": 0.1},  # invalid timing
        {"word": "malformed", "start": "x", "end": 2.0},  # unparseable
    ],
}


def test_normalize_contract_fields_and_word_layer():
    parsed = alignment.normalize_alignment(MFA_RESULT, transcript="A scientist")
    assert parsed["provider"] == "mfa"
    assert parsed["status"] == "aligned"
    assert parsed["calibrated"] is False
    assert parsed["declares_phone_alignment"] is True
    assert [w["word"] for w in parsed["words"]] == ["A", "scientist"]
    assert parsed["words"][0] == {"word": "A", "start": 0.0, "end": 0.2, "score": None}
    assert 0.0 <= parsed["coverage"] <= 1.0


def test_normalize_mfa_phone_layer_strips_speaker_suffixes():
    parsed = alignment.normalize_alignment(MFA_RESULT, transcript="A scientist")
    assert [p["phone"] for p in parsed["phones"]] == ["AH", "S"]
    assert parsed["phones"][0] == {"phone": "AH", "start": 0.0, "end": 0.2}


def test_normalize_whisperx_never_fabricates_phones():
    parsed = alignment.normalize_alignment({
        "status": "aligned", "provider": "whisperx",
        "words": [{"word": "hello", "start": 0.0, "end": 0.4}],
    }, transcript="hello")
    assert parsed["declares_phone_alignment"] is False
    assert parsed["phones"] == []


def test_normalize_failure_keeps_reason_and_empty_layers():
    parsed = alignment.normalize_alignment(
        {"status": "unavailable", "provider": "none", "reason": "disabled"},
        transcript="any words",
    )
    assert parsed["status"] == "unavailable"
    assert parsed["failure_reason"] == "disabled"
    assert parsed["words"] == [] and parsed["phones"] == []
    assert parsed["coverage"] == 0.0


# --- align() dispatch ---------------------------------------------------------

@pytest.fixture
def mfa_configured(monkeypatch):
    monkeypatch.setattr(settings, "pronunciation_aligner", "mfa")
    monkeypatch.setattr(settings, "mfa_dictionary_path", "dict.dic")
    monkeypatch.setattr(settings, "mfa_acoustic_model_path", "model.zip")


def test_align_disabled_by_default(monkeypatch):
    monkeypatch.setattr(settings, "pronunciation_aligner", "none")
    out = alignment.align("x.wav", "hello")
    assert out["status"] == "unavailable"
    assert out["reason"] == "disabled"


def test_align_missing_input(monkeypatch):
    monkeypatch.setattr(settings, "pronunciation_aligner", "mfa")
    assert alignment.align("", "text")["reason"] == "missing_input"
    assert alignment.align("a.wav", "")["reason"] == "missing_input"


def test_align_mfa_without_models_unavailable(monkeypatch):
    monkeypatch.setattr(settings, "pronunciation_aligner", "mfa")
    monkeypatch.setattr(settings, "mfa_dictionary_path", None)
    monkeypatch.setattr(settings, "mfa_acoustic_model_path", None)
    out = alignment.align("x.wav", "hello")
    assert out["status"] == "unavailable"
    assert out["reason"] == "models_not_configured"


def test_align_mfa_binary_missing_reports_unavailable(mfa_configured, monkeypatch):
    def raise_missing(*args, **kwargs):
        raise FileNotFoundError()

    monkeypatch.setattr(subprocess, "run", raise_missing)
    out = alignment.align("x.wav", "hello")
    assert out["status"] == "unavailable"
    assert out["reason"] == "binary_not_installed"


def test_align_mfa_timeout_fails_and_never_scores(mfa_configured, monkeypatch):
    def raise_timeout(*args, **kwargs):
        raise subprocess.TimeoutExpired("mfa", 30)

    monkeypatch.setattr(subprocess, "run", raise_timeout)
    out = alignment.align("x.wav", "hello")
    assert out["status"] == "failed"
    assert out["reason"] == "alignment_timeout"


def test_align_mfa_malformed_output_fails_closed(mfa_configured, monkeypatch):
    def run_stub(command, *args, **kwargs):
        Path(command[6]).write_text("{not json", encoding="utf-8")
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(subprocess, "run", run_stub)
    out = alignment.align("x.wav", "hello")
    # Malformed JSON bubbles up as failed with a truncated reason, never scores.
    assert out["status"] == "failed"
    assert out["reason"]


def test_align_mfa_happy_path_parses_contract(mfa_configured, monkeypatch):
    def run_stub(command, *args, **kwargs):
        Path(command[6]).write_text(json.dumps(
            {"phones": {"u1": [{"phone": "S_s1", "start": 0.0, "end": 0.1}]}},
        ), encoding="utf-8")
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(subprocess, "run", run_stub)
    out = alignment.align("x.wav", "hello")
    assert out["status"] == "aligned"
    assert out["provider"] == "mfa"
    assert out["declares_phone_alignment"] is True
    assert out["calibrated"] is False
    assert out["phones"] == [{"phone": "S", "start": 0.0, "end": 0.1}]


def test_align_whisperx_without_package_unavailable(monkeypatch):
    monkeypatch.setattr(settings, "pronunciation_aligner", "whisperx")
    out = alignment.align("x.wav", "hello")
    assert out["status"] == "unavailable"
    assert out["reason"] == "package_not_installed"
