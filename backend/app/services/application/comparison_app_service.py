"""
Comparison application service

Encapsulates route-level orchestration for comparison snapshot
creation, listing, and retrieval.
"""

from typing import Any, Dict, List, Optional

from ...models.project import ProjectManager
from ...services.consumer.api_guard import ConsumerApiGuard
from ...contracts.consumer_contracts import ComparisonSnapshot
from ...services.consumer.comparison_engine import (
    create_comparison,
    get_comparison,
    list_comparisons,
)
from ...services.simulation_manager import SimulationManager
from ...contracts.errors import NotFoundError
from ...utils.locale import t
from ...utils.logger import get_logger

logger = get_logger("miroconsumer.app_service.comparison")


class ComparisonAppService:
    """Application service for comparison snapshot orchestration."""

    @classmethod
    def create_comparison(cls, data: dict) -> dict:
        """
        Validate inputs and create a persisted comparison snapshot.

        Supports three modes:
        a) run_vs_run: { mode, left_simulation_id, right_simulation_id }
        b) branch_vs_base: { mode, simulation_id, branch_id }
        c) project_vs_project: { mode, left_project_id, right_project_id }

        Raises ValueError on validation failure.
        """
        mode = data.get("mode")
        if not mode:
            raise ValueError("mode is required")

        if mode == "run_vs_run":
            left_simulation_id = data.get("left_simulation_id")
            right_simulation_id = data.get("right_simulation_id")
            if not left_simulation_id or not right_simulation_id:
                raise ValueError("left_simulation_id and right_simulation_id are required")

            manager = SimulationManager()
            left_state = manager.get_simulation(left_simulation_id)
            right_state = manager.get_simulation(right_simulation_id)
            if not left_state or not right_state:
                missing = left_simulation_id if not left_state else right_simulation_id
                raise NotFoundError(t("api.simulationNotFound", id=missing))

            for st in (left_state, right_state):
                ok, error = ConsumerApiGuard.check_consumer_simulation(st)
                if not ok:
                    raise ValueError(error)

            return create_comparison(
                mode=mode,
                left_simulation_id=left_simulation_id,
                right_simulation_id=right_simulation_id,
            )

        if mode == "branch_vs_base":
            simulation_id = data.get("simulation_id")
            branch_id = data.get("branch_id")
            if not simulation_id or not branch_id:
                raise ValueError("simulation_id and branch_id are required")

            manager = SimulationManager()
            state = manager.get_simulation(simulation_id)
            if not state:
                raise NotFoundError(t("api.simulationNotFound", id=simulation_id))

            ok, error = ConsumerApiGuard.check_consumer_simulation(state)
            if not ok:
                raise ValueError(error)

            return create_comparison(
                mode=mode,
                simulation_id=simulation_id,
                branch_id=branch_id,
            )

        if mode == "project_vs_project":
            left_project_id = data.get("left_project_id")
            right_project_id = data.get("right_project_id")
            if not left_project_id or not right_project_id:
                raise ValueError("left_project_id and right_project_id are required")

            left_project = ProjectManager.get_project(left_project_id)
            right_project = ProjectManager.get_project(right_project_id)
            if not left_project or not right_project:
                missing = left_project_id if not left_project else right_project_id
                raise NotFoundError(t("api.projectNotFound", id=missing))

            for proj in (left_project, right_project):
                ok, error = ConsumerApiGuard.check_consumer_project(proj)
                if not ok:
                    raise ValueError(error)

            return create_comparison(
                mode=mode,
                left_project_id=left_project_id,
                right_project_id=right_project_id,
            )

        raise ValueError(f"Unsupported comparison mode: {mode}")

    @classmethod
    def list_comparisons(cls, project_id: str) -> List[dict]:
        """
        List comparison snapshots for a project.

        Raises ValueError if project_id is missing.
        """
        if not project_id:
            raise ValueError("project_id is required")
        return list_comparisons(project_id)

    @classmethod
    def get_comparison(cls, comparison_id: str) -> dict:
        """
        Get a single comparison snapshot with confidence backfill.

        Raises ValueError if snapshot not found.
        """
        snapshot = get_comparison(comparison_id)
        if not snapshot:
            raise NotFoundError(f"Comparison not found: {comparison_id}")

        # Materially reduce ad-hoc dict handling by using the typed contract
        typed = ComparisonSnapshot.from_dict(snapshot)

        # Backfill confidence fields for old snapshots (pre-Phase 4A)
        if not typed.comparison_confidence:
            from ...services.consumer.confidence_scoring import compute_comparison_confidence

            left_conf = typed.left_confidence.model_dump()
            right_conf = typed.right_confidence.model_dump()
            typed.comparison_confidence = compute_comparison_confidence(left_conf, right_conf)

        return typed.model_dump()
