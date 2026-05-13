"""Test-type specialization profiles for consumer simulations.

The profiles keep the public task-type labels from the product surface while
making the underlying simulation parameters explicit and testable.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Dict, Optional


@dataclass(frozen=True)
class PerceptionParams:
    """Perception-layer parameters that vary by test type."""

    visual_attention_enabled: bool = False
    element_weights: Dict[str, float] = field(default_factory=dict)
    shelf_context_simulated: bool = False


@dataclass(frozen=True)
class DecisionParams:
    """Decision-layer parameters that vary by test type."""

    price_sensitivity_model: Optional[str] = None
    preference_comparison_framework: Optional[str] = None
    choice_set_independence_test: bool = False


@dataclass(frozen=True)
class TestTypeProfile:
    """Complete differentiation profile for one consumer test type."""

    test_type: str
    focus_line: str
    perception: PerceptionParams
    decision: DecisionParams
    scoring_weights: Dict[str, float] = field(default_factory=dict)
    propagation_params: Dict[str, float] = field(default_factory=dict)


TEST_TYPE_PROFILES: Dict[str, TestTypeProfile] = {
    "concept_test": TestTypeProfile(
        test_type="concept_test",
        focus_line="Focus on consumer resonance, clarity, and potential misinterpretations.",
        perception=PerceptionParams(),
        decision=DecisionParams(),
        scoring_weights={"resonance": 0.45, "clarity": 0.35, "misread_risk": 0.20},
    ),
    "copy_test": TestTypeProfile(
        test_type="copy_test",
        focus_line="Focus on copy effectiveness, headline impact, message proof, and CTA clarity.",
        perception=PerceptionParams(
            element_weights={"headline": 0.40, "body": 0.30, "cta": 0.30},
        ),
        decision=DecisionParams(),
        scoring_weights={"headline_impact": 0.35, "proof_strength": 0.35, "cta_clarity": 0.30},
    ),
    "packaging_test": TestTypeProfile(
        test_type="packaging_test",
        focus_line="Focus on packaging design, shelf appeal, and trust cues.",
        perception=PerceptionParams(
            visual_attention_enabled=True,
            element_weights={"color": 0.35, "layout": 0.25, "imagery": 0.25, "text": 0.15},
            shelf_context_simulated=True,
        ),
        decision=DecisionParams(),
        scoring_weights={"visual_attention": 0.40, "trust_cues": 0.30, "shelf_standout": 0.30},
    ),
    "ab_test": TestTypeProfile(
        test_type="ab_test",
        focus_line="Focus on comparing messaging variants and preference differences.",
        perception=PerceptionParams(),
        decision=DecisionParams(
            preference_comparison_framework="paired_comparison",
            choice_set_independence_test=True,
        ),
        scoring_weights={"preference_strength": 0.45, "consistency": 0.30, "dominance_risk": 0.25},
    ),
    "price_test": TestTypeProfile(
        test_type="price_test",
        focus_line="Focus on price perception, value trade-offs, and purchase intent.",
        perception=PerceptionParams(),
        decision=DecisionParams(price_sensitivity_model="gabor_granger"),
        scoring_weights={"price_elasticity": 0.30, "willingness_to_pay": 0.30, "value_perception": 0.40},
    ),
}


def get_test_type_profile(task_type: Optional[str]) -> TestTypeProfile:
    """Return a specialization profile, falling back to concept_test."""

    if task_type and task_type in TEST_TYPE_PROFILES:
        return TEST_TYPE_PROFILES[task_type]
    return TEST_TYPE_PROFILES["concept_test"]


def profile_to_dict(profile: TestTypeProfile) -> Dict[str, object]:
    """Serialize a profile for snapshot/debug payloads."""

    return asdict(profile)