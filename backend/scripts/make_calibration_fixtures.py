"""Generate synthetic calibration audio fixtures (stdlib only).

Writes mono 16 kHz 16-bit PCM WAV files plus a manifest.json into
backend/tests/fixtures/audio/. These fixtures exercise the ASR confidence
pipeline (silence, noise-only, tone, truncated, repeated beeps) WITHOUT
requiring real learner recordings or a Whisper model download.

Real examiner-rated learner audio (speaker-disjoint, Part 1/2/3, varied
devices/noise) is still required for Phase 3 calibration; these synthetics
only guard the silence/noise/hallucination regression paths.
"""

import json
import math
import random
import wave
from pathlib import Path

SR = 16000
OUT_DIR = Path(__file__).resolve().parent.parent / "tests" / "fixtures" / "audio"


def _write_wav(path: Path, samples) -> None:
    import array

    data = array.array("h", (max(-32768, min(32767, int(v))) for v in samples))
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(SR)
        wf.writeframes(data.tobytes())


def _silence(seconds: float):
    return [0] * int(SR * seconds)


def _tone(freq: float, seconds: float, amp: float = 9000.0):
    return [amp * math.sin(2 * math.pi * freq * t / SR) for t in range(int(SR * seconds))]


def _noise(seconds: float, amp: float = 4000.0, seed: int = 7):
    rng = random.Random(seed)
    return [rng.uniform(-amp, amp) for _ in range(int(SR * seconds))]


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    manifest = {}

    cases = {
        "silence_2s.wav": (_silence(2.0), "pure silence; expect cant_hear, no hallucinated words"),
        "noise_only_2s.wav": (_noise(2.0), "white noise only; expect cant_hear or high hallucination risk"),
        "tone_440_2s.wav": (_tone(440.0, 2.0), "steady tone; non-speech energy without linguistic content"),
        "tone_with_gap_3s.wav": (
            _tone(440.0, 1.0) + _silence(1.0) + _tone(440.0, 1.0),
            "tone-silence-tone; exercises VAD speech/silence segmentation",
        ),
        "truncated_tone_0_3s.wav": (_tone(440.0, 0.3), "very short clip; exercises truncated-audio handling"),
        "repeated_beeps_3s.wav": (
            (_tone(880.0, 0.2) + _silence(0.1)) * 10,
            "repeated identical bursts; repetition/hallucination guard",
        ),
        "speech_like_mixed_4s.wav": (
            _tone(220.0, 0.5) + _noise(0.5, amp=1500.0) + _tone(330.0, 0.5) + _silence(0.5)
            + _tone(220.0, 0.5) + _noise(0.5, amp=1500.0) + _tone(330.0, 0.5) + _silence(0.5),
            "mixed energy/noise; mid-quality sample proxy",
        ),
    }
    for name, (samples, note) in cases.items():
        path = OUT_DIR / name
        _write_wav(path, samples)
        manifest[name] = {
            "sample_rate": SR,
            "channels": 1,
            "seconds": round(len(samples) / SR, 2),
            "expectation": note,
        }
    with open(OUT_DIR / "manifest.json", "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
    print(f"Wrote {len(cases)} fixtures to {OUT_DIR}")


if __name__ == "__main__":
    main()
