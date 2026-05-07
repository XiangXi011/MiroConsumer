"""Tests for the three-layer cognition engine (Perception → Decision → Expression)."""

from __future__ import annotations

import sys
from pathlib import Path
from types import ModuleType
from typing import Any, Dict, List
from unittest.mock import MagicMock

# Stub out heavy third-party deps that app.services.__init__ pulls in
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

from app.services.consumer.cognition.decision import DecisionEngine, DEFAULT_ACTIONS
from app.services.consumer.cognition.engine import ConsumerCognitionEngine
from app.services.consumer.cognition.expression import ExpressionEngine
from app.services.consumer.cognition.perception import PerceptionEngine
from app.services.consumer.society.consumer_roles import ConsumerRole
from app.services.consumer.society.population_models import ConsumerSocietyAgent


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_agent(**overrides: Any) -> ConsumerSocietyAgent:
    defaults = dict(
        agent_id="agent-001",
        parent_persona_id="persona-1",
        layer="core",
        segment="young_professional",
        role=ConsumerRole.Advocate,
        traits={"tech_savvy": True},
        channel_affinity={"weibo": 0.8, "wechat": 0.6},
        evidence_sensitivity=0.6,
        price_sensitivity=0.4,
        trust_baseline=0.5,
        share_propensity=0.5,
        skepticism=0.3,
        state={"trust": 0.5, "purchase_intent": 0.5, "awareness": 0.0},
    )
    defaults.update(overrides)
    return ConsumerSocietyAgent(**defaults)


def _make_social_context(*, positive: int = 2, negative: int = 1) -> Dict[str, Any]:
    opinions: List[Dict[str, Any]] = []
    for i in range(positive):
        opinions.append({"source_id": f"p{i}", "text": "great product, recommend", "trust": 0.8, "claim": "good quality"})
    for i in range(negative):
        opinions.append({"source_id": f"n{i}", "text": "terrible experience, avoid", "trust": 0.2, "claim": "bad quality"})
    return {"peer_opinions": opinions}


def _make_media_content(*, source_type: str = "official") -> Dict[str, Any]:
    return {
        "claims": ["Best in class", "Award winning"],
        "source_type": source_type,
        "emotional_tone": "excitement",
        "target_audience": ["young_professional"],
    }


# ---------------------------------------------------------------------------
# PerceptionEngine tests
# ---------------------------------------------------------------------------

class TestPerceptionEngine:
    def test_process_social_input_basic(self):
        engine = PerceptionEngine()
        agent = _make_agent()
        ctx = _make_social_context(positive=3, negative=1)

        result = engine.process_social_input(agent, ctx)

        assert "peer_opinions" in result
        assert "social_pressure" in result
        assert "dominant_sentiment" in result
        assert "trust_signals" in result
        assert len(result["peer_opinions"]) == 4
        assert result["dominant_sentiment"] == "positive"
        assert result["social_pressure"] > 0

    def test_process_social_input_all_negative(self):
        engine = PerceptionEngine()
        agent = _make_agent()
        ctx = _make_social_context(positive=0, negative=3)

        result = engine.process_social_input(agent, ctx)

        assert result["dominant_sentiment"] == "negative"

    def test_process_social_input_empty(self):
        engine = PerceptionEngine()
        agent = _make_agent()

        result = engine.process_social_input(agent, {})

        assert result["peer_opinions"] == []
        assert result["dominant_sentiment"] == "neutral"
        assert result["social_pressure"] == 0.0

    def test_process_media_input_official(self):
        engine = PerceptionEngine()
        agent = _make_agent()
        media = _make_media_content(source_type="official")

        result = engine.process_media_input(agent, media)

        assert result["claims"] == ["Best in class", "Award winning"]
        assert result["credibility"] > 0.5
        assert result["relevance"] == 1.0  # segment matches target_audience

    def test_process_media_input_low_credibility(self):
        engine = PerceptionEngine()
        agent = _make_agent(skepticism=0.9)
        media = _make_media_content(source_type="advertising")

        result = engine.process_media_input(agent, media)

        assert result["credibility"] < 0.5

    def test_build_perception_state_combines_inputs(self):
        engine = PerceptionEngine()
        agent = _make_agent()
        social = engine.process_social_input(agent, _make_social_context())
        media = engine.process_media_input(agent, _make_media_content())

        state = engine.build_perception_state(agent, social_input=social, media_input=media)

        assert state["agent_id"] == "agent-001"
        assert state["awareness"] == 1.0
        assert "social" in state
        assert "media" in state

    def test_build_perception_state_empty_inputs(self):
        engine = PerceptionEngine()
        agent = _make_agent()

        state = engine.build_perception_state(agent)

        assert state["agent_id"] == "agent-001"
        assert state["awareness"] == 0.0


