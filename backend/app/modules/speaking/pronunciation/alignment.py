"""Optional forced-alignment adapters.

Alignment improves timing/evidence; it does not become a pronunciation band
until the resulting features are calibrated against examiner labels.
"""

import json
import subprocess
import tempfile
import wave
from pathlib import Path

from app.core.config import settings

_whisperx_model = None
_whisperx_metadata = None


def _duration(path: str) -> float:
    try:
        with wave.open(path, "rb") as handle:
            return handle.getnframes() / float(handle.getframerate())
    except Exception:
        from app.integrations.audio.processor import probe_audio_duration
        return float(probe_audio_duration(path) or 0.0)


def _align_whisperx(audio_path: str, transcript: str) -> dict:
    global _whisperx_model, _whisperx_metadata
    import whisperx

    device = settings.pronunciation_alignment_device
    if _whisperx_model is None:
        _whisperx_model, _whisperx_metadata = whisperx.load_align_model(
            language_code="en", device=device,
        )
    duration = _duration(audio_path)
    if duration <= 0:
        return {"status": "failed", "provider": "whisperx", "reason": "invalid_duration"}
    audio = whisperx.load_audio(audio_path)
    result = whisperx.align(
        [{"text": transcript, "start": 0.0, "end": duration}],
        _whisperx_model,
        _whisperx_metadata,
        audio,
        device,
        return_char_alignments=True,
    )
    parsed = normalize_alignment({
        "status": "aligned",
        "provider": "whisperx",
        "words": result.get("word_segments") or [],
    }, transcript)
    # WhisperX provides word/character alignment only; phones stay empty.
    return {
        "status": parsed["status"],
        "provider": "whisperx",
        "words": parsed["words"],
        "characters": result.get("segments") or [],
        "phones": [],
        "coverage": parsed["coverage"],
        "declares_phone_alignment": False,
        "calibrated": False,
    }


def _align_mfa(audio_path: str, transcript: str) -> dict:
    if not settings.mfa_dictionary_path or not settings.mfa_acoustic_model_path:
        return {"status": "unavailable", "provider": "mfa", "reason": "models_not_configured"}
    with tempfile.TemporaryDirectory(prefix="lexilearn-mfa-") as temp_dir:
        text_path = Path(temp_dir) / "transcript.txt"
        output_path = Path(temp_dir) / "alignment.json"
        text_path.write_text(transcript, encoding="utf-8")
        command = [
            "mfa", "align_one", audio_path, str(text_path),
            settings.mfa_dictionary_path, settings.mfa_acoustic_model_path,
            str(output_path), "--output_format", "json", "--single_speaker",
        ]
        try:
            subprocess.run(
                command, check=True, capture_output=True, text=True,
                timeout=settings.pronunciation_alignment_timeout_seconds,
            )
            payload = json.loads(output_path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            return {"status": "unavailable", "provider": "mfa", "reason": "binary_not_installed"}
        except subprocess.TimeoutExpired:
            return {"status": "failed", "provider": "mfa", "reason": "alignment_timeout"}
        except Exception as exc:
            return {"status": "failed", "provider": "mfa", "reason": str(exc)[:500]}
    parsed = normalize_alignment(
        {"status": "aligned", "provider": "mfa", "raw": payload}, transcript,
    )
    words, phones = parsed["words"], parsed["phones"]
    return {
        "status": "aligned", "provider": "mfa", "raw": payload,
        "words": words, "phones": phones,
        "coverage": parsed["coverage"], "calibrated": False,
        "declares_phone_alignment": True,
    }


def normalize_alignment(result: dict, transcript: str = "") -> dict:
    """Parse any provider output into the shared alignment contract.

    MFA JSON aligns phones per file; WhisperX only ever provides word/char
    timing. Providers that supply no phone alignment must report
    ``phones: []`` — never fabricated phone evidence.
    """
    provider = (result or {}).get("provider", "none")
    raw = result.get("raw") or {}
    words, phones = [], []
    phone_layer = provider == "mfa"
    for item in (result.get("words") or []):
        word = str(item.get("word") or item.get("text") or "").strip()
        try:
            start = float(item.get("start"))
            end = float(item.get("end"))
        except (TypeError, ValueError):
            continue
        if end <= start or start < 0:
            continue
        words.append({
            "word": word,
            "start": round(start, 3),
            "end": round(end, 3),
            "score": item.get("score") or item.get("word_score"),
        })
    if phone_layer:
        for group in (raw.get("phones") or {}).values():  # grouped phone intervals
            for phone in group:
                name = str(phone.get("phone", "")).strip()
                try:
                    start = float(phone.get("start"))
                    end = float(phone.get("end"))
                except (TypeError, ValueError):
                    continue
                if not name or end <= start or start < 0:
                    continue
                phones.append({
                    "phone": name.rsplit("_", 1)[0],
                    "start": round(start, 3),
                    "end": round(end, 3),
                })
        # MFA output carries no per-phone score ranking; phones stay positional.
    coverage = 0.0
    if transcript:
        reference = len(str(transcript).split())
        coverage = len(words) / reference if reference else 0.0
    return {
        "status": result.get("status", "unavailable"),
        "provider": provider,
        "words": words,
        "phones": phones,
        "coverage": round(max(0.0, min(1.0, coverage)), 3),
        "failure_reason": result.get("reason"),
        "calibrated": False,
        "declares_phone_alignment": bool(phone_layer),
    }


def align(audio_path: str, transcript: str) -> dict:
    provider = (settings.pronunciation_aligner or "none").lower()
    if not audio_path or not transcript:
        return {"status": "unavailable", "provider": provider, "reason": "missing_input"}
    if provider == "whisperx":
        try:
            return _align_whisperx(audio_path, transcript)
        except ImportError:
            return {"status": "unavailable", "provider": "whisperx", "reason": "package_not_installed"}
        except Exception as exc:
            return {"status": "failed", "provider": "whisperx", "reason": str(exc)[:500]}
    if provider == "mfa":
        return _align_mfa(audio_path, transcript)
    return {"status": "unavailable", "provider": "none", "reason": "disabled"}
