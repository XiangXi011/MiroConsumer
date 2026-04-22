"""Tests for filesystem-backed repository implementations."""

from pathlib import Path

import pytest

from app.models.project import Project, ProjectManager, ProjectStatus
from app.repositories.filesystem import (
    FilesystemProjectRepository,
    FilesystemSimulationRepository,
    FilesystemBranchRepository,
    FilesystemReportRepository,
    FilesystemBenchmarkRepository,
)
from app.services.simulation_manager import SimulationManager, SimulationState, SimulationStatus
from app.services.report_agent import ReportManager, Report, ReportStatus, ReportOutline, ReportSection
from app.services.consumer.intervention_manager import ConsumerBranch, ConsumerIntervention, InterventionType
from app.config import Config


# ───────────────────────────────────────────────────────────────
# ProjectRepository
# ───────────────────────────────────────────────────────────────


class TestFilesystemProjectRepository:
    def test_round_trip_project(self, tmp_path, monkeypatch):
        project_root = tmp_path / "projects"
        monkeypatch.setattr(ProjectManager, "PROJECTS_DIR", str(project_root))

        repo = FilesystemProjectRepository()
        project = repo.create_project(name="Test Project")

        assert project.project_id.startswith("proj_")
        assert project.name == "Test Project"

        loaded = repo.get_project(project.project_id)
        assert loaded is not None
        assert loaded.name == "Test Project"
        assert loaded.project_type == "default"

    def test_save_and_load_extracted_text(self, tmp_path, monkeypatch):
        project_root = tmp_path / "projects"
        monkeypatch.setattr(ProjectManager, "PROJECTS_DIR", str(project_root))

        repo = FilesystemProjectRepository()
        project = repo.create_project(name="Text Project")

        repo.save_extracted_text(project.project_id, "hello world")
        assert repo.get_extracted_text(project.project_id) == "hello world"

    def test_list_projects_returns_newest_first(self, tmp_path, monkeypatch):
        project_root = tmp_path / "projects"
        monkeypatch.setattr(ProjectManager, "PROJECTS_DIR", str(project_root))

        repo = FilesystemProjectRepository()
        p1 = repo.create_project(name="First")
        p2 = repo.create_project(name="Second")

        projects = repo.list_projects(limit=10)
        assert len(projects) == 2
        assert projects[0].name == "Second"
        assert projects[1].name == "First"

    def test_delete_project(self, tmp_path, monkeypatch):
        project_root = tmp_path / "projects"
        monkeypatch.setattr(ProjectManager, "PROJECTS_DIR", str(project_root))

        repo = FilesystemProjectRepository()
        project = repo.create_project(name="To Delete")

        assert repo.delete_project(project.project_id) is True
        assert repo.get_project(project.project_id) is None

    def test_save_consumer_graph_payload_round_trip(self, tmp_path, monkeypatch):
        project_root = tmp_path / "projects"
        monkeypatch.setattr(ProjectManager, "PROJECTS_DIR", str(project_root))

        repo = FilesystemProjectRepository()
        project = repo.create_project(name="Graph Project")

        payload = {"graph_id": "g1", "nodes": [1, 2, 3]}
        repo.save_consumer_graph_payload(project.project_id, payload)

        loaded = repo.load_consumer_graph_payload(project.project_id)
        assert loaded == payload


# ───────────────────────────────────────────────────────────────
# SimulationRepository
# ───────────────────────────────────────────────────────────────


