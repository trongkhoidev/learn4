"""Cloud STT adapters normalized for the speaking evidence pipeline."""

import base64
import math
import mimetypes
import re
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


# Comprehensive dictionary of Vietnamese locations, provinces, cities, landmarks & proper names
# to ensure high-accuracy recognition and prevent dropping or misrecognizing proper names.
DEFAULT_VIETNAM_KEYTERMS = [
    # All 63 Provinces & Municipalities in Vietnam
    "Hanoi", "Ho Chi Minh City", "Saigon", "Da Nang", "Hai Phong", "Can Tho",
    "Quang Tri", "Quang Nam", "Hue", "Thua Thien Hue", "Quang Binh", "Quang Ngai",
    "Nha Trang", "Khanh Hoa", "Da Lat", "Lam Dong", "Vung Tau", "Ba Ria - Vung Tau",
    "Binh Duong", "Dong Nai", "Binh Phuoc", "Tay Ninh", "Binh Thuan", "Ninh Thuan",
    "Phu Yen", "Binh Dinh", "Gia Lai", "Kon Tum", "Dak Lak", "Dak Nong",
    "Long An", "Tien Giang", "Ben Tre", "Tra Vinh", "Vinh Long", "Dong Thap",
    "An Giang", "Kien Giang", "Phu Quoc", "Ca Mau", "Bac Lieu", "Soc Trang", "Hau Giang",
    "Thanh Hoa", "Nghe An", "Vinh", "Ha Tinh", "Ninh Binh", "Nam Dinh", "Ha Nam",
    "Thai Binh", "Hung Yen", "Hai Duong", "Bac Ninh", "Bac Giang", "Vinh Phuc",
    "Phu Tho", "Thai Nguyen", "Tuyen Quang", "Ha Giang", "Cao Bang", "Bac Kan",
    "Lang Son", "Lao Cai", "Sa Pa", "Yen Bai", "Dien Bien", "Lai Chau", "Son La",
    "Hoa Binh", "Quang Ninh", "Ha Long",
    # Academic & Landmark proper names
    "Vietnam", "Vietnamese", "Hanoi University", "Bach Khoa", "National University",
    "Foreign Trade University", "RMIT Vietnam",
]


def _merge_keyterms(keyterms: list[str] | None) -> list[str]:
    merged = []
    seen = set()
    for term in list(keyterms or []) + DEFAULT_VIETNAM_KEYTERMS:
        clean = str(term).strip()
        if clean and clean.lower() not in seen:
            seen.add(clean.lower())
            merged.append(clean)
    return merged[:100]


def _clean_punctuation_anomalies(text: str) -> str:
    """Clean duplicate or misplaced punctuation like 'hometown,.' without removing words."""
    if not text:
        return ""
    cleaned = re.sub(r'[,;:]+\s*\.', '.', text)
    cleaned = re.sub(r'\s+([,.;?!])', r'\1', cleaned)
    cleaned = re.sub(r'([.?!])\s*[,;:]+', r'\1', cleaned)
    return cleaned.strip()