# ---------------------------------------------------------------------------
# DecisionEngine tests
# ---------------------------------------------------------------------------

class TestDecisionEngine:
    def test_evaluate_options_returns_sorted_list(self):
        engine = DecisionEngine()
        agent = _make_agent()
        perception = {"trust": 0.7, "awareness": 0.8, "social": {"social_pressure": 0.3, "dominant_sentiment": "positive"}, "media": {"credibility": 0.7}}

        result = engine.evaluate_options(agent, perception)

        assert len(result) > 0
        for i in range(len(result) - 1):
            assert result[i]["score"] >= result[i + 1]["score"]
        assert all("action_id" in r and "score" in r and "rationale" in r for r in result)

    def test_evaluate_options_with_custom_actions(self):
        engine = DecisionEngine()
        agent = _make_agent()
        perception = {"trust": 0.5, "awareness": 0.5, "social": {}, "media": {}}
        custom = [{"id": "buy", "label": "Buy now", "type": "positive"}, {"id": "skip", "label": "Skip", "type": "negative"}]

        result = engine.evaluate_options(agent, perception, available_actions=custom)

        assert len(result) == 2
        ids = {r["action_id"] for r in result}
        assert ids == {"buy", "skip"}

    def test_make_decision_returns_choice(self):
        engine = DecisionEngine()
        agent = _make_agent()
        perception = {"trust": 0.8, "awareness": 0.9, "social": {"social_pressure": 0.5, "dominant_sentiment": "positive"}, "media": {"credibility": 0.8}}

        decision = engine.make_decision(agent, perception)

        assert "choice" in decision
        assert "reasoning" in decision
        assert "scores" in decision
        assert "confidence" in decision
        assert decision["choice"] in {a["id"] for a in DEFAULT_ACTIONS}

    def test_make_decision_high_trust_prefers_accept(self):
        engine = DecisionEngine()
        agent = _make_agent(skepticism=0.1, evidence_sensitivity=0.9, share_propensity=0.2)
        perception = {"trust": 0.95, "awareness": 1.0, "social": {"social_pressure": 0.2, "dominant_sentiment": "neutral"}, "media": {"credibility": 0.9}}

        decision = engine.make_decision(agent, perception)

        assert decision["choice"] == "accept"

    def test_make_decision_low_trust_prefers_negative(self):
        engine = DecisionEngine()
        agent = _make_agent(skepticism=0.9, evidence_sensitivity=0.2)
        perception = {"trust": 0.1, "awareness": 1.0, "social": {"social_pressure": 0.1, "dominant_sentiment": "negative"}, "media": {"credibility": 0.1}}

        decision = engine.make_decision(agent, perception)

        assert decision["choice"] in {"reject", "seek_evidence"}


# ---------------------------------------------------------------------------
# ExpressionEngine tests
# ---------------------------------------------------------------------------

