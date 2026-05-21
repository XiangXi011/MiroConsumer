"""Phase 1 consumer persona pack helpers."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Mapping, TypedDict


class SampleCharacteristics(TypedDict):
    age_range: str
    region: str
    income_level: str


class SourceBasis(TypedDict):
    psychology_theory: str
    data_sources: List[str]
    sample_characteristics: SampleCharacteristics


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
    source_trust: str
    skepticism: str
    # 6.1/6.2: New persona dimensions for richer consumer profiling
    category_involvement: str
    brand_relationship: str
    education_level: str
    source_basis: SourceBasis


class AgentTraitProfile(TypedDict):
    persona_id: str
    label: str
    attention_drivers: List[str]
    risk_sensitivities: List[str]
    expression_style: str
    influence_weight: float
    can_access_deep_graph: bool
    propagation_profile: Dict[str, str]
    source_trust: str
    skepticism: str
    # 6.1/6.2: New trait dimensions forwarded to agent profile
    category_involvement: str
    brand_relationship: str
    source_basis: SourceBasis


_DEFAULT_PERSONA_PATH = Path(__file__).with_name("data") / "default_personas.json"


def load_default_persona_pack() -> List[PersonaRecord]:
    """Load the repo-owned Phase 1 persona pack."""
    payload = json.loads(_DEFAULT_PERSONA_PATH.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError("Persona pack top-level JSON payload must be a list")

    personas = [_normalize_persona(persona) for persona in payload]
    _validate_unique_persona_ids(personas)
    return personas


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
        "source_trust": normalized["source_trust"],
        "skepticism": normalized["skepticism"],
        # 6.1/6.2: Forward new dimensions to agent profile for role derivation
        "category_involvement": normalized.get("category_involvement", "medium"),
        "brand_relationship": normalized.get("brand_relationship", "neutral"),
        "source_basis": normalized["source_basis"],
    }


def can_access_deep_graph(agent_traits: Mapping[str, Any]) -> bool:
    """Determine if an agent can access deep graph information.

    Uses a weighted scoring model instead of a hard binary threshold
    to allow borderline agents occasional deep access.

    Score components:
    - search_propensity: 0.4 weight (high=1.0, medium=0.5, low=0.0)
    - cognition_level: 0.4 weight (high=1.0, medium=0.5, low=0.0)
    - education_level: 0.2 weight (high=1.0, medium=0.5, low=0.0)

    Threshold: >= 0.6 for deep access
    """
    search = str(agent_traits.get("search_propensity", "")).strip().lower()
    cognition = str(agent_traits.get("cognition_level", "")).strip().lower()
    education = str(agent_traits.get("education_level", "medium")).strip().lower()

    level_score = {"high": 1.0, "medium": 0.5, "low": 0.0}

    score = (
        0.4 * level_score.get(search, 0.0)
        + 0.4 * level_score.get(cognition, 0.0)
        + 0.2 * level_score.get(education, 0.0)
    )

    return score >= 0.6


def _normalize_persona(persona: Mapping[str, Any]) -> PersonaRecord:
    if not isinstance(persona, Mapping):
        raise ValueError("Persona record must be a mapping")

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
        "source_trust": _normalize_level(persona.get("source_trust", "medium"), "source_trust"),
        "skepticism": _normalize_level(persona.get("skepticism", "medium"), "skepticism"),
        # 6.1/6.2: Normalize new persona dimensions with sensible defaults
        "category_involvement": _normalize_level(
            persona.get("category_involvement", "medium"), "category_involvement"
        ),
        "brand_relationship": _normalize_relationship(
            persona.get("brand_relationship", "neutral"), "brand_relationship"
        ),
        "education_level": _normalize_level(
            persona.get("education_level", "medium"), "education_level"
        ),
        "source_basis": _normalize_source_basis(
            persona.get("source_basis"), str(persona.get("persona_id", "unknown"))
        ),
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


def _normalize_relationship(value: Any, field_name: str) -> str:
    """Normalize brand relationship values with backward-compatible low/medium/high mapping."""
    text = _normalize_text(value, field_name).lower()
    if text not in {"loyal", "positive", "neutral", "negative", "hostile"}:
        # Map low/medium/high to relationship range for backward compatibility
        if text == "low":
            return "negative"
        if text == "medium":
            return "neutral"
        if text == "high":
            return "positive"
        raise ValueError(
            f"{field_name} must be one of: loyal, positive, neutral, negative, hostile "
            f"(or low/medium/high for compatibility)"
        )
    return text


def _normalize_influence_weight(value: Any) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("influence_weight must be numeric")
    normalized = float(value)
    if not 0.0 <= normalized <= 1.0:
        raise ValueError("influence_weight must be between 0.0 and 1.0 inclusive")
    return normalized


def _normalize_source_basis(value: Any, persona_id: str) -> SourceBasis:
    if value is None:
        return {
            "psychology_theory": "Default consumer segmentation heuristic; custom pack source_basis not supplied.",
            "data_sources": ["custom persona pack upload"],
            "sample_characteristics": {
                "age_range": "not specified",
                "region": "not specified",
                "income_level": "not specified",
            },
        }
    if not isinstance(value, Mapping):
        raise ValueError(f"source_basis for {persona_id} must be a mapping")

    psychology_theory = _normalize_text(
        value.get("psychology_theory"), f"source_basis.psychology_theory for {persona_id}"
    )
    data_sources = _normalize_string_list(
        value.get("data_sources"), f"source_basis.data_sources for {persona_id}"
    )

    sample = value.get("sample_characteristics")
    if not isinstance(sample, Mapping):
        raise ValueError(f"source_basis.sample_characteristics for {persona_id} must be a mapping")

    return {
        "psychology_theory": psychology_theory,
        "data_sources": data_sources,
        "sample_characteristics": {
            "age_range": _normalize_text(
                sample.get("age_range"),
                f"source_basis.sample_characteristics.age_range for {persona_id}",
            ),
            "region": _normalize_text(
                sample.get("region"),
                f"source_basis.sample_characteristics.region for {persona_id}",
            ),
            "income_level": _normalize_text(
                sample.get("income_level"),
                f"source_basis.sample_characteristics.income_level for {persona_id}",
            ),
        },
    }


def _validate_unique_persona_ids(personas: List[PersonaRecord]) -> None:
    seen_persona_ids = set()
    for persona in personas:
        persona_id = persona["persona_id"]
        if persona_id in seen_persona_ids:
            raise ValueError(f"Persona pack contains duplicate persona_id: {persona_id}")
        seen_persona_ids.add(persona_id)


__all__ = [
    "AgentTraitProfile",
    "PersonaRecord",
    "SampleCharacteristics",
    "SourceBasis",
    "can_access_deep_graph",
    "load_default_persona_pack",
    "map_persona_to_agent_traits",
]
