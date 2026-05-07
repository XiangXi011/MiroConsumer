"""File-system state store for Phase 6G society runtime."""

from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping

from ....config import Config
from ....utils.atomic_json import atomic_write_json, safe_read_json
from .population_models import ConsumerSocietyAgent, ConsumerSocietyRunConfig, ConsumerSocietySnapshot


class SocietyStateStore:
    """Persist society runtime artifacts under uploads/simulations/<simulation_id>/society."""

    def __init__(self, base_dir: str | Path | None = None):
        self.base_dir = Path(base_dir) if base_dir is not None else Path(Config.OASIS_SIMULATION_DATA_DIR)

    def society_dir(self, simulation_id: str) -> Path:
        return self.base_dir / simulation_id / "society"

    def ensure_started(self, simulation_id: str) -> Path:
        path = self.society_dir(simulation_id)
        path.mkdir(parents=True, exist_ok=True)
        (path / "rounds").mkdir(parents=True, exist_ok=True)
        return path

    def write_population(self, simulation_id: str, population: Iterable[ConsumerSocietyAgent]) -> None:
        self._write_json(
            self.society_dir(simulation_id) / "population.json",
            [agent.to_dict() for agent in population],
        )

    def write_config(self, simulation_id: str, config: ConsumerSocietyRunConfig) -> None:
        self._write_json(self.society_dir(simulation_id) / "society_config.json", config.to_dict())

    def write_profile_snapshot(self, simulation_id: str, snapshot: Mapping[str, Any]) -> None:
        self._write_json(self.society_dir(simulation_id) / "profile_snapshot.json", dict(snapshot))

    def read_profile_snapshot(self, simulation_id: str) -> Dict[str, Any]:
        path = self.society_dir(simulation_id) / "profile_snapshot.json"
        if not path.exists():
            return {}
        payload = safe_read_json(path, default={})
        return payload if isinstance(payload, dict) else {}

    def write_rounds(self, simulation_id: str, snapshots: Iterable[ConsumerSocietySnapshot]) -> None:
        path = self.society_dir(simulation_id) / "society_rounds.jsonl"
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as f:
            for snapshot in snapshots:
                f.write(json.dumps(snapshot.to_dict(), ensure_ascii=False, sort_keys=True) + "\n")

    def write_round_snapshot(self, simulation_id: str, snapshot: ConsumerSocietySnapshot) -> None:
        self._write_json(
            self.society_dir(simulation_id) / "rounds" / f"round_{snapshot.round_index}.json",
            snapshot.to_dict(),
        )

    def write_progress(self, simulation_id: str, progress: Mapping[str, Any]) -> None:
        self._write_json(self.society_dir(simulation_id) / "progress.json", dict(progress))

    def read_progress(self, simulation_id: str) -> Dict[str, Any]:
        path = self.society_dir(simulation_id) / "progress.json"
        if not path.exists():
            return {}
        payload = safe_read_json(path, default={})
        return payload if isinstance(payload, dict) else {}

    def append_runtime_event(self, simulation_id: str, event: Mapping[str, Any]) -> None:
        self._append_jsonl(self.society_dir(simulation_id) / "runtime_events.jsonl", event)

    def append_error(self, simulation_id: str, error: Mapping[str, Any]) -> None:
        self._append_jsonl(self.society_dir(simulation_id) / "errors.jsonl", error)

    def write_reasoning_traces(self, simulation_id: str, traces: Iterable[Mapping[str, Any]]) -> None:
        path = self.society_dir(simulation_id) / "reasoning_traces.jsonl"
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as f:
            for trace in traces:
                payload = trace.to_dict() if hasattr(trace, "to_dict") else dict(trace)
                f.write(json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n")

    def read_reasoning_traces(self, simulation_id: str) -> List[Dict[str, Any]]:
        path = self.society_dir(simulation_id) / "reasoning_traces.jsonl"
        if not path.exists():
            return []
        return [
            json.loads(line)
            for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]

    def write_metrics(self, simulation_id: str, metrics: Mapping[str, Any]) -> None:
        self._write_json(self.society_dir(simulation_id) / "society_metrics.json", dict(metrics))

    def write_channel_assignments(
        self,
        simulation_id: str,
        assignments: Mapping[str, Iterable[str]],
    ) -> None:
        self._write_json(
            self.society_dir(simulation_id) / "channel_assignments.json",
            {channel_id: list(agent_ids) for channel_id, agent_ids in assignments.items()},
        )

    def read_channel_assignments(self, simulation_id: str) -> Dict[str, List[str]]:
        path = self.society_dir(simulation_id) / "channel_assignments.json"
        if not path.exists():
            return {}
        payload = safe_read_json(path, default={})
        if not isinstance(payload, dict):
            return {}
        return {
            str(channel_id): [str(agent_id) for agent_id in agent_ids]
            for channel_id, agent_ids in payload.items()
            if isinstance(agent_ids, list)
        }

    def write_channel_metrics(self, simulation_id: str, metrics: Mapping[str, Any]) -> None:
        self._write_json(self.society_dir(simulation_id) / "channel_metrics.json", dict(metrics))

    def write_channel_events(self, simulation_id: str, events: Iterable[Mapping[str, Any]]) -> None:
        path = self.society_dir(simulation_id) / "channel_events.jsonl"
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as f:
            for event in events:
                f.write(json.dumps(dict(event), ensure_ascii=False, sort_keys=True) + "\n")

    def write_propagation_paths(
        self,
        simulation_id: str,
        paths: Iterable[Mapping[str, Any]],
    ) -> None:
        self._write_json(
            self.society_dir(simulation_id) / "propagation_paths.json",
            [dict(path) for path in paths],
        )

    def write_network_topology(self, simulation_id: str, topology: Mapping[str, Any]) -> None:
        self._write_json(self.society_dir(simulation_id) / "network_topology.json", dict(topology))

    def read_metrics(self, simulation_id: str) -> Dict[str, Any]:
        path = self.society_dir(simulation_id) / "society_metrics.json"
        if not path.exists():
            return {}
        return safe_read_json(path, default={})

    def read_channel_metrics(self, simulation_id: str) -> Dict[str, Any]:
        path = self.society_dir(simulation_id) / "channel_metrics.json"
        if not path.exists():
            return {}
        return safe_read_json(path, default={})

    def read_channel_events(self, simulation_id: str) -> List[Dict[str, Any]]:
        path = self.society_dir(simulation_id) / "channel_events.jsonl"
        if not path.exists():
            return []
        return [
            json.loads(line)
            for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]

    def read_propagation_paths(self, simulation_id: str) -> List[Dict[str, Any]]:
        path = self.society_dir(simulation_id) / "propagation_paths.json"
        if not path.exists():
            return []
        payload = safe_read_json(path, default=[])
        return payload if isinstance(payload, list) else []

    def read_network_topology(self, simulation_id: str) -> Dict[str, Any]:
        path = self.society_dir(simulation_id) / "network_topology.json"
        if not path.exists():
            return {}
        payload = safe_read_json(path, default={})
        return payload if isinstance(payload, dict) else {}

    def read_config(self, simulation_id: str) -> Dict[str, Any]:
        path = self.society_dir(simulation_id) / "society_config.json"
        if not path.exists():
            return {}
        return safe_read_json(path, default={})

    def read_population(self, simulation_id: str) -> List[Dict[str, Any]]:
        path = self.society_dir(simulation_id) / "population.json"
        if not path.exists():
            return []
        payload = safe_read_json(path, default=[])
        return payload if isinstance(payload, list) else []

    def read_rounds(self, simulation_id: str) -> List[Dict[str, Any]]:
        path = self.society_dir(simulation_id) / "society_rounds.jsonl"
        if not path.exists():
            return []
        return [
            json.loads(line)
            for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]

    def _write_json(self, path: Path, data: Any) -> None:
        atomic_write_json(path, data)

    def _append_jsonl(self, path: Path, data: Mapping[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = dict(data)
        payload.setdefault("timestamp", datetime.now().isoformat())
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n")


__all__ = ["SocietyStateStore"]
