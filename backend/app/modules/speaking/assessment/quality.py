"""Transparent evidence coverage for a diagnostic speaking assessment."""


def build_assessment_quality(stt, words, uncertain_spans, criteria) -> dict:
    stt = stt or {}
    words = words or []
    uncertain_spans = uncertain_spans or []
    criteria = criteria or {}
    word_count = len(words)
    timed_count = sum(1 for word in words if word.get("timing_valid"))
    timing_coverage = timed_count / word_count if word_count else 0.0
    uncertain_ids = {span.get("word_id") for span in uncertain_spans if span.get("word_id")}
    uncertain_ratio = len(uncertain_ids) / word_count if word_count else 1.0
    hypotheses = stt.get("provider_hypotheses") or []
    provider_count = len(hypotheses) or (1 if stt.get("provider") else 0)
    agreement = stt.get("ensemble_agreement", stt.get("decode_agreement"))
    try:
        agreement = max(0.0, min(1.0, float(agreement)))
    except (TypeError, ValueError):
        agreement = None

    language_keys = (
        "fluency_coherence", "lexical_resource", "grammatical_range_accuracy",
    )
    language_scored = sum(
        criteria.get(key, {}).get("band") is not None for key in language_keys
    )
    pronunciation_scored = criteria.get("pronunciation", {}).get("band") is not None
    score = 100
    blockers = []
    if provider_count < 2:
        score -= 8
        blockers.append("Transcript chưa được đối chiếu chéo giữa hai engine STT.")
    elif agreement is not None and agreement < .8:
        score -= 18
        blockers.append("Các engine nhận dạng chưa đồng thuận ở mức đủ cao.")
    if timing_coverage < .8:
        score -= 18
        blockers.append("Mốc thời gian theo từ chưa bao phủ đủ bài nói.")
    if uncertain_ratio > .3:
        score -= 25
        blockers.append("Quá nhiều từ còn cần nghe lại trước khi kết luận.")
    elif uncertain_ratio > .12:
        score -= 12
        blockers.append("Một phần transcript vẫn có bất định nhận dạng.")
    score -= (3 - language_scored) * 12
    if language_scored < 3:
        blockers.append("Chưa chấm đủ ba tiêu chí ngôn ngữ bằng evidence hợp lệ.")
    if not pronunciation_scored:
        score -= 20
        blockers.append("Chưa có engine pronunciation âm vị đã hiệu chỉnh với examiner.")
    score = max(0, min(100, score))
    level = "high" if score >= 80 else "medium" if score >= 65 else "low"
    return {
        "level": level,
        "coverage_score": score,
        "coverage_score_is_probability": False,
        "scope": "four_criteria" if pronunciation_scored else "language_criteria_only",
        "provider_count": provider_count,
        "provider_agreement": round(agreement, 3) if agreement is not None else None,
        "timing_coverage": round(timing_coverage, 3),
        "uncertain_word_ratio": round(uncertain_ratio, 3),
        "language_criteria_scored": language_scored,
        "pronunciation_audio_grounded": pronunciation_scored,
        "blockers_vi": list(dict.fromkeys(blockers)),
    }
