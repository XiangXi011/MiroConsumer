"""Global API error codes and response helpers."""

from __future__ import annotations

import datetime
import uuid
from enum import Enum
from typing import Any


class ErrorCode(str, Enum):
    INVALID_REQUEST = "INVALID_REQUEST"
    REQUEST_VALIDATION_FAILED = "REQUEST_VALIDATION_FAILED"
    BRIEF_VALIDATION_FAILED = "BRIEF_VALIDATION_FAILED"
    AUTH_REQUIRED = "AUTH_REQUIRED"
    AUTH_FAILED = "AUTH_FAILED"
    PERMISSION_DENIED = "PERMISSION_DENIED"
    TENANT_ISOLATION_VIOLATION = "TENANT_ISOLATION_VIOLATION"
    RESOURCE_NOT_FOUND = "RESOURCE_NOT_FOUND"
    PROJECT_NOT_FOUND = "PROJECT_NOT_FOUND"
    GRAPH_NOT_FOUND = "GRAPH_NOT_FOUND"
    SIMULATION_NOT_FOUND = "SIMULATION_NOT_FOUND"
    SIMULATION_ALREADY_RUNNING = "SIMULATION_ALREADY_RUNNING"
    SIMULATION_INVALID_PARAMS = "SIMULATION_INVALID_PARAMS"
    SIMULATION_FAILED = "SIMULATION_FAILED"
    SIMULATION_ENV_NOT_RUNNING = "SIMULATION_ENV_NOT_RUNNING"
    SIMULATION_LLM_TIMEOUT = "SIMULATION_LLM_TIMEOUT"
    REPORT_NOT_FOUND = "REPORT_NOT_FOUND"
    REPORT_GENERATION_ERROR = "REPORT_GENERATION_ERROR"
    REPORT_PROGRESS_NOT_AVAILABLE = "REPORT_PROGRESS_NOT_AVAILABLE"
    CONSUMER_NOT_FOUND = "CONSUMER_NOT_FOUND"
    CONSUMER_INTERVIEW_FAILED = "CONSUMER_INTERVIEW_FAILED"
    CONSUMER_FOCUS_GROUP_FAILED = "CONSUMER_FOCUS_GROUP_FAILED"
    PERSONA_PACK_NOT_FOUND = "PERSONA_PACK_NOT_FOUND"
    PERSONA_PATCH_FAILED = "PERSONA_PATCH_FAILED"
    BRANCH_NOT_FOUND = "BRANCH_NOT_FOUND"
    BRANCH_DIFF_FAILED = "BRANCH_DIFF_FAILED"
    INTERVENTION_REPLAY_FAILED = "INTERVENTION_REPLAY_FAILED"
    LLM_ERROR = "LLM_ERROR"
    LLM_QUOTA_EXCEEDED = "LLM_QUOTA_EXCEEDED"
    LLM_TIMEOUT = "LLM_TIMEOUT"
    CONCURRENCY_CONFLICT = "CONCURRENCY_CONFLICT"
    RATE_LIMITED = "RATE_LIMITED"
    TASK_NOT_FOUND = "TASK_NOT_FOUND"
    TIMEOUT = "TIMEOUT"
    INTERNAL_ERROR = "INTERNAL_ERROR"

    def to_http_status(self) -> int:
        return _STATUS_BY_CODE.get(self, 500)


