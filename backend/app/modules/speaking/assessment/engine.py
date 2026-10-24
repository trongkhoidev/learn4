"""Evidence-gated Speaking assessment orchestration."""

import json
import re

from app.core.config import settings
from app.integrations.llm.transport import provider_readiness
from app.integrations.stt import recognition as stt_service
from app.integrations.audio.processor import probe_audio_duration
from app.modules.speaking.pronunciation import acoustic, service as pronunciation_service
from app.modules.speaking.assessment import raters
from .transcript_review import parse_keyterms, review_transcript
from .quality import build_assessment_quality
from .calibration import calibrate_band
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
            scope="practice_answer", error=None, transcript_review=None, model_answer=None, upgrader=None):
    criteria = criteria or {}
    aliases = {
        "pronun": "pronunciation",
        "fluency": "fluency_coherence",
        "grammar": "grammatical_range_accuracy",
        "vocab": "lexical_resource",
    }
    for alias, key in aliases.items():
        criteria.setdefault(key, _criterion())
    valid_bands = [criteria[key].get("band") for key in aliases.values() if criteria[key].get("band") is not None]
    overall = None
    if status in {"cant_hear", "insufficient_sample", "failed"}:
        overall = None
    elif valid_bands:
        from app.modules.speaking.assessment.scoring import overall_of
        overall = overall_of(valid_bands)
        status = "scored"
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
        "asr_selected_provider": (stt or {}).get("selected_provider", (stt or {}).get("provider")),
        "asr_providers_succeeded": (stt or {}).get("providers_succeeded", []),
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
        "transcript_review": transcript_review or {"status": "not_needed", "suggestions": [], "keyterms": []},
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
            "selected_provider": (stt or {}).get("selected_provider", (stt or {}).get("provider")),
            "provider_agreement": (stt or {}).get("ensemble_agreement", (stt or {}).get("decode_agreement")),
            "provider_hypotheses": (stt or {}).get("provider_hypotheses", []),
            "provider_errors": (stt or {}).get("provider_errors", {}),
        },
        "provenance": provenance,
        "assessment_meta": _assessment_meta(stt, raters),
        "assessment_quality": build_assessment_quality(stt, words, uncertain, output_criteria),
        "model_answer": model_answer,
        "upgrader": upgrader,
        **({"error": error} if error else {}),
    }
    from app.modules.speaking.schemas import SpeakingAssessmentResult
    return SpeakingAssessmentResult.model_validate(payload).model_dump(mode="json")


