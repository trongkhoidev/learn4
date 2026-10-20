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
    return {
        "status": "aligned",
        "provider": "whisperx",
        "words": result.get("word_segments") or [],
        "characters": result.get("segments") or [],
        "phonemes": [],
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
            subprocess.run(command, check=True, capture_output=True, text=True, timeout=180)
            payload = json.loads(output_path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            return {"status": "unavailable", "provider": "mfa", "reason": "binary_not_installed"}
        except Exception as exc:
            return {"status": "failed", "provider": "mfa", "reason": str(exc)[:500]}
    return {
        "status": "aligned", "provider": "mfa", "raw": payload,
        "calibrated": False,
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