_STATUS_BY_CODE: dict[ErrorCode, int] = {
    ErrorCode.INVALID_REQUEST: 400,
    ErrorCode.REQUEST_VALIDATION_FAILED: 422,
    ErrorCode.BRIEF_VALIDATION_FAILED: 422,
    ErrorCode.AUTH_REQUIRED: 401,
    ErrorCode.AUTH_FAILED: 401,
    ErrorCode.PERMISSION_DENIED: 403,
    ErrorCode.TENANT_ISOLATION_VIOLATION: 403,
    ErrorCode.RESOURCE_NOT_FOUND: 404,
    ErrorCode.PROJECT_NOT_FOUND: 404,
    ErrorCode.GRAPH_NOT_FOUND: 404,
    ErrorCode.SIMULATION_NOT_FOUND: 404,
    ErrorCode.SIMULATION_ALREADY_RUNNING: 409,
    ErrorCode.SIMULATION_INVALID_PARAMS: 400,
    ErrorCode.SIMULATION_FAILED: 500,
    ErrorCode.SIMULATION_ENV_NOT_RUNNING: 400,
    ErrorCode.SIMULATION_LLM_TIMEOUT: 503,
    ErrorCode.REPORT_NOT_FOUND: 404,
    ErrorCode.REPORT_GENERATION_ERROR: 500,
    ErrorCode.REPORT_PROGRESS_NOT_AVAILABLE: 404,
    ErrorCode.CONSUMER_NOT_FOUND: 404,
    ErrorCode.CONSUMER_INTERVIEW_FAILED: 500,
    ErrorCode.CONSUMER_FOCUS_GROUP_FAILED: 500,
    ErrorCode.PERSONA_PACK_NOT_FOUND: 404,
    ErrorCode.PERSONA_PATCH_FAILED: 400,
    ErrorCode.BRANCH_NOT_FOUND: 404,
    ErrorCode.BRANCH_DIFF_FAILED: 400,
    ErrorCode.INTERVENTION_REPLAY_FAILED: 400,
    ErrorCode.LLM_ERROR: 502,
    ErrorCode.LLM_QUOTA_EXCEEDED: 429,
    ErrorCode.LLM_TIMEOUT: 504,
    ErrorCode.CONCURRENCY_CONFLICT: 409,
    ErrorCode.RATE_LIMITED: 429,
    ErrorCode.TASK_NOT_FOUND: 404,
    ErrorCode.TIMEOUT: 504,
    ErrorCode.INTERNAL_ERROR: 500,
}


_MESSAGES: dict[ErrorCode, str] = {
    ErrorCode.INVALID_REQUEST: "Invalid request.",
    ErrorCode.REQUEST_VALIDATION_FAILED: "Request validation failed.",
    ErrorCode.BRIEF_VALIDATION_FAILED: "Business brief validation failed.",
    ErrorCode.AUTH_REQUIRED: "Authentication required.",
    ErrorCode.AUTH_FAILED: "Authentication failed.",
    ErrorCode.PERMISSION_DENIED: "Permission denied.",
    ErrorCode.TENANT_ISOLATION_VIOLATION: "Tenant isolation violation.",
    ErrorCode.RESOURCE_NOT_FOUND: "Resource not found.",
    ErrorCode.PROJECT_NOT_FOUND: "Project not found.",
    ErrorCode.GRAPH_NOT_FOUND: "Graph not found.",
    ErrorCode.SIMULATION_NOT_FOUND: "Simulation not found.",
    ErrorCode.SIMULATION_ALREADY_RUNNING: "Simulation is already running.",
    ErrorCode.SIMULATION_INVALID_PARAMS: "Simulation parameters are invalid.",
    ErrorCode.SIMULATION_FAILED: "Simulation failed.",
    ErrorCode.SIMULATION_ENV_NOT_RUNNING: "Simulation environment is not running.",
    ErrorCode.SIMULATION_LLM_TIMEOUT: "Simulation LLM call timed out.",
    ErrorCode.REPORT_NOT_FOUND: "Report not found.",
    ErrorCode.REPORT_GENERATION_ERROR: "Report generation failed.",
    ErrorCode.REPORT_PROGRESS_NOT_AVAILABLE: "Report progress is not available.",
    ErrorCode.CONSUMER_NOT_FOUND: "Consumer data not found.",
    ErrorCode.CONSUMER_INTERVIEW_FAILED: "Consumer interview failed.",
    ErrorCode.CONSUMER_FOCUS_GROUP_FAILED: "Consumer focus group failed.",
    ErrorCode.PERSONA_PACK_NOT_FOUND: "Persona pack not found.",
    ErrorCode.PERSONA_PATCH_FAILED: "Persona patch failed.",
    ErrorCode.BRANCH_NOT_FOUND: "Branch not found.",
    ErrorCode.BRANCH_DIFF_FAILED: "Branch diff failed.",
    ErrorCode.INTERVENTION_REPLAY_FAILED: "Intervention replay failed.",
    ErrorCode.LLM_ERROR: "LLM service error.",
    ErrorCode.LLM_QUOTA_EXCEEDED: "LLM quota exceeded.",
    ErrorCode.LLM_TIMEOUT: "LLM request timed out.",
    ErrorCode.CONCURRENCY_CONFLICT: "Concurrency conflict.",
    ErrorCode.RATE_LIMITED: "Rate limit exceeded.",
    ErrorCode.TASK_NOT_FOUND: "Task not found.",
    ErrorCode.TIMEOUT: "Request timed out.",
    ErrorCode.INTERNAL_ERROR: "Internal server error.",
}