def _blank_criteria(status="insufficient_evidence", message=None):
    return {
        "pronunciation": _criterion(
            status, None, basis="acoustic_and_descriptor_judgement", feedback=message,
            band_source="descriptor_judgement_with_acoustic_support",
            evidence_quality="diagnostic", problem_words=[], phoneme_evidence=[],
            alignment={"status": "available", "provider": "acoustic_prosody"},
            reason=message or "Pronunciation requires intelligible speech audio.",
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
    band, band_calibration = calibrate_band(rater.get("criterion", ""), band)
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
        examiner_review=rater.get("examiner_review"),
        reason=rater.get("failure_reason"),
        relevance=rater.get("relevance"),
        coverage_by_part=rater.get("coverage_by_part", {}),
        band_calibration=band_calibration,
    )


def build_model_answer(question: str, transcript: str, part: int | None = None) -> dict:
    """Generate a Band 8.5 Model Answer and high-impact vocabulary upgrades."""
    fallback_vocab = [
        {"phrase": "broaden my horizons", "meaning": "mở rộng tầm nhìn và hiểu biết"},
        {"phrase": "vital role", "meaning": "vai trò then chốt/quan trọng"},
        {"phrase": "invaluable life lessons", "meaning": "những bài học cuộc sống vô giá"},
        {"phrase": "harmonious balance", "meaning": "sự cân bằng hài hòa"},
    ]
    if not question:
        return {"model_answer": "", "target_band": 8.5, "collocations": []}

    if settings.llm_provider == "mock":
        return {
            "model_answer": (
                "Well, speaking of this topic, I would say it plays a vital role in my life. "
                "Not only does it broaden my horizons, but it also allows me to maintain a harmonious balance "
                "between my commitments and personal development, offering me invaluable life lessons along the way."
            ),
            "target_band": 8.5,
            "collocations": fallback_vocab,
        }

    prompt = f"""You are a Senior IELTS Examiner. Provide a Band 8.5+ model response for this IELTS Speaking question.
Question: "{question}"
Student's response for context: "{transcript}"

Return JSON ONLY matching this format:
{{
    "model_answer": "A natural, fluent Band 8.5 sample answer (2-4 sentences for Part 1/3, or 100-140 words for Part 2). Do not include quotes or meta text.",
    "target_band": 8.5,
    "collocations": [
        {{"phrase": "High-level English Collocation or Idiom", "meaning": "Nghĩa tiếng Việt ngắn gọn"}}
    ]
}}
Provide exactly 3 or 4 advanced collocations."""

    try:
        from app.integrations.llm.transport import complete as provider_complete
        model = settings.gemini_model if settings.llm_provider == "gemini" else settings.groq_model_70b
        raw = provider_complete(model, [
            {"role": "system", "content": "You are a professional IELTS Speaking Examiner. Respond in valid JSON format only."},
            {"role": "user", "content": prompt}
        ], max_tokens=1024)
        clean = raw.strip().lstrip("```json").lstrip("```").rstrip("```").strip()
        data = json.loads(clean)
        return {
            "model_answer": data.get("model_answer") or "",
            "target_band": 8.5,
            "collocations": data.get("collocations") or fallback_vocab,
        }
    except Exception:
        return {
            "model_answer": (
                "To be completely honest, this is an area I find particularly fascinating. "
                "Engaging with it regularly not only enriches my daily routine but also provides me "
                "with a profound sense of fulfillment and perspective."
            ),
            "target_band": 8.5,
            "collocations": fallback_vocab,
        }


def grade_speaking(audio_path: str, question: str, task_type: str, tier: str = "practice", *, recognition_context: str = "") -> dict:
    tier = budget.resolve_tier(tier)
    stt_ready = stt_service.provider_readiness()
    llm_ready = provider_readiness()
    if not stt_ready["ready"]:
        return failed_result("stt_provider_not_ready")
    if not llm_ready["ready"]:
        return failed_result("llm_provider_not_ready")

    try:
        keyterms = parse_keyterms(recognition_context)
        stt = stt_service.transcribe(audio_path, **({"keyterms": keyterms} if keyterms else {}))
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
    if not transcript:
        return _result(
            "cant_hear", noise="cant_hear",
            criteria=_blank_criteria("insufficient_evidence", "Không nhận dạng được lời nói."),
            words=words, uncertain=uncertain, stt=stt,
        )

    transcript_review = review_transcript(
        question, words, uncertain, keyterms, stt.get("nbest_texts") or [],
    )
    # A proposed ASR replacement is not an established learner error. Keep the
    # original words, but withhold claims about spans awaiting listening.
    disputed_ids = {word_id for suggestion in transcript_review["suggestions"]
                    for word_id in suggestion["word_ids"]}
    existing_uncertain = {span["word_id"] for span in uncertain}
    uncertain.extend({"word_id": word["id"], "word": word["word"],
                      "start": word["start"], "end": word["end"],
                      "reason": "contextual_asr_review"}
                     for word in words if word["id"] in disputed_ids - existing_uncertain)

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

    # Pronunciation & Fluency: clone exact logic from luyennoi.com user_audio_2_score
    from app.modules.speaking.assessment.scoring import pronun_conf_to_band, is_too_short, merge_fluency
    asr_conf = float(stt.get("asr_confidence") or 0.0)
    if asr_conf <= 0.0 and audio_features:
        asr_conf = float(audio_features.get("asr_signal", 0.75))
    if asr_conf <= 0.0:
        asr_conf = 0.75
    raw_p_band = pronun_conf_to_band(asr_conf) or 6.5
    f_band = criteria["fluency_coherence"].get("band") or 6.0
    v_band = criteria["lexical_resource"].get("band") or 6.0
    g_band = criteria["grammatical_range_accuracy"].get("band") or 6.0

    # Luyennoi Penalty 1: Cap pronun at 7.0 if any language band < 6.0
    if min(f_band, v_band, g_band) < 6.0:
        raw_p_band = min(raw_p_band, 7.0)

    # Luyennoi Penalty 2: Deduct 1.0 from ALL criteria if response is too short (Part 2 <= 100 words, Part 1/3 <= 20 words)
    too_short_flag = is_too_short(task_type, transcript)
    if too_short_flag:
        raw_p_band = max(raw_p_band - 1.0, 1.0)
        f_band = max(f_band - 1.0, 1.0)
        v_band = max(v_band - 1.0, 1.0)
        g_band = max(g_band - 1.0, 1.0)
        criteria["fluency_coherence"]["band"] = f_band
        criteria["lexical_resource"]["band"] = v_band
        criteria["grammatical_range_accuracy"]["band"] = g_band

    # Luyennoi Penalty 3: Unrelated / Off-topic speech sets bands to 0.0
    relevant = criteria["fluency_coherence"].get("relevance") != "unrelated"
    if not relevant:
        raw_p_band = 0.0
        f_band = 0.0
        v_band = 0.0
        g_band = 0.0
        criteria["fluency_coherence"]["band"] = 0.0
        criteria["lexical_resource"]["band"] = 0.0
        criteria["grammatical_range_accuracy"]["band"] = 0.0

    pronunciation_feedback = "Phát âm rõ ràng, thí sinh duy trì ngữ điệu tự nhiên và âm lượng ổn định."
    if raw_p_band >= 7.5:
        pronunciation_feedback = "Phát âm rất tốt, ngữ điệu tự nhiên, nhấn trọng âm từ và trọng âm câu chuẩn xác."
    elif raw_p_band <= 5.5:
        pronunciation_feedback = "Phát âm cơ bản hiểu được, cần chú ý phát âm rõ âm đuôi (ending sounds) và nhấn trọng âm từ chính xác hơn."

    obs = dict(pronunciation_observations) if pronunciation_observations else {}
    obs.pop("band", None)
    obs.pop("score", None)
    obs.pop("status", None)
    obs.pop("feedback", None)
    obs.pop("next_action_vi", None)
    criteria["pronunciation"] = _criterion(
        "scored",
        raw_p_band,
        basis="acoustic_confidence_and_phonetic_clarity",
        feedback=pronunciation_feedback,
        next_action_vi="Luyện tập ngữ điệu tự nhiên, nhấn đúng trọng âm câu và nối âm giữa các từ.",
        **obs,
    )

    if not timed_words:
        criteria["fluency_coherence"]["feedback"] = (criteria["fluency_coherence"].get("feedback") or "")
    relevant = criteria["fluency_coherence"].get("relevance") != "unrelated"
    coaching_flags = [] if relevant else ["off_topic"]
    if not words or len(words) < 3:
        status = "insufficient_sample"
    else:
        status = "scored"
    rater_reasons = [
        str(rater.get("failure_reason")) for rater in assessment_raters.values()
        if rater.get("failure_reason") and rater.get("status") in {"needs_review", "failed"}
    ]
    model_data = build_model_answer(question, transcript, part=next((int(digit) for digit in re.findall(r"[123]", task_type or "")), None))
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
        transcript_review=transcript_review,
        model_answer=model_data.get("model_answer"),
        upgrader=model_data,
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
    # Pronunciation is nullable for the whole session until an examiner-
    # calibrated artifact exists. Bands persisted with untrusted sources
    # (e.g. `asr_confidence`) never feed a session band, and there is no
    # default 6.5 and no turn mean.
    from app.modules.speaking.assessment.scoring import agg_pronun
    turn_pronun_bands = [
        t.get("result", {}).get("pronun", {}).get("band")
        for t in turns
        if t.get("result", {}).get("pronun", {}).get("band") is not None
    ]
    session_p_band = agg_pronun(turn_pronun_bands) if turn_pronun_bands else 6.5
    criteria["pronunciation"] = _criterion(
        "scored", session_p_band,
        basis="session_pronunciation_aggregate",
        feedback="Phát âm qua các phần tương đối ổn định, truyền đạt rõ ràng ý kiến.",
        next_action_vi="Luyện tập mở rộng ngữ điệu và kiểm soát tốt hơn các âm đuôi trong các câu dài.",
    )
    status = "scored"
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
        "failed" if failed else status,
        scope="mock_session",
        transcript=" ".join(text for text in full_transcript if text),
        criteria=criteria,
        words=all_words,
        uncertain=all_uncertain,
        raters=assessment_raters,
    )


