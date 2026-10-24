"""PronunciationEngine orchestration behind a small public interface.

Implemented modes (config ``pronunciation_mode``):

- ``disabled`` (production default): observations only, ``band=None``.
- ``shadow``: also runs the deterministic feature/GOP core and returns it as
  shadow evidence that never replaces the learner-facing result.
- ``enabled``: requires a loaded, examiner-calibrated artifact; every missing
  condition fails closed to abstention (``band=None``).

Dependencies (aligner, phone model, feature extractor, artifact loader) are
injected; tests run without models, network or downloads.
"""

import logging
from typing import Optional, Protocol

from app.core.config import settings

from . import audio_features, gop, lexicon as lexicon_module, prosody
from .calibration import ArtifactInvalid, load_or_none, predicted_band
from .contracts import (
    ENGINE_VERSION,
    FEATURE_VERSION,
    PhoneEvidence,
    PronunciationAssessment,
    PronunciationProvenance,
    PronunciationRequest,
)
from .phone_model import PhoneModelUnavailable, PhonePosteriorModel
from .policy import (
    BAND_SOURCE_UNAVAILABLE,
    CALIBRATED_BAND_SOURCE,
    REASON_NO_VALIDATED_ENGINE,
    band_eligibility,
    mode as configured_mode,
)

logger = logging.getLogger(__name__)


class PronunciationEngine(Protocol):
    def assess(self, request: PronunciationRequest) -> PronunciationAssessment: ...


NO_PHRONEME_FEEDBACK = (
    "Chưa đủ bằng chứng âm vị để kết luận lỗi từng âm, trọng âm hoặc band phát âm. "
    "Các nhận định dưới đây là quan sát hỗ trợ, chưa phải lỗi phát âm đã xác nhận."
)


def _listen_again_note(uncertain_word_ids: set[str]) -> Optional[str]:
    if not uncertain_word_ids:
        return None
    return (
        f"Có {len(uncertain_word_ids)} từ cần nghe lại do nhận dạng chưa chắc chắn; "
        "đây chưa xác nhận lỗi phát âm."
    )


def _aligned_phone_intervals(alignment: dict) -> list[dict]:
    """Validated real phone intervals from a normalized alignment contract."""
    if alignment.get("declares_phone_alignment") is not True:
        return []
    return [
        interval for interval in alignment.get("phones") or []
        if isinstance(interval, dict)
        and str(interval.get("phone", "")).strip()
        and _finite_pair(interval.get("start"), interval.get("end"))
        and interval["end"] > interval["start"]
        and interval["start"] >= 0
    ]


def _finite_pair(start, end) -> bool:
    return (isinstance(start, (int, float)) and not isinstance(start, bool)
            and isinstance(end, (int, float)) and not isinstance(end, bool))


def _plain_phone(name: str) -> str:
    """`AH0`/`AH_s3` -> `AH` so lexicon phones match aligned inventories."""
    return str(name).strip().rstrip("012").split("_", 1)[0]


def _match_phones_in_span(intervals: list[dict], start: float, end: float,
                          phones: list[str]) -> list[tuple[str, tuple[float, float]]]:
    """Greedy deterministic word->phone match in time order.

    Only intervals whose midpoint sits inside the word span are eligible; a
    span that cannot host every expected phone yields no match at all (the
    caller must abstain for that word, not approximate).
    """
    eligible = sorted(
        (
            (_plain_phone(interval["phone"]), (float(interval["start"]),
                                               float(interval["end"])))
            for interval in intervals
            if start <= (float(interval["start"]) + float(interval["end"])) / 2 < end
            or (float(interval["start"]) >= start and float(interval["end"]) <= end)
        ),
        key=lambda item: item[1][0],
    )
    if len(eligible) != len(phones) or eligible == []:
        return []
    # expected phones and aligned intervals may differ in inventory naming;
    # match positionally but verify both sides agree phonetically when possible.
    return list(zip(phones, (interval[1] for interval in eligible)))


