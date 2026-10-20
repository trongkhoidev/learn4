"""Speech recognition with explicit evidence and uncertainty signals.

Whisper is an ASR model, not an IELTS pronunciation examiner. This module
keeps recognition confidence separate from pronunciation scoring and flags
doubtful spans instead of presenting them as learner errors.
"""

import logging
import math
import os
import re
import threading
import time
from difflib import SequenceMatcher

from app.core.config import settings
from app.integrations.audio.processor import normalize_audio_to_wav

_model = None
_model_error = None
_model_lock = threading.Lock()
_decode_lock = threading.Lock()
logger = logging.getLogger(__name__)


def _load_model():
    global _model, _model_error
    with _model_lock:
        if _model is None:
            try:
                from faster_whisper import WhisperModel

                _model = WhisperModel(
                    settings.whisper_model,
                    device=settings.whisper_device,
                    compute_type=settings.whisper_compute_type,
                    cpu_threads=settings.whisper_cpu_threads,
                    num_workers=1,
                )
                _model_error = None
            except Exception as exc:
                _model_error = type(exc).__name__
                raise
    return _model


def preload() -> None:
    if settings.stt_provider in {"selfhost", "auto"}:
        try:
            _load_model()
        except Exception:
            if settings.stt_provider != "auto" or not settings.groq_api_key:
                raise
            logger.warning("Local STT preload failed; configured Groq fallback is available")


def readiness() -> dict:
    needs_local = settings.stt_provider in {"selfhost", "auto"}
    local_ready = _model is not None or (not settings.whisper_preload and _model_error is None)
    remote_ready = bool(settings.groq_api_key)
    config = provider_readiness()
    ready = config["ready"]
    if needs_local:
        ready = local_ready or (settings.stt_provider == "auto" and remote_ready)
    return {
        "provider": settings.stt_provider,
        "model": config["model"],
        "model_loaded": _model is not None,
        "model_error": _model_error,
        "local_state": (
            "disabled" if not needs_local else "loaded" if _model is not None
            else "failed" if _model_error else "not_loaded"
        ),
        "fallback_available": settings.stt_provider == "auto" and remote_ready,
        "ready": ready,
    }


def provider_readiness() -> dict:
    """Configuration readiness without loading a model or contacting a provider."""
    provider = settings.stt_provider
    if provider == "mock":
        return {"ready": True, "provider": "mock", "model": "mock", "mock_explicit": True}
    if provider == "selfhost":
        ready, model = True, settings.whisper_model
    elif provider == "groq":
        ready, model = bool(settings.groq_api_key), settings.groq_stt_model
    elif provider == "auto":
        ready, model = True, settings.whisper_model
    else:
        ready, model = False, None
    return {"ready": ready, "provider": provider, "model": model, "mock_explicit": False}


def _segment_dict(segment) -> dict:
    return {
        "start": round(float(getattr(segment, "start", 0.0) or 0.0), 3),
        "end": round(float(getattr(segment, "end", 0.0) or 0.0), 3),
        "avg_logprob": getattr(segment, "avg_logprob", None),
        "no_speech_prob": getattr(segment, "no_speech_prob", None),
        "compression_ratio": getattr(segment, "compression_ratio", None),
    }


def _word_dict(word) -> dict:
    probability = getattr(word, "probability", None)
    return {
        "word": (getattr(word, "word", "") or "").strip(),
        "start": round(float(getattr(word, "start", 0.0) or 0.0), 3),
        "end": round(float(getattr(word, "end", 0.0) or 0.0), 3),
        "probability": float(probability) if probability is not None else None,
    }


def _decode(model, audio_path, *, beam_size=5, temperature=0.0):
    segments, _info = model.transcribe(
        audio_path,
        language="en",
        task="transcribe",
        beam_size=beam_size,
        temperature=temperature,
        word_timestamps=True,
        vad_filter=True,
        vad_parameters={"min_silence_duration_ms": 300},
        condition_on_previous_text=False,
        no_speech_threshold=0.6,
        log_prob_threshold=-1.0,
        compression_ratio_threshold=2.4,
    )
    seg_list = list(segments)
    text = " ".join((getattr(s, "text", "") or "").strip() for s in seg_list).strip()
    words = [_word_dict(w) for s in seg_list for w in (getattr(s, "words", None) or [])]
    return text, words, [_segment_dict(s) for s in seg_list]


