"""Versioned prosody feature extractor (pure standard library, deterministic).

Design rules:

- Missing evidence is ``None`` (missing), never a zero that reads as "bad".
- Pitch is normalized by the speaker's own voiced median; no absolute pitch
  thresholds are applied across voices.
- Word-duration dispersion is reported as a timing proxy and is NEVER labelled
  as lexical stress.
- Fluency interpretation stays with the fluency criterion; these values are
  pronunciation-side prosody observations (plan §4, P4).
"""

import math
from typing import Optional

from .audio_features import PcmAudio, energy_contour
from .policy import FEATURE_VERSION

FRAME_S = 0.04
HOP_S = 0.02
MIN_F0_HZ = 70.0
MAX_F0_HZ = 400.0
VOICED_ENERGY_FRACTION = 0.35  # relative to the median positive frame energy


def _median(values) -> Optional[float]:
    ordered = sorted(values)
    if not ordered:
        return None
    n = len(ordered)
    mid = n // 2
    return ordered[mid] if n % 2 else (ordered[mid - 1] + ordered[mid]) / 2


def _autocorrelation_pitch(segment: list[int], sample_rate: int) -> Optional[float]:
    n = len(segment)
    if n < sample_rate // int(MAX_F0_HZ) + 1:
        return None
    mean = sum(segment) / n
    centered = [v - mean for v in segment]
    denominator = sum(v * v for v in centered)
    if denominator <= 0:
        return None
    min_lag = max(2, int(sample_rate / MAX_F0_HZ))
    max_lag = min(int(sample_rate / MIN_F0_HZ), n // 2)
    best_lag, best_corr = None, 0.25
    for lag in range(min_lag, max_lag + 1):
        corr = sum(centered[i] * centered[i + lag] for i in range(n - lag)) / denominator
        if corr > best_corr:
            best_corr, best_lag = corr, lag
    if best_lag is None:
        return None
    pitch = sample_rate / best_lag
    if not MIN_F0_HZ <= pitch <= MAX_F0_HZ:
        return None
    return pitch


def f0_contour(pcm: PcmAudio) -> list[Optional[float]]:
    """Per-frame pitch estimates in Hz; ``None`` on unvoiced frames."""
    if not pcm or not pcm.samples:
        return []
    frame = max(1, int(pcm.sample_rate * FRAME_S))
    hop = max(1, int(pcm.sample_rate * HOP_S))
    contours = energy_contour(pcm, window_s=FRAME_S)
    voiced_threshold = VOICED_ENERGY_FRACTION * (_median([e for e in contours if e > 0]) or 0)
    values: list[Optional[float]] = []
    for index, start in enumerate(range(0, len(pcm.samples) - frame + 1, hop)):
        energy = contours[index] if index < len(contours) else 0.0
        if voiced_threshold <= 0 or energy < voiced_threshold:
            values.append(None)
            continue
        values.append(_autocorrelation_pitch(
            list(pcm.samples[start:start + frame]), pcm.sample_rate,
        ))
    return values


def voiced_frames(contour: list[Optional[float]]) -> list[tuple[int, float]]:
    return [(i, p) for i, p in enumerate(contour) if p is not None]


def pitch_statistics(contour: list[Optional[float]]) -> dict:
    voiced = voiced_frames(contour)
    median = _median([p for _, p in voiced])
    if not voiced or not median:
        return {
            "voiced_frames": len(voiced),
            "voiced_coverage": 0.0 if contour else None,
            "f0_median_hz": None,
            "f0_range_hz": None,
            "f0_interquartile_hz": None,
        }
    pitches = sorted(p for _, p in voiced)
    q1 = pitches[len(pitches) // 4] if len(pitches) >= 4 else pitches[0]
    q3 = pitches[(len(pitches) * 3) // 4] if len(pitches) >= 4 else pitches[-1]
    return {
        "voiced_frames": len(voiced),
        "voiced_coverage": round(len(voiced) / len(contour), 3) if contour else None,
        "f0_median_hz": round(median, 1),
        "f0_range_hz": round(pitches[-1] - pitches[0], 1),
        "f0_interquartile_hz": round(max(0.0, q3 - q1), 1),
    }


def normalized_pitch_shape(contour: list[Optional[float]]) -> Optional[list[float]]:
    """Semitone shape relative to the speaker's median (``None`` when too thin)."""
    voiced = voiced_frames(contour)
    median = _median([p for _, p in voiced])
    if len(voiced) < 5 or not median or median <= 0:
        return None
    return [round(12 * math.log2(p / median), 2) for _, p in voiced]


def terminal_movement(contour: list[Optional[float]]) -> Optional[str]:
    """Direction of the final voiced contour (rising/falling/level)."""
    shape = normalized_pitch_shape(contour)
    if not shape or len(shape) < 4:
        return None
    tail = shape[-max(3, len(shape) // 10):]
    delta = tail[-1] - tail[0]
    if delta > 1.0:
        return "rising"
    if delta < -1.0:
        return "falling"
    return "level"


def pitch_slope_semitones_per_second(contour: list[Optional[float]]) -> Optional[float]:
    """Overall slope between first and last voiced frames, in semitones/s."""
    voiced = voiced_frames(contour)
    if len(voiced) < 3:
        return None
    first_index, last_index = voiced[0][0], voiced[-1][0]
    if last_index == first_index:
        return None
    duration_s = (last_index - first_index) * HOP_S
    delta = 12 * math.log2(voiced[-1][1] / voiced[0][1])
    return round(delta / duration_s, 3)


def _word_timing(words, index) -> Optional[tuple[float, float]]:
    try:
        start, end = float(words[index]["start"]), float(words[index]["end"])
    except (IndexError, KeyError, TypeError, ValueError):
        return None
    return (start, end) if end > start else None


def extract_prosody_features(pcm: PcmAudio, words: list[dict]) -> dict:
    """Build the versioned pronunciation prosody feature block."""
    total_duration = pcm.duration_s if pcm else 0.0
    gaps: list[float] = []
    durations: list[float] = []
    for index, word in enumerate(words):
        timing = _word_timing(words, index)
        if timing is None:
            continue
        start, end = timing
        durations.append(min(end - start, 5.0))
        previous = _word_timing(words, index - 1)
        if previous and start > previous[1]:
            gaps.append(start - previous[1])
    pauses = [g for g in gaps if g > 0.3]
    long_pauses = [g for g in gaps if g > 1.0]
    contour = f0_contour(pcm) if pcm else []
    stats = pitch_statistics(contour)
    duration_mean = _median(durations)
    speech_time = total_duration - sum(pauses) if pauses else total_duration
    # A stress ratio around a dictionary-marked syllable is a timing
    # observation only; no accent conclusion is allowed from it.
    stress_ratios = [
        float(word["stress_duration_ratio"]) for word in words
        if word.get("stress_target") and isinstance(word.get("stress_duration_ratio"), (int, float))
    ]
    return {
        "feature_version": FEATURE_VERSION,
        "duration_s": round(total_duration, 3) if total_duration else None,
        "word_count": len(durations),
        "speech_rate_wpm": round(len(durations) / total_duration * 60, 1) if total_duration > 0 else None,
        "articulation_rate_wpm": (
            round(len(durations) / speech_time * 60, 1) if speech_time and speech_time > 0 else None
        ),
        "pause_count": len(pauses),
        "long_pause_count": len(long_pauses),
        "pause_ratio": round(sum(pauses) / total_duration, 3) if total_duration > 0 else None,
        "word_duration_median_s": round(duration_mean, 3) if duration_mean else None,
        "word_duration_range_s": round(max(durations) - min(durations), 3) if durations else None,
        # Timing proxy only; interpreting this as stress evidence is not allowed.
        "word_duration_dispersion_proxy": (
            round((max(durations) - min(durations)) / duration_mean, 3)
            if durations and duration_mean else None
        ),
        "voiced_coverage": stats["voiced_coverage"],
        "f0_median_hz": stats["f0_median_hz"],
        "f0_range_hz": stats["f0_range_hz"],
        "f0_interquartile_hz": stats["f0_interquartile_hz"],
        "pitch_slope_semitones_per_s": pitch_slope_semitones_per_second(contour),
        "terminal_movement": terminal_movement(contour),
        "lexical_stress_contrast": _median(stress_ratios) if stress_ratios else None,
        "lexical_stress_target_available": bool(stress_ratios),
        "rhythm_cv": None,
    }
