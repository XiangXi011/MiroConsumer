"""统一 API 错误码"""

import uuid
import datetime


class ErrorCodes:
    # 通用
    INTERNAL_ERROR = ("INTERNAL_ERROR", "内部服务器错误", 500)
    NOT_FOUND = ("NOT_FOUND", "资源不存在", 404)
    INVALID_REQUEST = ("INVALID_REQUEST", "请求参数无效", 400)
    VALIDATION_ERROR = ("VALIDATION_ERROR", "请求校验失败", 400)
    FORBIDDEN = ("FORBIDDEN", "权限不足", 403)
    AUTH_REQUIRED = ("AUTH_REQUIRED", "需要认证", 401)
    AUTH_FAILED = ("AUTH_FAILED", "认证失败", 401)

    # 仿真
    SIMULATION_NOT_FOUND = ("SIMULATION_NOT_FOUND", "仿真任务不存在", 404)
    SIMULATION_ALREADY_RUNNING = ("SIMULATION_ALREADY_RUNNING", "仿真任务正在运行中", 409)
    SIMULATION_INVALID_PARAMS = ("SIMULATION_INVALID_PARAMS", "仿真参数无效", 400)
    SIMULATION_FAILED = ("SIMULATION_FAILED", "仿真执行失败", 500)
    SIMULATION_ENV_NOT_RUNNING = ("SIMULATION_ENV_NOT_RUNNING", "仿真环境未运行", 400)

    # LLM
    LLM_ERROR = ("LLM_ERROR", "LLM 服务异常", 502)
    LLM_QUOTA_EXCEEDED = ("LLM_QUOTA_EXCEEDED", "LLM 配额超限", 429)
    LLM_TIMEOUT = ("LLM_TIMEOUT", "LLM 请求超时", 504)

    # 报告
    REPORT_NOT_FOUND = ("REPORT_NOT_FOUND", "报告不存在", 404)
    REPORT_GENERATION_FAILED = ("REPORT_GENERATION_FAILED", "报告生成失败", 500)
    REPORT_PROGRESS_NOT_AVAILABLE = ("REPORT_PROGRESS_NOT_AVAILABLE", "报告进度不可用", 404)

    # 消费者
    CONSUMER_NOT_FOUND = ("CONSUMER_NOT_FOUND", "消费者数据不存在", 404)
    CONSUMER_INTERVIEW_FAILED = ("CONSUMER_INTERVIEW_FAILED", "消费者访谈失败", 500)
    CONSUMER_FOCUS_GROUP_FAILED = ("CONSUMER_FOCUS_GROUP_FAILED", "焦点小组执行失败", 500)

    # 图谱
    GRAPH_NOT_FOUND = ("GRAPH_NOT_FOUND", "图谱不存在", 404)
    GRAPH_BUILD_FAILED = ("GRAPH_BUILD_FAILED", "图谱构建失败", 500)
    PROJECT_NOT_FOUND = ("PROJECT_NOT_FOUND", "项目不存在", 404)

    # 任务
    TASK_NOT_FOUND = ("TASK_NOT_FOUND", "任务不存在", 404)

    # 分支
    BRANCH_NOT_FOUND = ("BRANCH_NOT_FOUND", "分支不存在", 404)
    CONFLICT = ("CONFLICT", "资源冲突", 409)

    # 通用超时
    TIMEOUT = ("TIMEOUT", "请求超时", 504)


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


def success_response(data, **extra):
    """生成统一成功响应"""
    resp = {"success": True, "data": data}
    resp.update(extra)
    return resp


def paginated_response(items, pagination, **extra):
    """生成统一分页响应"""
    resp = {"success": True, "data": items, "pagination": pagination}
    resp.update(extra)
    return resp
