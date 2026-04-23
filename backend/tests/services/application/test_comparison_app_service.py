"""Focused regression tests for ComparisonAppService."""

from pathlib import Path
import sys

BACKEND_ROOT = Path(__file__).resolve().parents[3]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

import pytest
from unittest.mock import MagicMock

from app.contracts.errors import NotFoundError
from app.services.application.comparison_app_service import ComparisonAppService
from app.utils.locale import set_locale

set_locale("en")


class TestComparisonAppServiceCreate:
    def test_raises_when_mode_missing(self):
        with pytest.raises(ValueError, match="mode"):
            ComparisonAppService.create_comparison({})

    def test_raises_when_run_vs_run_missing_ids(self):
        with pytest.raises(ValueError, match="left_simulation_id"):
            ComparisonAppService.create_comparison({"mode": "run_vs_run"})

    def test_raises_when_run_vs_run_simulation_not_found(self, monkeypatch):
        monkeypatch.setattr(
            "app.services.application.comparison_app_service.SimulationManager.get_simulation",
            lambda self, sim_id: None,
        )

        with pytest.raises(NotFoundError):
            ComparisonAppService.create_comparison({
                "mode": "run_vs_run",
                "left_simulation_id": "sim_left",
                "right_simulation_id": "sim_right",
            })

    def test_raises_when_run_vs_run_non_consumer(self, monkeypatch):
        fake_state = MagicMock()
        fake_state.project_type = "default"

        monkeypatch.setattr(
            "app.services.application.comparison_app_service.SimulationManager.get_simulation",
            lambda self, sim_id: fake_state,
        )
        monkeypatch.setattr(
            "app.services.application.comparison_app_service.ConsumerApiGuard.check_consumer_simulation",
            lambda st: (False, "Must be consumer_test"),
        )

        with pytest.raises(ValueError, match="consumer_test"):
            ComparisonAppService.create_comparison({
                "mode": "run_vs_run",
                "left_simulation_id": "sim_left",
                "right_simulation_id": "sim_right",
            })

    def test_creates_run_vs_run_successfully(self, monkeypatch):
        fake_state = MagicMock()
        fake_state.project_type = "consumer_test"

        monkeypatch.setattr(
            "app.services.application.comparison_app_service.SimulationManager.get_simulation",
            lambda self, sim_id: fake_state,
        )
        monkeypatch.setattr(
            "app.services.application.comparison_app_service.ConsumerApiGuard.check_consumer_simulation",
            lambda st: (True, None),
        )
        monkeypatch.setattr(
            "app.services.application.comparison_app_service.create_comparison",
            lambda **kwargs: {"comparison_id": "cmp_123", "mode": "run_vs_run"},
        )

        result = ComparisonAppService.create_comparison({
            "mode": "run_vs_run",
            "left_simulation_id": "sim_left",
            "right_simulation_id": "sim_right",
        })

        assert result["comparison_id"] == "cmp_123"

    def test_raises_when_branch_vs_base_missing_ids(self):
        with pytest.raises(ValueError, match="simulation_id"):
            ComparisonAppService.create_comparison({"mode": "branch_vs_base"})

    def test_raises_when_project_vs_project_missing_ids(self):
        with pytest.raises(ValueError, match="left_project_id"):
            ComparisonAppService.create_comparison({"mode": "project_vs_project"})

    def test_raises_when_project_vs_project_not_found(self, monkeypatch):
        monkeypatch.setattr(
            "app.services.application.comparison_app_service.ProjectManager.get_project",
            lambda pid: None,
        )

        with pytest.raises(NotFoundError):
            ComparisonAppService.create_comparison({
                "mode": "project_vs_project",
                "left_project_id": "proj_left",
                "right_project_id": "proj_right",
            })

    def test_raises_on_unsupported_mode(self):
        with pytest.raises(ValueError, match="Unsupported"):
            ComparisonAppService.create_comparison({"mode": "unknown_mode"})


class TestComparisonAppServiceList:
    def test_raises_when_project_id_missing(self):
        with pytest.raises(ValueError, match="project_id"):
            ComparisonAppService.list_comparisons("")

    def test_returns_items(self, monkeypatch):
        monkeypatch.setattr(
            "app.services.application.comparison_app_service.list_comparisons",
            lambda pid: [{"comparison_id": "cmp_1"}],
        )

        result = ComparisonAppService.list_comparisons("proj_123")
        assert len(result) == 1


class TestComparisonAppServiceGet:
    def test_raises_when_not_found(self, monkeypatch):
        monkeypatch.setattr(
            "app.services.application.comparison_app_service.get_comparison",
            lambda cid: None,
        )

        with pytest.raises(NotFoundError):
            ComparisonAppService.get_comparison("cmp_missing")

    def test_backfills_confidence_for_old_snapshots(self, monkeypatch):
        old_snapshot = {
            "comparison_id": "cmp_old",
            "left_confidence": {"confidence_score": 0.8, "confidence_label": "high"},
            "right_confidence": None,
        }

        monkeypatch.setattr(
            "app.services.application.comparison_app_service.get_comparison",
            lambda cid: old_snapshot.copy(),
        )

        result = ComparisonAppService.get_comparison("cmp_old")

        assert "comparison_confidence" in result
        assert result["comparison_confidence"] is not None

    def test_does_not_mutate_confidence_when_present(self, monkeypatch):
        snapshot = {
            "comparison_id": "cmp_new",
            "comparison_confidence": {"score": 0.9},
        }

        monkeypatch.setattr(
            "app.services.application.comparison_app_service.get_comparison",
            lambda cid: snapshot.copy(),
        )

        result = ComparisonAppService.get_comparison("cmp_new")

        assert result["comparison_confidence"] == {"score": 0.9}
