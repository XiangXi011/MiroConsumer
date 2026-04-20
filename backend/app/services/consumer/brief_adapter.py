from typing import Any, Mapping

from .models import (
    ConsumerBusinessBrief,
    GraphVisibility,
    _normalize_graph_visibility,
    _normalize_string_list,
    _normalize_task_type,
)


_MISSING = object()


class ConsumerBriefAdapter:
    @staticmethod
    def from_payload(payload: Mapping[str, Any]) -> ConsumerBusinessBrief:
        if not isinstance(payload, Mapping):
            raise ValueError("payload must be a mapping")

        task_type = _normalize_task_type(payload.get("task_type"))

        product_concept_assets = _normalize_string_list(
            payload.get("product_concept_assets"), "product_concept_assets"
        )
        if not product_concept_assets:
            raise ValueError("Missing required field: product_concept_assets")

        research_goal = payload.get("research_goal")
        if not isinstance(research_goal, str) or not research_goal.strip():
            raise ValueError("Missing required field: research_goal")

        copy_material = _normalize_string_list(payload.get("copy_material"), "copy_material")

        claims_value = payload.get("claims", _MISSING)
        if claims_value is _MISSING or claims_value is None:
            claims = list(copy_material)
        else:
            claims = _normalize_string_list(claims_value, "claims")

        return ConsumerBusinessBrief(
            task_type=task_type,
            product_concept_assets=product_concept_assets,
            copy_material=copy_material,
            claims=claims,
            target_audience=_normalize_string_list(payload.get("target_audience"), "target_audience"),
            usage_scene=_normalize_string_list(payload.get("usage_scene"), "usage_scene"),
            research_goal=research_goal,
            optional_background_materials=_normalize_string_list(
                payload.get("optional_background_materials"), "optional_background_materials"
            ),
            graph_visibility=_normalize_graph_visibility(payload.get("graph_visibility")),
        )
