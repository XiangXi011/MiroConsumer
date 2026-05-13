"""Decision-layer specializations for consumer test types."""

from __future__ import annotations

import re
from typing import Any, Dict, Iterable, Mapping, Optional

from ..domain.test_type_profiles import TestTypeProfile

_PRICE_RE = re.compile(r"(?:[$]|USD|RMB|CNY)?\s*(\d+(?:\.\d+)?)")


def build_decision_signals(
    *,
    profile: TestTypeProfile,
    visible_nodes: Iterable[Mapping[str, Any]],
    agent_traits: Mapping[str, Any],
    prior_state: Optional[Mapping[str, Any]],
) -> Dict[str, Any]:
    """Build deterministic decision signals for a test-type profile."""

    nodes = list(visible_nodes)
    if profile.decision.price_sensitivity_model == "gabor_granger":
        return _build_price_signals(nodes, agent_traits, prior_state or {})

    if profile.decision.preference_comparison_framework == "paired_comparison":
        return _build_paired_comparison_signals(nodes, agent_traits, profile)

    return {
        "mode": "generic_decision",
        "choice_probability": {"accept": 0.5, "reject": 0.5},
        "decision_basis": profile.focus_line,
    }


def _build_price_signals(
    visible_nodes: list[Mapping[str, Any]],
    agent_traits: Mapping[str, Any],
    prior_state: Mapping[str, Any],
) -> Dict[str, Any]:
    observed_price = _first_price(visible_nodes)
    reference_price = _as_float(
        prior_state.get("reference_price") or agent_traits.get("reference_price"),
        default=observed_price or 1.0,
    )
    if observed_price is None:
        observed_price = reference_price

    category = _price_sensitivity_category(agent_traits)
    factor = {"high": 1.60, "medium": 1.00, "low": 0.55}[category]
    price_gap = 0.0 if reference_price <= 0 else (observed_price - reference_price) / reference_price
    probability = _clamp(0.68 - max(0.0, price_gap) * factor + max(0.0, -price_gap) * 0.35)
    elasticity = round(-factor * max(0.0, price_gap), 4)

    return {
        "mode": "gabor_granger",
        "price_sensitivity_category": category,
        "observed_price": round(observed_price, 4),
        "reference_price": round(reference_price, 4),
        "price_gap_ratio": round(price_gap, 4),
        "price_acceptance_probability": round(probability, 4),
        "price_elasticity_signal": elasticity,
    }


def _build_paired_comparison_signals(
    visible_nodes: list[Mapping[str, Any]],
    agent_traits: Mapping[str, Any],
    profile: TestTypeProfile,
) -> Dict[str, Any]:
    variants = [str(node.get("text") or node.get("name") or "").strip() for node in visible_nodes]
    variants = [variant for variant in variants if variant]
    if not variants:
        variants = ["A", "B"]

    evidence = _as_float(agent_traits.get("evidence_sensitivity"), default=0.5)
    novelty = _as_float(agent_traits.get("novelty_seeking"), default=0.5)
    variant_scores: Dict[str, float] = {}
    for index, variant in enumerate(variants):
        text = variant.lower()
        proof_boost = 0.18 * evidence if any(token in text for token in ("proof", "trust", "evidence")) else 0.0
        novelty_boost = 0.12 * novelty if any(token in text for token in ("new", "energetic", "discount")) else 0.0
        position_penalty = index * 0.03
        variant_scores[variant] = round(_clamp(0.5 + proof_boost + novelty_boost - position_penalty), 4)

    ordered = sorted(variant_scores.items(), key=lambda item: item[1], reverse=True)
    top = ordered[0][1]
    runner_up = ordered[1][1] if len(ordered) > 1 else 0.5
    return {
        "mode": "paired_comparison",
        "variant_scores": variant_scores,
        "preference_ranking": [name for name, _ in ordered],
        "preference_strength": round(abs(top - runner_up), 4),
        "choice_set_independence_checked": profile.decision.choice_set_independence_test,
    }


def _first_price(visible_nodes: list[Mapping[str, Any]]) -> Optional[float]:
    for node in visible_nodes:
        text = str(node.get("text", ""))
        if "price" not in text.lower() and str(node.get("type", "")).lower() != "pricepoint":
            continue
        match = _PRICE_RE.search(text)
        if match:
            return float(match.group(1))
    return None


def _price_sensitivity_category(agent_traits: Mapping[str, Any]) -> str:
    sensitivity = _as_float(
        agent_traits.get("price_sensitivity") or agent_traits.get("price_consciousness"),
        default=0.5,
    )
    income = str(agent_traits.get("income_level", "medium")).lower()
    if sensitivity >= 0.70 or income == "low":
        return "high"
    if sensitivity >= 0.40:
        return "medium"
    return "low"


def _as_float(value: Any, *, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, value))