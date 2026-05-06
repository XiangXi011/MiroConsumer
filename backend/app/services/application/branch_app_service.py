"""
Branch application service

Thin wrapper around ConsumerInterventionManager for route-level orchestration.
"""

import json
import os
from typing import Any, Dict, List, Optional, Tuple

from ...config import Config
from ...repositories import BranchRepository, SimulationRepository
from ...repositories.factory import create_repository_bundle
from ...services.consumer.api_guard import ConsumerApiGuard
from ...services.consumer.intervention_manager import InterventionType
from ...services.consumer.society.state_store import SocietyStateStore
from ...services.simulation_runner import SimulationRunner
from ...utils.locale import get_locale, set_locale
from ...utils.logger import get_logger
from .branch_fork_snapshot import BranchForkSnapshotService
from .concurrency import branch_fork_lock, create_lock_manager
from .task_executor import TaskExecutor, create_task_executor

logger = get_logger("miroconsumer.app_service.branch")


class BranchAppService:
    """Application service for branch and intervention orchestration."""

    _repository_bundle = create_repository_bundle()
    _simulation_repo: SimulationRepository = _repository_bundle.simulation_repo
    _branch_repo: BranchRepository = _repository_bundle.branch_repo
    _executor: TaskExecutor = create_task_executor()
    _lock_manager = create_lock_manager()
    _fork_snapshot_service = BranchForkSnapshotService()

    @classmethod
    def _require_consumer_simulation(cls, simulation_id: str) -> Tuple[Optional[Any], Optional[str]]:
        """
        Load simulation state and enforce consumer_test-only access.

        Returns (state, None) on success, or (None, error_message) on failure.
        """
        state = cls._simulation_repo.get_simulation(simulation_id)
        ok, error = ConsumerApiGuard.check_consumer_simulation(state)
        if not ok:
            return None, error
        return state, None

    @classmethod
    def create_branch(
        cls,
        simulation_id: str,
        name: str,
        fork_round: int,
        description: str = "",
        parent_branch_id: Optional[str] = None,
    ) -> dict:
        """Create a new branch for a consumer simulation."""
        lock_resource_id = f"{simulation_id}:fork:{parent_branch_id or 'base'}:{fork_round}"
        with cls._lock_manager.acquire(branch_fork_lock, lock_resource_id, timeout_seconds=0):
            state, error = cls._require_consumer_simulation(simulation_id)
            if error:
                raise ValueError(error)

            if not name:
                raise ValueError("name is required")
            if fork_round is None or not isinstance(fork_round, int) or fork_round < 0:
                raise ValueError("fork_round must be a non-negative integer")

            branch = cls._branch_repo.create_branch(
                simulation_id=simulation_id,
                name=name,
                fork_round=fork_round,
                description=description,
                parent_branch_id=parent_branch_id,
            )
            snapshot = cls._fork_snapshot_service.copy_pre_fork_state(
                simulation_id=simulation_id,
                branch_id=branch.branch_id,
                fork_round=fork_round,
            )
            payload = branch.model_dump()
            payload["fork_snapshot"] = snapshot
            return payload

    @classmethod
    def list_branches(cls, simulation_id: str) -> List[dict]:
        """List all branches for a simulation."""
        state, error = cls._require_consumer_simulation(simulation_id)
        if error:
            raise ValueError(error)

        branches = cls._branch_repo.list_branches(simulation_id)
        return [b.model_dump() for b in branches]

    @classmethod
    def list_interventions(
        cls,
        simulation_id: str,
        branch_id: Optional[str] = None,
    ) -> List[dict]:
        """List interventions for a simulation (optionally filtered by branch)."""
        state, error = cls._require_consumer_simulation(simulation_id)
        if error:
            raise ValueError(error)

        interventions = cls._branch_repo.list_interventions(simulation_id, branch_id=branch_id)
        return [i.model_dump() for i in interventions]

    @classmethod
    def add_intervention(
        cls,
        simulation_id: str,
        branch_id: str,
        intervention_type: str,
        payload: dict,
        target_round: Optional[int] = None,
    ) -> dict:
        """Add an intervention to a branch."""
        state, error = cls._require_consumer_simulation(simulation_id)
        if error:
            raise ValueError(error)

        if not intervention_type:
            raise ValueError("intervention_type is required")

        try:
            InterventionType(intervention_type)
        except ValueError:
            raise ValueError(f"Unsupported intervention_type: {intervention_type}")

        intervention = cls._branch_repo.add_intervention(
            simulation_id=simulation_id,
            branch_id=branch_id,
            intervention_type=intervention_type,
            payload=payload,
            target_round=target_round,
        )
        return intervention.model_dump()

    @classmethod
    def get_branch_comparison(cls, simulation_id: str, branch_id: str) -> dict:
        """Fetch branch comparison context with base-vs-branch summaries."""
        state, error = cls._require_consumer_simulation(simulation_id)
        if error:
            raise ValueError(error)

        branch = cls._branch_repo.get_branch(simulation_id, branch_id)
        if branch is None:
            raise ValueError("Branch not found")
        return cls._branch_repo.build_comparison_context(simulation_id, branch_id)

    @classmethod
    def get_branch_run_status(cls, simulation_id: str, branch_id: str) -> dict:
        """Get branch simulation run status."""
        state, error = cls._require_consumer_simulation(simulation_id)
        if error:
            raise ValueError(error)

        branch = cls._branch_repo.get_branch(simulation_id, branch_id)
        if branch is None:
            raise ValueError("Branch not found")

        run_status = cls._branch_repo.get_branch_run_status(simulation_id, branch_id)
        return {
            **run_status,
            "branch_status": branch.status,
        }

    @classmethod
    def resume_branch(
        cls,
        simulation_id: str,
        branch_id: str,
        max_rounds: Optional[int] = None,
    ) -> dict:
        lock_resource_id = f"{simulation_id}:{branch_id}"
        with cls._lock_manager.acquire(
            branch_fork_lock,
            lock_resource_id,
            timeout_seconds=0,
        ):
            return cls._resume_branch_unlocked(
                simulation_id=simulation_id,
                branch_id=branch_id,
                max_rounds=max_rounds,
            )

    @classmethod
    def _resume_branch_unlocked(
        cls,
        simulation_id: str,
        branch_id: str,
        max_rounds: Optional[int] = None,
    ) -> dict:
        """Run or resume a branch simulation (consumer_test only).

        The branch runs independently of the base simulation run_state.
        Output is persisted under branches/<branch_id>/rounds.jsonl.

        Raises ValueError on validation failure or if branch is already running.
        """
        state, error = cls._require_consumer_simulation(simulation_id)
        if error:
            raise ValueError(error)

        branch = cls._branch_repo.get_branch(simulation_id, branch_id)
        if branch is None:
            raise ValueError("Branch not found")

        run_status = cls._branch_repo.get_branch_run_status(simulation_id, branch_id)
        if run_status.get("status") == "running":
            raise ValueError("Branch is already running")

        config = cls._simulation_repo.load_simulation_config(simulation_id)
        if not config:
            raise ValueError("Simulation config not found")
        if not config.get("society_config"):
            base_society_config = SocietyStateStore().read_config(simulation_id)
            if base_society_config:
                config["society_config"] = base_society_config

        time_config = config.get("time_config", {})
        total_hours = time_config.get("total_simulation_hours", 72)
        minutes_per_round = time_config.get("minutes_per_round", 30)
        total_rounds = int(total_hours * 60 / minutes_per_round)
        if max_rounds is not None and max_rounds > 0:
            total_rounds = min(total_rounds, max_rounds)
        config["total_rounds"] = total_rounds

        cls._branch_repo.update_branch_status(simulation_id, branch_id, "running")

        current_locale = get_locale()

        def run_branch():
            set_locale(current_locale)
            SimulationRunner.run_branch_simulation(simulation_id, branch_id, config)

        cls._executor.submit(
            run_branch,
            task_type="resume_branch",
            idempotency_key=f"{simulation_id}:branch:{branch_id}:resume",
            simulation_id=simulation_id,
            run_id=branch_id,
        )

        return {
            "simulation_id": simulation_id,
            "branch_id": branch_id,
            "status": "running",
            "fork_round": branch.fork_round,
            "total_rounds": total_rounds,
        }
