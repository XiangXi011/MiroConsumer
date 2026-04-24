"""Hybrid simulation kernel with preserve-first base behaviour.

When ``prior_state`` is ``None`` or no threshold triggers, the base
attitude/bucket/quote output mirrors :class:`LegacySimulationKernel`
byte-for-byte.  ``prior_state`` fields then apply bounded adjustments.
"""

from __future__ import annotations

import hashlib
from typing import Any, Dict, List, Mapping, Optional

from .kernel_adapter import SimulationKernelAdapter, SimulationKernelResult

# ---------------------------------------------------------------------------
# Small deterministic quote-template pools keyed by bucket.
# Each pool has >= 3 variants; selection is seeded per (agent_id, round_num,
# bucket, hash-fragment-of-detail) to reduce inter-agent collisions.
# ---------------------------------------------------------------------------

_QUOTE_TEMPLATES: Dict[str, List[str]] = {
    "risk": [
        "I keep thinking about {detail}, so the claim starts to feel less trustworthy.",
        "Every time {detail} comes up it chips away at my confidence in the claim.",
        "{detail} keeps nagging at me — hard to trust the pitch with that lingering.",
    ],
    "resonance": [
        "This actually sounds like a practical fix because of {detail}.",
        "People would probably keep sharing {detail}, and that makes the idea feel credible.",
        "{detail} is the kind of thing that sticks — feels like a strong signal.",
    ],
    "question": [
        "I keep seeing {detail}, but I still want more proof before I fully buy in.",
        "I understand the pitch, but I need more concrete proof before reacting strongly.",
        "{detail} is interesting, yet I'm not fully convinced without harder evidence.",
    ],
    "misread": [
        "I think I misunderstood {detail} the first time around.",
        "On second pass {detail} doesn't quite say what I thought it did.",
        "Rereading {detail} muddied the picture more than it clarified.",
    ],
}


def _select_template(bucket: str, agent_id: str, round_num: int, detail: str) -> str:
    """Pick a deterministic quote from the pool for *bucket*.

    The seed is stable for a given (agent_id, round_num, bucket, detail-hash)
    tuple, giving variety across agents and rounds while remaining
    reproducible within a single agent+round.
    """
    pool = _QUOTE_TEMPLATES.get(bucket, _QUOTE_TEMPLATES["question"])
    detail_hash = hashlib.sha256(detail.encode("utf-8")).hexdigest()[:8]
    seed_str = f"{agent_id}:{round_num}:{bucket}:{detail_hash}"
    seed_int = int(hashlib.sha256(seed_str.encode("utf-8")).hexdigest(), 16)
    idx = seed_int % len(pool)
    return pool[idx]


# ---------------------------------------------------------------------------
# Engagement helpers
# ---------------------------------------------------------------------------

_LEGACY_BASE = 3
_LEGACY_INFLUENCE_SCALE = 7


def _legacy_formula(influence_weight: float, round_num: int) -> int:
    """Exact replica of LegacySimulationKernel._formula."""
    return max(1, min(10, int(round(_LEGACY_BASE + influence_weight * _LEGACY_INFLUENCE_SCALE + round_num))))


# ---------------------------------------------------------------------------
# HybridSimulationKernel
# ---------------------------------------------------------------------------


