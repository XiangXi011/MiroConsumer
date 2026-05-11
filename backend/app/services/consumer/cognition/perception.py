"""Perception layer — processes social and media inputs into structured perception state."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Mapping

from ..demographics.persona import ConsumerPersona
from ..society.population_models import ConsumerSocietyAgent

logger = logging.getLogger(__name__)


class PerceptionEngine:
    """Perception layer of the three-layer cognition architecture.

    Responsible for processing raw social and media inputs into a structured
    perception state that the Decision layer can reason over.
    """

    def process_social_input(
        self,
        agent: ConsumerSocietyAgent,
        social_context: Mapping[str, Any],
    ) -> Dict[str, Any]:
        """Process social information (other agents' opinions, behaviours).

        Returns a structured dict with:
            - peer_opinions: list of opinion summaries from peers
            - social_pressure: float 0-1 indicating conformity pressure
            - dominant_sentiment: str "positive" / "negative" / "neutral"
            - trust_signals: list of trust-relevant observations
        """
        peer_opinions: List[Dict[str, Any]] = []
        raw_opinions = social_context.get("peer_opinions", [])
        for opinion in raw_opinions if isinstance(raw_opinions, list) else []:
            if isinstance(opinion, dict):
                peer_opinions.append({
                    "source_id": opinion.get("source_id", ""),
                    "sentiment": self._classify_sentiment(opinion.get("text", "")),
                    "trust": float(opinion.get("trust", 0.5)),
                    "claim": opinion.get("claim", ""),
                })

        sentiments = [op["sentiment"] for op in peer_opinions]
        dominant_sentiment = self._aggregate_sentiment(sentiments)

        positive_count = sentiments.count("positive")
        negative_count = sentiments.count("negative")
        total = len(sentiments) if sentiments else 1
        social_pressure = round(abs(positive_count - negative_count) / total, 4)

        trust_signals = [
            op for op in peer_opinions
            if op["trust"] < 0.3 or op["trust"] > 0.7
        ]

        return {
            "peer_opinions": peer_opinions,
            "social_pressure": social_pressure,
            "dominant_sentiment": dominant_sentiment,
            "trust_signals": trust_signals,
        }

    def process_media_input(
        self,
        agent: ConsumerSocietyAgent,
        media_content: Mapping[str, Any],
    ) -> Dict[str, Any]:
        """Process media / advertising content.

        Returns a structured dict with:
            - claims: list of extracted claims
            - credibility: float 0-1
            - emotional_appeal: float 0-1
            - relevance: float 0-1 based on agent segment
        """
        raw_claims = media_content.get("claims", [])
        claims = [str(c) for c in raw_claims] if isinstance(raw_claims, list) else []

        source_type = str(media_content.get("source_type", "unknown"))
        credibility = self._assess_source_credibility(source_type, agent)

        emotional_tone = str(media_content.get("emotional_tone", "neutral"))
        emotional_appeal = self._assess_emotional_appeal(emotional_tone, agent)

        target_audience = media_content.get("target_audience", [])
        relevance = self._compute_relevance(agent.segment, target_audience)

        return {
            "claims": claims,
            "credibility": credibility,
            "emotional_appeal": emotional_appeal,
            "relevance": relevance,
        }

    def build_perception_state(
        self,
        agent: ConsumerSocietyAgent,
        social_input: Dict[str, Any] | None = None,
        media_input: Dict[str, Any] | None = None,
        persona: ConsumerPersona | None = None,
    ) -> Dict[str, Any]:
        """Build the unified perception state from processed inputs.

        Combines social and media perception into a single state dict
        that the Decision layer consumes.  When a *persona* is supplied its
        description and key traits are embedded in the state so downstream
        layers can reason over them.
        """
        social = social_input or {}
        media = media_input or {}

        awareness = agent.state.get("awareness", 0.0)
        if social.get("peer_opinions") or media.get("claims"):
            awareness = 1.0

        trust = float(agent.state.get("trust", agent.trust_baseline))
        if social.get("dominant_sentiment") == "negative":
            trust = max(0.0, trust - 0.05 * agent.skepticism)
        elif social.get("dominant_sentiment") == "positive":
            trust = min(1.0, trust + 0.03 * agent.evidence_sensitivity)

        state: Dict[str, Any] = {
            "agent_id": agent.agent_id,
            "awareness": awareness,
            "trust": round(trust, 4),
            "social": social,
            "media": media,
        }

        # Embed persona information when available
        if persona is not None:
            state["persona"] = {
                "persona_id": persona.persona_id,
                "description": persona.to_prompt_description(),
                "price_sensitivity": persona.price_sensitivity,
                "brand_loyalty": persona.brand_loyalty,
                "social_influence_weight": persona.social_influence_weight,
                "innovation_adoption": persona.innovation_adoption,
            }

        return state

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _classify_sentiment(text: str) -> str:
        """Very simple keyword-based sentiment classification."""
        positive_words = {"good", "great", "love", "recommend", "excellent", "positive", "trust"}
        negative_words = {"bad", "poor", "hate", "avoid", "terrible", "negative", "scam"}
        lower = text.lower()
        pos = sum(1 for w in positive_words if w in lower)
        neg = sum(1 for w in negative_words if w in lower)
        if pos > neg:
            return "positive"
        if neg > pos:
            return "negative"
        return "neutral"

    @staticmethod
    def _aggregate_sentiment(sentiments: List[str]) -> str:
        if not sentiments:
            return "neutral"
        counts = {"positive": 0, "negative": 0, "neutral": 0}
        for s in sentiments:
            counts[s] = counts.get(s, 0) + 1
        return max(counts, key=counts.get)  # type: ignore[arg-type]

    @staticmethod
    def _assess_source_credibility(source_type: str, agent: ConsumerSocietyAgent) -> float:
        base = {
            "official": 0.8,
            "news": 0.7,
            "social_media": 0.4,
            "advertising": 0.3,
            "unknown": 0.5,
        }
        credibility = base.get(source_type, 0.5)
        credibility -= 0.1 * (agent.skepticism - 0.5)
        return round(max(0.0, min(1.0, credibility)), 4)

    @staticmethod
    def _assess_emotional_appeal(tone: str, agent: ConsumerSocietyAgent) -> float:
        base = {"excitement": 0.8, "fear": 0.6, "trust": 0.7, "neutral": 0.3}
        appeal = base.get(tone, 0.3)
        appeal *= (0.5 + agent.share_propensity)
        return round(max(0.0, min(1.0, appeal)), 4)

    @staticmethod
    def _compute_relevance(agent_segment: str, target_audience: Any) -> float:
        if not target_audience:
            return 0.5
        if not isinstance(target_audience, list):
            return 0.5
        if agent_segment in target_audience:
            return 1.0
        return 0.3


__all__ = ["PerceptionEngine"]
