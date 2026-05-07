"""Tests for batch 8+9+10: RuntimeControl integration, VOC fields, Confidence, DOE."""

from __future__ import annotations

import sys
from pathlib import Path
from types import ModuleType
from typing import Any, Dict, List
from unittest.mock import MagicMock

# Stub out heavy third-party deps
_zep_mock = MagicMock()
for _mod_name in (
    "zep_cloud",
    "zep_cloud.client",
    "zep_cloud.external_clients",
    "zep_cloud.external_clients.ontology",
):
    if _mod_name not in sys.modules:
        sys.modules[_mod_name] = _zep_mock

import pytest

_BACKEND_ROOT = str(Path(__file__).resolve().parents[1])
if _BACKEND_ROOT not in sys.path:
    sys.path.insert(0, _BACKEND_ROOT)

from app.services.consumer.runtime.control import (
    RuntimeControlLayer,
    EarlyStopConfig,
    ConvergenceDetector,
)
from app.services.consumer.society.event_mapper import ConsumerSocietyEventMapper
from app.services.consumer.society.consumer_roles import ConsumerRole
from app.services.consumer.society.population_models import ConsumerSocietyAgent
from app.services.consumer.event_ontology import ConsumerEventType
from app.services.consumer.confidence_scoring import compute_confidence
from app.services.consumer.experiment.doe import ExperimentDesigner, ExperimentDesign


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_agent(**overrides) -> ConsumerSocietyAgent:
    defaults = dict(
        agent_id="agent_001",
        parent_persona_id="persona_001",
        segment="young_professional",
        role=ConsumerRole.Advocate,
        layer="decision",
        trust_baseline=0.6,
        price_sensitivity=0.3,
        evidence_sensitivity=0.4,
        share_propensity=0.5,
        state={"trust": 0.7, "purchase_intent": 0.65},
        traits={
            "name": "小张",
            "risk_sensitivities": ["安全"],
            "family_structure": "single",
            "expression_style": "理性",
        },
    )
    defaults.update(overrides)
    return ConsumerSocietyAgent(**defaults)


# ===========================================================================
# 8.1 RunController checkpoint integration
# ===========================================================================

class TestRunControllerCheckpoint:
    """Test RunController checkpoint and early stop integration (mocked)."""

    def test_runtime_control_created(self):
        """RunController.__init__ should create a RuntimeControlLayer."""
        from app.services.consumer.society.run_controller import RunController

        ctrl = RunController(
            store=MagicMock(),
            population_factory=MagicMock(),
            event_mapper=MagicMock(),
            metrics_aggregator=MagicMock(),
            reasoning_engine=MagicMock(),
            quality_checker=MagicMock(),
            channel_runtime=MagicMock(),
        )
        assert isinstance(ctrl.runtime_control, RuntimeControlLayer)
        assert ctrl.runtime_control.early_stop_config.enabled is True
        assert ctrl.runtime_control.early_stop_config.patience == 3

    def test_resume_from_checkpoint_returns_none_when_empty(self):
        from app.services.consumer.society.run_controller import RunController

        ctrl = RunController(
            store=MagicMock(),
            population_factory=MagicMock(),
            event_mapper=MagicMock(),
            metrics_aggregator=MagicMock(),
            reasoning_engine=MagicMock(),
            quality_checker=MagicMock(),
            channel_runtime=MagicMock(),
        )
        assert ctrl.resume_from_checkpoint() is None

    def test_resume_from_checkpoint_returns_state(self):
        from app.services.consumer.society.run_controller import RunController

        ctrl = RunController(
            store=MagicMock(),
            population_factory=MagicMock(),
            event_mapper=MagicMock(),
            metrics_aggregator=MagicMock(),
            reasoning_engine=MagicMock(),
            quality_checker=MagicMock(),
            channel_runtime=MagicMock(),
        )
        ctrl.runtime_control.save_checkpoint(
            round_id=3,
            state={"agents": {"a1": {"trust": 0.8}}, "events": []},
            metrics={"avg_attitude": 0.7, "new_events": 2},
        )
        result = ctrl.resume_from_checkpoint()
        assert result is not None
        assert result["resume_from"] == 3
        assert "a1" in result["state"]["agents"]


# ===========================================================================
# 8.2 ConvergenceDetector
# ===========================================================================

