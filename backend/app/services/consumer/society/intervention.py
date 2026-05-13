"""Intervention sequence recording and replay for society snapshots."""

from __future__ import annotations

import copy
import json
import uuid
from datetime import datetime, timezone
from typing import Any, Iterable, Mapping


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _flatten(data: Mapping[str, Any], prefix: str = "") -> dict[str, Any]:
    flattened: dict[str, Any] = {}
    for key, value in data.items():
        path = f"{prefix}.{key}" if prefix else str(key)
        if isinstance(value, Mapping):
            flattened.update(_flatten(value, path))
        else:
            flattened[path] = value
    return flattened


def _assign_dot_path(state: dict[str, Any], target: str, value: Any) -> None:
    keys = [part for part in str(target).split(".") if part]
    if not keys:
        return
    cursor = state
    for key in keys[:-1]:
        child = cursor.get(key)
        if not isinstance(child, dict):
            child = {}
            cursor[key] = child
        cursor = child
    cursor[keys[-1]] = value


class InterventionEngine:
    """Record, replay, export, and import intervention sequences."""

    def record_intervention(
        self,
        sequence: Iterable[Mapping[str, Any]],
        *,
        target: str,
        round_index: int,
        parameters: Mapping[str, Any],
    ) -> list[dict[str, Any]]:
        updated = [dict(item) for item in sequence]
        updated.append(
            {
                "intervention_id": f"int_{uuid.uuid4().hex[:12]}",
                "target": str(target),
                "round_index": int(round_index),
                "parameters": dict(parameters),
                "created_at": _now_iso(),
            }
        )
        return updated

    def replay(
        self,
        initial_state: Mapping[str, Any],
        sequence: Iterable[Mapping[str, Any]],
        *,
        parameter_overrides: Mapping[str, Mapping[str, Any]] | None = None,
    ) -> dict[str, Any]:
        before = copy.deepcopy(dict(initial_state))
        current = copy.deepcopy(dict(initial_state))
        applied: list[dict[str, Any]] = []
        overrides = dict(parameter_overrides or {})
        ordered = sorted([dict(item) for item in sequence], key=lambda item: int(item.get("round_index", 0)))
        for item in ordered:
            intervention_id = str(item.get("intervention_id"))
            params = dict(item.get("parameters") or {})
            if intervention_id in overrides:
                params.update(dict(overrides[intervention_id]))
            value = params.get("value", params.get("message", params))
            _assign_dot_path(current, str(item.get("target", "")), value)
            applied_item = dict(item)
            applied_item["applied_parameters"] = params
            applied.append(applied_item)
        return {
            "initial_state": before,
            "final_state": current,
            "applied_count": len(applied),
            "applied_interventions": applied,
            "delta": self._delta(before, current),
        }

    def export_sequence(self, sequence: Iterable[Mapping[str, Any]]) -> str:
        return json.dumps([dict(item) for item in sequence], ensure_ascii=False, sort_keys=True)

    def import_sequence(self, json_string: str) -> list[dict[str, Any]]:
        payload = json.loads(json_string)
        if not isinstance(payload, list):
            raise ValueError("Intervention sequence JSON must be a list")
        return [dict(item) for item in payload]

    def _delta(self, before: Mapping[str, Any], after: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
        before_flat = _flatten(before)
        after_flat = _flatten(after)
        delta: dict[str, dict[str, Any]] = {}
        for key in sorted(set(before_flat) | set(after_flat)):
            if before_flat.get(key) != after_flat.get(key):
                delta[key] = {"before": before_flat.get(key), "after": after_flat.get(key)}
        return delta


__all__ = ["InterventionEngine"]
