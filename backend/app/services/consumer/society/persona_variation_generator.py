"""Deterministic persona variation generation for expanded and shadow agents."""

from __future__ import annotations

import hashlib
import random
from typing import Any, Dict, Mapping

from .consumer_roles import ConsumerRole


ROLE_SEQUENCE = list(ConsumerRole)


def _level_to_float(value: Any, default: float = 0.5) -> float:
    text = str(value or "").strip().lower()
    if text == "low":
        return 0.25
    if text == "high":
        return 0.75
    if text == "medium":
        return 0.5
    return default


def _clamp(value: float) -> float:
    return round(max(0.0, min(1.0, value)), 4)


class PersonaVariationGenerator:
    """Generate deterministic individual variation from a parent persona."""

    def __init__(self, seed: int = 0):
        self.seed = int(seed or 0)

    def generate(self, persona: Mapping[str, Any], index: int, layer: str) -> Dict[str, Any]:
        persona_id = str(persona.get("persona_id", "persona")).strip() or "persona"
        rng = self._rng(persona_id, index, layer)
        source_trust = _level_to_float(persona.get("source_trust"), 0.5)
        skepticism = _level_to_float(persona.get("skepticism"), 0.5)
        influence_weight = float(persona.get("influence_weight", 0.5) or 0.5)
        herd = _level_to_float(persona.get("herd_tendency"), 0.5)
        cognition = _level_to_float(persona.get("cognition_level"), 0.5)

        role = ROLE_SEQUENCE[(index + int(rng.random() * len(ROLE_SEQUENCE))) % len(ROLE_SEQUENCE)]
        evidence_sensitivity = _clamp((skepticism + cognition) / 2 + rng.uniform(-0.15, 0.15))
        price_sensitivity = _clamp(0.35 + skepticism * 0.4 + rng.uniform(-0.2, 0.2))
        trust_baseline = _clamp(source_trust + rng.uniform(-0.2, 0.2))
        share_propensity = _clamp((influence_weight + herd) / 2 + rng.uniform(-0.15, 0.15))
        skepticism_score = _clamp(skepticism + rng.uniform(-0.2, 0.2))
        category_familiarity = _clamp(cognition + rng.uniform(-0.25, 0.2))
        risk_memory = _clamp((skepticism_score + evidence_sensitivity) / 2 + rng.uniform(-0.15, 0.15))
        social_influence_weight = _clamp((influence_weight + share_propensity) / 2)

        return {
            "segment": str(persona.get("label", persona_id)).strip() or persona_id,
            "role": role,
            "traits": {
                "attention_drivers": list(persona.get("attention_drivers", [])),
                "risk_sensitivities": list(persona.get("risk_sensitivities", [])),
                "expression_style": str(persona.get("expression_style", "")),
                "category_familiarity": category_familiarity,
                "risk_memory": risk_memory,
                "social_influence_weight": social_influence_weight,
            },
            "channel_affinity": {
                "consumer_society": _clamp(0.5 + rng.uniform(-0.2, 0.2)),
            },
            "evidence_sensitivity": evidence_sensitivity,
            "price_sensitivity": price_sensitivity,
            "trust_baseline": trust_baseline,
            "share_propensity": share_propensity,
            "skepticism": skepticism_score,
            "category_familiarity": category_familiarity,
            "social_influence_weight": social_influence_weight,
        }

    def _rng(self, persona_id: str, index: int, layer: str) -> random.Random:
        material = f"{self.seed}:{persona_id}:{index}:{layer}".encode("utf-8")
        digest = hashlib.sha256(material).hexdigest()
        return random.Random(int(digest[:16], 16))


__all__ = ["PersonaVariationGenerator"]