def transcribe_cloudflare(audio_path, *, keyterms=None) -> dict:
    """Transcribe English through the protected Workers AI Whisper endpoint."""
    if not settings.cloudflare_worker_url or not settings.cloudflare_worker_token:
        raise CloudSTTError("Cloudflare Workers AI is not configured")
    path = Path(audio_path)
    content_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    effective_keyterms = _merge_keyterms(keyterms)
    prompt = "English IELTS speaking in Vietnam. Preserve proper names, cities (such as Hanoi, Da Nang, Quang Tri, Ho Chi Minh City, Hue), fillers, repetitions and grammar exactly."
    if effective_keyterms:
        prompt += " Geographic names and places that may occur: " + ", ".join(effective_keyterms[:80])
    encoded_prompt = base64.b64encode(prompt[:1800].encode("utf-8")).decode("ascii")
    url = settings.cloudflare_worker_url.rstrip("/") + "/transcribe"
    with open(path, "rb") as audio, httpx.Client(timeout=settings.stt_remote_timeout_seconds) as client:
        response = client.post(
            url,
            headers={
                "Authorization": f"Bearer {settings.cloudflare_worker_token}",
                "Content-Type": content_type,
                "X-Initial-Prompt-B64": encoded_prompt,
            },
            content=audio.read(),
        )
    try:
        response.raise_for_status()
        payload = response.json()
    except (httpx.HTTPError, TypeError, ValueError) as exc:
        detail = response.text[:300] if response is not None else ""
        raise CloudSTTError(f"Cloudflare transcription failed: {detail}") from exc

    words = []
    raw_words = payload.get("words") or []
    info = payload.get("transcription_info") or {}
    if isinstance(info, list):
        info = info[0] if info else {}
    if not raw_words and isinstance(info, dict):
        raw_words = info.get("words") or []
    if not raw_words:
        raw_words = [
            word
            for segment in (payload.get("segments") or [])
            if isinstance(segment, dict)
            for word in (segment.get("words") or [])
            if isinstance(word, dict)
        ]
    for word in raw_words:
        raw_w = str(word.get("word", "")).strip()
        clean_w = _clean_punctuation_anomalies(raw_w)
        words.append({
            "word": clean_w or raw_w,
            "start": word.get("start", 0.0),
            "end": word.get("end", 0.0),
            # Workers AI does not expose calibrated per-word confidence.
            "probability": None,
        })

    raw_segments = payload.get("segments") or []
    segments = [{
        "start": segment.get("start", 0.0),
        "end": segment.get("end", 0.0),
        "avg_logprob": segment.get("avg_logprob"),
        "no_speech_prob": segment.get("no_speech_prob"),
        "compression_ratio": segment.get("compression_ratio"),
    } for segment in raw_segments if isinstance(segment, dict)]
    if not segments:
        duration = info.get("duration", 0.0) if isinstance(info, dict) else 0.0
        if words:
            duration = max(float(words[-1].get("end") or 0.0), float(duration or 0.0))
        segments = [{"start": 0.0, "end": duration or 0.0}]

    raw_text = payload.get("text") or ""
    return {
        "text": _clean_punctuation_anomalies(raw_text),
        "words": words,
        "segments": segments,
        # No provider confidence is fabricated; recognition.py derives a
        # conservative score from segment evidence and ensemble agreement.
        "provider_confidence": None,
        "provider": "cloudflare",
        "model": payload.get("model") or settings.cloudflare_stt_model,
        "language_code": info.get("language") if isinstance(info, dict) else None,
        "language_probability": _bounded_probability(
            info.get("language_probability") if isinstance(info, dict) else None
        ),
        "request_id": response.headers.get("cf-ray"),
    }


def transcribe_deepgram(audio_path, *, keyterms=None) -> dict:
    """Transcribe verbatim English with Nova-3 and provider-native confidence."""
    if not settings.deepgram_api_key:
        raise CloudSTTError("Deepgram API key is not configured")
    effective_keyterms = _merge_keyterms(keyterms)
    params = [
        ("model", settings.deepgram_stt_model),
        ("language", "en"),
        ("smart_format", "true"),
        ("punctuate", "true"),
        ("filler_words", "true"),
    ]
    params.extend(("keyterm", term) for term in effective_keyterms[:100])
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
    words = []
    for word in alternative.get("words") or []:
        raw_word = word.get("punctuated_word") or word.get("word", "")
        clean_word = _clean_punctuation_anomalies(raw_word)
        words.append({
            "word": clean_word or raw_word,
            "start": word.get("start", 0.0),
            "end": word.get("end", 0.0),
            "probability": _bounded_probability(word.get("confidence")),
        })
    try:
        duration = max(0.0, float(payload.get("metadata", {}).get("duration") or 0.0))
    except (TypeError, ValueError):
        duration = 0.0
    if words:
        duration = max(float(words[-1].get("end") or 0.0), duration or 0.0)
    raw_text = alternative.get("transcript") or ""
    return {
        "text": _clean_punctuation_anomalies(raw_text),
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
