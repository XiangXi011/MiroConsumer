"""Dynamic participation model for consumer society rounds."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any, Iterable, Mapping, Sequence


@dataclass(frozen=True)
class ParticipationDecision:
    participated: bool
    participation_probability: float
    engagement_level: float
    topic_relevance: float
    fatigue: float
    neighbor_activity: float
    random_draw: float
    reason: str


class DynamicParticipationModel:
    """Decide whether an agent should participate in a round.

    The model is deterministic for a given seed, agent id, and round. It combines
    agent engagement, brief/topic relevance, participation fatigue, and recent
    activity from nearby agents in the same segment.
    """

    def __init__(self, seed: int = 0):
        self.seed = int(seed or 0)

    def decide(
        self,
        *,
        agent: Any,
        round_index: int,
        claims: Sequence[str],
        brief_context: Mapping[str, Any],
        previous_events: Iterable[Mapping[str, Any]],
    ) -> ParticipationDecision:
        engagement = self._engagement_level(agent)
        topic_relevance = self._topic_relevance(agent, claims, brief_context)
        previous = list(previous_events or [])
        fatigue = self._fatigue(agent, previous)
        neighbor_activity = self._neighbor_activity(agent, round_index, previous)
        probability = self._probability(
            engagement=engagement,
            topic_relevance=topic_relevance,
            fatigue=fatigue,
            neighbor_activity=neighbor_activity,
            round_index=round_index,
        )
        random_draw = self._draw(str(getattr(agent, "agent_id", "")), round_index)
        participated = round_index == 0 or probability >= 0.9 or random_draw <= probability
        reason = self._reason(
            participated=participated,
            engagement=engagement,
            topic_relevance=topic_relevance,
            fatigue=fatigue,
            neighbor_activity=neighbor_activity,
        )
        return ParticipationDecision(
            participated=participated,
            participation_probability=probability,
            engagement_level=engagement,
            topic_relevance=topic_relevance,
            fatigue=fatigue,
            neighbor_activity=neighbor_activity,
            random_draw=random_draw,
            reason=reason,
        )

    def _probability(
        self,
        *,
        engagement: float,
        topic_relevance: float,
        fatigue: float,
        neighbor_activity: float,
        round_index: int,
    ) -> float:
        if round_index <= 0:
            return 1.0
        score = (
            0.10
            + 0.35 * engagement
            + 0.25 * topic_relevance
            + 0.15 * neighbor_activity
            - 0.25 * fatigue
        )
        return round(max(0.05, min(0.95, score)), 4)

    @staticmethod
    def _engagement_level(agent: Any) -> float:
        state = getattr(agent, "state", {}) or {}
        traits = getattr(agent, "traits", {}) or {}
        explicit = state.get("engagement_level", traits.get("engagement_level"))
        if explicit is not None:
            return _bounded_float(explicit, default=0.5)
        share = _bounded_float(getattr(agent, "share_propensity", 0.5), default=0.5)
        evidence = _bounded_float(getattr(agent, "evidence_sensitivity", 0.5), default=0.5)
        skepticism = _bounded_float(getattr(agent, "skepticism", 0.5), default=0.5)
        return round(max(0.0, min(1.0, (share + evidence + (1.0 - skepticism)) / 3)), 4)

    @staticmethod
    def _topic_relevance(
        agent: Any,
        claims: Sequence[str],
        brief_context: Mapping[str, Any],
    ) -> float:
        traits = getattr(agent, "traits", {}) or {}
        topic_text = " ".join(
            [
                " ".join(str(claim) for claim in claims or []),
                str(brief_context.get("product_category", "")) if isinstance(brief_context, Mapping) else "",
                str(brief_context.get("research_goal", "")) if isinstance(brief_context, Mapping) else "",
                " ".join(str(item) for item in brief_context.get("claims", []))
                if isinstance(brief_context, Mapping) and isinstance(brief_context.get("claims"), list)
                else "",
            ]
        ).lower()
        if not topic_text.strip():
            return 0.5

        signals = []
        for key in ("attention_drivers", "risk_sensitivities", "interested_topics"):
            signals.extend(str(item).lower().replace("_", " ") for item in traits.get(key, []) or [])
        if not signals:
            return 0.35

        matched = 0
        for signal in signals:
            parts = [part for part in signal.split() if part]
            if signal and signal in topic_text:
                matched += 1
            elif parts and any(part in topic_text for part in parts):
                matched += 1
        return round(max(0.0, min(1.0, matched / max(len(signals), 1))), 4)

    @staticmethod
    def _fatigue(agent: Any, previous_events: Sequence[Mapping[str, Any]]) -> float:
        agent_id = str(getattr(agent, "agent_id", "") or "")
        participated_count = 0
        for event in previous_events:
            if str(event.get("agent_id") or event.get("actor_id") or "") != agent_id:
                continue
            if str(event.get("consumer_event_type") or "") == "PARTICIPATION_SKIPPED":
                continue
            participated_count += 1
        return round(min(0.85, participated_count * 0.28), 4)

    @staticmethod
    def _neighbor_activity(
        agent: Any,
        round_index: int,
        previous_events: Sequence[Mapping[str, Any]],
    ) -> float:
        if not previous_events:
            return 0.0
        segment = str(getattr(agent, "segment", "") or "")
        agent_id = str(getattr(agent, "agent_id", "") or "")
        recent_round = max(0, round_index - 1)
        related = 0
        active = 0
        for event in previous_events:
            if int(event.get("round_index", -1) or -1) != recent_round:
                continue
            if str(event.get("agent_id") or event.get("actor_id") or "") == agent_id:
                continue
            if segment and str(event.get("segment") or "") != segment:
                continue
            related += 1
            if str(event.get("consumer_event_type") or "") not in {"", "PARTICIPATION_SKIPPED", "IGNORE"}:
                active += 1
        if related == 0:
            return 0.0
        return round(max(0.0, min(1.0, active / related)), 4)

    def _draw(self, agent_id: str, round_index: int) -> float:
        material = f"{self.seed}:{agent_id}:{round_index}".encode("utf-8")
        digest = hashlib.sha256(material).hexdigest()
        return round(int(digest[:12], 16) / float(0xFFFFFFFFFFFF), 6)

    @staticmethod
    def _reason(
        *,
        participated: bool,
        engagement: float,
        topic_relevance: float,
        fatigue: float,
        neighbor_activity: float,
    ) -> str:
        if participated and neighbor_activity >= 0.6:
            return "neighbor_activity"
        if participated and topic_relevance >= 0.5:
            return "topic_relevance"
        if participated:
            return "baseline_engagement"
        if fatigue >= 0.5:
            return "social_fatigue"
        if topic_relevance < 0.2:
            return "low_topic_relevance"
        if engagement < 0.2:
            return "low_engagement"
        return "probabilistic_skip"


def _bounded_float(value: Any, default: float = 0.5) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        parsed = default
    return round(max(0.0, min(1.0, parsed)), 4)


__all__ = ["DynamicParticipationModel", "ParticipationDecision"]
