"""Evidence-gated Speaking assessment orchestration."""

import re

from app.core.config import settings
from app.integrations.llm.transport import provider_readiness
from app.integrations.stt import recognition as stt_service
from app.integrations.audio.processor import probe_audio_duration
from app.modules.speaking.pronunciation import acoustic, service as pronunciation_service
from app.modules.speaking.assessment import raters
from app.operations import budget
from .rubric import RUBRIC_SOURCE, RUBRIC_VERSION


def _assessment_meta(stt=None, raters=None) -> dict:
    stt = stt or {}
    raters = raters or {}
    models = {
        key: value.get("model", "") for key, value in raters.items()
        if value.get("model")
    }
    providers = {value.get("provider") for value in raters.values() if value.get("provider")}
    return {
        "score_type": "diagnostic",
        "confidence_calibrated": False,
        "rubric": "IELTS Speaking public band descriptors",
        "rubric_version": RUBRIC_VERSION,
        "scoring_version": settings.scoring_version,
        "stt_profile_version": stt.get("decode_profile", settings.stt_profile_version),
        "calibration_version": settings.calibration_version,
        "llm_provider": next(iter(providers), settings.llm_provider),
        "llm_models": models,
        "stt_provider": stt.get("provider", settings.stt_provider),
        "asr_model": stt.get("model"),
        "asr_fallback_used": stt.get("fallback_used", False),
        "asr_fallback_reason": stt.get("fallback_reason"),
        "asr_latency_ms": stt.get("latency_ms"),
    }


def _criterion(status="insufficient_evidence", band=None, *, basis="not_calibrated", feedback=None, **extra) -> dict:
    return {
        "status": status,
        "band": band,
        "score": band,
        "confidence": None,
        "confidence_basis": basis,
        "feedback": feedback,
        "errors": [],
        "evidence": [],
        "next_action_vi": None,
        **extra,
    }


def _as_words(stt_words: list, transcript: str, duration: float | None, *, allow_unverified_mock: bool):
    source = list(stt_words or [])
    if not source:
        source = [{"word": token, "probability": None} for token in re.findall(r"\S+", transcript or "")]
    words = []
    review_reasons = []
    for index, source_word in enumerate(source, start=1):
        word = str(source_word.get("word", "")).strip()
        if not word:
            continue
        try:
            start = float(source_word.get("start"))
            end = float(source_word.get("end"))
        except (TypeError, ValueError):
            start = end = None
        timing_valid = (
            start is not None and end is not None and start >= 0 and end > start
            and (duration is None or end <= duration + 0.05)
        )
        if not timing_valid:
            start = end = None
            review_reasons.append("word_timing_missing_or_out_of_audio_bounds")
        if duration is None and not allow_unverified_mock:
            start = end = None
            timing_valid = False
            review_reasons.append("audio_duration_unavailable")
        words.append({
            "id": f"w{len(words) + 1}",
            "word": word,
            "text": word,
            "start": round(start, 3) if start is not None else None,
            "end": round(end, 3) if end is not None else None,
            "probability": source_word.get("probability"),
            "timing_valid": timing_valid,
        })
    return words, sorted(set(review_reasons))


def _attach_uncertainty(words: list, source_spans: list) -> list[dict]:
    uncertain = []
    used = set()
    for span in source_spans or []:
        index = span.get("word_index")
        match = words[index] if isinstance(index, int) and 0 <= index < len(words) else None
        if match and match["id"] in used:
            match = None
        if match is None:
            match = next((word for word in words if word["id"] not in used and (
                word["word"] == span.get("word")
                and word["start"] == span.get("start")
                and word["end"] == span.get("end")
            )), None)
        if not match:
            continue
        used.add(match["id"])
        uncertain.append({
            **span,
            "word_id": match["id"],
            "start": match["start"],
            "end": match["end"],
        })
    return uncertain


