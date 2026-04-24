"""Legacy deterministic simulation kernel.

Ports today's ``ConsumerSimulationOrchestrator._generate_response`` and
engagement formula byte-for-byte so that the orchestrator can delegate to
this kernel without changing observable behaviour.
"""

from __future__ import annotations

from typing import Any, List, Mapping, Optional

from .kernel_adapter import SimulationKernelAdapter, SimulationKernelResult


class LegacySimulationKernel(SimulationKernelAdapter):
    """Deterministic kernel that mirrors the current orchestrator logic.

    ``prior_state`` is accepted for interface compatibility but ignored —
    the legacy kernel is stateless, exactly like the original code path.
    """

    @staticmethod
    def _formula(influence_weight: float, round_num: int) -> int:
        return max(1, min(10, int(round(3 + influence_weight * 7 + round_num))))

    def generate_response(
        self,
        round_num: int,
        agent_traits: Mapping[str, Any],
        visible_nodes: List[Mapping[str, Any]],
        prior_state: Optional[Mapping[str, Any]] = None,
    ) -> SimulationKernelResult:
        influence_weight = float(agent_traits.get("influence_weight", 0.5))
        engagement = self._formula(influence_weight, round_num)

        risk_nodes = [node for node in visible_nodes if node["type"] == "RiskPoint"]
        talking_nodes = [node for node in visible_nodes if node["type"] != "RiskPoint"]

        if risk_nodes:
            risk_text = risk_nodes[0]["text"]
            return SimulationKernelResult(
                attitude_label="negative",
                bucket="risk",
                quote=f"I keep thinking about {risk_text}, so the claim starts to feel less trustworthy.",
                engagement=engagement,
            )

        if round_num >= 1 and talking_nodes:
            topic_text = talking_nodes[0]["text"]
            herd_tendency = str(agent_traits.get("herd_tendency", "medium")).strip().lower()
            if herd_tendency == "high":
                return SimulationKernelResult(
                    attitude_label="positive",
                    bucket="resonance",
                    quote=f"People would probably keep sharing {topic_text}, and that makes the idea feel credible.",
                    engagement=engagement,
                )
            return SimulationKernelResult(
                attitude_label="neutral",
                bucket="question",
                quote=f"I keep seeing {topic_text}, but I still want more proof before I fully buy in.",
                engagement=engagement,
            )

        if talking_nodes:
            topic_text = talking_nodes[0]["text"]
            return SimulationKernelResult(
                attitude_label="positive",
                bucket="resonance",
                quote=f"This actually sounds like a practical fix because of {topic_text}.",
                engagement=engagement,
            )

        return SimulationKernelResult(
            attitude_label="neutral",
            bucket="question",
            quote="I understand the pitch, but I need more concrete proof before reacting strongly.",
            engagement=engagement,
        )

    def compute_engagement(
        self,
        influence_weight: float,
        round_num: int,
        prior_state: Optional[Mapping[str, Any]] = None,
    ) -> int:
        return self._formula(influence_weight, round_num)