def _recognition_signals(segments: list) -> tuple[float, float, list[str]]:
    """Return conservative (confidence, hallucination risk, missing metrics)."""
    required = ("avg_logprob", "no_speech_prob", "compression_ratio")
    missing = [
        key for key in required
        if not segments or not any(s.get(key) is not None for s in segments)
    ]
    if not segments:
        return 0.20, 0.80, missing

    logps = [float(s["avg_logprob"]) for s in segments if s.get("avg_logprob") is not None]
    silence = [float(s["no_speech_prob"]) for s in segments if s.get("no_speech_prob") is not None]
    compression = [float(s["compression_ratio"]) for s in segments if s.get("compression_ratio") is not None]
    logp_score = sum(math.exp(min(0.0, v)) for v in logps) / len(logps) if logps else 0.45
    speech_score = 1.0 - (sum(silence) / len(silence)) if silence else 0.50
    compression_score = (
        sum(max(0.0, 1.0 - max(0.0, v - 1.6) / 1.2) for v in compression) / len(compression)
        if compression else 0.50
    )
    confidence = (0.55 * logp_score + 0.30 * speech_score + 0.15 * compression_score)
    confidence *= max(0.35, 1.0 - 0.20 * len(missing))
    hallu = 0.12 * len(missing)
    if logps and sum(logps) / len(logps) < -1.0:
        hallu += 0.35
    if compression and max(compression) > 2.4:
        hallu += 0.35
    if silence and sum(silence) / len(silence) > 0.6:
        hallu += 0.30
    return round(max(0.0, min(1.0, confidence)), 3), round(max(0.0, min(1.0, hallu)), 3), missing


def _build_uncertain_spans(words: list) -> list[dict]:
    spans = []
    normalized = [re.sub(r"[^a-z']", "", (w.get("word") or "").lower()) for w in (words or [])]
    for index, word in enumerate(words or []):
        probability = word.get("probability")
        try:
            confidence = float(probability) if probability is not None else 0.0
        except (TypeError, ValueError):
            confidence = 0.0
        start = float(word.get("start", 0.0) or 0.0)
        end = float(word.get("end", start) or start)
        reason = None
        if probability is None:
            reason = "missing_word_confidence"
        elif confidence < 0.65:
            reason = "low_alignment_confidence"
        elif end - start > 1.5:
            reason = "abnormal_word_duration"
        token = normalized[index]
        # Repetition can be real learner disfluency. Only flag an unusually long
        # consecutive run for review; never label common repeated words as
        # hallucinations based on a document-wide token count.
        if token and index >= 2 and normalized[index - 1] == token and normalized[index - 2] == token:
            reason = "repeated_sequence_needs_review"
        if reason:
            spans.append({
                "word": word.get("word", ""), "start": start, "end": end,
                "word_index": index,
                "confidence": round(max(0.0, min(1.0, confidence)), 3), "reason": reason,
            })
    return spans


def _decode_agreement(first: str, second: str) -> float:
    a = re.findall(r"[a-z']+", (first or "").lower())
    b = re.findall(r"[a-z']+", (second or "").lower())
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    return round(SequenceMatcher(None, a, b).ratio(), 3)


def _enrich(
    text: str,
    words: list,
    segments: list,
    *,
    nbest_texts=None,
    agreement=1.0,
    provider=None,
    model=None,
    fallback_used=False,
) -> dict:
    confidence, hallucination, missing = _recognition_signals(segments)
    agreement = max(0.0, min(1.0, float(agreement)))
    if agreement < 0.70:
        confidence = min(confidence, 0.50)
        hallucination = max(hallucination, 1.0 - agreement)
    uncertain = _build_uncertain_spans(words)
    return {
        "text": text, "words": words, "segments": segments,
        "asr_confidence": round(confidence, 3),
        "hallucination_risk": round(hallucination, 3),
        "missing_metrics": missing,
        "uncertain_spans": uncertain,
        "low_conf_spans": uncertain,
        "nbest_texts": nbest_texts or [text],
        "decode_agreement": round(agreement, 3),
        "provider": provider or settings.stt_provider,
        "model": model or settings.whisper_model,
        "decode_profile": settings.stt_profile_version,
        "fallback_used": bool(fallback_used),
    }


def transcribe_selfhost(audio_path) -> dict:
    # Keep both lazy segment iteration and the second decode inside the lock.
    # One model per process prevents concurrent uploads from exhausting RAM/VRAM.
    if not _decode_lock.acquire(timeout=settings.stt_local_wait_seconds):
        raise TimeoutError("Local STT is busy")
    try:
        return _transcribe_local(audio_path)
    finally:
        _decode_lock.release()


