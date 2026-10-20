import subprocess
import tempfile
import json
from pathlib import Path

from app.core.config import settings


def compress_audio(
    input_path: str | Path,
    output_path: str | Path,
    sample_rate: int = 16000,
    bitrate: str = "24k",
) -> str:
    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        str(input_path),
        "-ac",
        "1",
        "-ar",
        str(sample_rate),
        "-c:a",
        "libopus",
        "-b:a",
        bitrate,
        str(output_path),
    ]
    subprocess.run(cmd, check=True, capture_output=True, timeout=settings.audio_process_timeout_seconds)
    return str(output_path)


def normalize_audio_to_wav(
    input_path: str | Path,
    output_path: str | Path | None = None,
    sample_rate: int = 16000,
) -> str:
    """Decode any ffmpeg-supported input into the PCM format used by ASR.

    A new temporary file is used by default so callers never mutate an upload.
    The caller owns the returned file and should remove it when finished.
    """
    if output_path is None:
        handle = tempfile.NamedTemporaryFile(prefix="lexilearn-asr-", suffix=".wav", delete=False)
        handle.close()
        output_path = handle.name
    elif Path(input_path).resolve() == Path(output_path).resolve():
        raise ValueError("Normalized audio output must differ from the input")
    cmd = [
        "ffmpeg", "-y", "-i", str(input_path),
        "-vn", "-ac", "1", "-ar", str(sample_rate),
        "-c:a", "pcm_s16le", str(output_path),
    ]
    try:
        subprocess.run(cmd, check=True, capture_output=True, timeout=settings.audio_process_timeout_seconds)
    except Exception:
        Path(output_path).unlink(missing_ok=True)
        raise
    return str(output_path)


def probe_audio_duration(path: str | Path) -> float | None:
    """Read container duration without decoding the complete file."""
    cmd = [
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "json", str(path),
    ]
    try:
        completed = subprocess.run(
            cmd, check=True, capture_output=True, text=True,
            timeout=settings.audio_process_timeout_seconds,
        )
        value = json.loads(completed.stdout)["format"]["duration"]
        return float(value)
    except (subprocess.SubprocessError, KeyError, TypeError, ValueError, json.JSONDecodeError):
        return None