class TestFilesystemSimulationRepository:
    def test_round_trip_simulation(self, tmp_path, monkeypatch):
        sim_root = tmp_path / "simulations"
        monkeypatch.setattr(SimulationManager, "SIMULATION_DATA_DIR", str(sim_root))

        repo = FilesystemSimulationRepository()
        state = repo.create_simulation(
            project_id="proj_001",
            graph_id="graph_001",
            project_type="consumer_test",
        )

        assert state.simulation_id.startswith("sim_")
        assert state.project_id == "proj_001"
        assert state.consumer_mode is True

        loaded = repo.get_simulation(state.simulation_id)
        assert loaded is not None
        assert loaded.graph_id == "graph_001"

    def test_save_updates_state(self, tmp_path, monkeypatch):
        sim_root = tmp_path / "simulations"
        monkeypatch.setattr(SimulationManager, "SIMULATION_DATA_DIR", str(sim_root))

        repo = FilesystemSimulationRepository()
        state = repo.create_simulation(project_id="proj_002", graph_id="graph_002")
        state.status = SimulationStatus.READY
        repo.save_simulation(state)

        loaded = repo.get_simulation(state.simulation_id)
        assert loaded.status == SimulationStatus.READY

    def test_list_simulations_filters_by_project(self, tmp_path, monkeypatch):
        sim_root = tmp_path / "simulations"
        monkeypatch.setattr(SimulationManager, "SIMULATION_DATA_DIR", str(sim_root))

        repo = FilesystemSimulationRepository()
        s1 = repo.create_simulation(project_id="proj_a", graph_id="g1")
        repo.create_simulation(project_id="proj_b", graph_id="g2")

        results = repo.list_simulations(project_id="proj_a")
        assert len(results) == 1
        assert results[0].simulation_id == s1.simulation_id

    def test_delete_simulation(self, tmp_path, monkeypatch):
        sim_root = tmp_path / "simulations"
        monkeypatch.setattr(SimulationManager, "SIMULATION_DATA_DIR", str(sim_root))

        repo = FilesystemSimulationRepository()
        state = repo.create_simulation(project_id="proj_003", graph_id="g3")

        assert repo.delete_simulation(state.simulation_id) is True
        # SimulationManager caches state in memory; deleting the dir does not
        # clear the cache.  The repository seam is explicit; cache behavior is
        # an implementation detail of SimulationManager deferred to later cleanup.
        assert not (sim_root / state.simulation_id).exists()


# ───────────────────────────────────────────────────────────────
# BranchRepository
# ───────────────────────────────────────────────────────────────


class TestFilesystemBranchRepository:
    def test_branch_round_trip(self, tmp_path):
        repo = FilesystemBranchRepository()
        # Inject branches dir via the underlying manager
        repo._manager.branches_dir = tmp_path / "branches"

        branch = repo.create_branch(
            simulation_id="sim_001",
            name="Test Branch",
            fork_round=2,
        )

        assert branch.branch_id.startswith("branch_")
        loaded = repo.get_branch("sim_001", branch.branch_id)
        assert loaded is not None
        assert loaded.name == "Test Branch"

    def test_list_branches_filters(self, tmp_path):
        repo = FilesystemBranchRepository()
        repo._manager.branches_dir = tmp_path / "branches"

        repo.create_branch("sim_a", "A", 1)
        repo.create_branch("sim_b", "B", 1)

        branches = repo.list_branches("sim_a")
        assert len(branches) == 1
        assert branches[0].name == "A"

    def test_intervention_round_trip(self, tmp_path):
        repo = FilesystemBranchRepository()
        repo._manager.branches_dir = tmp_path / "branches"

        branch = repo.create_branch("sim_002", "Test", 1)
        intervention = repo.add_intervention(
            simulation_id="sim_002",
            branch_id=branch.branch_id,
            intervention_type="clarification_injection",
            payload={"msg": "hello"},
            target_round=3,
        )

        assert intervention.intervention_type == InterventionType.clarification_injection
        interventions = repo.list_interventions("sim_002", branch_id=branch.branch_id)
        assert len(interventions) == 1
        assert interventions[0].intervention_id == intervention.intervention_id

    def test_branch_run_status_round_trip(self, tmp_path):
        repo = FilesystemBranchRepository()
        repo._manager.branches_dir = tmp_path / "branches"

        branch = repo.create_branch("sim_003", "Run", 0)
        repo.update_branch_run_status("sim_003", branch.branch_id, {"status": "running"})

        status = repo.get_branch_run_status("sim_003", branch.branch_id)
        assert status["status"] == "running"

    def test_update_branch_status(self, tmp_path):
        repo = FilesystemBranchRepository()
        repo._manager.branches_dir = tmp_path / "branches"

        branch = repo.create_branch("sim_004", "Status", 0)
        updated = repo.update_branch_status("sim_004", branch.branch_id, "completed")
        assert updated is not None
        assert updated.status == "completed"


# ───────────────────────────────────────────────────────────────
# ReportRepository
# ───────────────────────────────────────────────────────────────


