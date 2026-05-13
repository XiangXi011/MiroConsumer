"""Structured JSON logging helpers for log aggregation."""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from typing import Any

from flask import g, has_request_context, request


class StructuredFormatter(logging.Formatter):
    """Emit JSON logs with stable aggregation and request correlation fields."""

    def __init__(self, service: str | None = None):
        super().__init__()
        self.service = service or os.environ.get("SERVICE_NAME", "backend")

    def formatTime(self, record: logging.LogRecord, datefmt: str | None = None) -> str:  # noqa: N802 - logging API
        return datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat()

    def _record_value(self, record: logging.LogRecord, name: str, default: Any = "") -> Any:
        value = getattr(record, name, default)
        return default if value is None else value

    def _request_value(self, name: str, default: Any = "") -> Any:
        if not has_request_context():
            return default
        return getattr(g, name, default)

    def _user_id(self, record: logging.LogRecord) -> str:
        record_user_id = self._record_value(record, "user_id", "")
        if record_user_id:
            return str(record_user_id)
        if not has_request_context():
            return ""
        user = getattr(g, "current_user", None)
        if user is None:
            return ""
        if isinstance(user, dict):
            return str(user.get("user_id") or user.get("id") or "")
        return str(getattr(user, "user_id", "") or getattr(user, "id", "") or "")

    def _tenant_id(self, record: logging.LogRecord) -> str:
        record_tenant_id = self._record_value(record, "tenant_id", "")
        if record_tenant_id:
            return str(record_tenant_id)
        if not has_request_context():
            return ""
        tenant_id = getattr(g, "current_tenant", "")
        if tenant_id:
            return str(tenant_id)
        user = getattr(g, "current_user", None)
        if isinstance(user, dict):
            return str(user.get("tenant_id") or "")
        return str(getattr(user, "tenant_id", "") or "")

    def format(self, record: logging.LogRecord) -> str:
        trace_id = self._record_value(record, "trace_id", "") or self._request_value("trace_id", "")
        span_id = self._record_value(record, "span_id", "") or self._request_value("span_id", "")
        service = self._record_value(record, "service", "") or self.service
        log_data: dict[str, Any] = {
            "timestamp": self.formatTime(record),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "trace_id": str(trace_id or ""),
            "span_id": str(span_id or ""),
            "service": str(service or ""),
            "tenant_id": self._tenant_id(record),
            "user_id": self._user_id(record),
        }

        for name in ("error_code", "run_id", "simulation_id", "branch_id", "agent_id", "task_id"):
            value = self._record_value(record, name, "")
            if value:
                log_data[name] = value

        if has_request_context():
            log_data.update(
                {
                    "request_id": str(trace_id or ""),
                    "method": request.method,
                    "path": request.path,
                    "remote_addr": request.remote_addr or "",
                }
            )

        if record.exc_info and record.exc_info[0]:
            log_data["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_data, ensure_ascii=False, default=str)


def setup_structured_logger(app):
    """Configure Flask and application loggers to emit structured JSON."""
    formatter = StructuredFormatter(service=app.config.get("SERVICE_NAME", os.environ.get("SERVICE_NAME", "backend")))

    target_loggers = [app.logger, logging.getLogger("miroconsumer"), logging.getLogger("miroconsumer.request")]
    for logger in target_loggers:
        for handler in logger.handlers:
            handler.setFormatter(formatter)

    app.logger.info("structured_logging_enabled")