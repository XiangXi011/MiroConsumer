"""Redis-backed JSON cache with graceful fallback."""

from __future__ import annotations

import gzip
import json
from collections.abc import Callable
from typing import Any, Optional

import redis


class RedisCache:
    """Small cache-aside helper backed by Redis."""

    COMPRESSION_PREFIX = b"gzip:"
    COMPRESSION_THRESHOLD_BYTES = 10 * 1024
    TTL_BY_DATA_TYPE = {
        "hot": 60,
        "warm": 300,
        "cold": 3600,
    }

    def __init__(
        self,
        redis_url: str = "redis://localhost:6379/0",
        compression_enabled: bool = True,
        compression_threshold_bytes: int = COMPRESSION_THRESHOLD_BYTES,
    ) -> None:
        self.redis_url = redis_url
        self.compression_enabled = compression_enabled
        self.compression_threshold_bytes = compression_threshold_bytes
        self._redis: Optional[redis.Redis] = None
        self._metrics = {
            "hits": 0,
            "misses": 0,
            "sets": 0,
            "errors": 0,
        }

        try:
            client = redis.Redis.from_url(redis_url)
            client.ping()
        except (ValueError, redis.exceptions.RedisError, RuntimeError):
            return

        self._redis = client

    @classmethod
    def ttl_for_data_type(cls, data_type: str = "warm") -> int:
        return cls.TTL_BY_DATA_TYPE.get(data_type, cls.TTL_BY_DATA_TYPE["warm"])

    def _encode_value(self, value: Any) -> str | bytes | None:
        try:
            payload = json.dumps(value)
        except (TypeError, ValueError):
            return None

        payload_bytes = payload.encode("utf-8")
        if self.compression_enabled and len(payload_bytes) > self.compression_threshold_bytes:
            return self.COMPRESSION_PREFIX + gzip.compress(payload_bytes)
        return payload

    def _decode_value(self, raw_value: Any) -> Any:
        if isinstance(raw_value, memoryview):
            raw_value = raw_value.tobytes()
        if isinstance(raw_value, bytes) and raw_value.startswith(self.COMPRESSION_PREFIX):
            raw_value = gzip.decompress(raw_value[len(self.COMPRESSION_PREFIX):]).decode("utf-8")
        return json.loads(raw_value)

    def get(self, key: str) -> Any:
        """Return the JSON-decoded cache value, or None when unavailable/missing."""
        if self._redis is None:
            return None

        try:
            raw_value = self._redis.get(key)
        except redis.exceptions.RedisError:
            self._metrics["errors"] += 1
            self._redis = None
            return None

        if raw_value is None:
            self._metrics["misses"] += 1
            from ...utils.metrics import record_cache_miss
            record_cache_miss()
            return None

        try:
            value = self._decode_value(raw_value)
        except (TypeError, ValueError, gzip.BadGzipFile, json.JSONDecodeError):
            self._metrics["misses"] += 1
            from ...utils.metrics import record_cache_miss
            record_cache_miss()
            return None
        self._metrics["hits"] += 1
        from ...utils.metrics import record_cache_hit
        record_cache_hit()
        return value

    def set(self, key: str, value: Any, ttl: int | None = 300, data_type: str = "warm") -> bool:
        """Store a JSON-serialized value with a TTL."""
        if self._redis is None:
            return False

        payload = self._encode_value(value)
        if payload is None:
            return False

        effective_ttl = self.ttl_for_data_type(data_type) if ttl is None else ttl
        try:
            return bool(self._redis.set(key, payload, ex=effective_ttl))
        except redis.exceptions.RedisError:
            self._metrics["errors"] += 1
            self._redis = None
            return False
        finally:
            if self._redis is not None:
                self._metrics["sets"] += 1

    def delete(self, key: str) -> bool:
        """Delete a cached value."""
        if self._redis is None:
            return False

        try:
            return bool(self._redis.delete(key))
        except redis.exceptions.RedisError:
            self._metrics["errors"] += 1
            self._redis = None
            return False

    def exists(self, key: str) -> bool:
        """Return whether a key exists in Redis."""
        if self._redis is None:
            return False

        try:
            return bool(self._redis.exists(key))
        except redis.exceptions.RedisError:
            self._metrics["errors"] += 1
            self._redis = None
            return False

    def get_or_set(self, key: str, factory_fn: Callable[[], Any], ttl: int = 300) -> Any:
        """Fetch from cache, or compute/store a value using cache-aside behavior."""
        cached_value = self.get(key)
        if cached_value is not None:
            return cached_value

        value = factory_fn()
        self.set(key, value, ttl=ttl)
        return value

    def metrics(self) -> dict:
        """Return local cache-aside counters for hit/miss visibility."""
        return {
            **self._metrics,
            "available": self._redis is not None,
        }

