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
from .state_store import SocietyStateStore
from ....utils.atomic_json import atomic_write_json


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
        started_at = datetime.now().isoformat()
        self.store.ensure_started(simulation_id)
        research_findings_list = list(research_findings or [])
        progress = self._progress(
            status="initializing",
            phase="profile_generation",
            simulation_id=simulation_id,
            run_id=run_id,
            config=config,
            total_agents=config.target_population_size,
            started_at=started_at,
        )
        self.store.write_progress(simulation_id, progress)

        profile_snapshot = self.store.read_profile_snapshot(simulation_id)
        if not profile_snapshot:
            generator = ConsumerProfileGenerator(seed=config.random_seed, enable_llm_enrichment=False)
            profile_snapshot = generator.build_snapshot(
                brief=brief_context or {},
                enabled_channels=config.enabled_channels,
                count=max(1, config.core_persona_count),
                research_findings=research_findings_list,
            )
            self.store.write_profile_snapshot(simulation_id, profile_snapshot)
            generator.adapter.export_oasis_profiles(
                profile_snapshot.get("profiles", []),
                self.store.society_dir(simulation_id) / "oasis_profiles",
            )

        personas = profile_snapshot.get("profiles") or list(persona_pack)
        population = self.population_factory.build_population(personas, config)
        self.quality_checker.validate(population, config)
        self.store.write_population(simulation_id, population)

        progress.update({
            "status": "population_ready",
            "phase": "population_ready",
            "total_agents": len(population),
            "updated_at": datetime.now().isoformat(),
        })
        self.store.write_progress(simulation_id, progress)
        budget = SocietyBudgetManager(config, population_size=len(population))

        all_events: List[Dict[str, Any]] = []
        snapshots: List[ConsumerSocietySnapshot] = []
        failed_count = 0
        template_fallback_count = 0
        llm_invoked_count = 0
        rules_count = 0
        claims = brief_context.get("claims", []) if isinstance(brief_context, Mapping) else []
        if not isinstance(claims, list):
            claims = [str(claims)]

        for round_index in range(config.max_rounds):
            round_events: List[Dict[str, Any]] = []
            for agent_index, agent in enumerate(population):
                event = self.event_mapper.map_agent_event(
                    agent=agent,
                    round_index=round_index,
                    visible_claims=claims,
                    previous_events=all_events,
                    brief_context=brief_context,
                    research_findings=research_findings_list,
                )
                reasoning_mode = self._reasoning_mode_for_layer(agent.layer)
                if reasoning_mode is None:
                    event["reasoning_layer"] = agent.layer
                    event["reasoning_method"] = "rule_state_machine"
                    event["reasoning_backend"] = "rules"
                    event["llm_invoked"] = False
                    rules_count += 1
                elif budget.record_llm_call(agent.layer):
                    try:
                        event = self.reasoning_engine.reason(
                            agent=agent,
                            base_event=event,
                            brief_context=brief_context,
                            research_findings=research_findings_list,
                            reasoning_mode=reasoning_mode,
                        )
                    except Exception as exc:
                        failed_count += 1
                        template_fallback_count += 1
                        event = self._failed_reasoning_event(agent, event, reasoning_mode, exc)
                        self.store.append_runtime_event(
                            simulation_id,
                            {
                                "event_type": "agent_reasoning_failed",
                                "agent_id": agent.agent_id,
                                "round_index": round_index,
                                "error_type": type(exc).__name__,
                                "error": str(exc),
                                "fallback": "template_fallback",
                            },
                        )
                        self.store.append_error(
                            simulation_id,
                            {
                                "event_type": "agent_reasoning_failed",
                                "agent_id": agent.agent_id,
                                "round_index": round_index,
                                "error_type": type(exc).__name__,
                                "error": str(exc),
                            },
                        )
                else:
                    event["reasoning_layer"] = agent.layer
                    event["reasoning_method"] = "rule_fallback_budget_exhausted"
                    event["reasoning_backend"] = "rules"
                    event["llm_invoked"] = False
                    rules_count += 1
                if event.get("llm_invoked"):
                    llm_invoked_count += 1
                if event.get("reasoning_backend") == "template_fallback":
                    template_fallback_count += 1
                self._update_agent_state(agent, event)
                round_events.append(event)
                completed_agents = (round_index * len(population)) + agent_index + 1
                progress.update(
                    {
                        "status": "running",
                        "phase": "agent_reasoning",
                        "current_round": round_index,
                        "completed_agents": completed_agents,
                        "total_agents": len(population) * config.max_rounds,
                        "current_agent_id": agent.agent_id,
                        "current_layer": agent.layer,
                        "reasoning_backend": event.get("reasoning_backend", "unknown"),
                        "llm_invoked_count": llm_invoked_count,
                        "rules_count": rules_count,
                        "template_fallback_count": template_fallback_count,
                        "failed_count": failed_count,
                        "updated_at": datetime.now().isoformat(),
                    }
                )
                self.store.write_progress(simulation_id, progress)
                self.store.append_runtime_event(
                    simulation_id,
                    {
                        "event_type": "agent_completed",
                        "agent_id": agent.agent_id,
                        "round_index": round_index,
                        "reasoning_backend": event.get("reasoning_backend", "unknown"),
                    },
                )

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
            self.store.write_round_snapshot(simulation_id, snapshots[-1])
            progress.update(
                {
                    "status": "round_completed",
                    "phase": "round_completed",
                    "current_round": round_index + 1,
                    "updated_at": datetime.now().isoformat(),
                }
            )
            self.store.write_progress(simulation_id, progress)

        final_metrics = snapshots[-1].metrics if snapshots else {}
        channel_result = self.channel_runtime.run(
            population=population,
            society_events=all_events,
            mode=config.mode,
            enabled_channels=config.enabled_channels,
            seed=config.channel_seed or config.random_seed,
        )
        network_topology = build_consumer_network_topology(
            population,
            channel_assignments=channel_result["assignments"],
            seed=config.random_seed,
        )
        config_to_write = ConsumerSocietyRunConfig(**config.to_dict())
        config_payload = config_to_write.to_dict()
        backend_counts: Dict[str, int] = {}
        for event in all_events:
            backend = str(event.get("reasoning_backend", "unknown") or "unknown")
            backend_counts[backend] = backend_counts.get(backend, 0) + 1
        config_payload["llm_budget_used"] = budget.used_llm_calls
        config_payload["reasoning_backend_counts"] = backend_counts
        config_payload["llm_invoked_count"] = llm_invoked_count
        config_payload["network_topology_version"] = network_topology.get("topology_version", "")
        config_payload["reasoning_calibration_status"] = os.environ.get(
            "SOCIETY_GOLDEN_CASE_CALIBRATION_STATUS",
            "golden_case_not_run",
        )

        self.store.write_config(simulation_id, config_to_write)
        config_path = self.store.society_dir(simulation_id) / "society_config.json"
        atomic_write_json(config_path, config_payload)
        self.store.write_rounds(simulation_id, snapshots)
        self.store.write_metrics(simulation_id, final_metrics)
        self.store.write_channel_assignments(simulation_id, channel_result["assignments"])
        self.store.write_channel_events(simulation_id, channel_result["events"])
        self.store.write_channel_metrics(simulation_id, channel_result["channel_metrics"])
        self.store.write_propagation_paths(simulation_id, channel_result["propagation_paths"])
        self.store.write_network_topology(simulation_id, network_topology)
        progress.update(
            {
                "status": "completed_with_errors" if failed_count else "completed",
                "phase": "completed",
                "current_round": config.max_rounds,
                "completed_agents": len(population) * config.max_rounds,
                "total_agents": len(population) * config.max_rounds,
                "llm_invoked_count": llm_invoked_count,
                "rules_count": rules_count,
                "template_fallback_count": template_fallback_count,
                "failed_count": failed_count,
                "updated_at": datetime.now().isoformat(),
            }
        )
        self.store.write_progress(simulation_id, progress)

        return SocietyReportAdapter(base_dir=self.store.base_dir).build_report_context(simulation_id)

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


__all__ = ["ConsumerSocietyRuntime"]
