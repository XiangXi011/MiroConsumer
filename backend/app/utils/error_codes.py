"""统一 API 错误码"""

import uuid
import datetime


class ErrorCodes:
    # 通用
    INTERNAL_ERROR = ("INTERNAL_ERROR", "内部服务器错误", 500)
    NOT_FOUND = ("NOT_FOUND", "资源不存在", 404)
    INVALID_REQUEST = ("INVALID_REQUEST", "请求参数无效", 400)

    # 仿真
    SIMULATION_NOT_FOUND = ("SIMULATION_NOT_FOUND", "仿真任务不存在", 404)
    SIMULATION_ALREADY_RUNNING = ("SIMULATION_ALREADY_RUNNING", "仿真任务正在运行中", 409)
    SIMULATION_INVALID_PARAMS = ("SIMULATION_INVALID_PARAMS", "仿真参数无效", 400)
    SIMULATION_FAILED = ("SIMULATION_FAILED", "仿真执行失败", 500)

    # LLM
    LLM_ERROR = ("LLM_ERROR", "LLM 服务异常", 502)
    LLM_QUOTA_EXCEEDED = ("LLM_QUOTA_EXCEEDED", "LLM 配额超限", 429)
    LLM_TIMEOUT = ("LLM_TIMEOUT", "LLM 请求超时", 504)

    # 报告
    REPORT_NOT_FOUND = ("REPORT_NOT_FOUND", "报告不存在", 404)
    REPORT_GENERATION_FAILED = ("REPORT_GENERATION_FAILED", "报告生成失败", 500)


def error_response(code_tuple, details=None):
    """生成统一错误响应"""
    code, message, status = code_tuple
    resp = {
        "success": False,
        "error": code,
        "message": message,
        "request_id": str(uuid.uuid4())[:8],
        "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
    }
    if details:
        resp["details"] = details
    return resp, status
