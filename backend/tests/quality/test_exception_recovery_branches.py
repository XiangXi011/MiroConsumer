"""Exception and recovery branch coverage for SPEC-P2-017."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

import app.utils.llm_client as llm_module
from app.redis.health import check_redis
from app.utils.llm_client import LLMClient


def _make_client() -> LLMClient:
    client = LLMClient.__new__(LLMClient)
    client.api_key = "fake-key"
    client.base_url = "http://fake"
    client.model = "fake-model"
    client.request_timeout = None
    client.client = MagicMock()
    client._response_cache = None
    client._response_cache_url = None
    return client


def test_redis_persistence_config_timeout_degrades_to_warning():
    redis_conn = MagicMock()
    redis_conn.config_get.side_effect = RuntimeError("CONFIG GET timeout")

    with patch("app.redis.health.redis.Redis.from_url", return_value=redis_conn):
        status, message = check_redis("redis://localhost:6379/0", persistence_required=True)

    assert status == "warning"
    assert "could not be verified" in message


def test_llm_api_5xx_records_circuit_failure(monkeypatch):
    client = _make_client()
    client.client.chat.completions.create.side_effect = RuntimeError("provider 500")
    failure_recorder = MagicMock()

    monkeypatch.setattr(llm_module.Config, "LLM_CACHE_ENABLED", False)
    monkeypatch.setattr(llm_module.governor, "check_budget", lambda *args, **kwargs: True)
    monkeypatch.setattr(llm_module.governor, "check_circuit", lambda service: True)
    monkeypatch.setattr(llm_module.governor, "record_circuit_failure", failure_recorder)

    with pytest.raises(RuntimeError, match="provider 500"):
        client.chat(messages=[{"role": "user", "content": "hello"}])

    failure_recorder.assert_called_once_with("llm")