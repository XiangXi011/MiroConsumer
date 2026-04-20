from typing import Any, Iterable, Mapping

from .models import ConsumerBusinessBrief, GraphVisibility


_SUPPORTED_TASK_TYPES = {"concept_test", "copy_feedback"}
_MISSING = object()


def _normalize_string_list(value: Any) -> list[str]:
    if value is None:
        return []

    if isinstance(value, str):
        items: Iterable[Any] = [value]
    elif isinstance(value, (list, tuple)):
        items = value
    else:
        raise ValueError("Expected a string or list of strings")

    cleaned: list[str] = []
    for item in items:
        if item is None:
            continue
        text = str(item).strip()
        if text:
            cleaned.append(text)
    return cleaned


def _normalize_graph_visibility(value: Any) -> GraphVisibility:
    if value is None:
        return GraphVisibility.Initial
    if isinstance(value, GraphVisibility):
        return value
    if isinstance(value, str):
        try:
            return GraphVisibility(value)
        except ValueError as exc:
            raise ValueError(f"Unsupported graph_visibility: {value}") from exc
    raise ValueError("graph_visibility must be a string or GraphVisibility")


class ConsumerBriefAdapter:
    @staticmethod
    def from_payload(payload: Mapping[str, Any]) -> ConsumerBusinessBrief:
        if not isinstance(payload, Mapping):
            raise ValueError("payload must be a mapping")

        task_type = payload.get("task_type")
        if not isinstance(task_type, str) or not task_type.strip():
            raise ValueError("Missing required field: task_type")
        task_type = task_type.strip()
        if task_type not in _SUPPORTED_TASK_TYPES:
            raise ValueError(f"Unsupported task_type: {task_type}")

        product_concept_assets = _normalize_string_list(payload.get("product_concept_assets"))
        if not product_concept_assets:
            raise ValueError("Missing required field: product_concept_assets")

        research_goal = payload.get("research_goal")
        if not isinstance(research_goal, str) or not research_goal.strip():
            raise ValueError("Missing required field: research_goal")
        research_goal = research_goal.strip()

        copy_material = _normalize_string_list(payload.get("copy_material"))

        claims_value = payload.get("claims", _MISSING)
        if claims_value is _MISSING or claims_value is None:
            claims = list(copy_material)
        else:
            claims = _normalize_string_list(claims_value)

        return ConsumerBusinessBrief(
            task_type=task_type,
            product_concept_assets=product_concept_assets,
            copy_material=copy_material,
            claims=claims,
            target_audience=_normalize_string_list(payload.get("target_audience")),
            usage_scene=_normalize_string_list(payload.get("usage_scene")),
            research_goal=research_goal,
            optional_background_materials=_normalize_string_list(
                payload.get("optional_background_materials")
            ),
            graph_visibility=_normalize_graph_visibility(payload.get("graph_visibility")),
        )
