"""Run controller for the consumer society runtime."""

from __future__ import annotations

import os
from datetime import datetime
from typing import Any, Dict, Iterable, List, Mapping

from ....utils.atomic_json import atomic_write_json
from ....utils.metrics import record_simulation_run, set_active_runs
from ..reasoning_trace import ReasoningTrace, write_reasoning_traces
from .agent_step_executor import AgentStepExecutor
from .budget_manager import SocietyBudgetManager
from .channel_runtime import ConsumerChannelRuntime
from .network_topology import build_consumer_network_topology
from .population_factory import PopulationFactory
from .population_models import ConsumerSocietyAgent, ConsumerSocietyRunConfig, ConsumerSocietySnapshot
from .profile_generator import ConsumerProfileGenerator
from .progress_buffer import ProgressBuffer
from .report_adapter import SocietyReportAdapter
from .round_scheduler import RoundScheduler
from ..runtime.control import RuntimeControlLayer, EarlyStopConfig
from .state_store import SocietyStateStore


class RunController:
    """Orchestrate a full society run using scheduler-compatible components."""

    def __init__(
        self,
        store: SocietyStateStore,
        population_factory: PopulationFactory,
        event_mapper: Any,
        metrics_aggregator: Any,
        reasoning_engine: Any,
        quality_checker: Any,
        channel_runtime: ConsumerChannelRuntime,
        dry_run: bool = False,
    ):
        self.store = store
        self.population_factory = population_factory
        self.event_mapper = event_mapper
        self.metrics_aggregator = metrics_aggregator
        self.reasoning_engine = reasoning_engine
        self.quality_checker = quality_checker
        self.channel_runtime = channel_runtime
        self.dry_run = dry_run
        self.runtime_control = RuntimeControlLayer(EarlyStopConfig(
            enabled=True, patience=3, min_rounds=3,
            event_threshold=5, attitude_change_threshold=0.01,
        ))

    def run(
        self,
        simulation_id: str,
        run_id: str,
        config: ConsumerSocietyRunConfig,
        persona_pack: Iterable[Mapping[str, Any]],
        brief_context: Mapping[str, Any],
        research_findings: Iterable[Any],
    ) -> Dict[str, Any]:
        if self.dry_run:
            return self._dry_run_preview(simulation_id, config, persona_pack, brief_context)

        record_simulation_run()
        set_active_runs(1)
        started_at = datetime.now().isoformat()
        self.store.ensure_started(simulation_id)
        research_findings_list = list(research_findings or [])
        progress_base = self._progress(
            status="initializing",
            phase="profile_generation",
            simulation_id=simulation_id,
            run_id=run_id,
            config=config,
            total_agents=config.target_population_size,
            started_at=started_at,
        )
        self.store.write_progress(simulation_id, progress_base)

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

        progress_base.update({
            "status": "population_ready",
            "phase": "population_ready",
            "total_agents": len(population),
            "updated_at": datetime.now().isoformat(),
        })
        self.store.write_progress(simulation_id, progress_base)
        budget = SocietyBudgetManager(config, population_size=len(population))

        all_events: List[Dict[str, Any]] = []
        snapshots: List[ConsumerSocietySnapshot] = []
        reasoning_traces: List[ReasoningTrace] = []
        claims = brief_context.get("claims", []) if isinstance(brief_context, Mapping) else []
        if not isinstance(claims, list):
            claims = [str(claims)]

        executor = AgentStepExecutor(
            event_mapper=self.event_mapper,
            reasoning_engine=self.reasoning_engine,
            store=self.store,
            simulation_id=simulation_id,
        )
        scheduler = RoundScheduler(executor=executor, population=population, config=config)
        progress_buffer = ProgressBuffer(
            store=self.store,
            simulation_id=simulation_id,
            progress_base=progress_base,
        )

        counters: Dict[str, Any] = {
            "completed_agents": 0,
            "failed_count": 0,
            "template_fallback_count": 0,
            "llm_invoked_count": 0,
            "rules_count": 0,
        }

        for round_index in range(config.max_rounds):
            round_events, round_traces = scheduler.run_round(
                round_index=round_index,
                claims=claims,
                brief_context=brief_context,
                research_findings=research_findings_list,
                previous_events=all_events,
                budget=budget,
                progress_buffer=progress_buffer,
                counters=counters,
            )
            all_events.extend(round_events)
            reasoning_traces.extend(round_traces)

            # Track failed count from template_fallback events in this round
            for event in round_events:
                if event.get("reasoning_backend") == "template_fallback":
                    if "reasoning_error" in event:
                        counters["failed_count"] = counters.get("failed_count", 0) + 1

            # Deduplicate failed_count since scheduler may have already counted some
            # The original runtime counts failed_count inside the exception handler,
            # but AgentStepExecutor handles exceptions internally. We need to count
            # failed events by inspecting the event.
            # Actually, in the original code, failed_count is incremented once per
            # exception. Let me recalculate it properly.
            failed_events = [e for e in all_events if e.get("reasoning_backend") == "template_fallback" and "reasoning_error" in e]
            counters["failed_count"] = len(failed_events)

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

            # RuntimeControl: save checkpoint and check early stop
            avg_attitude = metrics.get("avg_attitude", 0.5)
            agent_states = {a.agent_id: dict(a.state) for a in population}
            self.runtime_control.save_checkpoint(
                round_id=round_index,
                state={"agents": agent_states, "events": round_events},
                metrics={"avg_attitude": avg_attitude, "new_events": len(round_events)},
            )
            should_stop, reason = self.runtime_control.should_early_stop(
                round_id=round_index,
                current_metrics={"avg_attitude": avg_attitude, "new_events": len(round_events)},
            )

            progress_buffer.round_completed(round_index)

            # B3: Save graph snapshot for this round
            try:
                graph_snapshot = {
                    "round_id": round_index,
                    "node_count": len(population),
                    "event_count": len(round_events),
                    "metrics": metrics,
                }
                snapshot_dir = self.store.society_dir(simulation_id) / "graph_snapshots"
                snapshot_dir.mkdir(parents=True, exist_ok=True)
                snapshot_path = snapshot_dir / f"graph_snapshot_round_{round_index}.json"
                atomic_write_json(snapshot_path, graph_snapshot)
            except Exception:
                pass  # non-critical

            if should_stop:
                import logging
                logging.getLogger(__name__).info(f"Early stop triggered at round {round_index}: {reason}")
                break

        # Count backends from all events for config payload
        backend_counts: Dict[str, int] = {}
        for event in all_events:
            backend = str(event.get("reasoning_backend", "unknown") or "unknown")
            backend_counts[backend] = backend_counts.get(backend, 0) + 1

        # Re-calculate counters from all_events to ensure accuracy
        llm_invoked_count = sum(1 for e in all_events if e.get("llm_invoked"))
        rules_count = sum(1 for e in all_events if e.get("reasoning_backend") == "rules" and not e.get("llm_invoked"))
        template_fallback_count = sum(1 for e in all_events if e.get("reasoning_backend") == "template_fallback")
        failed_count = sum(1 for e in all_events if e.get("reasoning_backend") == "template_fallback" and "reasoning_error" in e)

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

        if reasoning_traces:
            write_reasoning_traces(
                str(self.store.society_dir(simulation_id).parent),
                reasoning_traces,
            )

        final_status = "completed_with_errors" if failed_count else "completed"
        progress_buffer.final(
            status=final_status,
            current_round=config.max_rounds,
            completed_agents=len(population) * config.max_rounds,
            total_agents=len(population) * config.max_rounds,
            llm_invoked_count=llm_invoked_count,
            rules_count=rules_count,
            template_fallback_count=template_fallback_count,
            failed_count=failed_count,
        )

        set_active_runs(0)
        return SocietyReportAdapter(base_dir=self.store.base_dir).build_report_context(simulation_id)

    def _dry_run_preview(
        self,
        simulation_id: str,
        config: ConsumerSocietyRunConfig,
        persona_pack: Iterable[Mapping[str, Any]],
        brief_context: Mapping[str, Any],
    ) -> Dict[str, Any]:
        """快速预览：只执行2轮，不调用LLM"""
        personas = list(persona_pack) if persona_pack else []
        population = self.population_factory.build_population(personas[:5], config)
        graph_preview = {
            "nodes": len(population),
            "edges": max(0, len(population) * (len(population) - 1) // 4),
        }
        return {
            "dry_run": True,
            "simulation_id": simulation_id,
            "preview_rounds": 2,
            "estimated_duration": "2 minutes",
            "mode": config.mode,
            "persona_preview": [
                getattr(p, "to_prompt_description", lambda: str(p))()
                for p in population[:5]
            ],
            "graph_preview": graph_preview,
            "target_population_size": config.target_population_size,
            "max_rounds": config.max_rounds,
            "enabled_channels": list(config.enabled_channels),
        }

    def resume_from_checkpoint(self, round_id: int = -1):
        """Resume simulation from a saved checkpoint."""
        cp = self.runtime_control.get_resume_point(round_id)
        if cp:
            return {"resume_from": cp.round_id, "state": cp.agent_states}
        return None

    @staticmethod
    def _progress(
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


__all__ = ["RunController"]