def _result(status, *, transcript="", noise=None, relevant=None, criteria=None, words=None,
            uncertain=None, reasons=None, coaching_flags=None, stt=None, raters=None,
            scope="practice_answer", error=None):
    criteria = criteria or {}
    aliases = {
        "pronun": "pronunciation",
        "fluency": "fluency_coherence",
        "grammar": "grammatical_range_accuracy",
        "vocab": "lexical_resource",
    }
    for alias, key in aliases.items():
        criteria.setdefault(key, _criterion())
    bands = [criteria[key].get("band") for key in aliases.values()]
    overall = None
    if all(band is not None for band in bands):
        from app.modules.speaking.assessment.scoring import overall_of
        overall = overall_of(bands)
        status = "scored"
    elif status == "scored":
        status = "partial"
    words = words or []
    uncertain = uncertain or []
    pronunciation = dict(criteria["pronunciation"])
    output_criteria = {
        "pronunciation": pronunciation,
        "fluency_coherence": criteria["fluency_coherence"],
        "lexical_resource": criteria["lexical_resource"],
        "grammatical_range_accuracy": criteria["grammatical_range_accuracy"],
    }
    provenance = {
        "asr_provider": (stt or {}).get("provider"),
        "asr_model": (stt or {}).get("model"),
        "decode_profile": (stt or {}).get("decode_profile", settings.stt_profile_version),
        "asr_fallback_used": (stt or {}).get("fallback_used", False),
        "rubric_version": RUBRIC_VERSION,
        "rubric_source": RUBRIC_SOURCE,
        "calibration_version": settings.calibration_version,
        "llm_models": {
            key: value.get("model") for key, value in (raters or {}).items()
            if value.get("model")
        },
    }
    text_words = acoustic.color_coded_transcript(words, uncertain)
    payload = {
        "schema_version": "speaking-v3",
        "scope": scope,
        "score_type": "diagnostic",
        "status": status,
        "transcript": transcript,
        "noise": noise,
        "is_relevant": relevant,
        "overall": overall,
        "criteria": output_criteria,
        "pronun": pronunciation,
        "fluency": criteria["fluency_coherence"],
        "grammar": criteria["grammatical_range_accuracy"],
        "vocab": criteria["lexical_resource"],
        "color_coded_transcript": text_words,
        "uncertain_spans": uncertain,
        "review_reasons": sorted(set(reasons or [])),
        "coaching_flags": sorted(set(coaching_flags or [])),
        "transcription": {
            "text": transcript,
            "words": text_words,
            "calibrated": False,
            "provider": (stt or {}).get("provider"),
            "model": (stt or {}).get("model"),
        },
        "provenance": provenance,
        "assessment_meta": _assessment_meta(stt, raters),
        **({"error": error} if error else {}),
    }
    from app.modules.speaking.schemas import SpeakingAssessmentResult
    return SpeakingAssessmentResult.model_validate(payload).model_dump(mode="json")


def _blank_criteria(status="insufficient_evidence", message=None):
    return {
        "pronunciation": _criterion(
            status, None, basis="no_validated_pronunciation_engine", feedback=message,
            band_source="unavailable_no_validated_pronunciation_model",
            evidence_quality="low", problem_words=[], phoneme_evidence=[],
            alignment={"status": "unavailable", "provider": "none"},
            reason="No validated pronunciation-to-band method is available.",
        ),
        "fluency_coherence": _criterion(status, None, basis="missing_or_unreliable_audio_evidence", feedback=message),
        "lexical_resource": _criterion(status, None, basis="missing_or_unreliable_asr_evidence", feedback=message),
        "grammatical_range_accuracy": _criterion(status, None, basis="missing_or_unreliable_asr_evidence", feedback=message),
    }


def _failed_result(reason: str):
    return _result(
        "failed",
        criteria=_blank_criteria("failed", "Chưa thể chấm vì nhà cung cấp chưa sẵn sàng."),
        reasons=[reason],
        error="Speaking assessment provider is not ready",
    )


def failed_result(reason: str, error: str | None = None, scope: str = "practice_answer"):
    return _result(
        "failed",
        scope=scope,
        criteria=_blank_criteria("failed", "Không thể hoàn tất đánh giá."),
        reasons=[reason],
        error=error or "Assessment processing failed",
    )


def _criterion_from_rater(rater: dict, *, basis: str, words: list, uncertainty: list) -> dict:
    status = rater.get("status", "failed")
    band = rater.get("band") if status == "scored" else None
    errors = []
    if rater.get("criterion") == "grammatical_range_accuracy":
        for error in rater.get("errors", []):
            quote = error.get("quote", "")
            errors.append({
                "error": quote,
                "quote": quote,
                "word_ids": error.get("word_ids", []),
                "correct": error.get("correction"),
                "explain": error.get("reason_vi"),
                "error_or_improvement": error.get("error_or_improvement"),
                "verification": "transcript_grounded_audio_not_human_verified",
            })
    return _criterion(
        status,
        band,
        basis=basis,
        feedback=rater.get("feedback_vi") or None,
        errors=errors,
        evidence=rater.get("evidence", []),
        next_action_vi=rater.get("next_action_vi") or None,
        reason=rater.get("failure_reason"),
        relevance=rater.get("relevance"),
        coverage_by_part=rater.get("coverage_by_part", {}),
    )


