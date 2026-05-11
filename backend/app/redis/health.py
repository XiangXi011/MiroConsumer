"""Redis dependency health checks for readiness."""

from __future__ import annotations

from typing import Optional, Tuple

import redis


def check_redis(redis_url: Optional[str]) -> Tuple[str, Optional[str]]:
    if not redis_url:
        return "skipped", None
    try:
        conn = redis.Redis.from_url(redis_url)
        conn.ping()
        return "ok", None
    except Exception as exc:  # pragma: no cover - exact client exceptions vary
        return "error", str(exc)
