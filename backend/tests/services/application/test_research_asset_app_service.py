"""Focused regression tests for ResearchAssetAppService."""

from pathlib import Path
import sys

BACKEND_ROOT = Path(__file__).resolve().parents[3]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

import pytest
from unittest.mock import MagicMock

from app.contracts.errors import NotFoundError
from app.services.application.research_asset_app_service import ResearchAssetAppService
from app.utils.locale import set_locale

set_locale("en")


class TestResearchAssetAppServiceExport:
    def test_raises_when_project_id_missing(self):
        with pytest.raises(ValueError, match="project_id"):
            ResearchAssetAppService.export_research_asset(
                project_id="",
                simulation_id="sim_123",
            )

    def test_raises_when_simulation_id_missing(self):
        with pytest.raises(ValueError, match="simulation_id"):
            ResearchAssetAppService.export_research_asset(
                project_id="proj_123",
                simulation_id="",
            )

    def test_raises_when_project_not_consumer(self, monkeypatch):
        fake_project = MagicMock()
        fake_project.project_type = "default"

        monkeypatch.setattr(
            "app.services.application.research_asset_app_service.ProjectManager.get_project",
            lambda pid: fake_project,
        )
        monkeypatch.setattr(
            "app.services.application.research_asset_app_service.ConsumerApiGuard.check_consumer_project",
            lambda proj: (False, "Project must be consumer_test"),
        )

        with pytest.raises(ValueError, match="consumer_test"):
            ResearchAssetAppService.export_research_asset(
                project_id="proj_123",
                simulation_id="sim_123",
            )

    def test_raises_when_simulation_not_found(self, monkeypatch):
        fake_project = MagicMock()
        fake_project.project_type = "consumer_test"

        monkeypatch.setattr(
            "app.services.application.research_asset_app_service.ProjectManager.get_project",
            lambda pid: fake_project,
        )
        monkeypatch.setattr(
            "app.services.application.research_asset_app_service.ConsumerApiGuard.check_consumer_project",
            lambda proj: (True, None),
        )
        monkeypatch.setattr(
            "app.services.application.research_asset_app_service.SimulationManager.get_simulation",
            lambda self, sim_id: None,
        )

        with pytest.raises(NotFoundError):
            ResearchAssetAppService.export_research_asset(
                project_id="proj_123",
                simulation_id="sim_missing",
            )

    def test_raises_when_simulation_does_not_belong_to_project(self, monkeypatch):
        fake_project = MagicMock()
        fake_project.project_type = "consumer_test"

        fake_state = MagicMock()
        fake_state.project_id = "proj_other"

        monkeypatch.setattr(
            "app.services.application.research_asset_app_service.ProjectManager.get_project",
            lambda pid: fake_project,
        )
        monkeypatch.setattr(
            "app.services.application.research_asset_app_service.ConsumerApiGuard.check_consumer_project",
            lambda proj: (True, None),
        )
        monkeypatch.setattr(
            "app.services.application.research_asset_app_service.SimulationManager.get_simulation",
            lambda self, sim_id: fake_state,
        )

        with pytest.raises(ValueError, match="does not belong"):
            ResearchAssetAppService.export_research_asset(
                project_id="proj_123",
                simulation_id="sim_123",
            )

    def test_returns_asset_pack_on_success(self, monkeypatch):
        fake_project = MagicMock()
        fake_project.project_type = "consumer_test"

        fake_state = MagicMock()
        fake_state.project_id = "proj_123"

        monkeypatch.setattr(
            "app.services.application.research_asset_app_service.ProjectManager.get_project",
            lambda pid: fake_project,
        )
        monkeypatch.setattr(
            "app.services.application.research_asset_app_service.ConsumerApiGuard.check_consumer_project",
            lambda proj: (True, None),
        )
        monkeypatch.setattr(
            "app.services.application.research_asset_app_service.SimulationManager.get_simulation",
            lambda self, sim_id: fake_state,
        )
        monkeypatch.setattr(
            "app.services.application.research_asset_app_service.export_asset",
            lambda **kwargs: {"asset_id": "asset_123", "project_id": "proj_123"},
        )

        result = ResearchAssetAppService.export_research_asset(
            project_id="proj_123",
            simulation_id="sim_123",
            name="Test Asset",
        )

        assert result["asset_id"] == "asset_123"


class TestResearchAssetAppServiceList:
    def test_raises_when_project_id_missing(self):
        with pytest.raises(ValueError, match="project_id"):
            ResearchAssetAppService.list_research_assets("")

    def test_raises_when_project_not_found(self, monkeypatch):
        monkeypatch.setattr(
            "app.services.application.research_asset_app_service.ProjectManager.get_project",
            lambda pid: None,
        )

        with pytest.raises(NotFoundError):
            ResearchAssetAppService.list_research_assets("proj_missing")

    def test_returns_items_on_success(self, monkeypatch):
        fake_project = MagicMock()
        monkeypatch.setattr(
            "app.services.application.research_asset_app_service.ProjectManager.get_project",
            lambda pid: fake_project,
        )
        monkeypatch.setattr(
            "app.services.application.research_asset_app_service.list_assets",
            lambda pid: [{"asset_id": "a1"}, {"asset_id": "a2"}],
        )

        result = ResearchAssetAppService.list_research_assets("proj_123")
        assert len(result) == 2


class TestResearchAssetAppServiceGet:
    def test_raises_when_asset_not_found(self, monkeypatch):
        monkeypatch.setattr(
            "app.services.application.research_asset_app_service.get_asset",
            lambda aid: None,
        )

        with pytest.raises(ValueError, match="not found"):
            ResearchAssetAppService.get_research_asset("asset_missing")

    def test_returns_asset_when_found(self, monkeypatch):
        monkeypatch.setattr(
            "app.services.application.research_asset_app_service.get_asset",
            lambda aid: {"asset_id": aid, "name": "Test"},
        )

        result = ResearchAssetAppService.get_research_asset("asset_123")
        assert result["name"] == "Test"
