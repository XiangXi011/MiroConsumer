"""Adapt society runtime artifacts into consumer report context."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Mapping

from .channel_report_adapter import ChannelReportAdapter
from .state_store import SocietyStateStore


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
        channel_context = ChannelReportAdapter(base_dir=self.store.base_dir).build_report_context(simulation_id)
        if not config and not metrics and not population:
            return {**dict(EMPTY_SOCIETY_CONTEXT), **channel_context}

        event_summary: Dict[str, int] = {}
        for snapshot in rounds:
            for event in snapshot.get("events", []):
                event_type = event.get("consumer_event_type", "")
                if event_type:
                    event_summary[event_type] = event_summary.get(event_type, 0) + 1

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
