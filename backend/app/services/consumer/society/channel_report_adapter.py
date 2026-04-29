"""Adapt Phase 6H channel artifacts into report context."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from .state_store import SocietyStateStore


EMPTY_CHANNEL_CONTEXT = {
    "channel_metrics": {},
    "channel_fit_scores": {},
    "channel_misread_summary": {},
    "channel_evidence_summary": {},
    "channel_price_summary": {},
    "cross_channel_paths": [],
}


class ChannelReportAdapter:
    """Build channel report context from persisted channel artifacts."""

    def __init__(self, base_dir: str | Path | None = None):
        self.store = SocietyStateStore(base_dir=base_dir)

    def build_report_context(self, simulation_id: str) -> Dict[str, Any]:
        metrics = self.store.read_channel_metrics(simulation_id)
        paths = self.store.read_propagation_paths(simulation_id)
        if not metrics and not paths:
            return dict(EMPTY_CHANNEL_CONTEXT)
        channels = metrics.get("channels", {}) if isinstance(metrics, dict) else {}
        return {
            "channel_metrics": metrics,
            "channel_fit_scores": {
                channel_id: values.get("fit_score", 0.0)
                for channel_id, values in channels.items()
            },
            "channel_misread_summary": {
                channel_id: values.get("misread_risk", 0.0)
                for channel_id, values in channels.items()
            },
            "channel_evidence_summary": {
                channel_id: values.get("evidence_demand", 0.0)
                for channel_id, values in channels.items()
            },
            "channel_price_summary": {
                channel_id: values.get("price_resistance", 0.0)
                for channel_id, values in channels.items()
            },
            "cross_channel_paths": paths,
        }


__all__ = ["EMPTY_CHANNEL_CONTEXT", "ChannelReportAdapter"]
