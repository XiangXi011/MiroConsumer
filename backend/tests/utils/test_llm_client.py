"""Tests for the LLMClient JSON compatibility layer."""

from pathlib import Path
import sys
import json

import pytest
from unittest.mock import MagicMock, patch

BACKEND_ROOT = Path(__file__).resolve().parents[2]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.utils.llm_client import LLMClient


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_client():
    """Return an LLMClient with a mocked underlying OpenAI client."""
    client = LLMClient(api_key="fake-key", base_url="http://fake", model="fake-model")
    client.client = MagicMock()
    return client


def _mock_response(content: str, finish_reason: str = "stop"):
    """Build a mock OpenAI chat completion response."""
    mock = MagicMock()
    mock.choices = [MagicMock()]
    mock.choices[0].message.content = content
    mock.choices[0].finish_reason = finish_reason
    return mock


# ---------------------------------------------------------------------------
# chat_json primary path success
# ---------------------------------------------------------------------------

def test_chat_json_primary_path_parses_json():
    client = _make_client()
    expected = {"name": "Alice", "age": 30}
    client.client.chat.completions.create.return_value = _mock_response(
        json.dumps(expected)
    )

    result = client.chat_json(messages=[{"role": "user", "content": "hi"}])

    assert result == expected
    # ensure primary path was used (response_format passed)
    call_kwargs = client.client.chat.completions.create.call_args.kwargs
    assert call_kwargs.get("response_format") == {"type": "json_object"}


def test_chat_json_with_meta_returns_diagnostics_for_primary():
    client = _make_client()
    expected = {"status": "ok"}
    client.client.chat.completions.create.return_value = _mock_response(
        json.dumps(expected)
    )

    data, diag = client.chat_json_with_meta(
        messages=[{"role": "user", "content": "hi"}]
    )

    assert data == expected
    assert diag["primary_attempted"] is True
    assert diag["primary_succeeded"] is True
    assert diag["fallback_attempted"] is False
    assert diag["parse_path"] == "primary"
    assert diag["raw_preview"] == json.dumps(expected)


# ---------------------------------------------------------------------------
# Fallback path success
# ---------------------------------------------------------------------------

def test_chat_json_fallback_on_malformed_primary_response():
    """Primary returns non-JSON; fallback returns valid JSON."""
    client = _make_client()
    fallback_data = {"recovered": True}

    def side_effect(**kwargs):
        if kwargs.get("response_format"):
            return _mock_response("this is not json")
        return _mock_response(json.dumps(fallback_data))

    client.client.chat.completions.create.side_effect = side_effect

    result = client.chat_json(messages=[{"role": "user", "content": "hi"}])

    assert result == fallback_data
    assert client.client.chat.completions.create.call_count == 2


def test_chat_json_with_meta_shows_fallback_diagnostics():
    client = _make_client()

    def side_effect(**kwargs):
        if kwargs.get("response_format"):
            return _mock_response("not json")
        return _mock_response(json.dumps({"fallback": True}))

    client.client.chat.completions.create.side_effect = side_effect

    data, diag = client.chat_json_with_meta(
        messages=[{"role": "user", "content": "hi"}]
    )

    assert data == {"fallback": True}
    assert diag["primary_attempted"] is True
    assert diag["primary_succeeded"] is False
    assert diag["fallback_attempted"] is True
    assert diag["fallback_succeeded"] is True
    assert diag["parse_path"] == "fallback"


def test_chat_json_fallback_appends_json_instruction_to_system():
    client = _make_client()

    def side_effect(**kwargs):
        if kwargs.get("response_format"):
            return _mock_response("bad")
        return _mock_response(json.dumps({"ok": True}))

    client.client.chat.completions.create.side_effect = side_effect

    client.chat_json(
        messages=[
            {"role": "system", "content": "You are a test bot."},
            {"role": "user", "content": "go"},
        ]
    )

    # second call = fallback; verify system message was amended
    second_call = client.client.chat.completions.create.call_args_list[1]
    msgs = second_call.kwargs["messages"]
    system_msg = next(m for m in msgs if m["role"] == "system")
    assert "JSON only" in system_msg["content"]


def test_chat_json_fallback_injects_system_when_none_present():
    client = _make_client()

    def side_effect(**kwargs):
        if kwargs.get("response_format"):
            return _mock_response("bad")
        return _mock_response(json.dumps({"ok": True}))

    client.client.chat.completions.create.side_effect = side_effect

    client.chat_json(messages=[{"role": "user", "content": "go"}])

    second_call = client.client.chat.completions.create.call_args_list[1]
    msgs = second_call.kwargs["messages"]
    assert msgs[0]["role"] == "system"
    assert "JSON only" in msgs[0]["content"]