def grade_speaking(audio_path: str, question: str, task_type: str, tier: str = "practice") -> dict:
    tier = budget.resolve_tier(tier)
    stt_ready = stt_service.provider_readiness()
    llm_ready = provider_readiness()
    if not stt_ready["ready"]:
        return failed_result("stt_provider_not_ready")
    if not llm_ready["ready"]:
        return failed_result("llm_provider_not_ready")

    try:
        stt = stt_service.transcribe(audio_path)
    except Exception as exc:
        return _result(
            "failed", criteria=_blank_criteria("failed", "Không thể nhận dạng audio."),
            reasons=["stt_request_failed"], error=str(exc)[:500],
        )

    transcript = (stt.get("text") or "").strip()
    words, timing_reasons = _as_words(
        stt.get("words") or [], transcript, probe_audio_duration(audio_path),
        allow_unverified_mock=stt.get("provider") == "mock",
    )
    uncertain = _attach_uncertainty(words, stt.get("uncertain_spans") or stt.get("low_conf_spans") or [])
    segments = stt.get("segments") or []
    noise = acoustic.detect_noise(segments, transcript)
    if noise == "cant_hear":
        return _result(
            "cant_hear", transcript=transcript, noise=noise,
            criteria=_blank_criteria("insufficient_evidence", "Không thu được lời nói đủ rõ."),
            words=words, uncertain=uncertain, stt=stt,
        )

    gate_reasons = []
    try:
        hallucination_risk = float(stt.get("hallucination_risk", 0.0) or 0.0)
        agreement = float(stt.get("decode_agreement", 1.0) or 0.0)
    except (TypeError, ValueError):
        hallucination_risk, agreement = 1.0, 0.0
    if hallucination_risk >= settings.speaking_review_hallucination_threshold:
        gate_reasons.append("high_asr_hallucination_risk_heuristic")
    if len(stt.get("nbest_texts") or []) > 1 and agreement < settings.speaking_review_agreement_threshold:
        gate_reasons.append("asr_decode_disagreement")
    if gate_reasons:
        return _result(
            "needs_review", transcript=transcript, noise=noise,
            criteria=_blank_criteria("needs_review", "Cần nghe lại audio trước khi chấm."),
            words=words, uncertain=uncertain, reasons=gate_reasons + timing_reasons, stt=stt,
        )
    if not transcript:
        return _result(
            "cant_hear", noise="cant_hear",
            criteria=_blank_criteria("insufficient_evidence", "Không nhận dạng được lời nói."),
            words=words, uncertain=uncertain, stt=stt,
        )

    timed_words = [word for word in words if word.get("timing_valid")]
    total_duration = 0.0
    if timed_words:
        total_duration = max(0.0, timed_words[-1]["end"] - timed_words[0]["start"])
    pronunciation_observations = pronunciation_service.assess_pronunciation(
        audio_path=audio_path,
        transcript=transcript,
        words=timed_words,
        uncertain_spans=uncertain,
        asr_confidence=stt.get("asr_confidence", 0.0),
        hallucination_risk=stt.get("hallucination_risk", 0.0),
        total_duration_s=total_duration,
    )
    acoustic_result = acoustic.build_acoustic_bands(
        stt_service.mean_avg_logprob(segments), segments, timed_words, transcript,
    )
    audio_features = acoustic_result["features"] if timed_words else {}
    assessment_raters = raters.assess_speaking(
        question,
        transcript,
        tier,
        words=words,
        part=next((int(digit) for digit in re.findall(r"[123]", task_type or "")), None),
        acoustic_features=audio_features,
        uncertain_spans=uncertain,
    )
    criteria = _blank_criteria()
    criteria["pronunciation"] = _criterion(
        "insufficient_evidence",
        basis="audio_timing_and_recording_quality_observations_not_a_pronunciation_band",
        **pronunciation_observations,
    )
    criteria["fluency_coherence"] = _criterion_from_rater(
        assessment_raters["fluency_coherence"], basis="descriptor_judgement_with_audio_timing_support",
        words=words, uncertainty=uncertain,
    )
    criteria["fluency_coherence"]["features"] = audio_features
    criteria["lexical_resource"] = _criterion_from_rater(
        assessment_raters["lexical_resource"], basis="descriptor_judgement_from_verbatim_asr",
        words=words, uncertainty=uncertain,
    )
    criteria["grammatical_range_accuracy"] = _criterion_from_rater(
        assessment_raters["grammatical_range_accuracy"], basis="descriptor_judgement_from_verbatim_asr",
        words=words, uncertainty=uncertain,
    )
    # No timestamps means FC lacks audio-timing evidence, even if transcript text exists.
    if not timed_words:
        criteria["fluency_coherence"] = _criterion(
            "insufficient_evidence", None,
            basis="missing_verified_word_timing",
            feedback="Không có mốc thời gian hợp lệ để đánh giá độ trôi chảy từ audio.",
            reason="Word timing could not be validated against audio duration.",
        )
    relevant = criteria["fluency_coherence"].get("relevance") != "unrelated"
    coaching_flags = [] if relevant else ["off_topic"]
    scores = [criteria[key].get("band") for key in (
        "fluency_coherence", "lexical_resource", "grammatical_range_accuracy",
    )]
    if all(score is None for score in scores) and any(
        criteria[key]["status"] == "needs_review" for key in (
            "fluency_coherence", "lexical_resource", "grammatical_range_accuracy",
        )
    ):
        status = "needs_review"
    elif all(score is None for score in scores) and all(
        criteria[key]["status"] == "failed" for key in (
            "fluency_coherence", "lexical_resource", "grammatical_range_accuracy",
        )
    ):
        status = "failed"
    elif all(
        criteria[key]["status"] == "insufficient_evidence" for key in (
            "fluency_coherence", "lexical_resource", "grammatical_range_accuracy",
        )
    ):
        status = "insufficient_sample"
    else:
        status = "partial"
    rater_reasons = [
        str(rater.get("failure_reason")) for rater in assessment_raters.values()
        if rater.get("failure_reason") and rater.get("status") in {"needs_review", "failed"}
    ]
    result = _result(
        status,
        transcript=transcript,
        noise=noise,
        relevant=relevant,
        criteria=criteria,
        words=words,
        uncertain=uncertain,
        reasons=timing_reasons + rater_reasons,
        coaching_flags=coaching_flags,
        stt=stt,
        raters=assessment_raters,
    )
    budget.record(tier)
    return result


