"""API输入校验函数"""

from flask import jsonify
from pydantic import BaseModel, ValidationError


def validate_simulation_params(data: dict) -> list[str]:
    """校验仿真请求参数。

    校验规则：
    - max_agents: 1-1000 之间（可选）
    - max_rounds: 1-100 之间（可选）
    - mode: 必须是 'standard' 或 'advanced'（可选）

    Returns:
        错误消息列表，空列表表示校验通过。
    """
    errors = []

    max_agents = data.get('max_agents')
    if max_agents is not None:
        if not isinstance(max_agents, int):
            errors.append("max_agents 必须是整数")
        elif max_agents < 1 or max_agents > 1000:
            errors.append("max_agents 必须在 1-1000 之间")

    max_rounds = data.get('max_rounds')
    if max_rounds is not None:
        if not isinstance(max_rounds, int):
            errors.append("max_rounds 必须是整数")
        elif max_rounds < 1 or max_rounds > 100:
            errors.append("max_rounds 必须在 1-100 之间")

    mode = data.get('mode')
    if mode is not None:
        if mode not in ('standard', 'advanced'):
            errors.append("mode 必须是 standard 或 advanced")

    return errors


def validate_graph_data(data: dict) -> list[str]:
    """校验图数据。

    校验规则：
    - nodes 必须存在且为列表
    - edges 必须存在且为列表

    Returns:
        错误消息列表，空列表表示校验通过。
    """
    errors = []

    nodes = data.get('nodes')
    if nodes is None:
        errors.append("nodes 字段是必需的")
    elif not isinstance(nodes, list):
        errors.append("nodes 必须是列表")

    edges = data.get('edges')
    if edges is None:
        errors.append("edges 字段是必需的")
    elif not isinstance(edges, list):
        errors.append("edges 必须是列表")

    return errors


def validate_request(schema_class: type[BaseModel], raw_data: dict | None):
    """Validate raw JSON data against a Pydantic schema.

    Returns (validated_data_dict, None) on success.
    Returns (None, flask_response_tuple) on validation failure.
    """
    raw = raw_data or {}
    try:
        validated = schema_class(**raw)
        return validated.model_dump(), None
    except ValidationError as e:
        return None, (
            jsonify({"success": False, "error": "VALIDATION_ERROR", "details": e.errors()}),
            400,
        )
