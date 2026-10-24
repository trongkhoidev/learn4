"""Deterministic phone evidence (GOP / log-likelihood ratios) from posteriors.

This module contains no I/O and no model loading: callers supply frozen
per-frame posterior arrays (``list[dict[phone, float]]``). Before calibration,
the only allowed output is an unscaled score with status ``candidate`` —
no probability, no band, no hard error claim (plan §5, P3).
"""

import math
from typing import Optional

LOG_FLOOR = 1e-9
MIN_PHONE_DURATION_S = 0.02
MAX_PHONE_DURATION_S = 0.75


def _log(value: float) -> float:
    return math.log(max(float(value), LOG_FLOOR))


def frame_posteriors(posterior: list[dict], start: int, end: int) -> list[dict]:
    frames = posterior[max(0, start):max(0, end)]
    return [frame for frame in frames if isinstance(frame, dict)]


def strongest_competitor(frame: dict, target: str) -> Optional[str]:
    best_phone, best_value = None, 0.0
    for phone, value in frame.items():
        if phone == target:
            continue
        if value > best_value:
            best_phone, best_value = phone, value
    return best_phone


def phone_log_likelihood_ratio(
    frames: list[dict], target: str,
) -> tuple[Optional[float], Optional[str], Optional[float]]:
    """Mean per-frame log P(target) - log P(best competitor).

    Returns ``(score_unscaled, competitor, observed_probability)``. ``None``
    score means there are no usable frames (treated as deletion evidence by
    the caller, never as a score of 0).
    """
    scores = []
    competitor_votes: dict[str, int] = {}
    observed_mean = 0.0
    for frame in frames:
        if not frame:
            continue
        if target not in frame:
            # Unknown target in this model's inventory: abstain, do not guess.
            return None, None, None
        competitor_phone = strongest_competitor(frame, target)
        if competitor_phone is None:
            competitor_phone = target
            competitor_score = frame[target]
        else:
            competitor_score = frame.get(competitor_phone, LOG_FLOOR)
        competitor_votes[competitor_phone] = competitor_votes.get(competitor_phone, 0) + 1
        scores.append(_log(frame[target]) - _log(competitor_score))
        observed_mean += frame[target]
    if not scores:
        return None, None, None
    observed = observed_mean / len(scores)
    competitor = max(competitor_votes, key=lambda phone: (competitor_votes[phone], phone)) \
        if competitor_votes else None
    return sum(scores) / len(scores), competitor, observed


def duration_sanity(duration_s: float) -> Optional[str]:
    if duration_s < MIN_PHONE_DURATION_S:
        return "phone_duration_too_short"
    if duration_s > MAX_PHONE_DURATION_S:
        return "phone_duration_too_long"
    if duration_s <= 0:
        return "phone_duration_invalid"
    return None


def assess_phone(
    posterior: list[dict],
    *,
    target: str,
    start_frame: int,
    end_frame: int,
    duration_s: float,
    word_id: str,
    word: str,
    start_s: float,
    end_s: float,
    model_version: str,
    evidence_id: str,
) -> Optional[dict]:
    """Create one candidate phone observation from frozen posteriors."""
    frames = frame_posteriors(posterior, start_frame, end_frame)
    sanity = duration_sanity(duration_s)
    if sanity == "phone_duration_invalid" or not frames:
        return None
    score, competitor, observed = phone_log_likelihood_ratio(frames, target)
    if score is None:
        if sanity:
            # No alignment AND no usable frames: abstain entirely.
            return None
        return {
            "id": evidence_id,
            "word_id": word_id,
            "word": word,
            "start": round(start_s, 3),
            "end": round(end_s, 3),
            "expected_phone": target,
            "observed_phone": None,
            "kind": "uncertain_phone" if sanity is None else "deletion",
            "status": "candidate",
            "score_unscaled": None,
            "confidence": None,
            "model_version": model_version,
            "reason_code": sanity or "no_posterior_frames",
        }
    kind = "duration_outlier" if sanity else "substitution" if competitor else "uncertain_phone"
    return {
        "id": evidence_id,
        "word_id": word_id,
        "word": word,
        "start": round(start_s, 3),
        "end": round(end_s, 3),
        "expected_phone": target,
        "observed_phone": competitor,
        "kind": kind,
        "status": "candidate",
        "score_unscaled": round(score, 4),
        "confidence": None,  # never a probability before calibration
        "model_version": model_version,
        "duration_hint": sanity,
        "reason_code": "gop_low_agreement" if score < 0 else "gop_supported",
    }


def word_rollup(phone_evidence: list[dict]) -> list[dict]:
    """Aggregate per phone, keeping the raw phone evidence unchanged."""
    by_word: dict[str, dict] = {}
    for evidence in phone_evidence:
        entry = by_word.setdefault(evidence["word_id"], {
            "word_id": evidence["word_id"],
            "word": evidence["word"],
            "phone_count": 0,
            "candidate_count": 0,
            "min_score_unscaled": None,
        })
        entry["phone_count"] += 1
        if evidence.get("status") == "candidate":
            entry["candidate_count"] += 1
        score = evidence.get("score_unscaled")
        if score is not None:
            current = entry["min_score_unscaled"]
            entry["min_score_unscaled"] = score if current is None else min(current, score)
    return list(by_word.values())