class TestExpressionEngine:
    def test_generate_opinion_non_empty(self):
        engine = ExpressionEngine()
        agent = _make_agent()
        decision = {"choice": "accept", "reasoning": "High trust"}

        opinion = engine.generate_opinion(agent, decision)

        assert isinstance(opinion, str)
        assert len(opinion) > 0

    def test_generate_social_post_non_empty(self):
        engine = ExpressionEngine()
        agent = _make_agent()
        decision = {"choice": "share", "reasoning": "Want to share"}

        post = engine.generate_social_post(agent, decision)

        assert isinstance(post, str)
        assert len(post) > 0

    def test_format_response_passes_valid_text(self):
        engine = ExpressionEngine()
        agent = _make_agent()

        result = engine.format_response(agent, "This is a valid opinion about the product.")

        assert result == "This is a valid opinion about the product."

    def test_format_response_rejects_empty_text(self):
        engine = ExpressionEngine()
        agent = _make_agent()

        result = engine.format_response(agent, "")

        assert "未生成" in result or "不可用" in result

    def test_template_opinion_varies_by_choice(self):
        engine = ExpressionEngine()
        agent = _make_agent()

        opinions = {c: engine.generate_opinion(agent, {"choice": c, "reasoning": ""})
                     for c in ("accept", "reject", "wait", "share", "seek_evidence")}

        # All should be non-empty and distinct
        assert all(len(v) > 0 for v in opinions.values())
        assert len(set(opinions.values())) == len(opinions)

    def test_llm_opinion_uses_client(self):
        mock_client = MagicMock()
        mock_client.chat_json.return_value = {"opinion": "LLM generated opinion"}
        engine = ExpressionEngine(llm_client=mock_client)
        agent = _make_agent()

        opinion = engine.generate_opinion(agent, {"choice": "accept", "reasoning": "test"})

        assert opinion == "LLM generated opinion"
        mock_client.chat_json.assert_called_once()

    def test_llm_social_post_uses_client(self):
        mock_client = MagicMock()
        mock_client.chat_json.return_value = {"post": "Great product! #recommend"}
        engine = ExpressionEngine(llm_client=mock_client)
        agent = _make_agent()

        post = engine.generate_social_post(agent, {"choice": "share", "reasoning": "test"})

        assert post == "Great product! #recommend"
        mock_client.chat_json.assert_called_once()

    def test_llm_failure_falls_back_to_template(self):
        mock_client = MagicMock()
        mock_client.chat_json.side_effect = RuntimeError("LLM down")
        engine = ExpressionEngine(llm_client=mock_client)
        agent = _make_agent()

        opinion = engine.generate_opinion(agent, {"choice": "accept", "reasoning": ""})

        assert len(opinion) > 0  # template fallback
        assert "young_professional" in opinion


# ---------------------------------------------------------------------------
# ConsumerCognitionEngine integration tests
# ---------------------------------------------------------------------------

class TestConsumerCognitionEngine:
    def test_process_turn_returns_complete_structure(self):
        engine = ConsumerCognitionEngine()
        agent = _make_agent()
        social = _make_social_context()
        media = _make_media_content()

        result = engine.process_turn(agent, social_context=social, media_content=media)

        assert "perception_state" in result
        assert "decision" in result
        assert "expression" in result
        assert "opinion" in result["expression"]
        assert "social_post" in result["expression"]
        assert result["decision"]["choice"] in {a["id"] for a in DEFAULT_ACTIONS}

    def test_process_turn_empty_social_context(self):
        engine = ConsumerCognitionEngine()
        agent = _make_agent()

        result = engine.process_turn(agent, social_context={}, media_content={})

        assert result["perception_state"]["social"]["peer_opinions"] == []
        assert result["perception_state"]["awareness"] == 0.0
        assert result["decision"]["choice"] in {a["id"] for a in DEFAULT_ACTIONS}
        assert len(result["expression"]["opinion"]) > 0

    def test_process_turn_none_inputs(self):
        engine = ConsumerCognitionEngine()
        agent = _make_agent()

        result = engine.process_turn(agent, social_context=None, media_content=None)

        assert result["perception_state"]["social"]["peer_opinions"] == []
        assert result["perception_state"]["media"]["claims"] == []

    def test_process_turn_preserves_agent_identity(self):
        engine = ConsumerCognitionEngine()
        agent = _make_agent(agent_id="test-agent-42", segment="gen_z")

        result = engine.process_turn(agent, social_context={}, media_content={})

        assert result["perception_state"]["agent_id"] == "test-agent-42"
        assert "test-agent-42" in result["decision"]["reasoning"]
        assert "gen_z" in result["expression"]["opinion"]

    def test_process_turn_with_llm_client(self):
        mock_client = MagicMock()
        mock_client.chat_json.side_effect = [
            {"opinion": "I think this is great!"},
            {"post": "Loving this product! #young_professional"},
        ]
        engine = ConsumerCognitionEngine(llm_client=mock_client)
        agent = _make_agent()

        result = engine.process_turn(agent, social_context=_make_social_context(), media_content=_make_media_content())

        assert result["expression"]["opinion"] == "I think this is great!"
        assert result["expression"]["social_post"] == "Loving this product! #young_professional"