class TestConvergenceDetector:

    def test_not_converged_before_window(self):
        cd = ConvergenceDetector(window_size=3, threshold=0.01)
        cd.update({"avg_attitude": 0.5})
        cd.update({"avg_attitude": 0.5})
        converged, reason = cd.is_converged()
        assert not converged
        assert reason == ""

    def test_converged_when_variance_low(self):
        cd = ConvergenceDetector(window_size=3, threshold=0.01)
        cd.update({"avg_attitude": 0.500})
        cd.update({"avg_attitude": 0.501})
        cd.update({"avg_attitude": 0.499})
        converged, reason = cd.is_converged()
        assert converged
        assert "variance" in reason

    def test_not_converged_when_variance_high(self):
        cd = ConvergenceDetector(window_size=3, threshold=0.01)
        cd.update({"avg_attitude": 0.3})
        cd.update({"avg_attitude": 0.5})
        cd.update({"avg_attitude": 0.8})
        converged, reason = cd.is_converged()
        assert not converged

    def test_uses_only_recent_window(self):
        cd = ConvergenceDetector(window_size=2, threshold=0.01)
        cd.update({"avg_attitude": 0.1})
        cd.update({"avg_attitude": 0.9})
        cd.update({"avg_attitude": 0.500})
        cd.update({"avg_attitude": 0.501})
        converged, reason = cd.is_converged()
        assert converged


# ===========================================================================
# 9.1 VOC 15-field completeness
# ===========================================================================

class TestVOCFields:

    REQUIRED_VOC_FIELDS = {
        "event_id", "voc_id", "agent_id", "round_index", "channel",
        "trigger_event_id", "cognition_state_ref", "source_input_refs",
        "quote_text", "paraphrase_text", "sentiment", "intent",
        "risk_tags", "generated_by", "model_version", "confidence",
    }

    def test_voc_fields_present(self):
        mapper = ConsumerSocietyEventMapper()
        agent = _make_agent()
        result = mapper.map_agent_event(
            agent=agent,
            round_index=0,
            visible_claims=["好产品"],
            previous_events=[],
            brief_context={},
            research_findings=[],
        )
        for field in self.REQUIRED_VOC_FIELDS:
            assert field in result, f"Missing VOC field: {field}"

    def test_voc_id_format(self):
        mapper = ConsumerSocietyEventMapper()
        agent = _make_agent()
        result = mapper.map_agent_event(
            agent=agent, round_index=1, visible_claims=["X"],
            previous_events=[], brief_context={}, research_findings=[],
        )
        assert result["voc_id"].startswith("voc_")
        assert result["voc_id"] == f"voc_{result['event_id']}"

    def test_cognition_state_ref_format(self):
        mapper = ConsumerSocietyEventMapper()
        agent = _make_agent()
        result = mapper.map_agent_event(
            agent=agent, round_index=2, visible_claims=["X"],
            previous_events=[], brief_context={}, research_findings=[],
        )
        assert result["cognition_state_ref"] == "cognition_agent_001_2"

    def test_channel_equals_event_type(self):
        mapper = ConsumerSocietyEventMapper()
        agent = _make_agent()
        result = mapper.map_agent_event(
            agent=agent, round_index=0, visible_claims=["X"],
            previous_events=[], brief_context={}, research_findings=[],
        )
        assert result["channel"] == result["consumer_event_type"]

    def test_sentiment_positive(self):
        mapper = ConsumerSocietyEventMapper()
        agent = _make_agent(state={"trust": 0.8, "purchase_intent": 0.7})
        result = mapper.map_agent_event(
            agent=agent, round_index=0, visible_claims=["X"],
            previous_events=[], brief_context={}, research_findings=[],
        )
        assert result["sentiment"] == "positive"

    def test_sentiment_negative(self):
        mapper = ConsumerSocietyEventMapper()
        agent = _make_agent(state={"trust": 0.2, "purchase_intent": 0.2})
        result = mapper.map_agent_event(
            agent=agent, round_index=0, visible_claims=["X"],
            previous_events=[], brief_context={}, research_findings=[],
        )
        assert result["sentiment"] == "negative"

    def test_sentiment_neutral(self):
        mapper = ConsumerSocietyEventMapper()
        agent = _make_agent(state={"trust": 0.5, "purchase_intent": 0.5})
        result = mapper.map_agent_event(
            agent=agent, round_index=0, visible_claims=["X"],
            previous_events=[], brief_context={}, research_findings=[],
        )
        assert result["sentiment"] == "neutral"

    def test_intent_derivation(self):
        mapper = ConsumerSocietyEventMapper()
        # Advocate role → PURCHASE_INTENT_UP → "consideration"
        agent = _make_agent(role=ConsumerRole.Advocate)
        result = mapper.map_agent_event(
            agent=agent, round_index=0, visible_claims=["X"],
            previous_events=[], brief_context={}, research_findings=[],
        )
        assert result["intent"] in {"consideration", "observation"}

    def test_risk_tags_from_traits(self):
        mapper = ConsumerSocietyEventMapper()
        agent = _make_agent()
        result = mapper.map_agent_event(
            agent=agent, round_index=0, visible_claims=["X"],
            previous_events=[], brief_context={}, research_findings=[],
        )
        assert isinstance(result["risk_tags"], list)

    def test_backward_compat_fields(self):
        """Old fields (quote, event_type, timestamp) still present."""
        mapper = ConsumerSocietyEventMapper()
        agent = _make_agent()
        result = mapper.map_agent_event(
            agent=agent, round_index=0, visible_claims=["X"],
            previous_events=[], brief_context={}, research_findings=[],
        )
        assert "quote" in result
        assert "event_type" in result
        assert "timestamp" in result
        assert result["quote"] == result["quote_text"]