_SUGGESTIONS: dict[ErrorCode, str] = {
    ErrorCode.INVALID_REQUEST: "Check the request parameters and retry.",
    ErrorCode.REQUEST_VALIDATION_FAILED: "Check the request JSON body and retry with the documented schema.",
    ErrorCode.BRIEF_VALIDATION_FAILED: "Fix the business brief fields reported in the error details.",
    ErrorCode.AUTH_REQUIRED: "Provide a valid Bearer token or API key.",
    ErrorCode.AUTH_FAILED: "Check credentials and retry.",
    ErrorCode.PERMISSION_DENIED: "Use an account or API key with the required permission.",
    ErrorCode.TENANT_ISOLATION_VIOLATION: "Request only resources that belong to the active tenant.",
    ErrorCode.RESOURCE_NOT_FOUND: "Verify the resource id and retry.",
    ErrorCode.PROJECT_NOT_FOUND: "Verify the project id and retry.",
    ErrorCode.GRAPH_NOT_FOUND: "Verify the graph id and retry.",
    ErrorCode.SIMULATION_NOT_FOUND: "Verify the simulation id and retry.",
    ErrorCode.SIMULATION_ALREADY_RUNNING: "Wait for the current run or stop it before retrying.",
    ErrorCode.SIMULATION_INVALID_PARAMS: "Check simulation parameters and retry.",
    ErrorCode.SIMULATION_FAILED: "Inspect simulation diagnostics and retry.",
    ErrorCode.SIMULATION_ENV_NOT_RUNNING: "Start or resume the simulation environment.",
    ErrorCode.SIMULATION_LLM_TIMEOUT: "Retry later or use deterministic fallback mode.",
    ErrorCode.REPORT_NOT_FOUND: "Verify the report id and retry.",
    ErrorCode.REPORT_GENERATION_ERROR: "Retry report generation or inspect report diagnostics.",
    ErrorCode.REPORT_PROGRESS_NOT_AVAILABLE: "Start report generation before polling progress.",
    ErrorCode.CONSUMER_NOT_FOUND: "Verify the consumer or persona id and retry.",
    ErrorCode.CONSUMER_INTERVIEW_FAILED: "Retry the interview or inspect runtime logs.",
    ErrorCode.CONSUMER_FOCUS_GROUP_FAILED: "Retry the focus group with a smaller participant set.",
    ErrorCode.PERSONA_PACK_NOT_FOUND: "Verify the persona pack id.",
    ErrorCode.PERSONA_PATCH_FAILED: "Check the patch fields and retry.",
    ErrorCode.BRANCH_NOT_FOUND: "Verify the branch id and simulation id.",
    ErrorCode.BRANCH_DIFF_FAILED: "Verify both branches have comparable snapshots.",
    ErrorCode.INTERVENTION_REPLAY_FAILED: "Check the intervention sequence JSON and retry.",
    ErrorCode.LLM_ERROR: "Retry later or switch provider.",
    ErrorCode.LLM_QUOTA_EXCEEDED: "Reduce workload or raise the LLM budget.",
    ErrorCode.LLM_TIMEOUT: "Retry after a short delay.",
    ErrorCode.CONCURRENCY_CONFLICT: "Refresh resource state and retry.",
    ErrorCode.RATE_LIMITED: "Wait for the retry window before sending more requests.",
    ErrorCode.TASK_NOT_FOUND: "Verify the task id and retry.",
    ErrorCode.TIMEOUT: "Retry with a longer timeout or smaller workload.",
    ErrorCode.INTERNAL_ERROR: "Retry later; contact support if the issue persists.",
}


