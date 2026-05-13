"""Tests for P1 test-type specialization profiles and runtime injection."""

from __future__ import annotations

from app.services.consumer.domain.test_type_profiles import (
    TEST_TYPE_PROFILES,
    get_test_type_profile,
)
from app.services.consumer.orchestrator import ConsumerSimulationOrchestrator
from app.services.consumer.society.decision_layer import build_decision_signals
from app.services.consumer.society.perception_layer import build_perception_signals


def test_profiles_define_five_distinct_test_types():
    assert set(TEST_TYPE_PROFILES) == {
        "concept_test",
        "copy_test",
        "packaging_test",
        "ab_test",
        "price_test",
    }

    packaging = TEST_TYPE_PROFILES["packaging_test"]
    assert packaging.perception.visual_attention_enabled is True
    assert packaging.perception.shelf_context_simulated is True
    assert round(sum(packaging.perception.element_weights.values()), 2) == 1.0

    price = TEST_TYPE_PROFILES["price_test"]
    assert price.decision.price_sensitivity_model == "gabor_granger"
    assert price.scoring_weights["price_elasticity"] > 0

    ab = TEST_TYPE_PROFILES["ab_test"]
    assert ab.decision.preference_comparison_framework == "paired_comparison"
    assert ab.decision.choice_set_independence_test is True


def test_unknown_profile_falls_back_to_concept_profile():
    profile = get_test_type_profile("unknown_type")
    assert profile.test_type == "concept_test"
    assert "consumer resonance" in profile.focus_line


def test_packaging_perception_layer_builds_visual_attention_heatmap():
    profile = get_test_type_profile("packaging_test")
    signals = build_perception_signals(
        profile=profile,
        visible_nodes=[
            {"type": "PackagingCue", "text": "matte green pack with bold logo and product photo"},
        ],
        brief_summary="Shelf-ready botanical serum packaging",
        agent_traits={"visual_sensitivity": 0.8},
    )

    assert signals["mode"] == "visual_attention"
    assert signals["visual_attention_score"] > 0
    assert set(signals["visual_attention_heatmap"]) >= {"color", "layout", "imagery", "text"}
    assert signals["shelf_context_simulated"] is True


def test_price_decision_layer_builds_gabor_granger_signals():
    profile = get_test_type_profile("price_test")
    signals = build_decision_signals(
        profile=profile,
        visible_nodes=[{"type": "PricePoint", "text": "$12.99 launch price"}],
        agent_traits={"price_sensitivity": 0.82, "income_level": "low"},
        prior_state={"reference_price": 9.99},
    )

    assert signals["mode"] == "gabor_granger"
    assert signals["price_sensitivity_category"] == "high"
    assert 0.0 <= signals["price_acceptance_probability"] <= 1.0
    assert signals["price_acceptance_probability"] < 0.5


def test_ab_decision_layer_builds_paired_comparison_signals():
    profile = get_test_type_profile("ab_test")
    signals = build_decision_signals(
        profile=profile,
        visible_nodes=[
            {"type": "Variant", "text": "A: calming proof-led message"},
            {"type": "Variant", "text": "B: energetic discount-led message"},
        ],
        agent_traits={"evidence_sensitivity": 0.7, "novelty_seeking": 0.3},
        prior_state=None,
    )

    assert signals["mode"] == "paired_comparison"
    assert len(signals["variant_scores"]) == 2
    assert 0.0 <= signals["preference_strength"] <= 1.0
    assert signals["choice_set_independence_checked"] is True


def test_orchestrator_snapshot_injects_profile_and_layer_signals():
    snapshot = ConsumerSimulationOrchestrator().build_round_snapshot(
        round_num=1,
        agent_traits={
            "search_propensity": "high",
            "cognition_level": "high",
            "price_sensitivity": 0.78,
            "income_level": "low",
        },
        brief_summary="Pinned BusinessBrief Summary: price test",
        visible_graph_nodes=[{"type": "PricePoint", "visibility": "Initial", "text": "$14.99"}],
        agent_id="agent_1",
        agent_name="Agent 1",
        task_type="price_test",
        prior_state={"reference_price": 10.0},
    )

    assert snapshot["test_type_profile"]["test_type"] == "price_test"
    assert snapshot["perception_signals"]["mode"] == "generic_perception"
    assert snapshot["decision_signals"]["mode"] == "gabor_granger"
    assert snapshot["decision_signals"]["price_sensitivity_category"] == "high"
    assert "price perception" in snapshot["prompt"]

def test_specialization_docs_describe_product_architecture_and_pricing():
    from pathlib import Path

    repo_root = Path(__file__).resolve().parents[3]
    docs = {
        "docs/product/test_type_differentiation.md": ["Packaging Test", "Price Test", "A/B Test"],
        "docs/architecture/test_type_specialization.md": ["Perception layer", "Decision layer", "TestTypeProfile"],
        "docs/product/pricing_strategy.md": ["differentiated pricing", "Gabor-Granger", "paired comparison"],
    }
    for relative_path, required_terms in docs.items():
        text = (repo_root / relative_path).read_text(encoding="utf-8")
        for term in required_terms:
            assert term in text
