"""Deterministic consumer society runtime bridge."""

from __future__ import annotations

import os
from datetime import datetime
from typing import Any, Dict, Iterable, List, Mapping

from .budget_manager import SocietyBudgetManager
from .channel_runtime import ConsumerChannelRuntime
from .event_mapper import ConsumerSocietyEventMapper
from .metrics_aggregator import SocietyMetricsAggregator
from .network_topology import build_consumer_network_topology
from .persona_quality_checker import PersonaQualityChecker
from .population_factory import PopulationFactory
from .population_models import ConsumerSocietyAgent, ConsumerSocietyRunConfig, ConsumerSocietySnapshot
from .profile_generator import ConsumerProfileGenerator
from .reasoning_engine import LayeredSocietyReasoningEngine
from .report_adapter import SocietyReportAdapter
from .run_controller import RunController
from ..research_boundary import enforce_research_boundary
from .state_store import SocietyStateStore
from ....utils.atomic_json import atomic_write_json
from ..reasoning_trace import ReasoningTrace, write_reasoning_traces


class ConsumerSocietyRuntime:
    """Run Phase 6G society simulation without exposing OASIS internals."""

    def __init__(
        self,
        base_dir: str | os.PathLike | None = None,
        population_factory: PopulationFactory | None = None,
        event_mapper: ConsumerSocietyEventMapper | None = None,
        metrics_aggregator: SocietyMetricsAggregator | None = None,
        reasoning_engine: LayeredSocietyReasoningEngine | None = None,
    ):
        self.store = SocietyStateStore(base_dir=base_dir)
        self.population_factory = population_factory or PopulationFactory()
        self.event_mapper = event_mapper or ConsumerSocietyEventMapper()
        self.metrics_aggregator = metrics_aggregator or SocietyMetricsAggregator()
        self.reasoning_engine = reasoning_engine or LayeredSocietyReasoningEngine()
        self.quality_checker = PersonaQualityChecker()
        self.channel_runtime = ConsumerChannelRuntime()

    def run(
        self,
        simulation_id: str,
        run_id: str,
        config: ConsumerSocietyRunConfig,
        persona_pack: Iterable[Mapping[str, Any]],
        brief_context: Mapping[str, Any],
        research_findings: Iterable[Any],
    ) -> Dict[str, Any]:
        persona_pack_list = list(persona_pack or [])
        boundary = enforce_research_boundary(
            simulation_id=simulation_id,
            brief_context=brief_context,
            persona_pack=persona_pack_list,
        )
        self.store.ensure_started(simulation_id)
        self.store.write_research_boundary(simulation_id, boundary)
        controller = RunController(
            store=self.store,
            population_factory=self.population_factory,
            event_mapper=self.event_mapper,
            metrics_aggregator=self.metrics_aggregator,
            reasoning_engine=self.reasoning_engine,
            quality_checker=self.quality_checker,
            channel_runtime=self.channel_runtime,
        )
        return controller.run(
            simulation_id=simulation_id,
            run_id=run_id,
            config=config,
            persona_pack=persona_pack_list,
            brief_context=brief_context,
            research_findings=research_findings,
        ) | {"applicability_boundary": boundary}

    def _progress(
        self,
        *,
        status: str,
        phase: str,
        simulation_id: str,
        run_id: str,
        config: ConsumerSocietyRunConfig,
        total_agents: int,
        started_at: str,
    ) -> Dict[str, Any]:
        now = datetime.now().isoformat()
        return {
            "status": status,
            "phase": phase,
            "simulation_id": simulation_id,
            "run_id": run_id,
            "mode": config.mode,
            "current_round": 0,
            "total_rounds": config.max_rounds,
            "completed_agents": 0,
            "total_agents": total_agents,
            "current_agent_id": "",
            "current_layer": "",
            "reasoning_backend": "",
            "llm_invoked_count": 0,
            "rules_count": 0,
            "template_fallback_count": 0,
            "failed_count": 0,
            "started_at": started_at,
            "updated_at": now,
        }

    def _failed_reasoning_event(
        self,
        agent: ConsumerSocietyAgent,
        base_event: Mapping[str, Any],
        reasoning_mode: str,
        exc: Exception,
    ) -> Dict[str, Any]:
        event = dict(base_event)
        event["reasoning_layer"] = agent.layer
        event["reasoning_method"] = reasoning_mode
        event["reasoning_backend"] = "template_fallback"
        event["llm_invoked"] = False
        event["reasoning_error"] = str(exc)
        event["quote"] = (
            f"{agent.segment}: 这条信息需要更多证据，我会先保留判断。"
        )
        return event

    def _update_agent_state(self, agent: ConsumerSocietyAgent, event: Mapping[str, Any]) -> None:
        event_type = event.get("consumer_event_type", "")
        trust = float(agent.state.get("trust", agent.trust_baseline))
        purchase = float(agent.state.get("purchase_intent", 0.5))
        if event_type in {"TRUST_DECAY", "ASK_PROOF", "MISREAD_CLAIM", "PRICE_RESISTANCE"}:
            trust -= 0.03 * agent.skepticism
            purchase -= 0.02 * agent.price_sensitivity
        if event_type in {"TRUST_RECOVERY", "AMPLIFY_CLAIM", "PURCHASE_INTENT_UP", "SHARE_TO_CHANNEL"}:
            trust += 0.03 * agent.evidence_sensitivity
            purchase += 0.02 * agent.share_propensity
        agent.state["trust"] = round(max(0.0, min(1.0, trust)), 4)
        agent.state["purchase_intent"] = round(max(0.0, min(1.0, purchase)), 4)
        agent.state["awareness"] = 1.0

    def _reasoning_mode_for_layer(self, layer: str) -> str | None:
        if layer == "core":
            return "llm_deep_reasoning"
        if layer == "expanded":
            return "lightweight_llm"
        if layer == "audit_sample":
            return "llm_audit_sample"
        return None

    def _trace_from_event(
        self,
        agent: ConsumerSocietyAgent,
        event: Mapping[str, Any],
        round_index: int,
    ) -> ReasoningTrace:
        """Create a ReasoningTrace from an agent event."""
        backend = str(event.get("reasoning_backend", "unknown") or "unknown")
        llm_invoked = bool(event.get("llm_invoked", False))
        reasoning_error = event.get("reasoning_error", "")
        quote = event.get("quote", "")
        perception_reasoning = "; ".join(
            part for part in [
                f"claim={event.get('claim', '')}" if event.get("claim") else "",
                f"agent_id={agent.agent_id}",
                f"segment={agent.segment}",
            ]
            if part
        )
        decision_reasoning = "; ".join(
            part for part in [
                f"backend={backend}",
                f"llm_invoked={llm_invoked}",
                f"reasoning_error={reasoning_error}" if reasoning_error else "",
            ]
            if part
        )
        expression_reasoning = f"quote={quote}" if quote else ""

        fallback_reason = ""
        if backend == "template_fallback" and reasoning_error:
            fallback_reason = str(reasoning_error)
        elif backend == "template_fallback":
            fallback_reason = "unknown"

        return ReasoningTrace(
            reasoning_backend=backend,
            llm_invoked=llm_invoked,
            source="society_runtime",
            fallback_reason=fallback_reason,
            model="",
            latency_ms=0.0,
            reasoning_summary=str(quote) if quote else "",
            perception_reasoning=perception_reasoning,
            decision_reasoning=decision_reasoning,
            expression_reasoning=expression_reasoning,
            reasoning_triplets=[
                {
                    "input": perception_reasoning,
                    "evidence": decision_reasoning,
                    "conclusion": str(quote) if quote else expression_reasoning,
                }
            ],
        )


__all__ = ["ConsumerSocietyRuntime"]
