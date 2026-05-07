"""Tests for Batch C: Decision layer + Evidence + DOE completion."""

import pytest
import sys
import os

# Ensure the backend package is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.services.consumer.cognition.decision import DEFAULT_ACTIONS, DecisionEngine
from app.services.consumer.cognition.schemas import DecisionOutput, CognitionResult
from app.services.consumer.evidence_validator import (
    validate_finding,
    EvidenceValidationResult,
    _detect_contradictions,
    _identify_gaps,
)
from app.services.consumer.experiment.doe import ExperimentDesigner
from app.services.consumer.experiment.modes import validate_experiment_config, EXPERIMENT_MODES


# ─── C1: DEFAULT_ACTIONS has 9 entries ───

class TestDefaultActions:
    def test_default_actions_count(self):
        assert len(DEFAULT_ACTIONS) == 9

    def test_default_actions_ids(self):
        ids = [a["id"] for a in DEFAULT_ACTIONS]
        expected = ["accept", "reject", "hesitate", "share", "challenge",
                    "ignore", "distort", "ask_more", "seek_evidence"]
        assert ids == expected

    def test_default_actions_have_base_score(self):
        for action in DEFAULT_ACTIONS:
            assert "base_score" in action
            assert 0 <= action["base_score"] <= 1

    def test_default_actions_have_label(self):
        for action in DEFAULT_ACTIONS:
            assert "label" in action
            assert len(action["label"]) > 0


# ─── C2: evidence_refs field ───

class TestEvidenceRefs:
    def test_decision_output_has_evidence_refs(self):
        d = DecisionOutput(choice="accept", reason_codes=["high_trust"])
        assert hasattr(d, "evidence_refs")
        assert isinstance(d.evidence_refs, list)

    def test_decision_output_evidence_refs_default_empty(self):
        d = DecisionOutput(choice="accept")
        assert d.evidence_refs == []

    def test_make_decision_generates_evidence_refs(self):
        """make_decision should produce evidence_refs in its output dict."""
        from app.services.consumer.society.population_models import ConsumerSocietyAgent

        agent = ConsumerSocietyAgent(
            agent_id="test_agent",
            segment="mainstream",
            role="consumer",
        )
        engine = DecisionEngine()
        perception_state = {
            "trust": 0.7,
            "awareness": 0.5,
            "trust_signals": ["signal_a", "signal_b", "signal_c", "signal_d"],
            "perceived_risks": ["risk_1", "risk_2"],
            "social": {},
            "media": {},
        }
        result = engine.make_decision(agent, perception_state)
        assert "evidence_refs" in result
        assert len(result["evidence_refs"]) > 0
        # Should have ts_0, ts_1, ts_2 (max 3) and pr_0, pr_1 (max 2)
        assert "ts_0" in result["evidence_refs"]
        assert "ts_1" in result["evidence_refs"]
        assert "ts_2" in result["evidence_refs"]
        assert "pr_0" in result["evidence_refs"]
        assert "pr_1" in result["evidence_refs"]

    def test_make_decision_evidence_refs_empty_when_no_signals(self):
        from app.services.consumer.society.population_models import ConsumerSocietyAgent

        agent = ConsumerSocietyAgent(
            agent_id="test_agent_2",
            segment="mainstream",
            role="consumer",
        )
        engine = DecisionEngine()
        perception_state = {"trust": 0.5, "awareness": 0.5, "social": {}, "media": {}}
        result = engine.make_decision(agent, perception_state)
        assert result["evidence_refs"] == []


# ─── C1 extended: reason_codes include new action types ───

class TestReasonCodes:
    def test_reason_codes_include_new_actions(self):
        """Ensure the scoring logic handles new action IDs like hesitate, challenge."""
        from app.services.consumer.society.population_models import ConsumerSocietyAgent

        agent = ConsumerSocietyAgent(
            agent_id="test_agent_3",
            segment="skeptic",
            role="consumer",
        )
        engine = DecisionEngine()
        perception_state = {
            "trust": 0.3,
            "awareness": 0.6,
            "social": {"social_pressure": 0.0, "dominant_sentiment": "negative"},
            "media": {"credibility": 0.2},
        }
        result = engine.make_decision(agent, perception_state)
        # With low trust and credibility, should have risk_concern
        assert "risk_concern" in result["reason_codes"]
        # With low trust/credibility, choice might be challenge or reject
        assert result["choice"] in [a["id"] for a in DEFAULT_ACTIONS]


# ─── C3: social_context field ───

