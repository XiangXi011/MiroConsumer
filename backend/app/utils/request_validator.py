"""API 请求验证辅助函数"""

from flask import request, jsonify
from pydantic import BaseModel, ValidationError
from typing import Type, TypeVar, Optional, Union

T = TypeVar('T', bound=BaseModel)


def safe_get_json(required: bool = True) -> Union[dict, tuple]:
    """安全获取 JSON 请求体，无效 JSON 返回 400。
    
    用法：
        data = safe_get_json()
        if isinstance(data, tuple): return data  # 错误响应
    """
    data = request.get_json(silent=True)
    if data is None:
        if required:
            return jsonify({
                "success": False,
                "error": "INVALID_REQUEST",
                "message": "Request body must be valid JSON"
            }), 400
        return {}
    if not isinstance(data, dict):
        return jsonify({
            "success": False,
            "error": "INVALID_REQUEST",
            "message": "Request body must be a JSON object"
        }), 400
    return data


def validate_json(schema_class: Type[T], data: dict = None) -> Union[T, tuple]:
    """用 Pydantic schema 验证数据。
    
    用法：
        data = safe_get_json()
        if isinstance(data, tuple): return data
        validated = validate_json(MySchema, data)
        if isinstance(validated, tuple): return validated
    """
    if data is None:
        data = safe_get_json()
        if isinstance(data, tuple):
            return data
    try:
        return schema_class(**data)
    except ValidationError as e:
        errors = []
        for err in e.errors():
            field = ".".join(str(loc) for loc in err["loc"])
            errors.append({"field": field, "message": err["msg"], "type": err["type"]})
        return jsonify({
            "success": False,
            "error": "VALIDATION_ERROR",
            "message": "Request validation failed",
            "details": errors
        }), 400
