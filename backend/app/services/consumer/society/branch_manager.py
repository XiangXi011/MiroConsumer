"""Branch snapshot diffing for consumer simulation branches."""

from __future__ import annotations

import re
from collections import Counter
from statistics import mean
from typing import Any, Mapping

_STOPWORDS = {
    "the", "and", "or", "to", "it", "is", "i", "a", "an", "this", "that", "too",
    "would", "with", "for", "of", "in", "on", "be", "am", "are",
}


def _events(snapshot: Mapping[str, Any]) -> list[dict[str, Any]]:
    return [dict(item) for item in snapshot.get("events", []) if isinstance(item, Mapping)]


def _event_id(event: Mapping[str, Any], fallback: int) -> str:
    return str(event.get("event_id") or f"event_{fallback}")


def _average_by_agent(events: list[dict[str, Any]], field: str) -> dict[str, float]:
    buckets: dict[str, list[float]] = {}
    for index, event in enumerate(events):
        agent_id = str(event.get("agent_id") or f"event_{index}")
        try:
            value = float(event.get(field, 0.0))
        except (TypeError, ValueError):
            value = 0.0
        buckets.setdefault(agent_id, []).append(value)
    return {agent_id: mean(values) for agent_id, values in buckets.items()}


def _keywords(events: list[dict[str, Any]]) -> list[str]:
    counter: Counter[str] = Counter()
    for event in events:
        for word in re.findall(r"[A-Za-z][A-Za-z'-]{2,}", str(event.get("quote") or "").lower()):
            if word not in _STOPWORDS:
                counter[word] += 1
    return [word for word, _count in counter.most_common(12)]


class BranchManager:
    """Compute structured differences between two branch snapshots."""

    def diff_branches(self, left: Mapping[str, Any], right: Mapping[str, Any]) -> dict[str, Any]:
        left_events = _events(left)
        right_events = _events(right)
        left_by_id = {_event_id(event, index): event for index, event in enumerate(left_events)}
        right_by_id = {_event_id(event, index): event for index, event in enumerate(right_events)}
        added = sorted(set(right_by_id) - set(left_by_id))
        removed = sorted(set(left_by_id) - set(right_by_id))
        common = sorted(set(left_by_id) & set(right_by_id))

        left_attitude = _average_by_agent(left_events, "attitude")
        right_attitude = _average_by_agent(right_events, "attitude")
        attitude_delta = {
            agent_id: round(right_attitude.get(agent_id, 0.0) - left_attitude.get(agent_id, 0.0), 6)
            for agent_id in sorted(set(left_attitude) | set(right_attitude))
        }

        left_conf = [float(event.get("confidence_score", 0.0) or 0.0) for event in left_events]
        right_conf = [float(event.get("confidence_score", 0.0) or 0.0) for event in right_events]
        left_avg = mean(left_conf) if left_conf else 0.0
        right_avg = mean(right_conf) if right_conf else 0.0

        diff = {
            "left_branch_id": left.get("branch_id"),
            "right_branch_id": right.get("branch_id"),
            "attitude_delta": attitude_delta,
            "event_delta": {
                "added_event_ids": added,
                "removed_event_ids": removed,
                "changed_event_ids": [event_id for event_id in common if left_by_id[event_id] != right_by_id[event_id]],
            },
            "voc_delta": {
                "left_keywords": _keywords(left_events),
                "right_keywords": _keywords(right_events),
            },
            "confidence_delta": {
                "left_average": left_avg,
                "right_average": right_avg,
                "average_delta": round(right_avg - left_avg, 6),
            },
        }
        diff["is_empty"] = (
            not added
            and not removed
            and not diff["event_delta"]["changed_event_ids"]
            and all(abs(value) < 1e-9 for value in attitude_delta.values())
            and abs(diff["confidence_delta"]["average_delta"]) < 1e-9
        )
        return diff


__all__ = ["BranchManager"]
