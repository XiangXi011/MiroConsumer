"""Filesystem-backed history store for consumer interviews and focus groups."""

import json
from pathlib import Path
from typing import Any, Dict, List

from ....config import Config


class HistoryStore:
    """Persist interview and focus group artifacts under uploads/simulations/<simulation_id>/consumer_interviews."""

    def __init__(self, base_dir: str | Path | None = None):
        self.base_dir = Path(base_dir) if base_dir is not None else Path(Config.OASIS_SIMULATION_DATA_DIR)

    def _interview_dir(self, simulation_id: str) -> Path:
        path = self.base_dir / simulation_id / "consumer_interviews"
        path.mkdir(parents=True, exist_ok=True)
        return path

    def _interviews_path(self, simulation_id: str) -> Path:
        return self._interview_dir(simulation_id) / "interviews.jsonl"

    def _focus_groups_path(self, simulation_id: str) -> Path:
        return self._interview_dir(simulation_id) / "focus_groups.jsonl"

    def write_interview(self, simulation_id: str, record: Dict[str, Any]) -> None:
        path = self._interviews_path(simulation_id)
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")

    def write_focus_group(self, simulation_id: str, record: Dict[str, Any]) -> None:
        path = self._focus_groups_path(simulation_id)
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")

    def list_interviews(self, simulation_id: str) -> List[Dict[str, Any]]:
        path = self._interviews_path(simulation_id)
        if not path.exists():
            return []
        return [
            json.loads(line)
            for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]

    def list_focus_groups(self, simulation_id: str) -> List[Dict[str, Any]]:
        path = self._focus_groups_path(simulation_id)
        if not path.exists():
            return []
        return [
            json.loads(line)
            for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