# ---------------------------------------------------------------------------
# Fenced JSON cleanup
# ---------------------------------------------------------------------------

def test_chat_json_strips_markdown_fences():
    client = _make_client()
    payload = {"key": "value"}
    fenced = f"```json\n{json.dumps(payload)}\n```"
    client.client.chat.completions.create.return_value = _mock_response(fenced)

    result = client.chat_json(messages=[])
    assert result == payload


def test_chat_json_strips_plain_fences():
    client = _make_client()
    payload = {"key": "value"}
    fenced = f"```\n{json.dumps(payload)}\n```"
    client.client.chat.completions.create.return_value = _mock_response(fenced)

    result = client.chat_json(messages=[])
    assert result == payload


# ---------------------------------------------------------------------------
# <think> cleanup
# ---------------------------------------------------------------------------

def test_chat_json_removes_think_tags():
    client = _make_client()
    payload = {"answer": 42}
    raw = f'<think>\nSome reasoning here\n</think>\n{json.dumps(payload)}'
    client.client.chat.completions.create.return_value = _mock_response(raw)

    result = client.chat_json(messages=[])
    assert result == payload


def test_chat_json_removes_think_tags_with_fences():
    client = _make_client()
    payload = {"answer": 42}
    raw = f'<think>Reasoning</think>\n```json\n{json.dumps(payload)}\n```'
    client.client.chat.completions.create.return_value = _mock_response(raw)

    result = client.chat_json(messages=[])
    assert result == payload


# ---------------------------------------------------------------------------
# Malformed JSON failure
# ---------------------------------------------------------------------------

def test_chat_json_raises_on_unparseable_json():
    client = _make_client()
    client.client.chat.completions.create.return_value = _mock_response("not json at all")

    with pytest.raises(ValueError):
        client.chat_json(messages=[], fallback_on_failure=False)


def test_chat_json_fallback_also_fails_raises():
    client = _make_client()

    def side_effect(**kwargs):
        return _mock_response("still not json")

    client.client.chat.completions.create.side_effect = side_effect

    with pytest.raises(ValueError):
        client.chat_json(messages=[])


# ---------------------------------------------------------------------------
# extract_json static helper
# ---------------------------------------------------------------------------

def test_extract_json_parses_clean_json():
    payload = {"foo": "bar"}
    assert LLMClient.extract_json(json.dumps(payload)) == payload


def test_extract_json_rejects_non_dict():
    with pytest.raises(ValueError):
        LLMClient.extract_json("[1, 2, 3]")


def test_extract_json_extracts_object_from_noise():
    text = 'Some preamble {\n  "a": 1\n} trailing text'
    assert LLMClient.extract_json(text) == {"a": 1}


def test_extract_json_raises_when_no_object_found():
    with pytest.raises(ValueError):
        LLMClient.extract_json("just plain text without braces")


# ---------------------------------------------------------------------------
# clean_llm_text static helper
# ---------------------------------------------------------------------------

def test_clean_llm_text_strips_think_and_fences():
    raw = '<think>hidden</think>\n```json\n{"a":1}\n```'
    assert LLMClient.clean_llm_text(raw) == '{"a":1}'


def test_clean_llm_text_noop_on_clean_json():
    clean = '{"a": 1}'
    assert LLMClient.clean_llm_text(clean) == clean


# ---------------------------------------------------------------------------
# chat_with_finish_reason
# ---------------------------------------------------------------------------

def test_chat_with_finish_reason_returns_tuple():
    client = _make_client()
    client.client.chat.completions.create.return_value = _mock_response(
        "hello", finish_reason="length"
    )

    content, reason = client.chat_with_finish_reason(messages=[])
    assert content == "hello"
    assert reason == "length"


# ---------------------------------------------------------------------------
# Backward compatibility: existing chat_json signature unchanged
# ---------------------------------------------------------------------------

def test_chat_json_backward_compatible_signature():
    """Ensure chat_json still accepts the original positional args."""
    client = _make_client()
    client.client.chat.completions.create.return_value = _mock_response(
        json.dumps({"ok": True})
    )

    # Original signature: messages, temperature=0.3, max_tokens=4096
    result = client.chat_json(
        messages=[{"role": "user", "content": "hi"}],
        temperature=0.5,
        max_tokens=1024,
    )
    assert result == {"ok": True}
    kwargs = client.client.chat.completions.create.call_args.kwargs
    assert kwargs["temperature"] == 0.5
    assert kwargs["max_tokens"] == 1024
