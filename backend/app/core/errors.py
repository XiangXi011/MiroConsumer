"""Canonical API error codes and response payload helpers."""

from __future__ import annotations

import uuid
from enum import Enum
from typing import Any


class MCErrCode(str, Enum):
    INVALID_REQUEST = "INVALID_REQUEST"
    REQUEST_VALIDATION_FAILED = "REQUEST_VALIDATION_FAILED"
    BRIEF_VALIDATION_FAILED = "BRIEF_VALIDATION_FAILED"
    AUTH_REQUIRED = "AUTH_REQUIRED"
    PERMISSION_DENIED = "PERMISSION_DENIED"
    TENANT_ISOLATION_VIOLATION = "TENANT_ISOLATION_VIOLATION"
    RESOURCE_NOT_FOUND = "RESOURCE_NOT_FOUND"
    BUSINESS_CONFLICT = "BUSINESS_CONFLICT"
    RATE_LIMITED = "RATE_LIMITED"
    SIMULATION_LLM_TIMEOUT = "SIMULATION_LLM_TIMEOUT"
    REPORT_GENERATION_ERROR = "REPORT_GENERATION_ERROR"
    INTERNAL_ERROR = "INTERNAL_ERROR"

    def to_http_status(self) -> int:
        return {
            MCErrCode.INVALID_REQUEST: 400,
            MCErrCode.REQUEST_VALIDATION_FAILED: 422,
            MCErrCode.BRIEF_VALIDATION_FAILED: 422,
            MCErrCode.AUTH_REQUIRED: 401,
            MCErrCode.PERMISSION_DENIED: 403,
            MCErrCode.TENANT_ISOLATION_VIOLATION: 403,
            MCErrCode.RESOURCE_NOT_FOUND: 404,
            MCErrCode.BUSINESS_CONFLICT: 409,
            MCErrCode.RATE_LIMITED: 429,
            MCErrCode.SIMULATION_LLM_TIMEOUT: 503,
            MCErrCode.REPORT_GENERATION_ERROR: 500,
            MCErrCode.INTERNAL_ERROR: 500,
        }[self]


_DEFAULT_MESSAGES: dict[MCErrCode, str] = {
    MCErrCode.INVALID_REQUEST: "Invalid request.",
    MCErrCode.REQUEST_VALIDATION_FAILED: "Request validation failed.",
    MCErrCode.BRIEF_VALIDATION_FAILED: "Business brief validation failed.",
    MCErrCode.AUTH_REQUIRED: "Authentication required.",
    MCErrCode.PERMISSION_DENIED: "Permission denied.",
    MCErrCode.TENANT_ISOLATION_VIOLATION: "Tenant isolation violation.",
    MCErrCode.RESOURCE_NOT_FOUND: "Resource not found.",
    MCErrCode.BUSINESS_CONFLICT: "Business rule conflict.",
    MCErrCode.RATE_LIMITED: "Rate limit exceeded.",
    MCErrCode.SIMULATION_LLM_TIMEOUT: "Simulation LLM call timed out.",
    MCErrCode.REPORT_GENERATION_ERROR: "Report generation failed.",
    MCErrCode.INTERNAL_ERROR: "Internal server error.",
}


_DEFAULT_SUGGESTIONS: dict[MCErrCode, str] = {
    MCErrCode.INVALID_REQUEST: "Check the request parameters and retry.",
    MCErrCode.REQUEST_VALIDATION_FAILED: "Check the request JSON body and retry with the documented schema.",
    MCErrCode.BRIEF_VALIDATION_FAILED: "Fix the business brief fields reported in the error details.",
    MCErrCode.AUTH_REQUIRED: "Provide a valid Bearer token or API key.",
    MCErrCode.PERMISSION_DENIED: "Use an account or API key with the required permission.",
    MCErrCode.TENANT_ISOLATION_VIOLATION: "Request only resources that belong to the active tenant.",
    MCErrCode.RESOURCE_NOT_FOUND: "Verify the resource id and retry.",
    MCErrCode.BUSINESS_CONFLICT: "Refresh the resource state and retry the operation.",
    MCErrCode.RATE_LIMITED: "Wait for the retry window before sending more requests.",
    MCErrCode.SIMULATION_LLM_TIMEOUT: "Retry later or use deterministic fallback mode.",
    MCErrCode.REPORT_GENERATION_ERROR: "Retry report generation or inspect report diagnostics.",
    MCErrCode.INTERNAL_ERROR: "Retry later; contact support if the issue persists.",
}


def build_error_payload(
    code: MCErrCode,
    *,
    message: str | None = None,
    field: str = "",
    request_id: str | None = None,
    suggestion: str | None = None,
    legacy_error: str | None = None,
    details: Any = None,
    **extra: Any,
) -> dict[str, Any]:
    error_message = message or _DEFAULT_MESSAGES[code]
    payload: dict[str, Any] = {
        "success": False,
        "error": legacy_error or code.value,
        "message": error_message,
        "error_code": code.value,
        "error_message": error_message,
        "field": field,
        "request_id": request_id or str(uuid.uuid4())[:8],
        "suggestion": suggestion or _DEFAULT_SUGGESTIONS[code],
    }
    if details is not None:
        payload["details"] = details
    payload.update(extra)
    return payload
