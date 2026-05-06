"""Atomic branch fork snapshot copy for Phase 7C."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict

from ...config import Config


class BranchForkSnapshotService:
    """Copy base pre-fork rounds into a branch-local immutable starting point."""

    def __init__(self, upload_folder: str | None = None):
        self.upload_folder = Path(upload_folder or Config.UPLOAD_FOLDER)

    def copy_pre_fork_state(
        self,
        *,
        simulation_id: str,
        branch_id: str,
        fork_round: int,
    ) -> Dict[str, Any]:
        source = self.upload_folder / "simulations" / simulation_id / "consumer_rounds.jsonl"
        target = (
            self.upload_folder
            / "simulations"
            / simulation_id
            / "branches"
            / branch_id
            / "rounds.jsonl"
        )
        target.parent.mkdir(parents=True, exist_ok=True)
        temp_target = target.with_suffix(".jsonl.tmp")
        copied = 0

        with temp_target.open("w", encoding="utf-8") as out:
            if source.exists():
                with source.open("r", encoding="utf-8") as inp:
                    for line in inp:
                        if not line.strip():
                            continue
                        row = json.loads(line)
                        if int(row.get("round", 0)) <= fork_round:
                            out.write(json.dumps(row, ensure_ascii=False) + "\n")
                            copied += 1

        os.replace(temp_target, target)
        return {
            "simulation_id": simulation_id,
            "branch_id": branch_id,
            "fork_round": fork_round,
            "copied_rounds": copied,
            "target_path": str(target),
        }
