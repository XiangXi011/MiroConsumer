"""Spec contracts for P3 consumer modeling and confidence extensions."""

from __future__ import annotations

import math
from pathlib import Path

import pytest

from app.contracts.consumer_contracts import BusinessBriefRequest
from app.services.consumer.brief_adapter import ConsumerBriefAdapter
from app.services.consumer.confidence_scoring import (
    CONFIDENCE_WEIGHTS,
    compute_weighted_confidence_score,
)
from app.services.consumer.evidence_validator import EvidenceValidationResult
from app.services.consumer.confidence_scoring import compute_finding_confidence
from app.services.consumer.society.profile_generator import (
    PROFILE_REQUIRED_FIELDS,
    ConsumerProfileGenerator,
)


ROOT = Path(__file__).resolve().parents[3]


def test_p3_005_business_brief_retry_budgets_are_split_and_documented():
    schema = BusinessBriefRequest.model_json_schema()
    props = schema["properties"]

    for field in ["llm_retry_budget", "task_retry_budget", "simulation_retry_budget"]:
        assert field in props
        assert props[field]["description"]

    assert props["llm_retry_budget"]["default"] == 2
    assert props["task_retry_budget"]["default"] == 1
    assert props["simulation_retry_budget"]["default"] == 0


def test_p3_005_legacy_retry_budget_maps_to_llm_retry_budget():
    brief = ConsumerBriefAdapter.from_payload(
        {
            "task_type": "concept_test",
            "product_concept_assets": ["protein pouch"],
            "copy_material": ["14g protein"],
            "target_audience": ["working moms"],
            "usage_scene": ["commute"],
            "research_goal": "Find objections",
            "retry_budget": 4,
        }
    )

    assert brief.llm_retry_budget == 4
    assert brief.task_retry_budget == 1
    assert brief.simulation_retry_budget == 0
    assert brief.to_summary()["llm_retry_budget"] == 4


def test_p3_006_generated_profiles_have_all_26_required_fields():
    generator = ConsumerProfileGenerator(seed=7)
    profiles = generator.generate_profiles(
        brief={
            "task_type": "price_test",
            "category": "food_beverage",
            "research_goal": "price elasticity",
            "price_context": {"price_band": "premium"},
        },
        count=3,
    )

    assert len(PROFILE_REQUIRED_FIELDS) == 26
    for profile in profiles:
        missing = [field for field in PROFILE_REQUIRED_FIELDS if not profile.get(field)]
        assert missing == []


def test_p3_007_influencer_graph_topology_exposes_power_law_fanout():
    from app.services.consumer.social.network_topology import (
        InfluencerGraphConfig,
        build_influencer_graph,
    )

    node_ids = [f"n{i:03d}" for i in range(100)]
    graph = build_influencer_graph(
        node_ids,
        config=InfluencerGraphConfig(influencer_ratio=0.05, fanout=40, seed=11),
    )

    influencers = [node for node, data in graph["nodes"].items() if data["role"] == "influencer"]
    follower_degrees = [
        graph["degree_distribution"][node]
        for node, data in graph["nodes"].items()
        if data["role"] == "follower"
    ]
    influencer_degrees = [graph["degree_distribution"][node] for node in influencers]

    assert len(influencers) == 5
    assert min(influencer_degrees) >= 40
    assert max(influencer_degrees) >= 5 * max(follower_degrees)
    assert graph["topology_type"] == "influencer_graph"


def test_p3_009_nlg_expression_adapter_prefers_llm_and_marks_source():
    from app.services.consumer.cognition.expression import NLGExpressionAdapter

    class FakeClient:
        def __init__(self):
            self.calls = []

        def chat_json(self, **kwargs):
            self.calls.append(kwargs)
            return {"voc": "这个配方听起来更像真实早餐场景，我会先买一袋试试。"}

    client = FakeClient()
    adapter = NLGExpressionAdapter(llm_client=client)
    result = adapter.generate_voc(
        agent_profile={"segment": "urban moms", "price_sensitivity": 0.4},
        claim="14g protein",
        platform="xiaohongshu",
    )

    assert result["generation_source"] == "llm"
    assert result["text"].startswith("这个配方")
    assert client.calls


def test_p3_009_reasoning_engine_declares_template_fallback_threshold():
    from app.services.consumer.society.reasoning_engine import LayeredSocietyReasoningEngine

    assert LayeredSocietyReasoningEngine().template_fallback_coverage_target <= 0.15


def test_p3_010_confidence_formula_uses_six_weights_and_reasons():
    assert round(sum(CONFIDENCE_WEIGHTS.values()), 8) == 1.0
    assert set(CONFIDENCE_WEIGHTS) == {
        "source_quality",
        "evidence_sufficiency",
        "signal_consistency",
        "replay_alignment",
        "external_validity",
        "expert_consensus",
    }

    score = compute_weighted_confidence_score(
        source_quality=1.0,
        evidence_sufficiency=0.8,
        signal_consistency=0.5,
        replay_alignment=0.5,
        external_validity=0.7,
        expert_consensus=0.6,
    )
    assert score == 0.765

    fc = compute_finding_confidence(
        {"finding_id": "f1", "finding_type": "risk_signal"},
        EvidenceValidationResult(
            finding_id="f1",
            validation_status="supported",
            evidence_sufficiency=0.8,
            aligned_snippet_ids=["s1"],
            missing_support_reasons=[],
            validator_notes="ok",
        ),
        source={"source_confidence": 1.0, "trust_tier": 1, "lane": "lane_a"},
        external_validity_score=0.7,
        expert_consensus_score=0.6,
    )

    assert "external_validity:0.7" in fc.confidence_reasons
    assert "expert_consensus:0.6" in fc.confidence_reasons
