"""Tests for the Redis JSON cache helper."""

import json
from unittest.mock import MagicMock, patch

import redis

from app.services.application.redis_cache import RedisCache


def _cache_with_mocked_redis():
    redis_conn = MagicMock()
    redis_conn.set.return_value = True
    return redis_conn, patch(
        "app.services.application.redis_cache.redis.Redis.from_url",
        return_value=redis_conn,
    )


def test_connects_with_redis_from_url_and_pings():
    redis_conn, from_url_patch = _cache_with_mocked_redis()

    with from_url_patch as from_url:
        RedisCache(redis_url="redis://localhost:6379/0")

    from_url.assert_called_once_with("redis://localhost:6379/0")
    redis_conn.ping.assert_called_once()


def test_get_reads_and_deserializes_json():
    redis_conn, from_url_patch = _cache_with_mocked_redis()
    redis_conn.get.return_value = b'{"name": "Ada", "count": 2}'

    with from_url_patch:
        cache = RedisCache(redis_url="redis://localhost:6379/0")

    assert cache.get("profile:1") == {"name": "Ada", "count": 2}
    redis_conn.get.assert_called_once_with("profile:1")


def test_get_returns_none_for_missing_or_invalid_json():
    redis_conn, from_url_patch = _cache_with_mocked_redis()
    redis_conn.get.side_effect = [None, b"not-json"]

    with from_url_patch:
        cache = RedisCache(redis_url="redis://localhost:6379/0")

    assert cache.get("missing") is None
    assert cache.get("invalid") is None


def test_set_serializes_json_and_passes_ttl():
    redis_conn, from_url_patch = _cache_with_mocked_redis()
    value = {"name": "Ada", "roles": ["admin"]}

    with from_url_patch:
        cache = RedisCache(redis_url="redis://localhost:6379/0")

    assert cache.set("profile:1", value, ttl=120) is True
    redis_conn.set.assert_called_once_with("profile:1", json.dumps(value), ex=120)


def test_delete_removes_key():
    redis_conn, from_url_patch = _cache_with_mocked_redis()
    redis_conn.delete.return_value = 1

    with from_url_patch:
        cache = RedisCache(redis_url="redis://localhost:6379/0")

    assert cache.delete("profile:1") is True
    redis_conn.delete.assert_called_once_with("profile:1")


def test_exists_checks_key_presence():
    redis_conn, from_url_patch = _cache_with_mocked_redis()
    redis_conn.exists.return_value = 1

    with from_url_patch:
        cache = RedisCache(redis_url="redis://localhost:6379/0")

    assert cache.exists("profile:1") is True
    redis_conn.exists.assert_called_once_with("profile:1")


def test_get_or_set_returns_cached_value_without_calling_factory():
    redis_conn, from_url_patch = _cache_with_mocked_redis()
    redis_conn.get.return_value = json.dumps({"cached": True})
    factory = MagicMock(return_value={"fresh": True})

    with from_url_patch:
        cache = RedisCache(redis_url="redis://localhost:6379/0")

    assert cache.get_or_set("profile:1", factory, ttl=45) == {"cached": True}
    factory.assert_not_called()
    redis_conn.set.assert_not_called()


def test_get_or_set_calls_factory_and_stores_on_cache_miss():
    redis_conn, from_url_patch = _cache_with_mocked_redis()
    redis_conn.get.return_value = None
    factory = MagicMock(return_value={"fresh": True})

    with from_url_patch:
        cache = RedisCache(redis_url="redis://localhost:6379/0")

    assert cache.get_or_set("profile:1", factory, ttl=45) == {"fresh": True}
    factory.assert_called_once_with()
    redis_conn.set.assert_called_once_with(
        "profile:1",
        json.dumps({"fresh": True}),
        ex=45,
    )


def test_metrics_track_hits_misses_sets_and_errors():
    redis_conn, from_url_patch = _cache_with_mocked_redis()
    redis_conn.get.side_effect = [
        json.dumps({"cached": True}),
        None,
        redis.exceptions.ConnectionError("redis down"),
    ]

    with from_url_patch:
        cache = RedisCache(redis_url="redis://localhost:6379/0")

    assert cache.get("hit") == {"cached": True}
    assert cache.get("miss") is None
    assert cache.get("error") is None
    assert cache.set("offline", {"value": True}) is False

    assert cache.metrics() == {
        "hits": 1,
        "misses": 1,
        "sets": 0,
        "errors": 1,
        "available": False,
    }


def test_graceful_fallback_when_redis_connection_fails():
    redis_conn = MagicMock()
    redis_conn.ping.side_effect = redis.exceptions.ConnectionError("redis down")
    factory = MagicMock(return_value={"fresh": True})

    with patch(
        "app.services.application.redis_cache.redis.Redis.from_url",
        return_value=redis_conn,
    ):
        cache = RedisCache(redis_url="redis://localhost:6379/0")

    assert cache.get("profile:1") is None
    assert cache.set("profile:1", {"name": "Ada"}) is False
    assert cache.delete("profile:1") is False
    assert cache.exists("profile:1") is False
    assert cache.get_or_set("profile:1", factory, ttl=30) == {"fresh": True}
    factory.assert_called_once_with()


def test_graceful_fallback_when_redis_operation_fails():
    redis_conn, from_url_patch = _cache_with_mocked_redis()
    redis_conn.get.side_effect = redis.exceptions.ConnectionError("redis down")
    factory = MagicMock(return_value={"fresh": True})

    with from_url_patch:
        cache = RedisCache(redis_url="redis://localhost:6379/0")

    assert cache.get("profile:1") is None
    assert cache.get_or_set("profile:1", factory, ttl=30) == {"fresh": True}
    factory.assert_called_once_with()