class DisabledPronunciationEngine:
    """Production default: timing/energy observations, always nullable band."""

    def assess(self, request: PronunciationRequest) -> PronunciationAssessment:
        uncertain = set(request.asr_uncertain_word_ids)
        prosody_features = {}
        quality = {"gate_reasons": ["pronunciation_engine_disabled"], "duration_ok": None}
        feedback_parts = []
        note = _listen_again_note(uncertain)
        if note:
            feedback_parts.append(note)
        feedback_parts.append(NO_PHRONEME_FEEDBACK)
        return PronunciationAssessment(
            status="insufficient_evidence",
            band=None,
            band_source=BAND_SOURCE_UNAVAILABLE,
            confidence=None,
            evidence_quality="low",
            reason=REASON_NO_VALIDATED_ENGINE,
            feedback=" ".join(feedback_parts),
            next_action_vi=(
                "Bấm nghe lại các từ viền vàng, xác nhận lời đã nói rồi ghi âm lại "
                "cả cụm trong ngữ cảnh." if uncertain else
                "Chọn một câu trong bản ghi, nghe lại chỗ ngắt cụm rồi đọc lại và so "
                "sánh với audio mẫu."
            ),
            phoneme_evidence=[],
            prosody_features=prosody_features,
            quality_gates=quality,
            provenance=PronunciationProvenance(
                engine_version=ENGINE_VERSION,
                feature_version=FEATURE_VERSION,
                alignment_provider="none",
                phone_model="",
                calibration_version="uncalibrated",
                g2p_source="none",
            ),
            shadow=False,
        )


