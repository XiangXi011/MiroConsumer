"""Append-only JSONL audit logging with sensitive-field redaction."""

from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Optional

from flask import current_app, has_app_context

SENSITIVE_KEY_PARTS = (
    "password",
    "token",
    "api_key",
    "apikey",
    "secret",
    "authorization",
    "credential",
)


class AuditLogger:
    """Small JSONL audit logger used by auth and tenant guard paths."""

    def __init__(self, path: str | os.PathLike[str]) -> None:
        self.path = Path(path) if path else None

    def record(
        self,
        *,
        event_type: str,
        actor_user_id: Optional[str] = None,
        actor_tenant_id: Optional[str] = None,
        target_type: Optional[str] = None,
        target_id: Optional[str] = None,
        ip: Optional[str] = None,
        user_agent: Optional[str] = None,
        success: bool = True,
        reason: Optional[str] = None,
        details: Optional[Mapping[str, Any]] = None,
    ) -> dict:
        event = {
            "event_id": f"audit_{uuid.uuid4().hex}",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event_type": event_type,
            "actor_user_id": actor_user_id,
            "actor_tenant_id": actor_tenant_id,
            "target_type": target_type,
            "target_id": target_id,
            "ip": ip,
            "user_agent": user_agent,
            "success": bool(success),
            "reason": reason,
            "details": redact(details or {}),
        }
        if self.path:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with self.path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n")
        return event


def redact(value: Any) -> Any:
    """Recursively redact values under sensitive-looking keys."""

    if isinstance(value, Mapping):
        redacted = {}
        for key, item in value.items():
            key_text = str(key).lower()
            if any(part in key_text for part in SENSITIVE_KEY_PARTS):
                redacted[key] = "***REDACTED***"
            else:
                redacted[key] = redact(item)
        return redacted
    if isinstance(value, list):
        return [redact(item) for item in value]
    if isinstance(value, tuple):
        return tuple(redact(item) for item in value)
    return value


def get_audit_logger() -> Optional[AuditLogger]:
    if not has_app_context():
        return None
    logger = current_app.extensions.get("audit_logger")
    if logger is not None:
        return logger
    path = current_app.config.get("AUDIT_LOG_PATH", "")
    logger = AuditLogger(path) if path else None
    current_app.extensions["audit_logger"] = logger
    return logger


def audit_event(**kwargs) -> Optional[dict]:
    logger = get_audit_logger()
    if logger is None:
        return None
    return logger.record(**kwargs)
