"""Fixed-window API rate limiting with memory and Redis backends."""

from __future__ import annotations

import time
import threading
from dataclasses import dataclass
from functools import wraps
from typing import Any, Callable, Optional

import redis
from flask import current_app, g, jsonify, request

from ..core.errors import MCErrCode, build_error_payload


@dataclass
class RateLimitResult:
    allowed: bool
    limit: int
    remaining: int
    retry_after: int
    count: int
    window_seconds: int = 60


@dataclass(frozen=True)
class RateLimitPolicy:
    limit: int
    window_seconds: int


class ExportConcurrencyLimiter:
    """Process-local guard that allows one active export per user identity."""

    def __init__(self) -> None:
        self._active: set[str] = set()
        self._lock = threading.Lock()

    def acquire(self, key: str) -> bool:
        with self._lock:
            if key in self._active:
                return False
            self._active.add(key)
            return True

    def release(self, key: str) -> None:
        with self._lock:
            self._active.discard(key)


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

    def check(self, key: str, *, limit: int, window_seconds: Optional[int] = None) -> RateLimitResult:
        window = int(window_seconds or self.window_seconds)
        if limit <= 0:
            return RateLimitResult(False, limit, 0, window, 0, window)
        if self.backend == "redis":
            return self._check_redis(key, limit, window)
        return self._check_memory(key, limit, window)

    def clear(self) -> None:
        self._memory.clear()

    def _bucket(self, window_seconds: int) -> int:
        return int(self.clock() // window_seconds)

    def _seconds_until_next_bucket(self, window_seconds: int) -> int:
        elapsed = int(self.clock() % window_seconds)
        return max(1, window_seconds - elapsed)

    def _redis_key(self, key: str, window_seconds: int) -> str:
        return f"{self.namespace}:{window_seconds}:{self._bucket(window_seconds)}:{key}"

    def _check_redis(self, key: str, limit: int, window_seconds: int) -> RateLimitResult:
        redis_key = self._redis_key(key, window_seconds)
        count = int(self._redis.incr(redis_key))
        if count == 1:
            self._redis.expire(redis_key, window_seconds)
        ttl = int(self._redis.ttl(redis_key) or self._seconds_until_next_bucket(window_seconds))
        retry_after = ttl if ttl > 0 else self._seconds_until_next_bucket(window_seconds)
        remaining = max(0, limit - count)
        return RateLimitResult(count <= limit, limit, remaining, retry_after, count, window_seconds)

    def _check_memory(self, key: str, limit: int, window_seconds: int) -> RateLimitResult:
        bucket = self._bucket(window_seconds)
        memory_key = f"{window_seconds}:{key}"
        stored_bucket, count = self._memory.get(memory_key, (bucket, 0))
        if stored_bucket != bucket:
            count = 0
            stored_bucket = bucket
        count += 1
        self._memory[memory_key] = (stored_bucket, count)
        remaining = max(0, limit - count)
        return RateLimitResult(
            count <= limit,
            limit,
            remaining,
            self._seconds_until_next_bucket(window_seconds),
            count,
            window_seconds,
        )


def configure_rate_limiter(app) -> RateLimiter:
    backend = app.config.get("RATE_LIMIT_BACKEND", "memory")
    redis_url = app.config.get("REDIS_URL", "")
    limiter = RateLimiter(backend=backend, redis_url=redis_url, window_seconds=60)
    app.extensions["rate_limiter"] = limiter
    app.extensions.setdefault("export_concurrency_limiter", ExportConcurrencyLimiter())
    return limiter


def get_rate_limiter() -> RateLimiter:
    limiter = current_app.extensions.get("rate_limiter")
    if limiter is None:
        limiter = configure_rate_limiter(current_app)
    return limiter


def get_export_concurrency_limiter() -> ExportConcurrencyLimiter:
    limiter = current_app.extensions.get("export_concurrency_limiter")
    if limiter is None:
        limiter = ExportConcurrencyLimiter()
        current_app.extensions["export_concurrency_limiter"] = limiter
    return limiter


def _rate_limit_response(result: RateLimitResult, limit_type: str):
    payload = build_error_payload(
        MCErrCode.RATE_LIMITED,
        message=f"Maximum {result.limit} requests per minute exceeded",
        request_id=getattr(g, "request_id", None),
        legacy_error="RATE_LIMITED",
        limit_type=limit_type,
        retry_after=result.retry_after,
    )
    response = jsonify(payload)
    response.status_code = 429
    response.headers["Retry-After"] = str(result.retry_after)
    _attach_rate_limit_headers(response)
    return response


def _concurrent_export_response():
    payload = build_error_payload(
        MCErrCode.RATE_LIMITED,
        message="Concurrent export limit exceeded",
        request_id=getattr(g, "request_id", None),
        legacy_error="RATE_LIMITED",
        limit_type="export_concurrency",
        retry_after=1,
    )
    response = jsonify(payload)
    response.status_code = 429
    response.headers["Retry-After"] = "1"
    _attach_rate_limit_headers(response)
    return response


def _parse_rate_limit_policy(raw_value: Any, default_limit: int = 60, default_window: int = 60) -> RateLimitPolicy:
    if raw_value is None:
        return RateLimitPolicy(default_limit, default_window)
    if isinstance(raw_value, int):
        return RateLimitPolicy(raw_value, default_window)

    text = str(raw_value).strip().lower()
    if not text:
        return RateLimitPolicy(default_limit, default_window)

    number_part = text.split("/", 1)[0].strip()
    try:
        limit = int(number_part)
    except ValueError:
        return RateLimitPolicy(default_limit, default_window)

    if "/" not in text:
        return RateLimitPolicy(limit, default_window)
    unit = text.split("/", 1)[1].split()[0].strip()
    windows = {
        "s": 1,
        "sec": 1,
        "second": 1,
        "seconds": 1,
        "m": 60,
        "min": 60,
        "minute": 60,
        "minutes": 60,
        "h": 3600,
        "hr": 3600,
        "hour": 3600,
        "hours": 3600,
    }
    return RateLimitPolicy(limit, windows.get(unit, default_window))


def _request_parts() -> dict[str, str]:
    ip = request.remote_addr or "unknown"
    user = getattr(g, "current_user", None)
    user_id = getattr(user, "user_id", "anon") if user else "anon"
    tenant_id = getattr(g, "current_tenant", None) or getattr(user, "tenant_id", None) or "default"
    return {"ip": ip, "user_id": user_id, "tenant_id": tenant_id, "path": request.path}


def _request_identity(scope: str) -> str:
    parts = _request_parts()
    ip = parts["ip"]
    user_id = parts["user_id"]
    tenant_id = parts["tenant_id"]
    if scope == "auth":
        payload = request.get_json(silent=True) or {}
        identifier = payload.get("username") or payload.get("email") or payload.get("user_id") or "unknown"
        return f"auth:ip:{ip}:id:{identifier}"
    if scope == "export":
        return f"export:tenant:{tenant_id}:user:{user_id}:ip:{ip}"
    return f"api:tenant:{tenant_id}:user:{user_id}:ip:{ip}:path:{parts['path']}"


def _api_dimension_checks() -> list[tuple[str, str, RateLimitPolicy]]:
    parts = _request_parts()
    return [
        (
            "tenant",
            f"api:tenant:{parts['tenant_id']}:path:{parts['path']}",
            _parse_rate_limit_policy(
                current_app.config.get("RATE_LIMIT_TENANT"),
                current_app.config.get("RATE_LIMIT_TENANT_PER_MINUTE", 1000),
            ),
        ),
        (
            "user",
            f"api:tenant:{parts['tenant_id']}:user:{parts['user_id']}:path:{parts['path']}",
            _parse_rate_limit_policy(
                current_app.config.get("RATE_LIMIT_USER"),
                current_app.config.get("RATE_LIMIT_USER_PER_MINUTE", current_app.config.get("RATE_LIMIT_PER_MINUTE", 60)),
            ),
        ),
        (
            "ip",
            f"api:ip:{parts['ip']}:path:{parts['path']}",
            _parse_rate_limit_policy(
                current_app.config.get("RATE_LIMIT_IP"),
                current_app.config.get("RATE_LIMIT_IP_PER_MINUTE", current_app.config.get("RATE_LIMIT_PER_MINUTE", 60)),
            ),
        ),
    ]


def _record_rate_limit_result(limit_type: str, result: RateLimitResult) -> None:
    results = getattr(g, "rate_limit_results", {})
    results[limit_type] = result
    g.rate_limit_results = results


def _attach_rate_limit_headers(response):
    results = getattr(g, "rate_limit_results", {})
    header_names = {
        "ip": "X-RateLimit-Remaining-IP",
        "user": "X-RateLimit-Remaining-User",
        "tenant": "X-RateLimit-Remaining-Tenant",
        "export": "X-RateLimit-Export-Remaining",
        "auth": "X-RateLimit-Remaining-Auth",
        "api": "X-RateLimit-Remaining",
    }
    for limit_type, result in results.items():
        header_name = header_names.get(limit_type)
        if header_name:
            response.headers[header_name] = str(result.remaining)
    return response


def _limit_decorator(config_name: str, scope: str, f=None):
    def decorator(func):
        @wraps(func)
        def decorated(*args, **kwargs):
            if not current_app.config.get("RATE_LIMIT_ENABLED", False):
                return func(*args, **kwargs)
            limiter = get_rate_limiter()
            if scope == "api":
                for limit_type, identity, policy in _api_dimension_checks():
                    result = limiter.check(identity, limit=policy.limit, window_seconds=policy.window_seconds)
                    _record_rate_limit_result(limit_type, result)
                    if not result.allowed:
                        return _rate_limit_response(result, limit_type)
                response = current_app.make_response(func(*args, **kwargs))
                return _attach_rate_limit_headers(response)

            concurrency_key = ""
            concurrency_limiter = None
            if scope == "export":
                concurrency_key = _request_identity(scope)
                concurrency_limiter = get_export_concurrency_limiter()
                if not concurrency_limiter.acquire(concurrency_key):
                    return _concurrent_export_response()

            policy = _parse_rate_limit_policy(
                current_app.config.get(config_name),
                current_app.config.get("RATE_LIMIT_PER_MINUTE", 60),
            )
            try:
                result = limiter.check(
                    concurrency_key or _request_identity(scope),
                    limit=policy.limit,
                    window_seconds=policy.window_seconds,
                )
                _record_rate_limit_result(scope, result)
                if not result.allowed:
                    return _rate_limit_response(result, scope)
                response = current_app.make_response(func(*args, **kwargs))
                return _attach_rate_limit_headers(response)
            finally:
                if concurrency_limiter is not None:
                    concurrency_limiter.release(concurrency_key)
        return decorated
    return decorator(f) if f is not None else decorator


def rate_limit(f=None):
    return _limit_decorator("RATE_LIMIT_PER_MINUTE", "api", f)


def auth_rate_limit(f=None):
    return _limit_decorator("AUTH_RATE_LIMIT_PER_MINUTE", "auth", f)


def export_rate_limit(f=None):
    return _limit_decorator("EXPORT_RATE_LIMIT", "export", f)