class HybridSimulationKernel(SimulationKernelAdapter):
    """Preserve-first kernel that augments the legacy deterministic path with
    ``PropagationState``-driven adjustments.

    Base behaviour (no prior_state or no threshold triggers) is identical to
    :class:`LegacySimulationKernel`.  When *prior_state* carries counters
    past their thresholds the engine applies bounded attitude/bucket shifts,
    engagement dampening/boosting, and deterministic quote variety.
    """

    # -- public API ---------------------------------------------------------

    def generate_response(
        self,
        round_num: int,
        agent_traits: Mapping[str, Any],
        visible_nodes: List[Mapping[str, Any]],
        prior_state: Optional[Mapping[str, Any]] = None,
    ) -> SimulationKernelResult:
        influence_weight = float(agent_traits.get("influence_weight", 0.5))

        # --- 1. Base path: mirror legacy exactly --------------------------
        risk_nodes = [n for n in visible_nodes if n["type"] == "RiskPoint"]
        talking_nodes = [n for n in visible_nodes if n["type"] != "RiskPoint"]

        if risk_nodes:
            detail = risk_nodes[0]["text"]
            base_attitude, base_bucket = "negative", "risk"
        elif round_num >= 1 and talking_nodes:
            detail = talking_nodes[0]["text"]
            herd = str(agent_traits.get("herd_tendency", "medium")).strip().lower()
            if herd == "high":
                base_attitude, base_bucket = "positive", "resonance"
            else:
                base_attitude, base_bucket = "neutral", "question"
        elif talking_nodes:
            detail = talking_nodes[0]["text"]
            base_attitude, base_bucket = "positive", "resonance"
        else:
            detail = ""
            base_attitude, base_bucket = "neutral", "question"

        # --- 2. Prior-state threshold adjustments -------------------------
        attitude_label = base_attitude
        bucket = base_bucket

        if prior_state:
            cumulative_risk = int(prior_state.get("cumulative_risk_exposure", 0))
            social_reinf = int(prior_state.get("social_reinforcement_count", 0))
            prop_only = int(prior_state.get("rounds_seen_propagation_only", 0))

            # cumulative_risk_exposure >= 2: push neutral/positive -> negative/risk
            if cumulative_risk >= 2 and attitude_label in ("neutral", "positive"):
                attitude_label = "negative"
                bucket = "risk"

            # social_reinforcement_count >= 3: push neutral -> positive/resonance
            if social_reinf >= 3 and attitude_label == "neutral":
                attitude_label = "positive"
                bucket = "resonance"

            # rounds_seen_propagation_only >= 3: neutral/question -> neutral/misread
            if prop_only >= 3 and attitude_label == "neutral" and bucket == "question":
                bucket = "misread"

        # --- 3. Engagement (with prior-state dampen/boost) -----------------
        engagement = self.compute_engagement(influence_weight, round_num, prior_state)

        # --- 4. Quote generation -------------------------------------------
        if prior_state is None:
            # Legacy path: exact same quote strings as LegacySimulationKernel.
            if bucket == "risk":
                quote = f"I keep thinking about {detail}, so the claim starts to feel less trustworthy."
            elif bucket == "resonance":
                herd = str(agent_traits.get("herd_tendency", "medium")).strip().lower()
                if round_num >= 1 and herd == "high":
                    quote = f"People would probably keep sharing {detail}, and that makes the idea feel credible."
                else:
                    quote = f"This actually sounds like a practical fix because of {detail}."
            else:
                quote = "I keep seeing " + detail + ", but I still want more proof before I fully buy in." if detail else "I understand the pitch, but I need more concrete proof before reacting strongly."
        else:
            # Template-pool variation path with deterministic seeding.
            agent_id = str(prior_state.get("agent_id") or agent_traits.get("agent_id", "anon"))
            quote_tpl = _select_template(bucket, agent_id, round_num, detail)
            quote = quote_tpl.format(detail=detail) if detail else quote_tpl.replace(" {detail}", "")

        return SimulationKernelResult(
            attitude_label=attitude_label,
            bucket=bucket,
            quote=quote,
            engagement=engagement,
        )

    def compute_engagement(
        self,
        influence_weight: float,
        round_num: int,
        prior_state: Optional[Mapping[str, Any]] = None,
    ) -> int:
        base = _legacy_formula(influence_weight, round_num)

        if prior_state is None:
            return base

        # Dampen by cumulative risk exposure (-1 per 2 exposure units)
        cumulative_risk = int(prior_state.get("cumulative_risk_exposure", 0))
        if cumulative_risk >= 2:
            base -= cumulative_risk // 2

        # Boost by social reinforcement (+1 per 3 reinforcements)
        social_reinf = int(prior_state.get("social_reinforcement_count", 0))
        if social_reinf >= 3:
            base += social_reinf // 3

        return max(1, min(10, base))
