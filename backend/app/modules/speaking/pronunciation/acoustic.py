"""Acoustic feature extraction (designed layer — needs calibration on real samples).

The raw features produced here must be converted to bands via
`pronun_conf_to_band` / `fluency_score_to_band` before being stored in
`score.pronun.score` / `score.fluency.score` and passed to `user_audio_2_score`.
"""

import math

PAUSE_GAP_S = 0.3
LONG_PAUSE_S = 1.0


def avg_logprob_to_confidence(avg_logprob):
    if avg_logprob is None:
        return 0.0
    return max(0.0, min(1.0, math.exp(avg_logprob)))


def _fluency_details(words, total_duration_s):
    if not words or total_duration_s <= 0:
        return {"raw": 0.0, "words_per_minute": 0.0, "pause_ratio": 0.0, "long_pauses": 0}
    n_words = len(words)
    speech_rate_wpm = (n_words / total_duration_s) * 60
    pauses = []
    for i in range(1, len(words)):
        try:
            gap = float(words[i].get("start")) - float(words[i - 1].get("end"))
        except (TypeError, ValueError):
            continue
        if gap > PAUSE_GAP_S:
            pauses.append(gap)
    pause_time = sum(pauses)
    pause_ratio = pause_time / total_duration_s
    long_pause_count = sum(1 for p in pauses if p > LONG_PAUSE_S)
    # This is a descriptive timing proxy only. It is not a fluency band or
    # probability and deliberately has no "ideal" speaking rate.
    timing_observation = 1.0 + pause_ratio + long_pause_count * 0.15
    return {
        "raw": round(timing_observation, 3),
        "words_per_minute": round(speech_rate_wpm, 1),
        "pause_ratio": round(pause_ratio, 3),
        "long_pauses": long_pause_count,
    }


def compute_fluency_acoustic(words, total_duration_s):
    return _fluency_details(words, total_duration_s)["raw"]


def detect_noise(segments, transcript):
    if segments:
        values = [float(s["no_speech_prob"]) for s in segments if s.get("no_speech_prob") is not None]
        avg_no_speech = sum(values) / len(values) if values else 0.0
    else:
        avg_no_speech = 1.0
    word_count = len((transcript or "").split())
    if avg_no_speech > 0.6 or word_count == 0:
        return "cant_hear"
    return None


def color_word(probability):
    if probability is None:
        return "gray"
    if probability >= 0.8:
        return "green"
    if probability >= 0.6:
        return "yellow"
    return "red"


def color_coded_transcript(words, uncertain_spans=None):
    by_word = {}
    for span in uncertain_spans or []:
        key = (span.get("word"), span.get("start"), span.get("end"))
        by_word[key] = span.get("reason", "asr_uncertain")
    return [
        {
            "id": w.get("id") or f"w{index + 1}",
            "word": w["word"],
            "color": color_word(w.get("probability", 0.0)),
            "score": round((w.get("probability") or 0.0) * 100),
            "asr_probability": w.get("probability"),
            "asr_probability_calibrated": False,
            "start": w.get("start"),
            "end": w.get("end"),
            "uncertain": (w.get("word"), w.get("start"), w.get("end")) in by_word,
            "uncertainty_reason": by_word.get((w.get("word"), w.get("start"), w.get("end"))),
        }
        for index, w in enumerate(words)
    ]


def build_acoustic_bands(avg_logprob, segments, words, transcript):
    confidence = avg_logprob_to_confidence(avg_logprob)
    if words:
        total_duration = float(words[-1].get("end", 0.0) or 0.0) - float(words[0].get("start", 0.0) or 0.0)
    elif segments:
        total_duration = float(segments[-1].get("end", 0.0) or 0.0) - float(segments[0].get("start", 0.0) or 0.0)
    else:
        total_duration = 0.0
    details = _fluency_details(words, total_duration)
    return {
        # Acoustic proxies do not produce IELTS bands without calibration.
        "pronun": None,
        "fluency": None,
        "noise": detect_noise(segments, transcript),
        "color_coded_transcript": color_coded_transcript(words),
        "features": {
            "asr_signal": confidence,
            "words_per_minute": details["words_per_minute"],
            "pause_ratio": details["pause_ratio"],
            "long_pauses": details["long_pauses"],
        },
    }