class TestSocialContext:
    def test_cognition_result_has_social_context(self):
        d = CognitionResult(
            agent_id="agent_1",
            round_id=1,
            perception={"perceived_benefits": [], "perceived_risks": [], "confusion_points": [], "trust_signals": [], "relevance_score": 0.5, "emotional_reaction": "neutral"},
            decision={"choice": "accept", "reason_codes": [], "confidence": 0.5, "purchase_intent_score": 0.5, "credibility_score": 0.5, "risk_level": "medium"},
            expression={"quote": "", "paraphrase": "", "sentiment": "neutral", "channel": "general", "generated_by": "fallback", "misread_variant": None, "first_person_voice": "", "channel_style": "neutral"},
            social_context={"platform": "weibo"},
        )
        assert d.social_context == {"platform": "weibo"}

    def test_cognition_result_social_context_default_none(self):
        d = CognitionResult(
            agent_id="agent_1",
            round_id=1,
            perception={"perceived_benefits": [], "perceived_risks": [], "confusion_points": [], "trust_signals": [], "relevance_score": 0.5, "emotional_reaction": "neutral"},
            decision={"choice": "accept", "reason_codes": [], "confidence": 0.5, "purchase_intent_score": 0.5, "credibility_score": 0.5, "risk_level": "medium"},
            expression={"quote": "", "paraphrase": "", "sentiment": "neutral", "channel": "general", "generated_by": "fallback", "misread_variant": None, "first_person_voice": "", "channel_style": "neutral"},
        )
        assert d.social_context is None


# ─── C4: contradiction_flags and evidence_gap ───

class TestContradictionAndGaps:
    def test_detect_contradictions_mixed(self):
        atoms = [
            {"support_level": "strong"},
            {"support_level": "weak"},
        ]
        result = _detect_contradictions(atoms)
        assert "mixed_evidence" in result

    def test_detect_contradictions_uniform(self):
        atoms = [
            {"support_level": "strong"},
            {"support_level": "moderate"},
        ]
        result = _detect_contradictions(atoms)
        assert result == []

    def test_identify_gaps_no_evidence(self):
        result = _identify_gaps([], "some claim")
        assert "no_evidence" in result

    def test_identify_gaps_insufficient_count(self):
        atoms = [{"source_type": "journal"}]
        result = _identify_gaps(atoms, "some claim")
        assert "insufficient_evidence_count" in result

    def test_identify_gaps_missing_source_type(self):
        atoms = [
            {"support_level": "strong"},
            {"support_level": "moderate"},
        ]
        result = _identify_gaps(atoms, "some claim")
        assert "missing_source_type" in result

    def test_identify_gaps_sufficient(self):
        atoms = [
            {"support_level": "strong", "source_type": "journal"},
            {"support_level": "moderate", "source_type": "news"},
        ]
        result = _identify_gaps(atoms, "some claim")
        assert result == []

    def test_validate_finding_has_contradiction_flags(self):
        finding = {
            "finding_id": "f1",
            "evidence_snippets": ["snippet1"],
            "finding_text": "test claim",
        }
        result = validate_finding(finding)
        assert hasattr(result, "contradiction_flags")
        assert isinstance(result.contradiction_flags, list)

    def test_validate_finding_has_evidence_gap(self):
        finding = {
            "finding_id": "f1",
            "evidence_snippets": ["snippet1"],
            "finding_text": "test claim",
        }
        result = validate_finding(finding)
        assert hasattr(result, "evidence_gap")
        assert isinstance(result.evidence_gap, list)

    def test_validate_finding_no_evidence_gap(self):
        """Finding with no evidence should have 'no_evidence' gap."""
        finding = {
            "finding_id": "f2",
            "evidence_snippets": [],
            "finding_text": "test claim",
        }
        result = validate_finding(finding)
        assert "no_evidence" in result.evidence_gap

    def test_validate_finding_insufficient_count_gap(self):
        """Finding with only 1 snippet should have 'insufficient_evidence_count'."""
        finding = {
            "finding_id": "f3",
            "evidence_snippets": ["only one snippet"],
            "finding_text": "test claim",
        }
        result = validate_finding(finding)
        assert "insufficient_evidence_count" in result.evidence_gap

    def test_validate_finding_missing_source_type_gap(self):
        """Finding with snippets but no source_type should flag it."""
        finding = {
            "finding_id": "f4",
            "evidence_snippets": ["snippet a", "snippet b", "snippet c"],
            "finding_text": "test claim",
        }
        result = validate_finding(finding)
        assert "missing_source_type" in result.evidence_gap


