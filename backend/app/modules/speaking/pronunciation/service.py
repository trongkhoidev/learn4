"""Compatibility facade for the pronunciation module.

``assessment/engine.py`` calls ``assess_pronunciation`` exactly as before, but
the implementation now delegates to a single ``PronunciationEngine`` interface
(see ``engine.py``). This file owns no scoring logic and must not grow one.
"""

import array
import logging
import math
import statistics
import wave

from app.core.config import settings

from . import policy
from .contracts import PronunciationRequest, WordTiming
from .engine import get_engine

logger = logging.getLogger(__name__)

BAND_SOURCE = policy.BAND_SOURCE_UNAVAILABLE


def analyze_prosody(words, total_duration_s: float) -> dict:
    """Timing/rhythm/pause features from word timestamps (no audio needed)."""
    empty = {
        "coverage": 0.0,
        "speech_rate_wpm": 0.0,
        "articulation_rate": 0.0,
        "pause_ratio": 0.0,
        "long_pauses": 0,
        "duration_mean_s": 0.0,
        "duration_std_s": 0.0,
        "rhythm_cv": 0.0,
        "duration_dispersion_proxy": 0.0,
    }
    timed = []
    for w in words or []:
        try:
            s = float(w.get("start", 0.0) or 0.0)
            e = float(w.get("end", 0.0) or 0.0)
        except (TypeError, ValueError):
            continue
        if e > s and (e - s) < 5.0:
            timed.append(e - s)
    n = len(words or [])
    if not timed or n == 0 or not total_duration_s or total_duration_s <= 0:
        return empty

    mean_d = statistics.fmean(timed)
    std_d = statistics.pstdev(timed) if len(timed) > 1 else 0.0
    gaps = []
    for i in range(1, len(words)):
        try:
            a = float(words[i - 1].get("end", 0.0) or 0.0)
            b = float(words[i].get("start", 0.0) or 0.0)
        except (TypeError, ValueError):
            continue
        if b > a:
            gaps.append(b - a)
    pause_time = sum(g for g in gaps if g > 0.3)
    art_time = total_duration_s - pause_time
    return {
        "coverage": round(len(timed) / n, 3),
        "speech_rate_wpm": round(n / total_duration_s * 60, 1),
        "articulation_rate": round(n / art_time * 60, 1) if art_time > 0 else 0.0,
        "pause_ratio": round(pause_time / total_duration_s, 3),
        "long_pauses": sum(1 for g in gaps if g > 1.0),
        "duration_mean_s": round(mean_d, 3),
        "duration_std_s": round(std_d, 3),
        "rhythm_cv": round(std_d / mean_d, 3) if mean_d > 0 else 0.0,
        # Word duration variation is not lexical stress evidence.
        "duration_dispersion_proxy": round((max(timed) - min(timed)) / mean_d, 3) if mean_d > 0 else 0.0,
    }


def analyze_waveform_energy(audio_path: str | None) -> dict:
    """Energy-based speech/silence features from a PCM WAV file.

    Returns {} when the audio cannot be read as PCM (e.g. raw webm/opus) —
    callers must treat missing energy features as "no evidence", not as bad
    pronunciation.
    """
    if not audio_path:
        return {}
    try:
        with wave.open(audio_path, "rb") as wf:
            n_channels = wf.getnchannels()
            sampwidth = wf.getsampwidth()
            framerate = wf.getframerate()
            n_frames = wf.getnframes()
            if sampwidth != 2 or framerate <= 0 or n_frames <= 0:
                return {}
            raw = wf.readframes(n_frames)
        samples = array.array("h")
        samples.frombytes(raw)
        if n_channels == 2:
            samples = array.array("h", (
                (samples[i] + samples[i + 1]) // 2
                for i in range(0, len(samples) - 1, 2)
            ))
        elif n_channels != 1:
            return {}
        window = max(1, int(framerate * 0.1))  # 100 ms windows
        n_samples = len(samples)
        if n_samples < window:
            return {}
        peak = max(1, max(abs(v) for v in samples))
        clipping = sum(1 for v in samples if abs(v) >= 32760) / n_samples
        energies = []
        for i in range(0, n_samples - window + 1, window):
            seg = samples[i: i + window]
            rms = math.sqrt(sum(v * v for v in seg) / len(seg)) / peak
            energies.append(rms)
        if not energies:
            return {}
        speech = [e for e in energies if e >= 0.05]
        silence = [e for e in energies if e < 0.05]
        snr_proxy = None
        if speech and silence:
            num = sum(speech) / len(speech)
            den = max(1e-6, sum(silence) / len(silence))
            snr_proxy = round(20 * math.log10(num / den), 1)
        return {
            "low_energy_ratio": round(len(silence) / len(energies), 3),
            "clipping_ratio": round(clipping, 4),
            "snr_proxy_db": snr_proxy,
        }
    except Exception as exc:  # unreadable format -> no evidence, not an error
        logger.debug("waveform energy analysis skipped: %s", exc)
        return {}