class ErrorCodes:
    INTERNAL_ERROR = ("INTERNAL_ERROR", "\u5185\u90e8\u670d\u52a1\u5668\u9519\u8bef", 500)
    NOT_FOUND = ("NOT_FOUND", "\u8d44\u6e90\u4e0d\u5b58\u5728", 404)
    INVALID_REQUEST = ("INVALID_REQUEST", "\u8bf7\u6c42\u53c2\u6570\u65e0\u6548", 400)
    VALIDATION_ERROR = ("VALIDATION_ERROR", "\u8bf7\u6c42\u6821\u9a8c\u5931\u8d25", 400)
    FORBIDDEN = ("FORBIDDEN", "\u6743\u9650\u4e0d\u8db3", 403)
    AUTH_REQUIRED = ("AUTH_REQUIRED", "\u9700\u8981\u8ba4\u8bc1", 401)
    AUTH_FAILED = ("AUTH_FAILED", "\u8ba4\u8bc1\u5931\u8d25", 401)
    SIMULATION_NOT_FOUND = ("SIMULATION_NOT_FOUND", "\u4eff\u771f\u4efb\u52a1\u4e0d\u5b58\u5728", 404)
    SIMULATION_ALREADY_RUNNING = ("SIMULATION_ALREADY_RUNNING", "\u4eff\u771f\u4efb\u52a1\u6b63\u5728\u8fd0\u884c\u4e2d", 409)
    SIMULATION_INVALID_PARAMS = ("SIMULATION_INVALID_PARAMS", "\u4eff\u771f\u53c2\u6570\u65e0\u6548", 400)
    SIMULATION_FAILED = ("SIMULATION_FAILED", "\u4eff\u771f\u6267\u884c\u5931\u8d25", 500)
    SIMULATION_ENV_NOT_RUNNING = ("SIMULATION_ENV_NOT_RUNNING", "\u4eff\u771f\u73af\u5883\u672a\u8fd0\u884c", 400)
    LLM_ERROR = ("LLM_ERROR", "LLM \u670d\u52a1\u5f02\u5e38", 502)
    LLM_QUOTA_EXCEEDED = ("LLM_QUOTA_EXCEEDED", "LLM \u914d\u989d\u8d85\u9650", 429)
    LLM_TIMEOUT = ("LLM_TIMEOUT", "LLM \u8bf7\u6c42\u8d85\u65f6", 504)
    REPORT_NOT_FOUND = ("REPORT_NOT_FOUND", "\u62a5\u544a\u4e0d\u5b58\u5728", 404)
    REPORT_GENERATION_FAILED = ("REPORT_GENERATION_FAILED", "\u62a5\u544a\u751f\u6210\u5931\u8d25", 500)
    REPORT_PROGRESS_NOT_AVAILABLE = ("REPORT_PROGRESS_NOT_AVAILABLE", "\u62a5\u544a\u8fdb\u5ea6\u4e0d\u53ef\u7528", 404)
    CONSUMER_NOT_FOUND = ("CONSUMER_NOT_FOUND", "\u6d88\u8d39\u8005\u6570\u636e\u4e0d\u5b58\u5728", 404)
    CONSUMER_INTERVIEW_FAILED = ("CONSUMER_INTERVIEW_FAILED", "\u6d88\u8d39\u8005\u8bbf\u8c08\u5931\u8d25", 500)
    CONSUMER_FOCUS_GROUP_FAILED = ("CONSUMER_FOCUS_GROUP_FAILED", "\u7126\u70b9\u5c0f\u7ec4\u6267\u884c\u5931\u8d25", 500)
    GRAPH_NOT_FOUND = ("GRAPH_NOT_FOUND", "\u56fe\u8c31\u4e0d\u5b58\u5728", 404)
    GRAPH_BUILD_FAILED = ("GRAPH_BUILD_FAILED", "\u56fe\u8c31\u6784\u5efa\u5931\u8d25", 500)
    PROJECT_NOT_FOUND = ("PROJECT_NOT_FOUND", "\u9879\u76ee\u4e0d\u5b58\u5728", 404)
    TASK_NOT_FOUND = ("TASK_NOT_FOUND", "\u4efb\u52a1\u4e0d\u5b58\u5728", 404)
    BRANCH_NOT_FOUND = ("BRANCH_NOT_FOUND", "\u5206\u652f\u4e0d\u5b58\u5728", 404)
    CONFLICT = ("CONFLICT", "\u8d44\u6e90\u51b2\u7a81", 409)
    TIMEOUT = ("TIMEOUT", "\u8bf7\u6c42\u8d85\u65f6", 504)


