"""Provider responses must be complete before criterion JSON is validated."""

import json
import sys
import types

import pytest

from app.core.config import settings
from app.integrations.llm import transport
from app.modules.speaking.assessment import raters


@pytest.fixture
def gemini_client(monkeypatch):
    from google import genai

    monkeypatch.setattr(settings, "llm_provider", "gemini")
    monkeypatch.setattr(settings, "google_api_key", "test-key")
    # No test may reach the deprecated SDK or the network.
    monkeypatch.setitem(sys.modules, "google.generativeai", types.SimpleNamespace())
    calls, closed, responses = [], [], []

    def generate_content(**kwargs):
        calls.append(kwargs)
        result = responses.pop(0)
        if isinstance(result, Exception):
            raise result
        return result

    monkeypatch.setattr(genai, "Client", lambda **kwargs: types.SimpleNamespace(
        models=types.SimpleNamespace(generate_content=generate_content),
        close=lambda: closed.append(True),
    ))
    return calls, closed, responses


def response(text, finish="STOP"):
    return types.SimpleNamespace(
        text=text, candidates=[types.SimpleNamespace(finish_reason=finish)],
    )


def test_gemini_retries_truncated_json_with_larger_budget(gemini_client):
    calls, closed, responses = gemini_client
    responses.extend([response('{"criterion":', "MAX_TOKENS"), response('{"ok":true}')])
    raw = transport.complete("gemini-2.5-flash", [
        {"role": "system", "content": "Return JSON"},
        {"role": "user", "content": "Grade the answer"},
        {"role": "assistant", "content": '{"invalid":'},
        {"role": "user", "content": "Correct the JSON"},
    ], max_tokens=4096, response_schema={"type": "object", "properties": {"ok": {"type": "boolean"}}})
    assert json.loads(raw) == {"ok": True}
    assert len(calls) == 2
    assert calls[1]["config"].max_output_tokens > calls[0]["config"].max_output_tokens
    assert calls[0]["config"].thinking_config.thinking_budget == 1024
    assert calls[0]["config"].response_json_schema["properties"]["ok"]["type"] == "boolean"
    assert [item.role for item in calls[0]["contents"]] == ["user", "model", "user"]
    assert len(closed) == 2


def test_gemini_never_returns_truncated_response_as_success(gemini_client):
    calls, closed, responses = gemini_client
    responses.extend([response('{"unfinished":', "MAX_TOKENS")] * 2)
    with pytest.raises(transport.ProviderRequestFailed, match="MAX_TOKENS"):
        transport.complete("gemini-2.5-flash", [{"role": "user", "content": "Grade"}])
    assert len(calls) == len(closed) == 2


def test_rater_reserves_enough_output_for_vietnamese_feedback(monkeypatch):
    calls = []

    def complete(model, messages, max_tokens=900):
        calls.append(max_tokens)
        return json.dumps({
            "criterion": "fluency_coherence", "status": "scored", "band": 6.0,
            "feedback_vi": "Câu trả lời có ý rõ ràng.",
            "evidence": [{"quote": "hello", "word_ids": ["w1"]}],
        })

    monkeypatch.setattr(raters, "_complete", complete)
    result = raters._request_rater(
        "fluency_coherence", {"scope": "practice_answer"},
        words=[{"id": "w1", "word": "hello"}], uncertain_spans=[], model="test",
    )
    assert result["band"] == 6.0
    assert calls[0] >= 4096


def test_gemini_respects_quota_retry_delay(gemini_client, monkeypatch):
    from google.genai.errors import ClientError

    calls, closed, responses = gemini_client
    delays = []
    monkeypatch.setattr(transport.time, "sleep", delays.append)
    responses.extend([
        ClientError(429, {"error": {"details": [{
            "@type": "type.googleapis.com/google.rpc.RetryInfo", "retryDelay": "42s",
        }]}}),
        response('{"ok":true}'),
    ])
    assert json.loads(transport.complete("gemini-2.5-flash", [])) == {"ok": True}
    assert delays == [42.0]
    assert len(calls) == len(closed) == 2


def test_quota_without_retry_window_is_not_hammered(gemini_client):
    from google.genai.errors import ClientError

    calls, closed, responses = gemini_client
    responses.append(ClientError(429, {"error": {"message": "Daily quota reached"}}))
    with pytest.raises(transport.ProviderRateLimited):
        transport.complete("gemini-2.5-flash", [])
    assert len(calls) == len(closed) == 1


def test_rate_limit_is_not_misreported_as_invalid_rater_json(monkeypatch):
    def limited(*args, **kwargs):
        raise transport.ProviderRateLimited("quota")

    monkeypatch.setattr(raters, "_complete", limited)
    result = raters._run_one("fluency_coherence", {}, [], [], "70b")
    assert result["failure_reason"] == "llm_rate_limited"
    assert "giới hạn lượt gọi" in result["feedback_vi"]
    assert result["next_action_vi"]


def test_groq_truncation_retries_with_budget_and_closes_clients(monkeypatch):
    monkeypatch.setattr(settings, "llm_provider", "groq")
    monkeypatch.setattr(settings, "groq_api_key", "test-key")
    calls, constructors, closed = [], [], []
    responses = iter([
        types.SimpleNamespace(choices=[types.SimpleNamespace(finish_reason="length", message=types.SimpleNamespace(content='{"unfinished":'))]),
        types.SimpleNamespace(choices=[types.SimpleNamespace(finish_reason="stop", message=types.SimpleNamespace(content='{"ok":true}'))]),
    ])

    def create(**kwargs):
        calls.append(kwargs)
        return next(responses)

    def client(**kwargs):
        constructors.append(kwargs)
        return types.SimpleNamespace(
            chat=types.SimpleNamespace(completions=types.SimpleNamespace(create=create)),
            close=lambda: closed.append(True),
        )

    monkeypatch.setitem(sys.modules, "groq", types.SimpleNamespace(Groq=client))
    assert json.loads(transport.complete("openai/gpt-oss-120b", [])) == {"ok": True}
    assert calls[1]["max_tokens"] > calls[0]["max_tokens"]
    assert constructors[0]["max_retries"] == 0
    assert constructors[0]["timeout"] == 90
    assert len(closed) == 2
