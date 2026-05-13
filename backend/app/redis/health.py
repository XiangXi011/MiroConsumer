"""Redis dependency health checks for readiness."""

from __future__ import annotations

from typing import Optional, Tuple

import redis


def _normalize_config_value(value: object) -> str:
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace").lower()
    return str(value or "").lower()


def _get_config_value(conn: redis.Redis, key: str) -> str:
    values = conn.config_get(key)
    return _normalize_config_value(values.get(key) or values.get(key.encode("utf-8")))


def check_redis(redis_url: Optional[str], persistence_required: bool = False) -> Tuple[str, Optional[str]]:
    if not redis_url:
        return "skipped", None
    try:
        conn = redis.Redis.from_url(redis_url)
        conn.ping()
        if not persistence_required:
            return "ok", None

        appendonly = _get_config_value(conn, "appendonly")
        appendfsync = _get_config_value(conn, "appendfsync")
        if appendonly == "yes" and appendfsync == "everysec":
            return "ok", None
        return (
            "warning",
            "Redis persistence is not production-ready: "
            f"appendonly={appendonly or 'unknown'}, appendfsync={appendfsync or 'unknown'}; "
            "expected appendonly=yes and appendfsync=everysec",
        )
    except Exception as exc:  # pragma: no cover - exact client exceptions vary
        if persistence_required and "CONFIG" in str(exc).upper():
            return "warning", f"Redis persistence status could not be verified: {exc}"
        return "error", str(exc)