def grade_mock_session(turns: list, tier: str = "exam") -> dict:
    """Assess a full mock from its Part-grouped evidence, never turn means."""
    llm_ready = provider_readiness()
    if not llm_ready["ready"]:
        return _result(
            "failed",
            scope="mock_session",
            criteria=_blank_criteria("failed", "Nhà cung cấp chấm chưa sẵn sàng."),
            reasons=["llm_provider_not_ready"],
            error="Speaking assessment provider is not ready",
        )
    normalized_turns = []
    all_words = []
    all_uncertain = []
    full_transcript = []
    for turn_index, turn in enumerate(turns, start=1):
        result = turn.get("result") or {}
        token_words = result.get("color_coded_transcript") or []
        if not token_words:
            token_words = [{"word": token} for token in re.findall(r"\S+", result.get("transcript", ""))]
        words = []
        for word_index, source in enumerate(token_words, start=1):
            item = dict(source)
            item["id"] = f"t{turn_index}_w{word_index}"
            item["text"] = item.get("word", "")
            item["probability"] = item.get("asr_probability", item.get("probability"))
            words.append(item)
        spans = []
        source_spans = result.get("uncertain_spans") or []
        for span in source_spans:
            word_index = span.get("word_index")
            matched = words[word_index] if isinstance(word_index, int) and 0 <= word_index < len(words) else None
            if matched is None:
                matched = next((word for word in words if (
                    word.get("word") == span.get("word")
                    and word.get("start") == span.get("start")
                    and word.get("end") == span.get("end")
                )), None)
            if matched:
                spans.append({**span, "word_id": matched["id"]})
        all_words.extend(words)
        all_uncertain.extend(spans)
        full_transcript.append(result.get("transcript", ""))
        normalized_turns.append({
            "part": int(turn.get("part", 0)),
            "question": turn.get("question_text", ""),
            "words": words,
            "uncertain_spans": spans,
        })

    assessment_raters = raters.assess_mock_session(normalized_turns, tier)
    criteria = _blank_criteria()
    criteria["pronunciation"] = _criterion(
        "insufficient_evidence", None,
        basis="no_validated_pronunciation_engine",
        feedback="Chưa có phép đo âm vị đã kiểm chứng cho toàn bộ phiên.",
        reason="No validated pronunciation-to-band method is available.",
        band_source="unavailable_no_validated_pronunciation_model",
        evidence_quality="low",
        problem_words=[], phoneme_evidence=[],
        alignment={"status": "unavailable", "provider": settings.pronunciation_aligner},
    )
    criteria["fluency_coherence"] = _criterion_from_rater(
        assessment_raters["fluency_coherence"], basis="session_descriptor_judgement_with_audio_timing_support",
        words=all_words, uncertainty=all_uncertain,
    )
    criteria["lexical_resource"] = _criterion_from_rater(
        assessment_raters["lexical_resource"], basis="session_descriptor_judgement_from_verbatim_asr",
        words=all_words, uncertainty=all_uncertain,
    )
    criteria["grammatical_range_accuracy"] = _criterion_from_rater(
        assessment_raters["grammatical_range_accuracy"], basis="session_descriptor_judgement_from_verbatim_asr",
        words=all_words, uncertainty=all_uncertain,
    )
    failed = all(criteria[key]["status"] == "failed" for key in (
        "fluency_coherence", "lexical_resource", "grammatical_range_accuracy",
    ))
    return _result(
        "failed" if failed else "partial",
        scope="mock_session",
        transcript=" ".join(text for text in full_transcript if text),
        criteria=criteria,
        words=all_words,
        uncertain=all_uncertain,
        raters=assessment_raters,
    )


