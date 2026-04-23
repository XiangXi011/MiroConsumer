"""
Research asset application service

Encapsulates route-level orchestration for research asset export,
listing, and retrieval.
"""

from typing import Dict, List, Optional

from ...contracts.errors import NotFoundError
from ...models.project import ProjectManager
from ...services.consumer.api_guard import ConsumerApiGuard
from ...services.consumer.asset_library import export_asset, get_asset, list_assets
from ...services.simulation_manager import SimulationManager
from ...utils.locale import t
from ...utils.logger import get_logger

logger = get_logger("miroconsumer.app_service.research_asset")


class ResearchAssetAppService:
    """Application service for research asset orchestration."""

    @classmethod
    def export_research_asset(
        cls,
        project_id: str,
        simulation_id: str,
        branch_id: Optional[str] = None,
        name: Optional[str] = None,
    ) -> dict:
        """
        Validate and export a research asset pack.

        Raises ValueError on validation failure.
        """
        if not project_id:
            raise ValueError("project_id is required")
        if not simulation_id:
            raise ValueError("simulation_id is required")

        project = ProjectManager.get_project(project_id)
        ok, error = ConsumerApiGuard.check_consumer_project(project)
        if not ok:
            raise ValueError(error)

        manager = SimulationManager()
        state = manager.get_simulation(simulation_id)
        if not state:
            raise NotFoundError(t("api.simulationNotFound", id=simulation_id))

        if state.project_id != project_id:
            raise ValueError("Simulation does not belong to project")

        return export_asset(
            project_id=project_id,
            simulation_id=simulation_id,
            branch_id=branch_id,
            name=name,
        )

    @classmethod
    def list_research_assets(cls, project_id: str) -> List[dict]:
        """
        List research asset packs for a project.

        Raises ValueError if project_id is missing or project not found.
        """
        if not project_id:
            raise ValueError("project_id is required")

        project = ProjectManager.get_project(project_id)
        if not project:
            raise NotFoundError(t("api.projectNotFound", id=project_id))

        return list_assets(project_id)

    @classmethod
    def get_research_asset(cls, asset_id: str) -> dict:
        """
        Get a single research asset pack.

        Raises ValueError if asset not found.
        """
        asset_pack = get_asset(asset_id)
        if not asset_pack:
            raise NotFoundError(f"Asset not found: {asset_id}")
        return asset_pack
