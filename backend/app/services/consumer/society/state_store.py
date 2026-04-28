"""File-system state store for Phase 6G society runtime."""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping

from ....config import Config
from .population_models import ConsumerSocietyAgent, ConsumerSocietyRunConfig, ConsumerSocietySnapshot


class SocietyStateStore:
    """Persist society runtime artifacts under uploads/simulations/<simulation_id>/society."""

    def __init__(self, base_dir: str | Path | None = None):
        self.base_dir = Path(base_dir) if base_dir is not None else Path(Config.OASIS_SIMULATION_DATA_DIR)

    def society_dir(self, simulation_id: str) -> Path:
        return self.base_dir / simulation_id / "society"

    def write_population(self, simulation_id: str, population: Iterable[ConsumerSocietyAgent]) -> None:
        self._write_json(
            self.society_dir(simulation_id) / "population.json",
            [agent.to_dict() for agent in population],
        )

    def write_config(self, simulation_id: str, config: ConsumerSocietyRunConfig) -> None:
        self._write_json(self.society_dir(simulation_id) / "society_config.json", config.to_dict())

    def write_rounds(self, simulation_id: str, snapshots: Iterable[ConsumerSocietySnapshot]) -> None:
        path = self.society_dir(simulation_id) / "society_rounds.jsonl"
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as f:
            for snapshot in snapshots:
                f.write(json.dumps(snapshot.to_dict(), ensure_ascii=False, sort_keys=True) + "\n")

    def write_metrics(self, simulation_id: str, metrics: Mapping[str, Any]) -> None:
        self._write_json(self.society_dir(simulation_id) / "society_metrics.json", dict(metrics))

    def read_metrics(self, simulation_id: str) -> Dict[str, Any]:
        path = self.society_dir(simulation_id) / "society_metrics.json"
        if not path.exists():
            return {}
        return json.loads(path.read_text(encoding="utf-8"))

    def read_config(self, simulation_id: str) -> Dict[str, Any]:
        path = self.society_dir(simulation_id) / "society_config.json"
        if not path.exists():
            return {}
        return json.loads(path.read_text(encoding="utf-8"))

    def read_population(self, simulation_id: str) -> List[Dict[str, Any]]:
        path = self.society_dir(simulation_id) / "population.json"
        if not path.exists():
            return []
        payload = json.loads(path.read_text(encoding="utf-8"))
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
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")


__all__ = ["SocietyStateStore"]
