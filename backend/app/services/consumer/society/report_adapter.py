"""Adapt society runtime artifacts into consumer report context."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Mapping

from .channel_report_adapter import ChannelReportAdapter
from .state_store import SocietyStateStore
from ..research_boundary import default_applicability_boundary


EMPTY_SOCIETY_CONTEXT = {
    "society_mode": "quick",
    "society_agents_count": 0,
    "society_rounds_completed": 0,
    "society_llm_budget_used": 0,
    "society_metrics": {},
    "representative_agents": [],
    "society_event_summary": {},
    "society_risk_summary": {},
    "society_purchase_intent_summary": {},
    "society_reasoning_summary": {
        "backend_counts": {},
        "llm_invoked_count": 0,
        "calibration_status": "golden_case_not_run",
        "production_readiness": "requires_golden_case_calibration",
    },
    "society_network_summary": {},
}


class SocietyReportAdapter:
    """Build and merge society context for ReportAgent."""

    def __init__(self, base_dir: str | Path | None = None):
        self.store = SocietyStateStore(base_dir=base_dir)

    def build_report_context(self, simulation_id: str) -> Dict[str, Any]:
        config = self.store.read_config(simulation_id)
        metrics = self.store.read_metrics(simulation_id)
        population = self.store.read_population(simulation_id)
        rounds = self.store.read_rounds(simulation_id)
        network_topology = self.store.read_network_topology(simulation_id)
        research_boundary = self.store.read_research_boundary(simulation_id) or default_applicability_boundary()
        channel_context = ChannelReportAdapter(base_dir=self.store.base_dir).build_report_context(simulation_id)
        if not config and not metrics and not population:
            return {
                **dict(EMPTY_SOCIETY_CONTEXT),
                "applicability_boundary": research_boundary,
                **channel_context,
            }

        event_summary: Dict[str, int] = {}
        backend_counts: Dict[str, int] = dict(config.get("reasoning_backend_counts", {}) or {})
        llm_invoked_count = int(config.get("llm_invoked_count", 0) or 0)
        should_count_backends_from_rounds = not backend_counts
        should_count_llm_invocations_from_rounds = "llm_invoked_count" not in config
        for snapshot in rounds:
            for event in snapshot.get("events", []):
                event_type = event.get("consumer_event_type", "")
                if event_type:
                    event_summary[event_type] = event_summary.get(event_type, 0) + 1
                if should_count_backends_from_rounds:
                    backend = str(event.get("reasoning_backend", "unknown") or "unknown")
                    backend_counts[backend] = backend_counts.get(backend, 0) + 1
                if should_count_llm_invocations_from_rounds and event.get("llm_invoked"):
                    llm_invoked_count += 1

        calibration_status = str(config.get("reasoning_calibration_status", "golden_case_not_run"))
        production_readiness = (
            "ready_for_calibrated_reporting"
            if calibration_status == "golden_case_passed"
            else "requires_golden_case_calibration"
        )

        context = {
            "society_mode": config.get("mode", "quick"),
            "society_agents_count": len(population),
            "society_rounds_completed": len(rounds),
            "society_llm_budget_used": config.get("llm_budget_used", 0),
            "society_metrics": metrics,
            "representative_agents": self._representative_agents(population),
            "society_event_summary": event_summary,
            "society_risk_summary": {
                "misread_rate": metrics.get("misread_rate", 0.0),
                "negative_cascade_probability": metrics.get("negative_cascade_probability", 0.0),
                "trust_decay_rate": metrics.get("trust_decay_rate", 0.0),
            },
            "society_purchase_intent_summary": {
                "purchase_intent_delta": metrics.get("purchase_intent_delta", 0.0),
                "price_resistance_index": metrics.get("price_resistance_index", 0.0),
            },
            "society_reasoning_summary": {
                "backend_counts": backend_counts,
                "llm_invoked_count": llm_invoked_count,
                "calibration_status": calibration_status,
                "production_readiness": production_readiness,
            },
            "society_network_summary": {
                "topology_version": network_topology.get("topology_version", ""),
                "node_count": network_topology.get("node_count", 0),
                "edge_count": network_topology.get("edge_count", 0),
                "graphs": {
                    key: len(value)
                    for key, value in dict(network_topology.get("graphs", {}) or {}).items()
                },
            },
            "applicability_boundary": research_boundary,
        }
        context.update(channel_context)
        return context

    def merge_into_context(
        self,
        context: Mapping[str, Any],
        society_context: Mapping[str, Any],
    ) -> Dict[str, Any]:
        merged = dict(context)
        merged.update(dict(society_context))
        return merged

    def _representative_agents(self, population: list[dict]) -> list[str]:
        return [str(agent.get("agent_id", "")) for agent in population[:8] if agent.get("agent_id")]


__all__ = ["EMPTY_SOCIETY_CONTEXT", "SocietyReportAdapter"]