_LEGACY_CODE_MAP: dict[str, ErrorCode] = {
    "NOT_FOUND": ErrorCode.RESOURCE_NOT_FOUND,
    "VALIDATION_ERROR": ErrorCode.REQUEST_VALIDATION_FAILED,
    "FORBIDDEN": ErrorCode.PERMISSION_DENIED,
    "CONFLICT": ErrorCode.CONCURRENCY_CONFLICT,
    "GRAPH_BUILD_FAILED": ErrorCode.GRAPH_NOT_FOUND,
}
def _coerce_code(code: ErrorCode | str) -> ErrorCode:
    if isinstance(code, ErrorCode):
        return code
    raw = str(code)
    if raw in _LEGACY_CODE_MAP:
        return _LEGACY_CODE_MAP[raw]
    try:
        return ErrorCode(raw)
    except ValueError:
        return ErrorCode.INTERNAL_ERROR

def error_payload(
    code: ErrorCode | str,
    *,
    message: str | None = None,
    field: str = "",
    request_id: str | None = None,
    suggestion: str | None = None,
    details: Any = None,
    **extra: Any,
) -> dict[str, Any]:
    canonical = _coerce_code(code)
    error_message = message or _MESSAGES[canonical]
    payload: dict[str, Any] = {
        "success": False,
        "error": canonical.value,
        "message": error_message,
        "error_code": canonical.value,
        "error_message": error_message,
        "field": field,
        "request_id": request_id or str(uuid.uuid4())[:8],
        "suggestion": suggestion or _SUGGESTIONS[canonical],
        "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
    }
    if details is not None:
        payload["details"] = details
    payload.update(extra)
    return payload


def infer_error_code(status_code: int, error: Any = None) -> ErrorCode:
    text = str(error or "").upper()
    for code in ErrorCode:
        if code.value == text:
            return code
    if status_code == 401:
        return ErrorCode.AUTH_REQUIRED
    if status_code == 403:
        return ErrorCode.PERMISSION_DENIED
    if status_code == 404:
        return ErrorCode.RESOURCE_NOT_FOUND
    if status_code == 409:
        return ErrorCode.CONCURRENCY_CONFLICT
    if status_code == 422:
        return ErrorCode.REQUEST_VALIDATION_FAILED
    if status_code == 429:
        return ErrorCode.RATE_LIMITED
    if status_code == 504:
        return ErrorCode.TIMEOUT
    if status_code >= 500:
        return ErrorCode.INTERNAL_ERROR
    return ErrorCode.INVALID_REQUEST


def normalize_error_payload(payload: dict[str, Any], status_code: int) -> dict[str, Any]:
    if payload.get("success") is not False or payload.get("error_code"):
        return payload
    code = infer_error_code(status_code, payload.get("error"))
    message = str(payload.get("message") or payload.get("error") or _MESSAGES[code])
    normalized = error_payload(
        code,
        message=message,
        details=payload.get("details"),
    )
    original_error = payload.get("error")
    for key, value in payload.items():
        if key == "error":
            continue
        normalized.setdefault(key, value)
    if original_error:
        normalized["error"] = original_error
    return normalized


def error_response(code_tuple: tuple[str, str, int] | ErrorCode, details: Any = None):
    if isinstance(code_tuple, ErrorCode):
        code = code_tuple
        status = code.to_http_status()
        message = None
    else:
        raw_code, message, status = code_tuple
        code = _coerce_code(raw_code)
    return error_payload(code, message=message, details=details), status


def success_response(data: Any, **extra: Any) -> dict[str, Any]:
    resp = {"success": True, "data": data}
    resp.update(extra)
    return resp


def paginated_response(items: Any, pagination: Any, **extra: Any) -> dict[str, Any]:
    resp = {"success": True, "data": items, "pagination": pagination}
    resp.update(extra)
    return resp


__all__ = [
    "ErrorCode",
    "ErrorCodes",
    "error_payload",
    "error_response",
    "infer_error_code",
    "normalize_error_payload",
    "paginated_response",
    "success_response",
]

