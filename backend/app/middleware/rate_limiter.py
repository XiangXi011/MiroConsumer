"""Fixed-window API rate limiting with memory and Redis backends."""

from __future__ import annotations

import time
from dataclasses import dataclass
from functools import wraps
from typing import Any, Callable, Optional

import redis
from flask import current_app, g, jsonify, request


@dataclass
class RateLimitResult:
    allowed: bool
    limit: int
    remaining: int
    retry_after: int
    count: int


class RateLimiter:
    """Fixed-window limiter.

    Redis uses atomic INCR and sets EXPIRE on the first increment. Memory is for
    development and tests only; production validation rejects it.
    """

    def __init__(
        self,
        *,
        backend: str = "memory",
        redis_url: str = "",
        redis_client: Any = None,
        window_seconds: int = 60,
        namespace: str = "miroconsumer:rl",
        clock: Callable[[], float] = time.time,
    ) -> None:
        self.backend = (backend or "memory").lower()
        self.redis_url = redis_url or ""
        self.window_seconds = int(window_seconds)
        self.namespace = namespace
        self.clock = clock
        self._memory: dict[str, tuple[int, int]] = {}
        self._redis = redis_client
        if self.backend not in {"memory", "redis"}:
            raise ValueError("RATE_LIMIT_BACKEND must be one of ('memory', 'redis')")
        if self.backend == "redis" and self._redis is None:
            if not self.redis_url:
                raise ValueError("REDIS_URL is required when RATE_LIMIT_BACKEND=redis")
            self._redis = redis.Redis.from_url(self.redis_url)

    def check(self, key: str, *, limit: int) -> RateLimitResult:
        if limit <= 0:
            return RateLimitResult(False, limit, 0, self.window_seconds, 0)
        if self.backend == "redis":
            return self._check_redis(key, limit)
        return self._check_memory(key, limit)

    def clear(self) -> None:
        self._memory.clear()

    def _bucket(self) -> int:
        return int(self.clock() // self.window_seconds)

    def _seconds_until_next_bucket(self) -> int:
        elapsed = int(self.clock() % self.window_seconds)
        return max(1, self.window_seconds - elapsed)

    def _redis_key(self, key: str) -> str:
        return f"{self.namespace}:{self._bucket()}:{key}"

    def _check_redis(self, key: str, limit: int) -> RateLimitResult:
        redis_key = self._redis_key(key)
        count = int(self._redis.incr(redis_key))
        if count == 1:
            self._redis.expire(redis_key, self.window_seconds)
        ttl = int(self._redis.ttl(redis_key) or self._seconds_until_next_bucket())
        retry_after = ttl if ttl > 0 else self._seconds_until_next_bucket()
        remaining = max(0, limit - count)
        return RateLimitResult(count <= limit, limit, remaining, retry_after, count)

    def _check_memory(self, key: str, limit: int) -> RateLimitResult:
        bucket = self._bucket()
        stored_bucket, count = self._memory.get(key, (bucket, 0))
        if stored_bucket != bucket:
            count = 0
            stored_bucket = bucket
        count += 1
        self._memory[key] = (stored_bucket, count)
        remaining = max(0, limit - count)
        return RateLimitResult(count <= limit, limit, remaining, self._seconds_until_next_bucket(), count)


def configure_rate_limiter(app) -> RateLimiter:
    backend = app.config.get("RATE_LIMIT_BACKEND", "memory")
    redis_url = app.config.get("REDIS_URL", "")
    limiter = RateLimiter(backend=backend, redis_url=redis_url, window_seconds=60)
    app.extensions["rate_limiter"] = limiter
    return limiter


def get_rate_limiter() -> RateLimiter:
    limiter = current_app.extensions.get("rate_limiter")
    if limiter is None:
        limiter = configure_rate_limiter(current_app)
    return limiter


def _rate_limit_response(result: RateLimitResult, limit_type: str):
    payload = {
        "success": False,
        "error": "RATE_LIMITED",
        "message": f"Maximum {result.limit} requests per minute exceeded",
        "limit_type": limit_type,
        "retry_after": result.retry_after,
    }
    response = jsonify(payload)
    response.status_code = 429
    response.headers["Retry-After"] = str(result.retry_after)
    return response


def _request_identity(scope: str) -> str:
    ip = request.remote_addr or "unknown"
    user = getattr(g, "current_user", None)
    user_id = getattr(user, "user_id", "anon") if user else "anon"
    tenant_id = getattr(g, "current_tenant", None) or getattr(user, "tenant_id", None) or "default"
    if scope == "auth":
        payload = request.get_json(silent=True) or {}
        identifier = payload.get("username") or payload.get("email") or payload.get("user_id") or "unknown"
        return f"auth:ip:{ip}:id:{identifier}"
    if scope == "export":
        return f"export:tenant:{tenant_id}:user:{user_id}:ip:{ip}"
    return f"api:tenant:{tenant_id}:user:{user_id}:ip:{ip}:path:{request.path}"


def _limit_decorator(config_name: str, scope: str, f=None):
    def decorator(func):
        @wraps(func)
        def decorated(*args, **kwargs):
            if not current_app.config.get("RATE_LIMIT_ENABLED", False):
                return func(*args, **kwargs)
            limit = int(current_app.config.get(config_name, current_app.config.get("RATE_LIMIT_PER_MINUTE", 60)))
            result = get_rate_limiter().check(_request_identity(scope), limit=limit)
            if not result.allowed:
                return _rate_limit_response(result, scope)
            return func(*args, **kwargs)
        return decorated
    return decorator(f) if f is not None else decorator


def rate_limit(f=None):
    return _limit_decorator("RATE_LIMIT_PER_MINUTE", "api", f)


def auth_rate_limit(f=None):
    return _limit_decorator("AUTH_RATE_LIMIT_PER_MINUTE", "auth", f)


def export_rate_limit(f=None):
    return _limit_decorator("EXPORT_RATE_LIMIT_PER_MINUTE", "export", f)
