"""Unified cognition engine — orchestrates Perception → Decision → Expression."""

from __future__ import annotations

import logging
from typing import Any, Dict, Mapping

from ..demographics.persona import ConsumerPersona
from ..society.population_models import ConsumerSocietyAgent
from .decision import DecisionEngine
from .expression import ExpressionEngine
from .perception import PerceptionEngine
from .schemas import (
    CognitionResult,
    DecisionOutput,
    ExpressionOutput,
    PerceptionOutput,
)

logger = logging.getLogger(__name__)


class ConsumerCognitionEngine:
    """Three-layer cognition engine for consumer agents.

    Orchestrates the full cognitive cycle:
        Perception (感知) → Decision (决策) → Expression (表达)

    Usage::

        engine = ConsumerCognitionEngine(llm_client=my_llm)
        result = engine.process_turn(agent, social_context, media_content, persona=persona)
    """

    def __init__(self, llm_client: Any | None = None):
        self.llm_client = llm_client
        self.perception = PerceptionEngine()
        self.decision = DecisionEngine()
        self.expression = ExpressionEngine(llm_client=llm_client)

    def process_turn(
        self,
        agent: ConsumerSocietyAgent,
        social_context: Mapping[str, Any] | None = None,
        media_content: Mapping[str, Any] | None = None,
        persona: ConsumerPersona | Mapping[str, Any] | None = None,
    ) -> Dict[str, Any]:
        """Run one complete cognitive cycle and return full result.

        Returns a dict with keys:
            - perception_state: structured perception data
            - decision: decision dict (choice, reasoning, scores, confidence)
            - expression: dict with opinion and social_post
            - reasoning_trace: trace of the cognitive reasoning process
        """
        # Resolve persona to ConsumerPersona if given as dict
        if isinstance(persona, dict):
            persona = ConsumerPersona(**persona)

        # --- Perception ---
        social_input = self.perception.process_social_input(
            agent, social_context or {},
        )
        media_input = self.perception.process_media_input(
            agent, media_content or {},
        )
        perception_state = self.perception.build_perception_state(
            agent, social_input=social_input, media_input=media_input,
            persona=persona,
        )

        # --- Decision ---
        decision = self.decision.make_decision(agent, perception_state, persona=persona)

        # --- Expression ---
        opinion = self.expression.generate_opinion(agent, decision)
        social_post = self.expression.generate_social_post(agent, decision)

        formatted_opinion = self.expression.format_response(agent, opinion)
        formatted_post = self.expression.format_response(agent, social_post)

        # --- Expression enrichment ---
        misread_variant = self.expression.generate_misread_variant(perception_state)
        channel_style = "formal" if media_content and media_content.get("source_type") == "official" else "casual"

        # --- Reasoning Trace ---
        reasoning_trace = {
            "perception_summary": str(perception_state),
            "decision_reasoning": decision.get("reasoning", ""),
            "confidence": decision.get("confidence", 0.0),
            "persona_id": persona.persona_id if persona else None,
        }

        # --- Pydantic validation ---
        perception_out = PerceptionOutput(
            perceived_benefits=perception_state.get("perceived_benefits", []),
            perceived_risks=perception_state.get("perceived_risks", []),
            confusion_points=perception_state.get("confusion_points", []),
            trust_signals=perception_state.get("trust_signals", []),
            relevance_score=perception_state.get("relevance_score", 0.5),
            emotional_reaction=perception_state.get("emotional_reaction", "neutral"),
        )

        decision_out = DecisionOutput(
            choice=decision.get("choice", "hesitate"),
            reason_codes=decision.get("reason_codes", []),
            confidence=decision.get("confidence", 0.5),
            purchase_intent_score=decision.get("purchase_intent_score", 0.5),
            credibility_score=decision.get("credibility_score", 0.5),
            risk_level=decision.get("risk_level", "medium"),
            evidence_refs=decision.get("evidence_refs", []),
        )

        expression_out = ExpressionOutput(
            quote=formatted_opinion,
            paraphrase=formatted_post,
            sentiment=decision.get("sentiment", "neutral"),
            channel=decision.get("channel", "general"),
            misread_variant=misread_variant,
            first_person_voice=formatted_opinion,
            channel_style=channel_style,
        )

        # --- Traceability fields ---
        input_span = f"{agent.agent_id}:r{decision.get('round_id', 0)}"
        memory_state = {
            "trust": perception_state.get("trust", agent.trust_baseline),
            "awareness": perception_state.get("awareness", 0.0),
            "social_pressure": perception_state.get("social", {}).get("social_pressure", 0.0),
        }

        result = CognitionResult(
            agent_id=str(agent.agent_id),
            round_id=decision.get("round_id", 0),
            perception=perception_out,
            decision=decision_out,
            expression=expression_out,
            reasoning_trace=reasoning_trace,
            dimension_scores=decision.get("dimension_scores", {}),
            persona_id=persona.persona_id if persona else None,
            input_span=input_span,
            memory_state=memory_state,
            social_context=social_context or {},
        )

        return result.model_dump()


__all__ = ["ConsumerCognitionEngine"]