# ─── C5: DOE pack_variant + channel_variant ───

class TestDOEPackAndChannel:
    def test_create_pack_variant(self):
        designer = ExperimentDesigner()
        packs = [
            {"name": "Pack A", "description": "Red pack"},
            {"name": "Pack B", "description": "Blue pack"},
            {"name": "Pack C", "description": "Green pack"},
        ]
        design = designer.create_pack_variant("Pack Test", packs)
        assert design.name == "Pack Test"
        assert len(design.variants) == 3
        assert design.control_variant_id == "pack_0"
        assert design.independent_variables == ["packaging"]
        assert "purchase_intent" in design.dependent_metrics
        assert design.variants[0].variant_id == "pack_0"
        assert design.variants[1].variant_id == "pack_1"

    def test_create_channel_variant(self):
        designer = ExperimentDesigner()
        channels = ["weibo", "wechat", "douyin"]
        design = designer.create_channel_variant("Channel Test", channels)
        assert design.name == "Channel Test"
        assert len(design.variants) == 3
        assert design.control_variant_id == "channel_0"
        assert design.independent_variables == ["channel"]
        assert "reach" in design.dependent_metrics
        assert design.variants[0].variant_id == "channel_0"
        assert design.variants[0].name == "weibo"


# ─── C6: factorial design ───

class TestFactorialDesign:
    def test_create_factorial(self):
        designer = ExperimentDesigner()
        factors = {
            "color": ["red", "blue"],
            "size": ["small", "large"],
        }
        design = designer.create_factorial("Factorial Test", factors)
        assert design.name == "Factorial Test"
        # 2 colors x 2 sizes = 4 combinations
        assert len(design.variants) == 4
        assert design.control_variant_id == "factorial_0"
        assert set(design.independent_variables) == {"color", "size"}
        assert "purchase_intent" in design.dependent_metrics

    def test_factorial_three_factors(self):
        designer = ExperimentDesigner()
        factors = {
            "color": ["red", "blue"],
            "size": ["small", "large"],
            "shape": ["round"],
        }
        design = designer.create_factorial("3-Factor Test", factors)
        # 2 x 2 x 1 = 4
        assert len(design.variants) == 4

    def test_factorial_variant_configs(self):
        designer = ExperimentDesigner()
        factors = {"a": [1, 2], "b": ["x", "y"]}
        design = designer.create_factorial("Config Test", factors)
        configs = [v.modifications for v in design.variants]
        assert {"a": 1, "b": "x"} in configs
        assert {"a": 2, "b": "y"} in configs


# ─── C7: validate_experiment_config hypothesis check ───

class TestValidateExperimentConfig:
    def test_quick_mode_no_hypothesis_required(self):
        """quick mode does not require hypothesis."""
        errors = validate_experiment_config("quick", 10, 1)
        # No hypothesis error expected for quick mode
        hypothesis_errors = [e for e in errors if "hypothesis" in e.lower()]
        assert len(hypothesis_errors) == 0

    def test_research_mode_requires_hypothesis(self):
        """research mode requires a hypothesis."""
        errors = validate_experiment_config("research", 50, 15)
        assert any("hypothesis" in e.lower() for e in errors)

    def test_research_mode_with_hypothesis(self):
        """research mode with hypothesis should pass hypothesis check."""
        errors = validate_experiment_config("research", 50, 15, hypothesis="Test H1")
        hypothesis_errors = [e for e in errors if "hypothesis" in e.lower()]
        assert len(hypothesis_errors) == 0

    def test_enterprise_mode_requires_hypothesis(self):
        """enterprise mode requires a hypothesis."""
        errors = validate_experiment_config("enterprise", 200, 50)
        assert any("hypothesis" in e.lower() for e in errors)

    def test_enterprise_mode_with_hypothesis(self):
        """enterprise mode with hypothesis passes hypothesis check."""
        errors = validate_experiment_config("enterprise", 200, 50, hypothesis="Test H2")
        hypothesis_errors = [e for e in errors if "hypothesis" in e.lower()]
        assert len(hypothesis_errors) == 0

    def test_unknown_mode(self):
        errors = validate_experiment_config("unknown", 10, 1)
        assert errors == ["Unknown mode: unknown"]

    def test_agent_count_validation_still_works(self):
        """Existing agent_count validation should still work."""
        errors = validate_experiment_config("quick", 5, 1)
        assert any("agents" in e.lower() for e in errors)
