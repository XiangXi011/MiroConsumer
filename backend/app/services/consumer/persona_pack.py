"""Phase 1 consumer persona pack helpers."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Mapping, TypedDict


class PersonaRecord(TypedDict):
    persona_id: str
    label: str
    attention_drivers: List[str]
    risk_sensitivities: List[str]
    expression_style: str
    search_propensity: str
    cognition_level: str
    herd_tendency: str
    influence_weight: float


class AgentTraitProfile(TypedDict):
    persona_id: str
    label: str
    attention_drivers: List[str]
    risk_sensitivities: List[str]
    expression_style: str
    influence_weight: float
    can_access_deep_graph: bool
    propagation_profile: Dict[str, str]


_DEFAULT_PERSONA_PATH = Path(__file__).with_name("data") / "default_personas.json"


def load_default_persona_pack() -> List[PersonaRecord]:
    """Load the repo-owned Phase 1 persona pack."""
    payload = json.loads(_DEFAULT_PERSONA_PATH.read_text(encoding="utf-8"))
    return [_normalize_persona(persona) for persona in payload]


def map_persona_to_agent_traits(persona: Mapping[str, Any]) -> AgentTraitProfile:
    """Expose only the propagation-relevant traits needed by simulation prep."""
    normalized = _normalize_persona(persona)
    propagation_profile = {
        "search_propensity": normalized["search_propensity"],
        "cognition_level": normalized["cognition_level"],
        "herd_tendency": normalized["herd_tendency"],
    }
    return {
        "persona_id": normalized["persona_id"],
        "label": normalized["label"],
        "attention_drivers": list(normalized["attention_drivers"]),
        "risk_sensitivities": list(normalized["risk_sensitivities"]),
        "expression_style": normalized["expression_style"],
        "influence_weight": normalized["influence_weight"],
        "can_access_deep_graph": can_access_deep_graph(propagation_profile),
        "propagation_profile": propagation_profile,
    }


def can_access_deep_graph(agent_traits: Mapping[str, Any]) -> bool:
    return (
        str(agent_traits.get("search_propensity", "")).strip().lower() == "high"
        and str(agent_traits.get("cognition_level", "")).strip().lower() == "high"
    )


def _normalize_persona(persona: Mapping[str, Any]) -> PersonaRecord:
    required_fields = (
        "persona_id",
        "label",
        "attention_drivers",
        "risk_sensitivities",
        "expression_style",
        "search_propensity",
        "cognition_level",
        "herd_tendency",
        "influence_weight",
    )
    missing = [field for field in required_fields if field not in persona]
    if missing:
        raise ValueError(f"Persona record missing required fields: {', '.join(missing)}")

    return {
        "persona_id": _normalize_text(persona["persona_id"], "persona_id"),
        "label": _normalize_text(persona["label"], "label"),
        "attention_drivers": _normalize_string_list(
            persona["attention_drivers"], "attention_drivers"
        ),
        "risk_sensitivities": _normalize_string_list(
            persona["risk_sensitivities"], "risk_sensitivities"
        ),
        "expression_style": _normalize_text(persona["expression_style"], "expression_style"),
        "search_propensity": _normalize_level(persona["search_propensity"], "search_propensity"),
        "cognition_level": _normalize_level(persona["cognition_level"], "cognition_level"),
        "herd_tendency": _normalize_level(persona["herd_tendency"], "herd_tendency"),
        "influence_weight": _normalize_influence_weight(persona["influence_weight"]),
    }


def _normalize_text(value: Any, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be a non-empty string")
    return value.strip()


def _normalize_string_list(value: Any, field_name: str) -> List[str]:
    if not isinstance(value, list):
        raise ValueError(f"{field_name} must be a list of strings")

    cleaned = []
    for item in value:
        if not isinstance(item, str) or not item.strip():
            raise ValueError(f"{field_name} must contain only non-empty strings")
        cleaned.append(item.strip())
    return cleaned


def _normalize_level(value: Any, field_name: str) -> str:
    text = _normalize_text(value, field_name).lower()
    if text not in {"low", "medium", "high"}:
        raise ValueError(f"{field_name} must be one of: low, medium, high")
    return text


def _normalize_influence_weight(value: Any) -> float:
    if not isinstance(value, (int, float)):
        raise ValueError("influence_weight must be numeric")
    return float(value)


__all__ = [
    "AgentTraitProfile",
    "PersonaRecord",
    "can_access_deep_graph",
    "load_default_persona_pack",
    "map_persona_to_agent_traits",
]