def _transcribe_local(audio_path) -> dict:
    model = _load_model()
    normalized = normalize_audio_to_wav(audio_path)
    should_remove = os.fspath(normalized) != os.fspath(audio_path)
    try:
        text, words, segments = _decode(model, normalized, beam_size=5, temperature=0.0)
        first = _enrich(text, words, segments, provider="selfhost", model=settings.whisper_model)
        uncertain_ratio = len(first["uncertain_spans"]) / max(1, len(words))
        if first["asr_confidence"] < 0.65 or first["hallucination_risk"] >= 0.35 or uncertain_ratio > 0.30:
            text2, _words2, _segments2 = _decode(model, normalized, beam_size=1, temperature=0.2)
            return _enrich(
                text, words, segments, nbest_texts=[text, text2],
                agreement=_decode_agreement(text, text2),
                provider="selfhost", model=settings.whisper_model,
            )
        return first
    finally:
        if should_remove:
            try:
                os.remove(normalized)
            except OSError:
                pass


def transcribe_groq(audio_path) -> dict:
    from groq import Groq
    client = Groq(
        api_key=settings.groq_api_key,
        timeout=settings.stt_remote_timeout_seconds,
        max_retries=0,  # Durable Speaking jobs already own bounded retries.
    )
    try:
        with open(audio_path, "rb") as file_obj:
            res = client.audio.transcriptions.create(
                model=settings.groq_stt_model,
                file=file_obj,
                response_format="verbose_json",
                timestamp_granularities=["segment", "word"],
                language="en",
                temperature=0.0,
            )
    finally:
        client.close()
    if hasattr(res, "model_dump"):
        res = res.model_dump()
    segments, words = [], []
    for seg in res.get("segments") or []:
        segments.append({
            "start": seg.get("start", 0.0), "end": seg.get("end", 0.0),
            "avg_logprob": seg.get("avg_logprob"),
            "no_speech_prob": seg.get("no_speech_prob"),
            "compression_ratio": seg.get("compression_ratio"),
        })
        for word in seg.get("words") or []:
            words.append({
                "word": word.get("word", ""), "start": word.get("start", 0.0),
                "end": word.get("end", 0.0), "probability": word.get("probability"),
            })
    if not words:
        for word in res.get("words") or []:
            words.append({
                "word": word.get("word", ""), "start": word.get("start", 0.0),
                "end": word.get("end", 0.0), "probability": word.get("probability"),
            })
    return _enrich(
        res.get("text") or "", words, segments,
        provider="groq", model=settings.groq_stt_model,
    )


def transcribe_mock(audio_path) -> dict:
    text = "This is a mock transcript for testing with enough words to produce a diagnostic score."
    tokens = text.split()
    words = [
        {"word": token, "start": i * 0.35, "end": i * 0.35 + 0.28, "probability": 0.96}
        for i, token in enumerate(tokens)
    ]
    segments = [{
        "start": 0.0, "end": words[-1]["end"], "avg_logprob": -0.08,
        "no_speech_prob": 0.01, "compression_ratio": 1.0,
    }]
    return _enrich(text, words, segments, provider="mock", model="mock")


def transcribe(audio_path) -> dict:
    started = time.perf_counter()
    result = _transcribe(audio_path)
    result["latency_ms"] = round((time.perf_counter() - started) * 1000, 2)
    return result


def _transcribe(audio_path) -> dict:
    provider = settings.stt_provider
    if provider == "mock":
        return transcribe_mock(audio_path)
    if provider == "selfhost":
        return transcribe_selfhost(audio_path)
    if provider == "groq":
        return transcribe_groq(audio_path)
    if provider != "auto":
        raise ValueError("Unsupported STT provider")
    try:
        return transcribe_selfhost(audio_path)
    except Exception as exc:
        if not settings.groq_api_key:
            raise
        logger.warning("Local STT failed (%s); using Groq fallback", type(exc).__name__)
        result = transcribe_groq(audio_path)
        result["fallback_used"] = True
        result["fallback_reason"] = type(exc).__name__
        return result


def mean_avg_logprob(segments: list) -> float | None:
    if not segments:
        return None
    vals = [float(s["avg_logprob"]) for s in segments if s.get("avg_logprob") is not None]
    return sum(vals) / len(vals) if vals else None