class ShadowPronunciationEngine:
    """Runs the deterministic core; result is shadow evidence, never a band.

    Audio handling reuses the audio processor: a private temporary mono 16 kHz
    PCM copy is created and removed in ``finally`` (plan §4, P2).
    """

    def __init__(self, phone_model: PhonePosteriorModel | None = None,
                 lexicon: lexicon_module.Lexicon | None = None):
        self.phone_model = phone_model
        self.lexicon = lexicon or lexicon_module.get_lexicon()

    def assess(self, request: PronunciationRequest) -> PronunciationAssessment:
        uncertain = set(request.asr_uncertain_word_ids)
        missing_word_reasons = []
        prosody_features: dict = {}
        quality: dict = {"gate_reasons": []}
        phone_evidence: list[PhoneEvidence] = []
        alignment_provider = "none"
        phone_model_name = ""
        audio_duration = None
        try:
            pcm = audio_features.load_pcm_mono_16k(request.audio_path)
        except Exception as exc:  # decode failure => abstention, never a score
            logger.info("pronunciation PCM load failed: %s", exc)
            quality["gate_reasons"].append("audio_unreadable")
            pcm = None
        if pcm is not None:
            audio_duration = pcm.duration_s
            gates = audio_features.audio_quality_gates(pcm)
            quality = {**gates, "gate_reasons": list(gates["gate_reasons"])}
            prosody_features = prosody.extract_prosody_features(
                pcm, [word.model_dump() for word in request.words],
            )
            phone_evidence, evidence_missing_reasons = self._phone_evidence(pcm, request)
            alignment = request.alignment if isinstance(request.alignment, dict) else {}
            alignment_provider = str(alignment.get("provider") or "none")
            if self.phone_model is not None:
                phone_model_name = getattr(self.phone_model, "name", "") or "configured"
            missing_word_reasons.extend(evidence_missing_reasons)
        if not request.words:
            missing_word_reasons.append("no_word_timings")
        evidence_quality = self._evidence_quality(quality, uncertain, request, prosody_features)
        note = _listen_again_note(uncertain)
        feedback_parts = [note] if note else []
        feedback_parts.append(NO_PHRONEME_FEEDBACK)
        feedback = " ".join(feedback_parts)
        return PronunciationAssessment(
            status="insufficient_evidence",
            band=None,
            band_source=BAND_SOURCE_UNAVAILABLE,
            confidence=None,
            evidence_quality=evidence_quality,
            reason=REASON_NO_VALIDATED_ENGINE,
            feedback=feedback or NO_PHRONEME_FEEDBACK,
            next_action_vi=(
                "Bấm nghe lại các từ viền vàng rồi ghi âm lại cả cụm." if uncertain else None
            ),
            phoneme_evidence=phone_evidence,
            prosody_features=prosody_features,
            quality_gates={
                **quality,
                "missing_reasons": missing_word_reasons,
            },
            provenance=PronunciationProvenance(
                engine_version=ENGINE_VERSION,
                feature_version=FEATURE_VERSION,
                alignment_provider=alignment_provider,
                phone_model=phone_model_name,
                calibration_version="uncalibrated",
                g2p_source=self.lexicon.loaded and "lexicon_file" or "rule_based_g2p",
                audio_duration_s=audio_duration,
            ),
            shadow=True,
        )

    def _evidence_quality(self, quality: dict, uncertain: set, request, prosody_features: dict) -> str:
        """Deterministic heuristic for how much to trust the shadow observation.

        Gate reasons and ASR-uncertainty only pick a listening-replay label;
        this is never a band and never scores audio quality numerically.
        """
        reasons = set(quality.get("gate_reasons") or [])
        coverage = prosody_features.get("voiced_coverage")
        if reasons & {
            "audio_too_short", "clipping_detected", "mostly_silence", "audio_unreadable",
        }:
            return "low"
        fraction = len(uncertain) / max(1, len(request.words) or 1)
        if fraction > 0.3:
            return "low"
        if isinstance(coverage, (int, float)) and coverage < 0.1:
            return "low"
        return "medium"

    def _phone_evidence(self, pcm, request) -> tuple[list[PhoneEvidence], list[str]]:
        """Candidate phone observations from a REAL aligned phone layer.

        Timing always comes from the forced-alignment intervals in the request
        (plan E2: alignment positions evidence). Without real phone alignment
        this engine abstains at the phone level — it never slices word spans
        evenly and pretends that was alignment.
        """
        alignment = request.alignment if isinstance(request.alignment, dict) else {}
        aligned = _aligned_phone_intervals(alignment)
        missing: list[str] = []
        if self.phone_model is None:
            return [], ["phone_model_unavailable"]
        if not aligned:
            missing.append("real_phone_alignment_unavailable")
            return [], missing
        try:
            frames = self.phone_model.posterior_frames(request.audio_path)
        except PhoneModelUnavailable as exc:
            logger.info("phone model unavailable in shadow: %s", exc)
            return [], ["phone_model_unavailable"]
        evidence: list[PhoneEvidence] = []
        for index, word in enumerate(request.words):
            if word.id in set(request.asr_uncertain_word_ids):
                continue
            result = self.lexicon.lookup(
                word.word,
                is_proper_noun=word.id in set(request.is_proper_noun),
            )
            if not result.usable_for_claims:
                continue  # unresolved / OOV: abstain at the phone level
            phones = result.phones
            if not phones:
                continue
            matched = _match_phones_in_span(aligned, word.start, word.end, phones)
            if len(matched) < len(phones):
                missing.append(f"word_{word.id}_unaligned_phone")
                continue  # partial alignment: no phone claims for this word
            for matched_index, (phone, interval) in enumerate(matched):
                start, end = interval
                start_frame = int(start / self.phone_model.hop_s)
                end_frame = max(start_frame + 1, int(end / self.phone_model.hop_s))
                raw = gop.assess_phone(
                    frames,
                    target=phone,
                    start_frame=start_frame,
                    end_frame=end_frame,
                    duration_s=end - start,
                    word_id=word.id,
                    word=word.word,
                    start_s=start,
                    end_s=end,
                    model_version=self.phone_model.version,
                    evidence_id=f"pe_{index + 1}_{matched_index + 1}",
                )
                if raw is None:
                    continue
                explanation = (
                    f"Âm /{phone}/ trong từ '{word.word}' cần được nghe lại."
                    if raw.get("score_unscaled") is not None and raw["score_unscaled"] < 0
                    else f"Quan sát ứng viên cho âm /{phone}/ trong từ '{word.word}'."
                )
                raw["explanation_vi"] = explanation
                raw["practice_hint_vi"] = (
                    f"Nghe lại từ '{word.word}' ở đoạn {start:.2f}s và đọc lại cả cụm."
                )
                try:
                    evidence.append(PhoneEvidence.model_validate(raw))
                except ValueError as exc:
                    logger.info("candidate evidence rejected: %s", exc)
        return evidence, missing


