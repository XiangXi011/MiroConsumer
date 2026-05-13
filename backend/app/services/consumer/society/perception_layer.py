"""Perception-layer specializations for consumer test types."""

from __future__ import annotations

from typing import Any, Dict, Iterable, Mapping

from ..domain.test_type_profiles import TestTypeProfile

_COLOR_WORDS = {"black", "blue", "bold", "color", "green", "matte", "pink", "red", "white"}
_LAYOUT_WORDS = {"badge", "bold", "hierarchy", "label", "layout", "logo", "shelf"}
_IMAGERY_WORDS = {"icon", "illustration", "image", "imagery", "photo", "picture", "visual"}
_TEXT_WORDS = {"claim", "copy", "ingredient", "message", "text", "word"}


def build_perception_signals(
    *,
    profile: TestTypeProfile,
    visible_nodes: Iterable[Mapping[str, Any]],
    brief_summary: str,
    agent_traits: Mapping[str, Any],
) -> Dict[str, Any]:
    """Build deterministic perception signals for a test-type profile."""

    node_text = " ".join(str(node.get("text", "")) for node in visible_nodes)
    stimulus_text = f"{brief_summary} {node_text}".lower()

    if profile.perception.visual_attention_enabled:
        return _build_visual_attention(profile, stimulus_text, agent_traits)

    if profile.perception.element_weights:
        element_scores = {
            element: round(weight * _keyword_boost(stimulus_text, {element}), 4)
            for element, weight in profile.perception.element_weights.items()
        }
        return {
            "mode": "copy_element_attention",
            "element_scores": element_scores,
            "dominant_element": _dominant_key(element_scores),
        }

    return {
        "mode": "generic_perception",
        "focus_line": profile.focus_line,
        "salience_score": round(min(1.0, 0.25 + len(stimulus_text) / 400.0), 4),
    }


def _build_visual_attention(
    profile: TestTypeProfile,
    stimulus_text: str,
    agent_traits: Mapping[str, Any],
) -> Dict[str, Any]:
    sensitivity = _as_float(agent_traits.get("visual_sensitivity"), default=0.5)
    heatmap: Dict[str, float] = {}
    keyword_sets = {
        "color": _COLOR_WORDS,
        "layout": _LAYOUT_WORDS,
        "imagery": _IMAGERY_WORDS,
        "text": _TEXT_WORDS,
    }
    for element, weight in profile.perception.element_weights.items():
        boost = _keyword_boost(stimulus_text, keyword_sets.get(element, {element}))
        heatmap[element] = round(min(1.0, weight * boost * (1.0 + sensitivity * 0.2)), 4)

    score = round(sum(heatmap.values()) / max(1, len(heatmap)), 4)
    return {
        "mode": "visual_attention",
        "visual_attention_score": score,
        "visual_attention_heatmap": heatmap,
        "dominant_element": _dominant_key(heatmap),
        "shelf_context_simulated": profile.perception.shelf_context_simulated,
    }


def _keyword_boost(text: str, keywords: set[str]) -> float:
    hits = sum(1 for word in keywords if word in text)
    return 1.0 + min(0.75, hits * 0.25)


def _dominant_key(scores: Mapping[str, float]) -> str:
    if not scores:
        return ""
    return max(scores.items(), key=lambda item: item[1])[0]


def _as_float(value: Any, *, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default