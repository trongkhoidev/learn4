"""Provider transport for configured LLM backends, without assessment rules."""

import math
import time

from app.core.config import settings


class ProviderNotReady(RuntimeError):
    pass


class ProviderRequestFailed(RuntimeError):
    pass


class ProviderRateLimited(ProviderRequestFailed):
    pass


def _retry_delay(error) -> float | None:
    response = getattr(error, "response", None)
    value = getattr(response, "headers", {}).get("retry-after")
    details = getattr(error, "details", {})
    if value is None and isinstance(details, dict):
        body = details.get("error", details)
        if isinstance(body, dict):
            for item in body.get("details", []):
                if isinstance(item, dict) and item.get("@type", "").endswith("RetryInfo"):
                    value = item.get("retryDelay")
                    break
    try:
        delay = float(str(value).removesuffix("s"))
        return max(1.0, delay) if math.isfinite(delay) and delay >= 0 else None
    except (TypeError, ValueError):
        return None


class _ResponseTruncated(RuntimeError):
    pass


def _gemini_completion(model: str, messages: list, max_tokens: int, response_schema=None) -> str:
    from google import genai
    from google.genai import types

    system = "\n".join(message["content"] for message in messages if message["role"] == "system")
    contents = [
        types.Content(
            role="model" if message["role"] == "assistant" else "user",
            parts=[types.Part.from_text(text=message["content"])],
        )
        for message in messages if message["role"] != "system"
    ]
    config = types.GenerateContentConfig(
        system_instruction=system,
        temperature=0.0,
        max_output_tokens=max_tokens,
        response_mime_type="application/json",
        response_json_schema=response_schema,
        automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
        # Gemini 2.5 shares the output limit between thinking and response tokens.
        # Reserve room for criterion JSON rather than letting thinking consume it.
        thinking_config=types.ThinkingConfig(thinking_budget=1024)
        if model.startswith("gemini-2.5-") else None,
    )
    client = genai.Client(
        api_key=settings.google_api_key,
        http_options=types.HttpOptions(
            timeout=90000, retry_options=types.HttpRetryOptions(attempts=1),
        ),
    )
    try:
        response = client.models.generate_content(model=model, contents=contents, config=config)
        candidate = next(iter(response.candidates or []), None)
        finish = getattr(candidate, "finish_reason", None)
        finish = getattr(finish, "value", finish)
        if finish == "MAX_TOKENS":
            raise _ResponseTruncated("Gemini response reached MAX_TOKENS before completion")
        if finish != "STOP":
            raise ProviderRequestFailed(f"Gemini response did not finish successfully ({finish})")
        return response.text or ""
    finally:
        client.close()


def provider_readiness() -> dict:
    provider = settings.llm_provider
    if provider == "mock":
        return {"ready": True, "provider": "mock", "model": "mock", "mock_explicit": True}
    if provider == "groq":
        ready = bool(settings.groq_api_key)
        model = settings.groq_model_70b
    elif provider == "gemini":
        ready = bool(settings.google_api_key)
        model = settings.gemini_model
    else:
        ready = False
        model = None
    return {"ready": ready, "provider": provider, "model": model, "mock_explicit": False}


def complete(model: str, messages: list, max_tokens: int = 4096, *, response_schema=None) -> str:
    provider = settings.llm_provider
    if provider == "groq" and not settings.groq_api_key:
        raise ProviderNotReady("LLM provider groq is configured without credentials")
    if provider == "gemini" and not settings.google_api_key:
        raise ProviderNotReady("LLM provider gemini is configured without credentials")
    if provider not in {"groq", "gemini"}:
        raise ProviderNotReady(f"Unsupported LLM provider: {provider}")

    last_error = None
    token_budget = max(max_tokens, 4096) if provider == "gemini" else max_tokens
    for _attempt in range(2):
        try:
            if provider == "gemini":
                content = _gemini_completion(model, messages, token_budget, response_schema)
            else:
                from groq import Groq

                client = Groq(api_key=settings.groq_api_key, timeout=90, max_retries=0)
                try:
                    response = client.chat.completions.create(
                        model=model,
                        messages=messages,
                        temperature=0.0,
                        max_tokens=token_budget,
                        response_format={"type": "json_object"},
                    )
                    choice = response.choices[0]
                    if choice.finish_reason == "length":
                        raise _ResponseTruncated("Groq response reached its token limit before completion")
                    if choice.finish_reason != "stop":
                        raise ProviderRequestFailed(f"Groq response did not finish successfully ({choice.finish_reason})")
                    content = choice.message.content or ""
                finally:
                    client.close()
            if content.strip():
                return content
            last_error = "provider returned an empty response"
        except _ResponseTruncated as exc:
            last_error = str(exc)
            token_budget = min(token_budget * 2, 16384)
        except Exception as exc:
            if getattr(exc, "code", None) == 429 or getattr(exc, "status_code", None) == 429:
                delay = _retry_delay(exc)
                if _attempt == 0 and delay is not None and delay <= 60:
                    time.sleep(delay)
                    continue
                raise ProviderRateLimited("LLM request quota reached; try again later") from exc
            last_error = str(exc)
            for secret in (settings.google_api_key, settings.groq_api_key):
                if secret:
                    last_error = last_error.replace(secret, "<REDACTED>")
    raise ProviderRequestFailed(last_error or "LLM request failed")


def groq_completion(model: str, messages: list, *, temperature: float = 0.0) -> str:
    from groq import Groq

    response = Groq(api_key=settings.groq_api_key).chat.completions.create(
        model=model,
        messages=messages,
        temperature=temperature,
        response_format={"type": "json_object"},
    )
    return response.choices[0].message.content or "{}"


def groq_vision_completion(model: str, messages: list, *, temperature: float = 0.0) -> str:
    from groq import Groq

    response = Groq(api_key=settings.groq_api_key).chat.completions.create(
        model=model,
        messages=messages,
        temperature=temperature,
    )
    return response.choices[0].message.content or ""
