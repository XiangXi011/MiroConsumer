"""External-service SPEC-P2-018 integration scenarios."""

from __future__ import annotations

import io

import pytest
import redis

from app.services.application.redis_cache import RedisCache
from app.utils.llm_client import LLMClient


class ScriptedLLMClient(LLMClient):
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls: list[dict] = []

    def chat(self, messages, **kwargs):
        self.calls.append({"messages": messages, "kwargs": kwargs})
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


class FakeRedisClient:
    def __init__(self, *, fail_get: bool = False, fail_set: bool = False):
        self.fail_get = fail_get
        self.fail_set = fail_set
        self.values: dict[str, bytes] = {}

    def ping(self):
        return True

    def get(self, key):
        if self.fail_get:
            raise redis.exceptions.ConnectionError("redis unavailable")
        return self.values.get(key)

    def set(self, key, value, ex=None):
        if self.fail_set:
            raise redis.exceptions.TimeoutError("redis timeout")
        self.values[key] = value.encode("utf-8") if isinstance(value, str) else value
        return True

    def delete(self, key):
        return int(self.values.pop(key, None) is not None)

    def exists(self, key):
        return int(key in self.values)


class InMemoryMinioAdapter:
    """Small MinIO-compatible adapter used for upload/download integration checks."""

    def __init__(self) -> None:
        self.objects: dict[tuple[str, str], bytes] = {}

    def upload(self, bucket: str, object_name: str, stream: io.BytesIO) -> dict:
        payload = stream.read()
        self.objects[(bucket, object_name)] = payload
        return {"bucket": bucket, "object_name": object_name, "bytes": len(payload)}

    def download(self, bucket: str, object_name: str) -> bytes:
        return self.objects[(bucket, object_name)]

    def list_objects(self, bucket: str) -> list[str]:
        return sorted(name for (stored_bucket, name), _ in self.objects.items() if stored_bucket == bucket)

    def delete(self, bucket: str, object_name: str) -> bool:
        return self.objects.pop((bucket, object_name), None) is not None


def test_llm_json_primary_path_succeeds_without_fallback():
    client = ScriptedLLMClient(['{"summary": "ok", "score": 0.8}'])

    data, meta = client.chat_json_with_meta([{"role": "user", "content": "Return JSON"}])

    assert data == {"summary": "ok", "score": 0.8}
    assert meta["primary_succeeded"] is True
    assert meta["fallback_attempted"] is False
    assert client.calls[0]["kwargs"]["response_format"] == {"type": "json_object"}


def test_llm_fallback_chain_recovers_from_invalid_primary_json():
    client = ScriptedLLMClient(["not-json", '{"summary": "fallback", "score": 0.5}'])

    data, meta = client.chat_json_with_meta([{"role": "user", "content": "Return JSON"}])

    assert data["summary"] == "fallback"
    assert meta["primary_succeeded"] is False
    assert meta["fallback_attempted"] is True
    assert meta["fallback_succeeded"] is True
    assert meta["parse_path"] == "fallback"


def test_llm_fallback_disabled_surfaces_primary_failure():
    client = ScriptedLLMClient(["not-json"])

    with pytest.raises(ValueError, match="Invalid JSON"):
        client.chat_json_with_meta(
            [{"role": "user", "content": "Return JSON"}],
            fallback_on_failure=False,
        )

    assert len(client.calls) == 1


def test_redis_ping_failure_degrades_cache_to_noop(monkeypatch):
    monkeypatch.setattr(
        "app.services.application.redis_cache.redis.Redis.from_url",
        lambda url: (_ for _ in ()).throw(redis.exceptions.ConnectionError("down")),
    )

    cache = RedisCache(redis_url="redis://integration-redis:6379/0")

    assert cache.get("missing") is None
    assert cache.set("key", {"value": 1}) is False
    assert cache.metrics()["available"] is False


def test_redis_read_failure_disables_client_for_degradation(monkeypatch):
    fake = FakeRedisClient(fail_get=True)
    monkeypatch.setattr("app.services.application.redis_cache.redis.Redis.from_url", lambda url: fake)
    cache = RedisCache(redis_url="redis://integration-redis:6379/0")

    assert cache.get("cached") is None
    assert cache.metrics()["errors"] == 1
    assert cache.metrics()["available"] is False


def test_redis_write_failure_returns_false_without_raising(monkeypatch):
    fake = FakeRedisClient(fail_set=True)
    monkeypatch.setattr("app.services.application.redis_cache.redis.Redis.from_url", lambda url: fake)
    cache = RedisCache(redis_url="redis://integration-redis:6379/0")

    assert cache.set("cached", {"value": "warm"}, data_type="warm") is False
    assert cache.metrics()["errors"] == 1
    assert cache.metrics()["available"] is False


def test_minio_upload_download_round_trip_uses_bucket_and_object_name():
    minio = InMemoryMinioAdapter()

    upload = minio.upload("miroconsumer-test", "reports/report-1.md", io.BytesIO(b"# Report"))
    downloaded = minio.download("miroconsumer-test", "reports/report-1.md")

    assert upload == {"bucket": "miroconsumer-test", "object_name": "reports/report-1.md", "bytes": 8}
    assert downloaded == b"# Report"
    assert minio.list_objects("miroconsumer-test") == ["reports/report-1.md"]


def test_minio_delete_removes_downloadable_object():
    minio = InMemoryMinioAdapter()
    minio.upload("miroconsumer-test", "briefs/brief.json", io.BytesIO(b'{"brief": true}'))

    assert minio.delete("miroconsumer-test", "briefs/brief.json") is True
    assert minio.list_objects("miroconsumer-test") == []
