"""Consumer intervention and branch persistence for Phase 3B."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from .report_context import ConsumerReportContextBuilder
from .scoring import ConsumerScoringService


class InterventionType(str, Enum):
    clarification_injection = "clarification_injection"
    revised_claim_injection = "revised_claim_injection"
    evidence_reveal = "evidence_reveal"


class ConsumerIntervention(BaseModel):
    intervention_id: str
    branch_id: str
    simulation_id: str
    intervention_type: InterventionType
    payload: Dict[str, Any] = Field(default_factory=dict)
    target_round: Optional[int] = None
    applied_at: Optional[str] = None
    created_at: str = ""

    def model_post_init(self, __context: Any) -> None:
        if not self.created_at:
            self.created_at = datetime.now(timezone.utc).isoformat()


class ConsumerBranch(BaseModel):
    branch_id: str
    simulation_id: str
    parent_branch_id: Optional[str] = None
    fork_round: int = 0
    name: str = ""
    description: str = ""
    status: str = "active"
    created_at: str = ""

    def model_post_init(self, __context: Any) -> None:
        if not self.created_at:
            self.created_at = datetime.now(timezone.utc).isoformat()


class ConsumerInterventionManager:
    """Manage branches and interventions with repo-local persistence."""

    def __init__(self, branches_dir: Optional[str | Path] = None):
        self.branches_dir = Path(branches_dir) if branches_dir is not None else None

    def _simulation_branches_path(self, simulation_id: str) -> Path:
        if self.branches_dir is not None:
            return Path(self.branches_dir)
        from ...config import Config
        return Path(Config.UPLOAD_FOLDER) / "simulations" / simulation_id / "branches"

    def _branch_path(self, simulation_id: str, branch_id: str) -> Path:
        return self._simulation_branches_path(simulation_id) / branch_id

    def _branch_file(self, simulation_id: str, branch_id: str) -> Path:
        return self._branch_path(simulation_id, branch_id) / "branch.json"

    def _interventions_file(self, simulation_id: str, branch_id: str) -> Path:
        return self._branch_path(simulation_id, branch_id) / "interventions.jsonl"

    def _rounds_file(self, simulation_id: str, branch_id: str) -> Path:
        return self._branch_path(simulation_id, branch_id) / "rounds.jsonl"

    def _branch_run_status_file(self, simulation_id: str, branch_id: str) -> Path:
        return self._branch_path(simulation_id, branch_id) / "run_status.json"

    def _base_simulation_rounds_path(self, simulation_id: str) -> Path:
        from ...config import Config
        return Path(Config.UPLOAD_FOLDER) / "simulations" / simulation_id / "consumer_rounds.jsonl"

    def create_branch(
        self,
        simulation_id: str,
        name: str,
        fork_round: int,
        description: str = "",
        parent_branch_id: Optional[str] = None,
    ) -> ConsumerBranch:
        if parent_branch_id is not None:
            parent = self.get_branch(simulation_id, parent_branch_id)
            if parent is None:
                raise ValueError("Parent branch not found")
        branch = ConsumerBranch(
            branch_id=f"branch_{uuid.uuid4().hex[:12]}",
            simulation_id=simulation_id,
            parent_branch_id=parent_branch_id,
            fork_round=fork_round,
            name=name,
            description=description,
        )
        self._persist_branch(branch)
        return branch

    def _persist_branch(self, branch: ConsumerBranch) -> None:
        path = self._branch_file(branch.simulation_id, branch.branch_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(branch.model_dump_json(indent=2), encoding="utf-8")

    def get_branch(self, simulation_id: str, branch_id: str) -> Optional[ConsumerBranch]:
        path = self._branch_file(simulation_id, branch_id)
        if not path.exists():
            return None
        data = json.loads(path.read_text(encoding="utf-8"))
        return ConsumerBranch(**data)

    def list_branches(self, simulation_id: str) -> List[ConsumerBranch]:
        sim_dir = self._simulation_branches_path(simulation_id)
        if not sim_dir.exists():
            return []
        branches: List[ConsumerBranch] = []
        for branch_dir in sim_dir.iterdir():
            branch_file = branch_dir / "branch.json"
            if branch_file.exists():
                data = json.loads(branch_file.read_text(encoding="utf-8"))
                branch = ConsumerBranch(**data)
                if branch.simulation_id == simulation_id:
                    branches.append(branch)
        return branches

    def update_branch_status(self, simulation_id: str, branch_id: str, status: str) -> Optional[ConsumerBranch]:
        branch = self.get_branch(simulation_id, branch_id)
        if branch is None:
            return None
        branch.status = status
        self._persist_branch(branch)
        return branch

    def get_branch_run_status(self, simulation_id: str, branch_id: str) -> Dict[str, Any]:
        path = self._branch_run_status_file(simulation_id, branch_id)
        if not path.exists():
            return {"status": "idle", "branch_id": branch_id, "simulation_id": simulation_id}
        return json.loads(path.read_text(encoding="utf-8"))

    def update_branch_run_status(self, simulation_id: str, branch_id: str, status_data: Dict[str, Any]) -> None:
        path = self._branch_run_status_file(simulation_id, branch_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(status_data, ensure_ascii=False, indent=2), encoding="utf-8")

    def add_intervention(
        self,
        simulation_id: str,
        branch_id: str,
        intervention_type: InterventionType | str,
        payload: Dict[str, Any],
        target_round: Optional[int] = None,
    ) -> ConsumerIntervention:
        if isinstance(intervention_type, str):
            try:
                intervention_type = InterventionType(intervention_type)
            except ValueError as exc:
                raise ValueError(f"Unsupported intervention_type: {intervention_type}") from exc

        branch = self.get_branch(simulation_id, branch_id)
        if branch is None:
            raise ValueError("Branch not found")

        intervention = ConsumerIntervention(
            intervention_id=f"int_{uuid.uuid4().hex[:12]}",
            branch_id=branch_id,
            simulation_id=simulation_id,
            intervention_type=intervention_type,
            payload=payload,
            target_round=target_round,
        )
        self._persist_intervention(intervention)
        return intervention

    def _persist_intervention(self, intervention: ConsumerIntervention) -> None:
        path = self._interventions_file(intervention.simulation_id, intervention.branch_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as f:
            f.write(intervention.model_dump_json())
            f.write("\n")

    def list_interventions(
        self, simulation_id: str, branch_id: Optional[str] = None
    ) -> List[ConsumerIntervention]:
        if branch_id is not None:
            branch = self.get_branch(simulation_id, branch_id)
            if branch is None:
                raise ValueError("Branch not found")
            return self._load_interventions_for_branch(simulation_id, branch_id)

        interventions: List[ConsumerIntervention] = []
        for branch in self.list_branches(simulation_id):
            interventions.extend(self._load_interventions_for_branch(simulation_id, branch.branch_id))
        return interventions

    def _load_interventions_for_branch(self, simulation_id: str, branch_id: str) -> List[ConsumerIntervention]:
        path = self._interventions_file(simulation_id, branch_id)
        if not path.exists():
            return []
        interventions: List[ConsumerIntervention] = []
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            interventions.append(ConsumerIntervention(**json.loads(line)))
        return interventions

    def build_comparison_context(self, simulation_id: str, branch_id: str) -> Dict[str, Any]:
        branch = self.get_branch(simulation_id, branch_id)
        if branch is None:
            raise ValueError("Branch not found")

        base_branch_id = branch.parent_branch_id
        if base_branch_id is not None:
            base_summary = self._summarize_branch_rounds(simulation_id, base_branch_id)
        else:
            # If no explicit parent, use the base simulation run as base
            base_summary = self._summarize_base_simulation_rounds(simulation_id)

        branch_summary = self._summarize_branch_rounds(simulation_id, branch_id)
        interventions = self.list_interventions(simulation_id, branch_id=branch_id)

        return {
            "branch_id": branch.branch_id,
            "base_branch_id": base_branch_id,
            "fork_round": branch.fork_round,
            "branch_name": branch.name,
            "branch_description": branch.description,
            "interventions": [i.model_dump() for i in interventions],
            "base_summary": base_summary,
            "branch_summary": branch_summary,
        }

    def _summarize_rounds_at_path(self, rounds_path: Path) -> Dict[str, Any]:
        if not rounds_path.exists():
            return {"events_count": 0, "has_data": False}

        builder = ConsumerReportContextBuilder()
        events = builder.load_events(str(rounds_path))
        if not events:
            return {"events_count": 0, "has_data": False}

        scoring = ConsumerScoringService()
        initial_labels = [e["attitude_label"] for e in events if e.get("round_num") == 0]
        latest: Dict[str, str] = {}
        for e in events:
            aid = e.get("agent_id", "")
            if aid:
                latest[aid] = e.get("attitude_label", "neutral")
        final_labels = list(latest.values())

        summary = scoring.summarize(initial_labels, final_labels)
        evidence = scoring.build_evidence_bundle(events)

        return {
            "events_count": len(events),
            "has_data": True,
            "initial_acceptance": summary.initial_acceptance,
            "post_propagation_acceptance": summary.post_propagation_acceptance,
            "attitude_shift_rate": summary.attitude_shift_rate,
            "initial_counts": summary.initial_counts,
            "final_counts": summary.final_counts,
            "top_resonance_quotes": evidence.top_resonance_quotes[:3],
            "top_risk_quotes": evidence.top_risk_quotes[:3],
            "top_misread_quotes": evidence.top_misread_quotes[:3],
        }

    def _summarize_branch_rounds(self, simulation_id: str, branch_id: str) -> Dict[str, Any]:
        return self._summarize_rounds_at_path(self._rounds_file(simulation_id, branch_id))

    def _summarize_base_simulation_rounds(self, simulation_id: str) -> Dict[str, Any]:
        return self._summarize_rounds_at_path(self._base_simulation_rounds_path(simulation_id))


__all__ = [
    "ConsumerBranch",
    "ConsumerIntervention",
    "ConsumerInterventionManager",
    "InterventionType",
]