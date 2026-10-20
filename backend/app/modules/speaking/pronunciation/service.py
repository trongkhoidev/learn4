"""Audio observations for pronunciation coaching.

No forced-alignment / phoneme model is available in this environment, so
phoneme-level (GOP) evidence is explicitly marked pending. This module provides
everything that *can* be measured without it:

- prosody features from word timestamps (timing, rhythm, pause structure),
- waveform energy features when a readable PCM WAV is obtainable,
- an intelligibility proxy from recognition-uncertainty spans,
- problem-word filtering: drop LLM claims not present in the transcript and
  relabel words inside uncertain spans as `asr_uncertain`.

This module does not assign a pronunciation band or phoneme error. Word timing,
ASR uncertainty, and energy summaries are supporting observations only.
"""

import array
import logging
import math
import wave

logger = logging.getLogger(__name__)

BAND_SOURCE = "unavailable_no_validated_pronunciation_model"


def _norm_token(w: str) -> str:
    return (w or "").strip().lower().strip(".,!?;:\"'()[]")


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
    import statistics

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
    """Return only evidence available without a validated pronunciation model."""
    try:
        asr_c = max(0.0, min(1.0, float(asr_confidence or 0.0)))
    except (TypeError, ValueError):
        asr_c = 0.0
    prosody = analyze_prosody(words, total_duration_s)

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
    from app.modules.speaking.pronunciation import alignment as alignment_service
    alignment = alignment_service.align(audio_path, transcript)
    word_count = max(1, len((transcript or "").split()))
    is_high_uncertainty = len(uncertain_spans or []) / word_count > 0.30
    evidence_quality = decide_evidence_quality(
        asr_c, is_high_uncertainty, intel["score"], prosody.get("coverage", 0.0)
    )
    observations = []
    if prosody["coverage"] > 0:
        observations.append(
            f"Mốc thời gian ghi nhận {prosody['long_pauses']} khoảng nghỉ trên 1 giây "
            "giữa các từ; cần nghe lại theo cụm ý để xác định đó là ngắt nghỉ tự nhiên hay ngập ngừng."
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
    observations.append("Chưa đủ bằng chứng âm vị để kết luận lỗi từng âm, trọng âm hoặc band phát âm.")
    next_action = (
        "Bấm nghe lại các từ viền vàng, xác nhận lời đã nói rồi ghi âm lại cả cụm trong ngữ cảnh."
        if uncertain_spans else
        "Chọn một câu trong bản ghi, nghe lại chỗ ngắt cụm rồi đọc lại và so sánh với audio mẫu."
    )
    return {
        "band": None,
        "band_source": BAND_SOURCE,
        "confidence": None,
        "evidence_quality": evidence_quality,
        "prosody_features": prosody,
        "energy_features": energy,
        "intelligibility": intel,
        "problem_words": [],
        "reason": "No validated pronunciation-to-band or phoneme-error engine is available.",
        "phoneme_evidence": [],
        "alignment": alignment,
        "feedback": " ".join(observations),
        "next_action_vi": next_action,
    }