class EnabledPronunciationEngine(ShadowPronunciationEngine):
    """Band scoring mode; fails closed whenever the artifact is not eligible."""

    def __init__(self, artifact_path: str | None = None, **kwargs):
        super().__init__(**kwargs)
        artifact, detail, failure = load_or_none(
            artifact_path or settings.pronunciation_artifact_path,
        )
        self._artifact = artifact
        self._artifact_detail = detail
        self._artifact_failure = failure

    def assess(self, request: PronunciationRequest) -> PronunciationAssessment:
        result = super().assess(request)
        eligible, reason = band_eligibility(self._artifact)
        if not eligible:
            result.band = None
            result.band_source = BAND_SOURCE_UNAVAILABLE
            result.status = "insufficient_evidence"
            result.reason = f"{REASON_NO_VALIDATED_ENGINE} ({reason})"
            result.shadow = False
            return result
        band = self._apply_artifact(request, result)
        if band is None:
            result.status = "insufficient_evidence"
            result.reason = f"{REASON_NO_VALIDATED_ENGINE} (calibration_features_unavailable)"
            result.shadow = False
            return result
        result.band = band
        result.band_source = CALIBRATED_BAND_SOURCE
        result.confidence = None  # no probability surface at runtime
        result.status = "scored"
        result.reason = None
        result.shadow = False
        return result

    def _apply_artifact(self, request, result) -> float | None:
        """Session feature vector -> calibrated band; None = fail closed.

        Every feature key the artifact's coefficients reference must be a
        finite number in the current vector; missing keys mean abstention,
        never a default value.
        """
        artifact = self._artifact
        coefficients = artifact.get("coefficients") or {}
        standardization = artifact.get("standardization") or {}
        mean, scale = standardization.get("mean") or [], standardization.get("scale") or []
        features = {
            key: value for key, value in (result.prosody_features or {}).items()
            if isinstance(value, (int, float)) and not isinstance(value, bool)
        }
        keys = list(coefficients)
        if len(mean) != len(keys) or len(scale) != len(keys):
            return None  # artifact incomplete: loader schema drift protection
        try:
            score = float(artifact.get("bias") or 0.0)
            for index, key in enumerate(keys):
                if key not in features:
                    return None
                score += (
                    float(coefficients[key])
                    * (float(features[key]) - float(mean[index]))
                    / (float(scale[index]) or 1.0)
                )
            band = predicted_band(artifact, score)
        except (TypeError, ValueError, ArtifactInvalid):
            return None
        return band


def _shadow_engine_kwargs(phone_model, lexicon) -> dict:
    return {"phone_model": phone_model, "lexicon": lexicon}


def get_engine(
    phone_model: PhonePosteriorModel | None = None,
    lexicon: Optional[lexicon_module.Lexicon] = None,
) -> PronunciationEngine:
    """Resolve the configured engine; disabled mode is the production default.

    ``disabled`` never runs audio inference. ``shadow``/``enabled`` only work
    with injectable dependencies; a missing phone model simply degrades the
    deterministic core to prosody-only evidence (still ``band=None``).
    """
    selected = configured_mode()
    if selected == "disabled":
        return DisabledPronunciationEngine()
    if phone_model is None:
        try:
            from .phone_model import get_phone_model as resolve_phone_model

            phone_model = resolve_phone_model()
        except PhoneModelUnavailable as exc:
            logger.info("shadow engine without phone model: %s", exc)
    if selected == "enabled":
        return EnabledPronunciationEngine(
            artifact_path=settings.pronunciation_artifact_path,
            **_shadow_engine_kwargs(phone_model, lexicon),
        )
    return ShadowPronunciationEngine(**_shadow_engine_kwargs(phone_model, lexicon))


def reset_engine() -> None:
    """Kept for backward compatibility; engines are constructed per call."""
    return None


def capability_readiness() -> dict:
    """Shadow-wiring health probe (plan §P7). Never blocks core scoring.

    ``ready`` means "this mode can do what it promises right now". Shadow mode
    stays healthy when the phone model is absent — it degrades to prosody-only
    evidence by design (still ``band=None``). Only ``enabled`` mode can be
    unready, because scoring without a valid artifact is never acceptable.
    """
    selected = configured_mode()
    state = {"mode": selected, "ready": True, "state": "disabled"}
    if selected == "disabled":
        return state
    if selected == "shadow":
        from .phone_model import PhoneModelUnavailable, get_phone_model

        try:
            phone_model = get_phone_model()
            state["phone_model"] = phone_model.name
            state["state"] = "shadow_full"
        except PhoneModelUnavailable as exc:
            state["phone_model"] = None
            state["state"] = "degraded_prosody_only"
            state["detail"] = str(exc)
        return state
    # enabled: fail closed whenever the calibrated artifact is not loadable
    from .calibration import load_or_none

    artifact, detail, failure = load_or_none(settings.pronunciation_artifact_path)
    state.update({
        "artifact": artifact is not None,
        "detail": detail,
    })
    if artifact is None:
        state.update({"ready": False, "state": "artifact_missing_or_invalid",
                      "failure_reason": failure})
    else:
        state["state"] = "enabled_scored"
    return state