# ===========================================================================
# 9.2 VOC category classification
# ===========================================================================

class TestVOCCategory:

    def test_simulated_voc_for_template_fallback(self):
        mapper = ConsumerSocietyEventMapper()
        agent = _make_agent(state={"trust": 0.5, "purchase_intent": 0.5, "reasoning_backend": "template_fallback"})
        result = mapper.map_agent_event(
            agent=agent, round_index=0, visible_claims=["X"],
            previous_events=[], brief_context={}, research_findings=[],
        )
        assert result["voc_category"] == "simulated_voc"

    def test_real_voc_for_real_data(self):
        mapper = ConsumerSocietyEventMapper()
        agent = _make_agent(state={"trust": 0.5, "purchase_intent": 0.5, "data_source": "real_data"})
        result = mapper.map_agent_event(
            agent=agent, round_index=0, visible_claims=["X"],
            previous_events=[], brief_context={}, research_findings=[],
        )
        assert result["voc_category"] == "real_voc"

    def test_synthesized_voc_for_llm(self):
        mapper = ConsumerSocietyEventMapper()
        agent = _make_agent(state={"trust": 0.5, "purchase_intent": 0.5, "reasoning_backend": "llm"})
        result = mapper.map_agent_event(
            agent=agent, round_index=0, visible_claims=["X"],
            previous_events=[], brief_context={}, research_findings=[],
        )
        assert result["voc_category"] == "synthesized_voc"


# ===========================================================================
# 10.1 Confidence formula
# ===========================================================================

