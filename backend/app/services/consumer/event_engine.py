"""Propagation event taxonomy and helpers for Phase 2 consumer simulation.

Event classification is grounded in:
1. Rumor psychology (DiFonzo & Bordia, 2007): anxiety-driven rumor spreading
   maps to positive_relay and misread_amplification
2. Social judgment theory (Sherif & Hovland, 1961): attitude latitude of
   acceptance/rejection maps to skeptical_challenge and clarification_recovery
3. ELM central-peripheral route (Petty & Cacioppo, 1986): high-involvement
   agents produce skeptical_challenge; low-involvement agents produce
   positive_relay or misread_amplification
4. Innovation diffusion (Rogers, 2003): adopters' uncertainty reduction
   maps to clarification_recovery after initial misread_amplification
"""

from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from .models import PropagationEvent


def _normalize_attitude(attitude: str | float) -> str:
    """Normalize attitude to discrete label.

    Supports both discrete string labels and continuous values (-1.0 to +1.0).
    """
    if isinstance(attitude, (int, float)):
        val = float(attitude)
        if val >= 0.3:
            return "positive"
        if val <= -0.3:
            return "negative"
        return "neutral"
    return str(attitude).strip().lower()


def classify_propagation_event(
    before_attitude: str | float,
    after_attitude: str | float,
    trigger: str = "",
    speech_act: str = "",
) -> Literal[
    "positive_relay",
    "skeptical_challenge",
    "misread_amplification",
    "risk_discovery",
    "clarification_recovery",
]:
    """Classify a propagation event from attitude transition and context.

    Classification draws on:
    - Rumor psychology for anxiety-driven transitions (positive→negative)
    - Social judgment theory for acceptance/rejection latitude shifts
    - Innovation diffusion for post-adoption uncertainty reduction

    Args:
        before_attitude: Attitude label from the previous round.
            Supports discrete labels ("positive"/"neutral"/"negative") or
            continuous values in [-1.0, +1.0] (added for Phase 2 attitude
            continuum support).
        after_attitude: Attitude label in the current round.
            Supports discrete labels ("positive"/"neutral"/"negative") or
            continuous values in [-1.0, +1.0].
        trigger: Dominant trigger type (e.g. risk_signal, competitor_signal).
        speech_act: Speech act label derived from the bucket.

    Returns:
        One of the five propagation event types.
    """
    # Normalize continuous attitudes (-1.0 to +1.0) to discrete labels
    before_val = _normalize_attitude(before_attitude)
    after_val = _normalize_attitude(after_attitude)
    before = before_val
    after = after_val

    if before == "positive" and after == "negative":
        if speech_act == "reinterpretation":
            return "misread_amplification"
        if trigger in {"risk_signal", "competitor_signal"}:
            return "risk_discovery"
        return "misread_amplification"

    if before == "negative" and after in {"positive", "neutral"}:
        return "clarification_recovery"

    # Handle misread -> positive (recovery from misinterpretation)
    if before == "misread" and after == "positive":
        return "clarification_recovery"

    # Explicit neutral transitions
    if before == "neutral" and after == "negative":
        return "skeptical_challenge"

    if before == "neutral" and after == "positive":
        return "positive_relay"

    # positive -> neutral (interest decay/hesitation)
    if before == "positive" and after == "neutral":
        return "skeptical_challenge"

    if after == "negative":
        return "skeptical_challenge"

    if after == "positive":
        return "positive_relay"

    return "skeptical_challenge"


def build_propagation_event(
    actor_id: str,
    target_ids: List[str],
    event_type: str,
    trigger_finding_ids: List[str],
    supporting_quote: str,
    round_index: int,
    actor_community: str = "",
    actor_role: str = "",
    cross_community: bool = False,
    target_communities: Optional[List[str]] = None,
) -> PropagationEvent:
    """Build a typed PropagationEvent with a deterministic ID."""
    event_id = f"evt_{actor_id}_r{round_index}_{event_type[:3]}_{__import__('uuid').uuid4().hex[:8]}"
    return PropagationEvent(
        event_id=event_id,
        event_type=event_type,  # type: ignore[arg-type]
        actor_id=actor_id,
        target_ids=list(target_ids),
        trigger_finding_ids=list(trigger_finding_ids),
        supporting_quote=supporting_quote,
        round_index=round_index,
        actor_community=actor_community,
        actor_role=actor_role,
        cross_community=cross_community,
        target_communities=list(target_communities or []),
    )


def derive_trigger_from_findings(visible_findings: List[Dict[str, Any]]) -> str:
    """Derive the dominant trigger type from visible research findings."""
    for finding in visible_findings:
        finding_type = finding.get("finding_type", "")
        if finding_type == "risk_signal":
            return "risk_signal"
        if finding_type == "competitor_signal":
            return "competitor_signal"
    return "category_context"


def derive_speech_act_from_bucket(bucket: str) -> str:
    """Map attitude bucket to a speech act label."""
    mapping: Dict[str, str] = {
        "resonance": "endorsement",
        "risk": "challenge",
        "question": "inquiry",
        "misread": "reinterpretation",
    }
    return mapping.get(str(bucket).strip().lower(), "statement")
