"""Unified cognition engine — orchestrates Perception → Decision → Expression."""

from __future__ import annotations

import logging
from typing import Any, Dict, Mapping

from ..society.population_models import ConsumerSocietyAgent
from .decision import DecisionEngine
from .expression import ExpressionEngine
from .perception import PerceptionEngine

logger = logging.getLogger(__name__)


class ConsumerCognitionEngine:
    """Three-layer cognition engine for consumer agents.

    Orchestrates the full cognitive cycle:
        Perception (感知) → Decision (决策) → Expression (表达)

    Usage::

        engine = ConsumerCognitionEngine(llm_client=my_llm)
        result = engine.process_turn(agent, social_context, media_content)
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
    ) -> Dict[str, Any]:
        """Run one complete cognitive cycle and return full result.

        Returns a dict with keys:
            - perception_state: structured perception data
            - decision: decision dict (choice, reasoning, scores, confidence)
            - expression: dict with opinion and social_post
        """
        # --- Perception ---
        social_input = self.perception.process_social_input(
            agent, social_context or {},
        )
        media_input = self.perception.process_media_input(
            agent, media_content or {},
        )
        perception_state = self.perception.build_perception_state(
            agent, social_input=social_input, media_input=media_input,
        )

        # --- Decision ---
        decision = self.decision.make_decision(agent, perception_state)

        # --- Expression ---
        opinion = self.expression.generate_opinion(agent, decision)
        social_post = self.expression.generate_social_post(agent, decision)

        formatted_opinion = self.expression.format_response(agent, opinion)
        formatted_post = self.expression.format_response(agent, social_post)

        return {
            "perception_state": perception_state,
            "decision": decision,
            "expression": {
                "opinion": formatted_opinion,
                "social_post": formatted_post,
            },
        }


__all__ = ["ConsumerCognitionEngine"]
