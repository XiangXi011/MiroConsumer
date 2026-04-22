"""
Branch application service

Thin wrapper around ConsumerInterventionManager for route-level orchestration.
"""

from typing import Any, Dict, List, Optional, Tuple

from ...repositories import BranchRepository, SimulationRepository
from ...repositories.filesystem import FilesystemBranchRepository, FilesystemSimulationRepository
from ...services.consumer.api_guard import ConsumerApiGuard
from ...services.consumer.intervention_manager import InterventionType


class BranchAppService:
    """Application service for branch and intervention orchestration."""

    _simulation_repo: SimulationRepository = FilesystemSimulationRepository()
    _branch_repo: BranchRepository = FilesystemBranchRepository()

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
        return branch.model_dump()

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