def intelligibility_proxy(transcript: str, uncertain_spans, hallucination_risk: float) -> dict:
    """Share of the transcript the recognizer itself doubts (0-1)."""
    tokens = [_norm_word(t) for t in (transcript or "").split()]
    tokens = [t for t in tokens if t]
    uncertain_tokens = {
        _norm_word(s.get("word", "")) for s in (uncertain_spans or [])
        if _norm_word(s.get("word", ""))
    }
    ratio = (len([t for t in set(tokens) if t in uncertain_tokens]) / len(set(tokens))) if tokens else 1.0
    try:
        hallu = float(hallucination_risk or 0.0)
    except (TypeError, ValueError):
        hallu = 0.0
    score = max(0.0, min(1.0, 1.0 - ratio - 0.5 * max(0.0, min(1.0, hallu))))
    return {"score": round(score, 3), "uncertain_word_ratio": round(min(1.0, ratio), 3)}


def _norm_word(w: str) -> str:
    return _norm_token(w)


def _norm_token(w: str) -> str:
    return (w or "").strip().lower().strip(".,!?;:\"'()[]")


def filter_problem_words(problem_words, transcript: str, uncertain_spans) -> list:
    """Keep only transcript-grounded claims; relabel ASR-doubtful words.

    - Drop any `heard` word that does not occur in the transcript (LLM
      hallucination guard).
    - Force `type="asr_uncertain"` when the word sits inside an uncertain span.
    """
    tokens = {_norm_token(t) for t in (transcript or "").split() if _norm_token(t)}
    uncertain_tokens = {
        _norm_token(s.get("word", "")) for s in (uncertain_spans or [])
        if _norm_token(s.get("word", ""))
    }
    kept = []
    for pw in problem_words or []:
        if isinstance(pw, str):
            heard, entry = pw, {"heard": pw, "intended": None, "type": "pronun"}
        elif isinstance(pw, dict):
            heard = pw.get("heard", "")
            entry = dict(pw)
        else:
            continue
        if _norm_token(heard) not in tokens:
            continue
        if _norm_token(heard) in uncertain_tokens:
            entry["type"] = "asr_uncertain"
        kept.append(entry)
    return kept


def decide_evidence_quality(asr_confidence: float, is_high_uncertainty: bool,
                            intelligibility: float, prosody_coverage: float) -> str:
    if is_high_uncertainty or asr_confidence < 0.60:
        return "low"
    if asr_confidence < 0.85 or intelligibility < 0.70 or prosody_coverage < 0.50:
        return "medium"
    return "high"


