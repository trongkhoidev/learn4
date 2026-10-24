"""Private PCM handling and audio quality gates for pronunciation evidence.

The learner audio is never mutated: a temporary mono 16 kHz PCM WAV copy is
created and removed in a ``finally`` block. Quality gates lower evidence
quality or trigger abstention — they never create pronunciation errors.
"""

import array
import math
import tempfile
import wave
from dataclasses import dataclass

from app.integrations.audio.processor import normalize_audio_to_wav

TARGET_SAMPLE_RATE = 16000
CLIP_ABS_THRESHOLD = 32760
MIN_SPEECH_DURATION_S = 1.0


@dataclass
class PcmAudio:
    samples: array.array
    sample_rate: int
    duration_s: float

    def segment(self, start_s: float, end_s: float) -> array.array:
        lo = max(0, int(start_s * self.sample_rate))
        hi = min(len(self.samples), int(end_s * self.sample_rate))
        return self.samples[lo:hi]


def load_pcm_mono_16k(audio_path: str) -> PcmAudio:
    """Decode into a private temp PCM WAV, read samples, then delete the copy."""
    import os

    handle = tempfile.NamedTemporaryFile(
        prefix="lexilearn-pronun-", suffix=".wav", delete=False,
    )
    handle.close()
    tmp_path = handle.name
    try:
        normalized = normalize_audio_to_wav(audio_path, tmp_path)
        with wave.open(normalized, "rb") as wf:
            if wf.getnchannels() != 1 or wf.getsampwidth() != 2:
                raise ValueError("normalized PCM is not mono 16-bit")
            sample_rate = wf.getframerate()
            raw = wf.readframes(wf.getnframes())
        samples = array.array("h")
        samples.frombytes(raw)
        duration = len(samples) / sample_rate if sample_rate else 0.0
        return PcmAudio(samples, sample_rate, duration)
    finally:
        try:
            os.remove(tmp_path)
        except OSError:
            pass


def load_pcm_from_wav_file(path: str) -> PcmAudio:
    """Read an already-normalized PCM WAV (tests/tools); no temp file involved."""
    with wave.open(path, "rb") as wf:
        if wf.getnchannels() not in (1, 2) or wf.getsampwidth() != 2:
            raise ValueError("expected 16-bit WAV audio")
        sample_rate = wf.getframerate()
        raw = wf.readframes(wf.getnframes())
    samples = array.array("h")
    samples.frombytes(raw)
    if wf.getnchannels() == 2:
        samples = array.array("h", (
            (samples[i] + samples[i + 1]) // 2 for i in range(0, len(samples) - 1, 2)
        ))
    duration = len(samples) / sample_rate if sample_rate else 0.0
    return PcmAudio(samples, sample_rate, duration)


def energy_contour(pcm: PcmAudio, window_s: float = 0.025) -> list[float]:
    window = max(1, int(pcm.sample_rate * window_s))
    peak = max(1, max((abs(v) for v in pcm.samples), default=1))
    return [
        math.sqrt(sum(v * v for v in pcm.samples[i:i + window]) / window) / peak
        for i in range(0, len(pcm.samples) - window + 1, window)
    ]


def audio_quality_gates(pcm: PcmAudio) -> dict:
    """Descriptive quality features; presence of noise lowers quality, not scores."""
    n = len(pcm.samples)
    if n == 0:
        return {
            "duration_s": 0.0,
            "duration_ok": False,
            "clipping_ratio": None,
            "low_energy_ratio": None,
            "snr_proxy_db": None,
            "gate_reasons": ["empty_audio"],
        }
    clips = sum(1 for v in pcm.samples if abs(v) >= CLIP_ABS_THRESHOLD)
    energies = energy_contour(pcm)
    low_energy = [e for e in energies if e < 0.05]
    speech = [e for e in energies if e >= 0.05]
    snr = None
    if speech and low_energy:
        snr = round(20 * math.log10(max(1e-6, sum(speech) / len(speech))
                                    / max(1e-6, sum(low_energy) / len(low_energy))), 1)
    reasons = []
    if pcm.duration_s < MIN_SPEECH_DURATION_S:
        reasons.append("audio_too_short")
    if n and clips / n > 0.01:
        reasons.append("clipping_detected")
    if energies and len(low_energy) / len(energies) > 0.85:
        reasons.append("mostly_silence")
    return {
        "duration_s": round(pcm.duration_s, 3),
        "duration_ok": pcm.duration_s >= MIN_SPEECH_DURATION_S,
        "clipping_ratio": round(clips / n, 4) if n else None,
        "low_energy_ratio": round(len(low_energy) / len(energies), 3) if energies else None,
        "snr_proxy_db": snr,
        "gate_reasons": reasons,
    }
