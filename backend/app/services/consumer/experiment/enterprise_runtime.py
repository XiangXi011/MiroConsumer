"""Enterprise experiment runtime helpers for consumer simulation groups."""

from __future__ import annotations

import copy
import math
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Iterable, Mapping


@dataclass(frozen=True)
class ExperimentGroupPlan:
    """Runtime plan for one isolated experiment group."""

    group_id: str
    llm_budget_quota: int
    parameters: Mapping[str, Any] = field(default_factory=dict)
    metadata: Mapping[str, Any] = field(default_factory=dict)


class EnterpriseExperimentRuntime:
    """Run experiment groups with isolated state and aggregate lightweight stats."""

    def __init__(self, max_parallel_groups: int = 3) -> None:
        self.max_parallel_groups = max(1, int(max_parallel_groups or 1))

    def run_groups(
        self,
        groups: Iterable[ExperimentGroupPlan],
        runner: Callable[[ExperimentGroupPlan, dict[str, Any]], Mapping[str, Any]],
        *,
        initial_state: Mapping[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        results: list[dict[str, Any]] = []
        for index, group in enumerate(list(groups)):
            isolation_key = f"{group.group_id}:{uuid.uuid4().hex[:12]}"
            state = copy.deepcopy(dict(initial_state or {}))
            state["_experiment_isolation_key"] = isolation_key
            raw_result = dict(runner(group, state) or {})
            raw_result.setdefault("state", state)
            raw_result.update(
                {
                    "group_id": group.group_id,
                    "parameters": dict(group.parameters),
                    "llm_budget_quota": int(group.llm_budget_quota),
                    "state_isolation_key": isolation_key,
                    "parallel_batch_index": index // self.max_parallel_groups,
                }
            )
            results.append(raw_result)
        return results

    def aggregate_results(
        self,
        results: Iterable[Mapping[str, Any]],
        *,
        objective_metric: str = "acceptance_rate",
    ) -> dict[str, Any]:
        rows = [dict(item) for item in results]
        if not rows:
            return {
                "best_group_id": None,
                "recommended_parameters": {},
                "metric_summary": {},
                "statistical_tests": {"anova": {"status": "insufficient_data"}},
            }

        def metric_value(row: Mapping[str, Any]) -> float:
            try:
                return float(row.get(objective_metric, 0.0))
            except (TypeError, ValueError):
                return 0.0

        best = max(rows, key=metric_value)
        values = [metric_value(row) for row in rows]
        mean = sum(values) / len(values)
        variance = sum((value - mean) ** 2 for value in values) / len(values)
        stddev = math.sqrt(variance)
        return {
            "objective_metric": objective_metric,
            "best_group_id": best.get("group_id"),
            "recommended_parameters": dict(best.get("parameters") or {}),
            "metric_summary": {
                "count": len(rows),
                "mean": mean,
                "min": min(values),
                "max": max(values),
                "stddev": stddev,
            },
            "statistical_tests": {
                "anova": {
                    "method": "one_way_anova_lightweight",
                    "group_count": len(rows),
                    "between_group_variance": variance,
                    "p_value": None,
                    "interpretation": "descriptive_only",
                },
                "pairwise_t_test": {
                    "method": "welch_t_test_lightweight",
                    "status": "insufficient_replication" if len(rows) < 4 else "descriptive_only",
                },
            },
        }


__all__ = ["EnterpriseExperimentRuntime", "ExperimentGroupPlan"]
