"""Structured trace logging helpers for Phase 7D."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List

from ...utils.logger import LOG_DIR, get_logger

TRACE_FIELDS = [
    "trace_id",
    "run_id",
    "simulation_id",
    "branch_id",
    "agent_id",
    "channel_id",
    "event_id",
    "finding_id",
    "source_id",
    "task_id",
]


def normalize_trace_fields(fields: Dict[str, Any] | None = None) -> Dict[str, str]:
    fields = fields or {}
    return {name: str(fields.get(name) or "") for name in TRACE_FIELDS}


def filter_trace_events(
    events: Iterable[Dict[str, Any]],
    *,
    trace_id: str = "",
    run_id: str = "",
    simulation_id: str = "",
) -> List[Dict[str, Any]]:
    result = []
    for event in events:
        trace = event.get("trace", event)
        if trace_id and trace.get("trace_id") != trace_id:
            continue
        if run_id and trace.get("run_id") != run_id:
            continue
        if simulation_id and trace.get("simulation_id") != simulation_id:
            continue
        result.append(event)
    return result


class TraceLogStore:
    """Append-only JSONL trace log store."""

    def __init__(self, log_path: str | Path | None = None):
        self.log_path = Path(log_path) if log_path is not None else Path(LOG_DIR) / "trace.jsonl"
        self.logger = get_logger("miroconsumer.trace")

    def log_event(self, event_name: str, **fields: Any) -> Dict[str, Any]:
        event = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event_name": event_name,
            "trace": normalize_trace_fields(fields),
        }
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        with self.log_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(event, ensure_ascii=False) + "\n")
        self.logger.info(
            event_name,
            extra=event["trace"],
        )
        return event

    def read_events(self) -> List[Dict[str, Any]]:
        if not self.log_path.exists():
            return []
        events = []
        with self.log_path.open("r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    events.append(json.loads(line))
        return events
