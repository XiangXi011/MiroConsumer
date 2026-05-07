"""Decision layer — evaluates options and makes decisions based on perception state."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Mapping

from ..demographics.persona import ConsumerPersona
from ..society.population_models import ConsumerSocietyAgent

logger = logging.getLogger(__name__)

# Default action set when caller does not supply one
DEFAULT_ACTIONS = [
    {"id": "accept", "label": "接受", "base_score": 0.5},
    {"id": "reject", "label": "拒绝", "base_score": 0.3},
    {"id": "hesitate", "label": "犹豫", "base_score": 0.4},
    {"id": "share", "label": "分享", "base_score": 0.6},
    {"id": "challenge", "label": "质疑", "base_score": 0.3},
    {"id": "ignore", "label": "忽略", "base_score": 0.2},
    {"id": "distort", "label": "误读", "base_score": 0.3},
    {"id": "ask_more", "label": "追问", "base_score": 0.5},
    {"id": "seek_evidence", "label": "求证", "base_score": 0.5},
]


class DecisionEngine:
    """Decision layer of the three-layer cognition architecture.

    Given a perception state and a set of available actions, evaluates each
    action and returns a structured decision with reasoning.
    """

    def evaluate_options(
        self,
        agent: ConsumerSocietyAgent,
        perception_state: Mapping[str, Any],
        available_actions: List[Dict[str, Any]] | None = None,
    ) -> List[Dict[str, Any]]:
        """Score every available action and return sorted list (highest first).

        Each returned dict has: action_id, score (0-1), rationale (str).
        """
        actions = available_actions if available_actions else DEFAULT_ACTIONS
        trust = float(perception_state.get("trust", agent.trust_baseline))
        awareness = float(perception_state.get("awareness", 0.0))
        social = perception_state.get("social", {})
        media = perception_state.get("media", {})
        social_pressure = float(social.get("social_pressure", 0.0))
        dominant_sentiment = social.get("dominant_sentiment", "neutral")
        credibility = float(media.get("credibility", 0.5))

        evaluated: List[Dict[str, Any]] = []
        for action in actions:
            score, rationale = self._score_action(
                action=action,
                agent=agent,
                trust=trust,
                awareness=awareness,
                social_pressure=social_pressure,
                dominant_sentiment=dominant_sentiment,
                credibility=credibility,
            )
            evaluated.append({
                "action_id": action.get("id", ""),
                "score": round(score, 4),
                "rationale": rationale,
            })

        evaluated.sort(key=lambda x: x["score"], reverse=True)
        return evaluated

    def make_decision(
        self,
        agent: ConsumerSocietyAgent,
        perception_state: Mapping[str, Any],
        options: List[Dict[str, Any]] | None = None,
        persona: ConsumerPersona | None = None,
    ) -> Dict[str, Any]:
        """Make a decision by evaluating options and picking the top one.

        Returns:
            choice: str — the chosen action id
            reasoning: str — human-readable explanation
            scores: list — full scored option list
            confidence: float 0-1
            dimension_scores: dict — persona-alignment scores (when persona provided)
        """
        evaluated = self.evaluate_options(agent, perception_state, options)
        if not evaluated:
            return {
                "choice": "wait",
                "reasoning": "No options available; defaulting to wait.",
                "scores": [],
                "confidence": 0.0,
            }

        best = evaluated[0]
        second_score = evaluated[1]["score"] if len(evaluated) > 1 else 0.0
        confidence = round(best["score"] - second_score, 4)

        reasoning = (
            f"Agent {agent.agent_id} ({agent.segment}/{agent.role.value}) "
            f"chose '{best['action_id']}' with score {best['score']:.3f}. "
            f"{best['rationale']}"
        )

        # Generate reason_codes based on perception scores
        trust_score = float(perception_state.get("trust", 0.5))
        price_score = float(perception_state.get("persona", {}).get("price_sensitivity", 0.5))
        risk_score = (1.0 - trust_score + (1.0 - float(perception_state.get("media", {}).get("credibility", 0.5)))) / 2.0
        social_influence = float(perception_state.get("social", {}).get("social_pressure", 0.0))

        reason_codes: List[str] = []
        if trust_score > 0.7:
            reason_codes.append("high_trust")
        if price_score > 0.7:
            reason_codes.append("price_appealing")
        if risk_score > 0.6:
            reason_codes.append("risk_concern")
        if social_influence > 0.5:
            reason_codes.append("social_influenced")
        if not reason_codes:
            reason_codes.append("neutral_assessment")
        # Generate evidence_refs
        evidence_refs = []
        if perception_state.get("trust_signals"):
            evidence_refs.extend([f"ts_{i}" for i, _ in enumerate(perception_state["trust_signals"][:3])])
        if perception_state.get("perceived_risks"):
            evidence_refs.extend([f"pr_{i}" for i, _ in enumerate(perception_state["perceived_risks"][:2])])

        result: Dict[str, Any] = {
            "choice": best["action_id"],
            "reasoning": reasoning,
            "scores": evaluated,
            "confidence": confidence,
            "reason_codes": reason_codes,
            "evidence_refs": evidence_refs,
        }

        # Compute dimension alignment scores when persona is available
        if persona is not None:
            persona_state = perception_state.get("persona", {})
            price_score = persona_state.get("price_sensitivity", 0.5)
            brand_score = persona_state.get("brand_loyalty", 0.5)
            social_score = persona_state.get("social_influence_weight", 0.5)

            result["dimension_scores"] = {
                "price_alignment": 1.0 - abs(persona.price_sensitivity - price_score),
                "brand_alignment": 1.0 - abs(persona.brand_loyalty - brand_score),
                "social_alignment": 1.0 - abs(persona.social_influence_weight - social_score),
            }

        return result

    # ------------------------------------------------------------------
    # Internal scoring
    # ------------------------------------------------------------------

    def _score_action(
        self,
        action: Mapping[str, Any],
        agent: ConsumerSocietyAgent,
        trust: float,
        awareness: float,
        social_pressure: float,
        dominant_sentiment: str,
        credibility: float,
    ) -> tuple[float, str]:
        """Return (score, rationale) for a single action."""
        action_type = str(action.get("type", "neutral"))
        action_id = str(action.get("id", ""))

        if action_type == "positive":
            return self._score_positive(trust, awareness, credibility, agent)
        if action_type == "negative":
            return self._score_negative(trust, credibility, agent.skepticism)
        if action_type == "social":
            return self._score_social(social_pressure, dominant_sentiment, agent.share_propensity)
        if action_type == "investigative":
            return self._score_investigative(trust, credibility, agent.evidence_sensitivity)
        # neutral / wait
        return self._score_neutral(awareness, trust)

    @staticmethod
    def _score_positive(
        trust: float, awareness: float, credibility: float, agent: ConsumerSocietyAgent,
    ) -> tuple[float, str]:
        score = (trust * 0.4 + credibility * 0.3 + awareness * 0.3) * (1 - agent.skepticism * 0.3)
        rationale = (
            f"Positive response score={score:.3f} based on trust={trust:.2f}, "
            f"credibility={credibility:.2f}, low skepticism={agent.skepticism:.2f}."
        )
        return score, rationale

    @staticmethod
    def _score_negative(
        trust: float, credibility: float, skepticism: float,
    ) -> tuple[float, str]:
        score = ((1 - trust) * 0.4 + (1 - credibility) * 0.3 + skepticism * 0.3)
        rationale = (
            f"Negative response score={score:.3f} based on low trust={trust:.2f}, "
            f"low credibility={credibility:.2f}, high skepticism={skepticism:.2f}."
        )
        return score, rationale

    @staticmethod
    def _score_social(
        social_pressure: float, dominant_sentiment: str, share_propensity: float,
    ) -> tuple[float, str]:
        sentiment_boost = 0.2 if dominant_sentiment == "positive" else -0.1
        score = (social_pressure * 0.5 + share_propensity * 0.3 + sentiment_boost + 0.2)
        score = max(0.0, min(1.0, score))
        rationale = (
            f"Social action score={score:.3f} based on pressure={social_pressure:.2f}, "
            f"share_propensity={share_propensity:.2f}, sentiment={dominant_sentiment}."
        )
        return score, rationale

    @staticmethod
    def _score_investigative(
        trust: float, credibility: float, evidence_sensitivity: float,
    ) -> tuple[float, str]:
        uncertainty = (1 - trust) * 0.5 + (1 - credibility) * 0.5
        score = uncertainty * 0.6 + evidence_sensitivity * 0.4
        rationale = (
            f"Investigative action score={score:.3f} driven by uncertainty={uncertainty:.2f}, "
            f"evidence_sensitivity={evidence_sensitivity:.2f}."
        )
        return score, rationale

    @staticmethod
    def _score_neutral(awareness: float, trust: float) -> tuple[float, str]:
        score = (1 - awareness) * 0.5 + 0.3
        rationale = f"Wait/neutral score={score:.3f}; awareness={awareness:.2f}, trust={trust:.2f}."
        return score, rationale


__all__ = ["DecisionEngine", "DEFAULT_ACTIONS"]