def assess_pronunciation(audio_path=None, transcript: str = "", words=None,
                         uncertain_spans=None, asr_confidence: float = 0.0,
                         hallucination_risk: float = 0.0,
                         total_duration_s: float = 0.0,
                         llm_band: float = 0.0, llm_problem_words=None) -> dict:
    """Facade: build a request and delegate to the configured engine."""
    del llm_band, llm_problem_words  # never a band source
    timed_words = [
        {"id": w.get("id") or f"w{index}", "word": w.get("word", ""),
         "start": w.get("start"), "end": w.get("end")}
        for index, w in enumerate(words or [], start=1)
        if w.get("start") is not None and w.get("end") is not None
        and float(w.get("end") or 0) > float(w.get("start") or 0)
    ]
    uncertain_ids = {
        str(span.get("word_id")) for span in (uncertain_spans or []) if span.get("word_id")
    }
    request = PronunciationRequest(
        audio_path=audio_path or "missing",
        transcript=transcript or "",
        words=[
            WordTiming.model_validate({
                "id": item["id"], "word": item["word"] or "-",
                "start": float(item["start"]), "end": float(item["end"]),
            })
            for item in timed_words
        ],
        asr_uncertain_word_ids=sorted(uncertain_ids),
        asr_confidence=asr_confidence,
        task_metadata={"hallucination_risk": hallucination_risk},
    )

    # One alignment call per assessment, before the engine so real phone
    # timings can drive phone evidence (plan E2). No aligner configured means
    # no decode happens here and no phone layer is claimed.
    from app.modules.speaking.pronunciation import alignment as alignment_service

    aligner = (settings.pronunciation_aligner or "none").lower()
    alignment = alignment_service.align(audio_path, transcript) \
        if audio_path and aligner != "none" \
        and (transcript or "").strip() else {
            "status": "unavailable", "provider": "none", "reason": "disabled",
        }
    request.alignment = {
        "provider": alignment.get("provider", "none"),
        "words": alignment.get("words") or [],
        "phones": alignment.get("phones") or [],
        "coverage": alignment.get("coverage", 0.0),
        "declares_phone_alignment": bool(alignment.get("declares_phone_alignment")),
        "calibrated": False,
    }

    engine_result = get_engine().assess(request)
    assessment = engine_result.model_dump(mode="json")

    # The shadow and enabled engines both decode the audio once: reuse their
    # prosody and energy-derived gates instead of running a second analysis
    # path. The disabled engine leaves the prosody block to legacy code.
    engine_prosody = assessment.get("prosody_features") or {}
    engine_ran = isinstance(engine_prosody, dict) and "feature_version" in engine_prosody
    if engine_ran:
        prosody_features = dict(engine_prosody)
        gates = dict(assessment.get("quality_gates") or {})
        energy = {
            "low_energy_ratio": gates.get("low_energy_ratio"),
            "clipping_ratio": gates.get("clipping_ratio"),
            "snr_proxy_db": gates.get("snr_proxy_db"),
        }
    else:
        prosody_features = analyze_prosody(words, total_duration_s)
        energy = {}
        if audio_path:
            # Normalize a private copy for energy analysis; never touch the input.
            try:
                from app.integrations.audio.processor import normalize_audio_to_wav

                tmp_wav = normalize_audio_to_wav(audio_path)
                try:
                    energy = analyze_waveform_energy(tmp_wav)
                finally:
                    import os

                    try:
                        os.remove(tmp_wav)
                    except OSError:
                        pass
            except Exception as exc:
                logger.debug("pronunciation energy analysis skipped: %s", exc)

    intel = intelligibility_proxy(transcript, uncertain_spans, hallucination_risk)
    word_count = max(1, len((transcript or "").split()))
    is_high_uncertainty = len(uncertain_spans or []) / word_count > 0.30
    evidence_quality = decide_evidence_quality(
        asr_confidence, is_high_uncertainty, intel["score"], prosody_features.get("coverage", 0.0)
    )
    observations = []
    legacy_coverage = prosody_features.get("coverage")
    if legacy_coverage is not None:
        if legacy_coverage > 0:
            observations.append(
                f"Mốc thời gian ghi nhận {prosody_features.get('long_pauses', 0)} khoảng nghỉ "
                "trên 1 giây giữa các từ; cần nghe lại theo cụm ý để xác định đó là ngắt nghỉ "
                "tự nhiên hay ngập ngừng."
            )
        else:
            observations.append("Mốc thời gian chưa đủ để nhận xét nhịp nói trong bản ghi này.")
    elif prosody_features.get("pause_ratio") is not None:
        observations.append(
            f"Mốc thời gian ghi nhận {prosody_features.get('long_pause_count', 0)} khoảng nghỉ "
            f"dài, tỉ lệ nghỉ {prosody_features['pause_ratio']} trên tổng thời lượng; cần nghe "
            "lại theo cụm ý để xác định đó là ngắt nghỉ tự nhiên hay ngập ngừng."
        )
    else:
        observations.append("Mốc thời gian chưa đủ để nhận xét nhịp nói trong bản ghi này.")
    if uncertain_spans:
        observations.append(
            f"Có {len(uncertain_spans)}/{word_count} từ cần nghe lại do nhận dạng chưa chắc chắn; "
            "đây chưa xác nhận lỗi phát âm."
        )
    if energy.get("clipping_ratio", 0) > 0.01:
        observations.append("Bản ghi có dấu hiệu vỡ tiếng; hãy giảm âm lượng hoặc đặt micro xa hơn.")
    observations.append(engine_result.feedback or
                        "Chưa đủ bằng chứng âm vị để kết luận lỗi từng âm, trọng âm hoặc band phát âm.")
    scored = engine_result.status == "scored" and engine_result.band is not None
    return {
        "band": float(engine_result.band) if scored else None,
        "band_source": (
            engine_result.band_source if scored else BAND_SOURCE
        ),
        "confidence": (float(engine_result.confidence) if scored
                       and engine_result.confidence is not None else None),
        "evidence_quality": evidence_quality,
        "prosody_features": prosody_features,
        "energy_features": energy,
        "intelligibility": intel,
        "problem_words": [],
        "reason": (engine_result.reason if scored
                   else engine_result.reason or policy.REASON_NO_VALIDATED_ENGINE),
        "phoneme_evidence": assessment["phoneme_evidence"],
        "alignment": alignment,
        "feedback": " ".join(observations),
        "next_action_vi": assessment["next_action_vi"] or (
            "Bấm nghe lại các từ viền vàng, xác nhận lời đã nói rồi ghi âm lại cả cụm trong ngữ cảnh."
            if uncertain_spans else
            "Chọn một câu trong bản ghi, nghe lại chỗ ngắt cụm rồi đọc lại và so sánh với audio mẫu."
        ),
        "shadow_evidence": assessment if engine_result.shadow else None,
    }
