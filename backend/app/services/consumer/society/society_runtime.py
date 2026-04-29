"""Deterministic consumer society runtime bridge."""

from __future__ import annotations

import os
from typing import Any, Dict, Iterable, List, Mapping

from .budget_manager import SocietyBudgetManager
from .channel_runtime import ConsumerChannelRuntime
from .event_mapper import ConsumerSocietyEventMapper
from .metrics_aggregator import SocietyMetricsAggregator
from .persona_quality_checker import PersonaQualityChecker
from .population_factory import PopulationFactory
from .population_models import ConsumerSocietyAgent, ConsumerSocietyRunConfig, ConsumerSocietySnapshot
from .reasoning_engine import LayeredSocietyReasoningEngine
from .report_adapter import SocietyReportAdapter
from .state_store import SocietyStateStore


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
        population = self.population_factory.build_population(persona_pack, config)
        self.quality_checker.validate(population, config)
        budget = SocietyBudgetManager(config, population_size=len(population))

        all_events: List[Dict[str, Any]] = []
        snapshots: List[ConsumerSocietySnapshot] = []
        claims = brief_context.get("claims", []) if isinstance(brief_context, Mapping) else []
        if not isinstance(claims, list):
            claims = [str(claims)]

        for round_index in range(config.max_rounds):
            round_events: List[Dict[str, Any]] = []
            for agent in population:
                event = self.event_mapper.map_agent_event(
                    agent=agent,
                    round_index=round_index,
                    visible_claims=claims,
                    previous_events=all_events,
                    brief_context=brief_context,
                    research_findings=research_findings,
                )
                reasoning_mode = self._reasoning_mode_for_layer(agent.layer)
                if reasoning_mode is None:
                    event["reasoning_layer"] = agent.layer
                    event["reasoning_method"] = "rule_state_machine"
                    event["reasoning_backend"] = "rules"
                    event["llm_invoked"] = False
                elif budget.record_llm_call(agent.layer):
                    event = self.reasoning_engine.reason(
                        agent=agent,
                        base_event=event,
                        brief_context=brief_context,
                        research_findings=research_findings,
                        reasoning_mode=reasoning_mode,
                    )
                else:
                    event["reasoning_layer"] = agent.layer
                    event["reasoning_method"] = "rule_fallback_budget_exhausted"
                    event["reasoning_backend"] = "rules"
                    event["llm_invoked"] = False
                self._update_agent_state(agent, event)
                round_events.append(event)

            all_events.extend(round_events)
            metrics = self.metrics_aggregator.aggregate(
                all_events,
                population_size=len(population),
                segments_count=len({agent.segment for agent in population}),
            )
            snapshots.append(
                ConsumerSocietySnapshot(
                    simulation_id=simulation_id,
                    run_id=run_id,
                    round_index=round_index,
                    agents_count=len(population),
                    events=round_events,
                    metrics=metrics,
                    representative_agent_ids=[agent.agent_id for agent in population[: config.audit_sample_size]],
                )
            )

        final_metrics = snapshots[-1].metrics if snapshots else {}
        channel_result = self.channel_runtime.run(
            population=population,
            society_events=all_events,
            mode=config.mode,
            enabled_channels=config.enabled_channels,
            seed=config.channel_seed or config.random_seed,
        )
        config_to_write = ConsumerSocietyRunConfig(**config.to_dict())
        config_payload = config_to_write.to_dict()
        backend_counts: Dict[str, int] = {}
        llm_invoked_count = 0
        for event in all_events:
            backend = str(event.get("reasoning_backend", "unknown") or "unknown")
            backend_counts[backend] = backend_counts.get(backend, 0) + 1
            if event.get("llm_invoked"):
                llm_invoked_count += 1
        config_payload["llm_budget_used"] = budget.used_llm_calls
        config_payload["reasoning_backend_counts"] = backend_counts
        config_payload["llm_invoked_count"] = llm_invoked_count
        config_payload["reasoning_calibration_status"] = os.environ.get(
            "SOCIETY_GOLDEN_CASE_CALIBRATION_STATUS",
            "golden_case_not_run",
        )

        self.store.write_population(simulation_id, population)
        self.store.write_config(simulation_id, config_to_write)
        config_path = self.store.society_dir(simulation_id) / "society_config.json"
        config_path.write_text(
            __import__("json").dumps(config_payload, ensure_ascii=False, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        self.store.write_rounds(simulation_id, snapshots)
        self.store.write_metrics(simulation_id, final_metrics)
        self.store.write_channel_assignments(simulation_id, channel_result["assignments"])
        self.store.write_channel_events(simulation_id, channel_result["events"])
        self.store.write_channel_metrics(simulation_id, channel_result["channel_metrics"])
        self.store.write_propagation_paths(simulation_id, channel_result["propagation_paths"])

        return SocietyReportAdapter(base_dir=self.store.base_dir).build_report_context(simulation_id)

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


__all__ = ["ConsumerSocietyRuntime"]