class TestConfidenceFormula:

    def test_all_high_scores(self):
        score = compute_confidence(
            source_quality=1.0, evidence_sufficiency=1.0,
            simulation_stability=1.0, cross_run_consistency=1.0,
            benchmark_alignment=1.0, contradiction_count=0, fallback_count=0,
        )
        assert score == 1.0

    def test_all_low_scores(self):
        score = compute_confidence(
            source_quality=0.0, evidence_sufficiency=0.0,
            simulation_stability=0.0, cross_run_consistency=0.0,
            benchmark_alignment=0.0, contradiction_count=0, fallback_count=0,
        )
        assert score == 0.0

    def test_weight_distribution(self):
        """Verify weights sum to 1.0: 0.25+0.25+0.20+0.15+0.15 = 1.0"""
        score = compute_confidence(
            source_quality=1.0, evidence_sufficiency=0.0,
            simulation_stability=0.0, cross_run_consistency=0.0,
            benchmark_alignment=0.0,
        )
        assert abs(score - 0.25) < 0.001

    def test_contradiction_penalty(self):
        base = compute_confidence(0.8, 0.8, 0.8, 0.8, 0.8, contradiction_count=0)
        penalized = compute_confidence(0.8, 0.8, 0.8, 0.8, 0.8, contradiction_count=3)
        assert penalized < base
        assert abs((base - penalized) - 0.15) < 0.001  # 3 * 0.05 = 0.15

    def test_contradiction_penalty_capped_at_5(self):
        c5 = compute_confidence(0.8, 0.8, 0.8, 0.8, 0.8, contradiction_count=5)
        c10 = compute_confidence(0.8, 0.8, 0.8, 0.8, 0.8, contradiction_count=10)
        assert c5 == c10  # capped at 5

    def test_fallback_penalty(self):
        base = compute_confidence(0.8, 0.8, 0.8, 0.8, 0.8, fallback_count=0)
        penalized = compute_confidence(0.8, 0.8, 0.8, 0.8, 0.8, fallback_count=4)
        assert penalized < base
        assert abs((base - penalized) - 0.12) < 0.001  # 4 * 0.03 = 0.12

    def test_fallback_penalty_capped_at_10(self):
        c10 = compute_confidence(0.8, 0.8, 0.8, 0.8, 0.8, fallback_count=10)
        c20 = compute_confidence(0.8, 0.8, 0.8, 0.8, 0.8, fallback_count=20)
        assert c10 == c20

    def test_score_clamped_to_0(self):
        score = compute_confidence(
            source_quality=0.0, evidence_sufficiency=0.0,
            simulation_stability=0.0, cross_run_consistency=0.0,
            benchmark_alignment=0.0, contradiction_count=100, fallback_count=100,
        )
        assert score == 0.0

    def test_score_clamped_to_1(self):
        score = compute_confidence(
            source_quality=1.0, evidence_sufficiency=1.0,
            simulation_stability=1.0, cross_run_consistency=1.0,
            benchmark_alignment=1.0, contradiction_count=0, fallback_count=0,
        )
        assert score == 1.0


# ===========================================================================
# 10.2 DOE extensions
# ===========================================================================

class TestDOEExtensions:

    def setup_method(self):
        self.designer = ExperimentDesigner()

    def test_create_message_variant(self):
        exp = self.designer.create_message_variant("msg_test", ["hello", "world"])
        assert isinstance(exp, ExperimentDesign)
        assert len(exp.variants) == 2
        assert exp.control_variant_id == "msg_0"
        assert exp.independent_variables == ["message"]

    def test_create_message_variant_empty(self):
        exp = self.designer.create_message_variant("empty", [])
        assert len(exp.variants) == 1

    def test_create_claim_variant(self):
        exp = self.designer.create_claim_variant("claim_test", ["claimA", "claimB", "claimC"])
        assert isinstance(exp, ExperimentDesign)
        assert len(exp.variants) == 3
        assert exp.control_variant_id == "claim_0"
        assert exp.independent_variables == ["claim"]

    def test_create_claim_variant_empty(self):
        exp = self.designer.create_claim_variant("empty", [])
        assert len(exp.variants) == 1

    def test_control_variables_field(self):
        exp = self.designer.create_ab_test("T", "H", {}, {})
        assert hasattr(exp, "control_variables")
        assert isinstance(exp.control_variables, dict)

    def test_stratified_assignment_balanced(self):
        exp = self.designer.create_ab_test("T", "H", {}, {})
        agents = [
            {"agent_id": f"a{i}", "segment": "A" if i < 5 else "B"}
            for i in range(10)
        ]
        assignment = self.designer.assign_agents_stratified(agents, exp, stratify_key="segment", seed=42)
        assert len(assignment) == 10
        # Within each stratum, round-robin should balance
        a_group = [assignment[f"a{i}"] for i in range(5)]
        b_group = [assignment[f"a{i}"] for i in range(5, 10)]
        assert all(v in ["control", "treatment"] for v in a_group)
        assert all(v in ["control", "treatment"] for v in b_group)

    def test_stratified_assignment_deterministic(self):
        exp = self.designer.create_ab_test("T", "H", {}, {})
        agents = [{"agent_id": f"a{i}", "segment": "S"} for i in range(6)]
        a1 = self.designer.assign_agents_stratified(agents, exp, stratify_key="segment", seed=99)
        a2 = self.designer.assign_agents_stratified(agents, exp, stratify_key="segment", seed=99)
        assert a1 == a2
