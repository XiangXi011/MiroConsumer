"""Convergence detection for consumer propagation rounds."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class ConvergenceConfig:
    """Thresholds used to stop stable consumer propagation runs early."""

    enabled: bool = True
    min_rounds: int = 3
    attitude_change_threshold: float = 0.02
    active_agent_ratio_threshold: float = 0.05


class ConvergenceDetector:
    """Evaluate round-to-round propagation convergence."""

    def __init__(
        self,
        attitude_change_threshold: float = 0.02,
        active_agent_ratio_threshold: float = 0.05,
        min_rounds: int = 3,
        enabled: bool = True,
    ):
        self.config = ConvergenceConfig(
            enabled=bool(enabled),
            min_rounds=max(0, int(min_rounds)),
            attitude_change_threshold=max(0.0, float(attitude_change_threshold)),
            active_agent_ratio_threshold=max(0.0, float(active_agent_ratio_threshold)),
        )

    def should_stop(
        self,
        round_index: int,
        current_state: Any,
        previous_state: Any,
    ) -> Dict[str, Any]:
        """Return convergence decision, reason, and metrics for a completed round."""
        current_snapshots = self._extract_snapshots(current_state)
        previous_snapshots = self._extract_snapshots(previous_state)
        current_distribution = self._attitude_distribution(current_snapshots)
        previous_distribution = self._attitude_distribution(previous_snapshots)
        attitude_change_rate = self._distribution_difference(
            current_distribution,
            previous_distribution,
        )
        active_agent_ratio, active_agent_count, total_agent_count, event_count = (
            self._active_agent_metrics(current_snapshots)
        )

        metrics: Dict[str, Any] = {
            "attitude_change_rate": round(attitude_change_rate, 6),
            "active_agent_ratio": round(active_agent_ratio, 6),
            "active_agent_count": active_agent_count,
            "total_agent_count": total_agent_count,
            "propagation_event_count": event_count,
            "current_attitude_distribution": current_distribution,
            "previous_attitude_distribution": previous_distribution,
        }

        if not self.config.enabled:
            return {"stop": False, "reason": "disabled", "metrics": metrics}

        completed_rounds = round_index + 1
        if completed_rounds < self.config.min_rounds:
            return {"stop": False, "reason": "min_rounds_not_met", "metrics": metrics}

        reasons: List[str] = []
        if previous_snapshots and attitude_change_rate <= self.config.attitude_change_threshold:
            reasons.append(
                "attitude_change_rate "
                f"{metrics['attitude_change_rate']} <= "
                f"{self.config.attitude_change_threshold}"
            )
        if active_agent_ratio <= self.config.active_agent_ratio_threshold:
            reasons.append(
                "active_agent_ratio "
                f"{metrics['active_agent_ratio']} <= "
                f"{self.config.active_agent_ratio_threshold}"
            )

        if reasons:
            return {
                "stop": True,
                "reason": "; ".join(reasons),
                "metrics": metrics,
            }

        return {"stop": False, "reason": "not_converged", "metrics": metrics}

    def _extract_snapshots(self, state: Any) -> List[Mapping[str, Any]]:
        if state is None:
            return []

        if isinstance(state, Mapping):
            for key in ("snapshots", "round_snapshots", "agents"):
                value = state.get(key)
                if value is None:
                    continue
                if isinstance(value, Mapping):
                    return [
                        item
                        for item in value.values()
                        if isinstance(item, Mapping)
                    ]
                return [
                    item
                    for item in self._iter_items(value)
                    if isinstance(item, Mapping)
                ]
            if "attitude_label" in state or "propagation_events" in state:
                return [state]
            return [
                item
                for item in state.values()
                if isinstance(item, Mapping)
            ]

        return [
            item
            for item in self._iter_items(state)
            if isinstance(item, Mapping)
        ]

    def _iter_items(self, value: Any) -> Iterable[Any]:
        if isinstance(value, (str, bytes)):
            return []
        if isinstance(value, Iterable):
            return value
        return []

    def _attitude_distribution(
        self,
        snapshots: List[Mapping[str, Any]],
    ) -> Dict[str, float]:
        labels: List[str] = []
        for snapshot in snapshots:
            label = snapshot.get("attitude_label")
            if label is None:
                label = snapshot.get("attitude")
            if label is None:
                continue
            normalized = str(label).strip()
            if normalized:
                labels.append(normalized)

        total = len(labels)
        if total == 0:
            return {}

        counts: Dict[str, int] = {}
        for label in labels:
            counts[label] = counts.get(label, 0) + 1

        return {
            label: round(count / total, 6)
            for label, count in sorted(counts.items())
        }

    def _distribution_difference(
        self,
        current_distribution: Mapping[str, float],
        previous_distribution: Mapping[str, float],
    ) -> float:
        labels = set(current_distribution) | set(previous_distribution)
        if not labels:
            return 0.0
        return 0.5 * sum(
            abs(current_distribution.get(label, 0.0) - previous_distribution.get(label, 0.0))
            for label in labels
        )

    def _active_agent_metrics(
        self,
        snapshots: List[Mapping[str, Any]],
    ) -> tuple[float, int, int, int]:
        if not snapshots:
            return 0.0, 0, 0, 0

        all_agents: set[str] = set()
        active_agents: set[str] = set()
        event_count = 0

        for index, snapshot in enumerate(snapshots):
            agent_id = str(snapshot.get("agent_id") or snapshot.get("id") or index)
            all_agents.add(agent_id)
            events = self._extract_events(snapshot)
            if events:
                active_agents.add(agent_id)
                event_count += len(events)

        total_agent_count = len(all_agents)
        if total_agent_count == 0:
            return 0.0, 0, 0, event_count
        active_agent_ratio = len(active_agents) / total_agent_count
        return active_agent_ratio, len(active_agents), total_agent_count, event_count

    def _extract_events(self, snapshot: Mapping[str, Any]) -> List[Any]:
        for key in ("propagation_events", "events"):
            raw_events = snapshot.get(key)
            if raw_events is None:
                continue
            if isinstance(raw_events, list):
                return raw_events
            if isinstance(raw_events, tuple):
                return list(raw_events)
            if raw_events:
                return [raw_events]
        return []


__all__ = ["ConvergenceConfig", "ConvergenceDetector"]