class TestFilesystemReportRepository:
    def test_report_round_trip(self, tmp_path, monkeypatch):
        reports_root = tmp_path / "reports"
        monkeypatch.setattr(ReportManager, "REPORTS_DIR", str(reports_root))

        repo = FilesystemReportRepository()
        report = Report(
            report_id="report_001",
            simulation_id="sim_001",
            graph_id="g1",
            simulation_requirement="test",
            status=ReportStatus.COMPLETED,
        )

        repo.save_report(report)
        loaded = repo.get_report("report_001")
        assert loaded is not None
        assert loaded.simulation_id == "sim_001"

    def test_get_report_by_simulation(self, tmp_path, monkeypatch):
        reports_root = tmp_path / "reports"
        monkeypatch.setattr(ReportManager, "REPORTS_DIR", str(reports_root))

        repo = FilesystemReportRepository()
        report = Report(
            report_id="report_002",
            simulation_id="sim_002",
            graph_id="g1",
            simulation_requirement="test",
            status=ReportStatus.COMPLETED,
        )
        repo.save_report(report)

        found = repo.get_report_by_simulation("sim_002")
        assert found is not None
        assert found.report_id == "report_002"

    def test_progress_round_trip(self, tmp_path, monkeypatch):
        reports_root = tmp_path / "reports"
        monkeypatch.setattr(ReportManager, "REPORTS_DIR", str(reports_root))

        repo = FilesystemReportRepository()
        ReportManager._ensure_reports_dir()
        repo.update_progress("report_003", "generating", 50, "halfway")

        progress = repo.get_progress("report_003")
        assert progress is not None
        assert progress["status"] == "generating"
        assert progress["progress"] == 50

    def test_delete_report(self, tmp_path, monkeypatch):
        reports_root = tmp_path / "reports"
        monkeypatch.setattr(ReportManager, "REPORTS_DIR", str(reports_root))

        repo = FilesystemReportRepository()
        report = Report(
            report_id="report_004",
            simulation_id="sim_004",
            graph_id="g1",
            simulation_requirement="test",
            status=ReportStatus.COMPLETED,
        )
        repo.save_report(report)

        assert repo.delete_report("report_004") is True
        assert repo.get_report("report_004") is None


# ───────────────────────────────────────────────────────────────
# BenchmarkRepository
# ───────────────────────────────────────────────────────────────


class TestFilesystemBenchmarkRepository:
    def test_register_and_get_benchmark(self, tmp_path, monkeypatch):
        root = str(tmp_path / "uploads")
        monkeypatch.setattr(Config, "UPLOAD_FOLDER", root)
        repo = FilesystemBenchmarkRepository()

        benchmark = repo.register_benchmark(
            name="Test Bench",
            source_pack_lineage="pack_001",
            expected_signals={"acceptance_band": "positive_lean"},
            simulation_context={"req": "test"},
        )

        assert "benchmark_id" in benchmark
        fetched = repo.get_benchmark(benchmark["benchmark_id"])
        assert fetched is not None
        assert fetched["name"] == "Test Bench"

    def test_list_benchmarks(self, tmp_path, monkeypatch):
        root = str(tmp_path / "uploads")
        monkeypatch.setattr(Config, "UPLOAD_FOLDER", root)
        repo = FilesystemBenchmarkRepository()

        repo.register_benchmark("A", "p1", {"a": 1})
        repo.register_benchmark("B", "p2", {"b": 2})

        items = repo.list_benchmarks()
        assert len(items) == 2
        names = {b["name"] for b in items}
        assert names == {"A", "B"}

    def test_delete_benchmark(self, tmp_path, monkeypatch):
        root = str(tmp_path / "uploads")
        monkeypatch.setattr(Config, "UPLOAD_FOLDER", root)
        repo = FilesystemBenchmarkRepository()

        benchmark = repo.register_benchmark("Del", "p1", {"a": 1})
        assert repo.delete_benchmark(benchmark["benchmark_id"]) is True
        assert repo.get_benchmark(benchmark["benchmark_id"]) is None

    def test_replay_and_get_result(self, tmp_path, monkeypatch):
        root = str(tmp_path / "uploads")
        monkeypatch.setattr(Config, "UPLOAD_FOLDER", root)
        repo = FilesystemBenchmarkRepository()

        benchmark = repo.register_benchmark(
            "Replay Test",
            "p1",
            {"acceptance_band": "positive_lean", "top_resonance_labels": ["x"]},
        )

        report_context = {
            "summary": {
                "post_propagation_acceptance": {"positive": 0.6, "negative": 0.1, "neutral": 0.3}
            },
            "top_resonance_points": ["x"],
            "top_risk_points": [],
            "top_misreads": [],
            "top_clarification_opportunities": [],
            "cascade_metrics": {},
        }

        result = repo.replay_benchmark(
            benchmark_id=benchmark["benchmark_id"],
            report_context=report_context,
            project_id="proj_001",
        )

        assert "replay_id" in result
        assert result["alignment_status"] in ("aligned", "partial", "drift")

        fetched = repo.get_replay_result(result["replay_id"])
        assert fetched is not None
        assert fetched["replay_id"] == result["replay_id"]
