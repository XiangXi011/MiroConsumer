"""Redis-backed JSON cache with graceful fallback."""

import json
from collections.abc import Callable
from typing import Any, Optional

import redis


class RedisCache:
    """Small cache-aside helper backed by Redis."""

    def __init__(self, redis_url: str = "redis://localhost:6379/0") -> None:
        self.redis_url = redis_url
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
        except (ValueError, redis.exceptions.RedisError):
            return

        self._redis = client

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
            return None

        try:
            value = json.loads(raw_value)
        except (TypeError, ValueError):
            self._metrics["misses"] += 1
            return None
        self._metrics["hits"] += 1
        return value

    def set(self, key: str, value: Any, ttl: int = 300) -> bool:
        """Store a JSON-serialized value with a TTL."""
        if self._redis is None:
            return False

        try:
            payload = json.dumps(value)
        except (TypeError, ValueError):
            return False

        try:
            return bool(self._redis.set(key, payload, ex=ttl))
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
