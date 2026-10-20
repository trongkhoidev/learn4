"""Cloud STT adapters normalized for the speaking evidence pipeline."""

import math
import mimetypes
from pathlib import Path

import httpx

from app.core.config import settings


class CloudSTTError(RuntimeError):
    pass


def _bounded_probability(value, default=None):
    try:
        return max(0.0, min(1.0, float(value)))
    except (TypeError, ValueError):
        return default


def transcribe_deepgram(audio_path, *, keyterms=None) -> dict:
    """Transcribe verbatim English with Nova-3 and provider-native confidence."""
    if not settings.deepgram_api_key:
        raise CloudSTTError("Deepgram API key is not configured")
    params = [
        ("model", settings.deepgram_stt_model),
        ("language", "en"),
        ("smart_format", "true"),
        ("punctuate", "true"),
        ("filler_words", "true"),
    ]
    params.extend(("keyterm", term) for term in (keyterms or [])[:100])
    content_type = mimetypes.guess_type(str(audio_path))[0] or "application/octet-stream"
    with open(audio_path, "rb") as audio, httpx.Client(timeout=settings.stt_remote_timeout_seconds) as client:
        response = client.post(
            "https://api.deepgram.com/v1/listen",
            params=params,
            headers={
                "Authorization": f"Token {settings.deepgram_api_key}",
                "Content-Type": content_type,
            },
            content=audio.read(),
        )
    try:
        response.raise_for_status()
        payload = response.json()
        alternative = payload["results"]["channels"][0]["alternatives"][0]
    except (httpx.HTTPError, KeyError, IndexError, TypeError, ValueError) as exc:
        detail = response.text[:300] if response is not None else ""
        raise CloudSTTError(f"Deepgram transcription failed: {detail}") from exc
    words = [{
        "word": word.get("punctuated_word") or word.get("word", ""),
        "start": word.get("start", 0.0),
        "end": word.get("end", 0.0),
        "probability": _bounded_probability(word.get("confidence")),
    } for word in alternative.get("words") or []]
    try:
        duration = max(0.0, float(payload.get("metadata", {}).get("duration") or 0.0))
    except (TypeError, ValueError):
        duration = 0.0
    if words:
        duration = max(float(words[-1].get("end") or 0.0), duration or 0.0)
    return {
        "text": alternative.get("transcript") or "",
        "words": words,
        "segments": [{"start": 0.0, "end": duration or 0.0}],
        "provider_confidence": _bounded_probability(alternative.get("confidence")),
        "provider": "deepgram",
        "model": settings.deepgram_stt_model,
        "request_id": payload.get("metadata", {}).get("request_id"),
    }


def transcribe_elevenlabs(audio_path, *, keyterms=None) -> dict:
    """Transcribe in verbatim mode with Scribe v2 word timing and logprobs."""
    if not settings.elevenlabs_api_key:
        raise CloudSTTError("ElevenLabs API key is not configured")
    path = Path(audio_path)
    form = [
        ("model_id", (None, settings.elevenlabs_stt_model)),
        ("language_code", (None, "en")),
        ("timestamps_granularity", (None, "word")),
        ("diarize", (None, "false")),
        ("tag_audio_events", (None, "true")),
        ("no_verbatim", (None, "false")),
    ]
    # Multipart array values are represented as repeated fields.
    form.extend(("keyterms", (None, term)) for term in (keyterms or [])[:100])
    content_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    with open(path, "rb") as audio, httpx.Client(timeout=settings.stt_remote_timeout_seconds) as client:
        response = client.post(
            "https://api.elevenlabs.io/v1/speech-to-text",
            headers={"xi-api-key": settings.elevenlabs_api_key},
            files=[*form, ("file", (path.name, audio, content_type))],
        )
    try:
        response.raise_for_status()
        payload = response.json()
    except (httpx.HTTPError, TypeError, ValueError) as exc:
        detail = response.text[:300] if response is not None else ""
        raise CloudSTTError(f"ElevenLabs transcription failed: {detail}") from exc
    words = []
    confidences = []
    for item in payload.get("words") or []:
        if item.get("type") != "word":
            continue
        try:
            probability = math.exp(min(0.0, float(item.get("logprob"))))
        except (TypeError, ValueError):
            probability = None
        if probability is not None:
            confidences.append(probability)
        words.append({
            "word": item.get("text", ""),
            "start": item.get("start", 0.0),
            "end": item.get("end", 0.0),
            "probability": probability,
        })
    provider_confidence = sum(confidences) / len(confidences) if confidences else None
    return {
        "text": payload.get("text") or "",
        "words": words,
        "segments": [{
            "start": words[0]["start"] if words else 0.0,
            "end": words[-1]["end"] if words else 0.0,
        }],
        "provider_confidence": _bounded_probability(provider_confidence),
        "provider": "elevenlabs",
        "model": settings.elevenlabs_stt_model,
        "language_code": payload.get("language_code"),
        "language_probability": _bounded_probability(payload.get("language_probability")),
        "transcription_id": payload.get("transcription_id"),
    }
