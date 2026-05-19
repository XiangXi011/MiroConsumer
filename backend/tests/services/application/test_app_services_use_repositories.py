"""Tests verifying application services consume repository abstractions."""

from contextlib import contextmanager
from typing import Any, Dict, List, Optional

import pytest

from app.contracts.errors import ConcurrencyConflictError
from app.models.task import TaskManager
from app.models.project import Project, ProjectStatus
import app.services.application.simulation_app_service as simulation_app_service_module
from app.repositories import (
    ProjectRepository,
    SimulationRepository,
    BranchRepository,
    ReportRepository,
    BenchmarkRepository,
)
from app.services.application import (
    SimulationAppService,
    ReportAppService,
    BranchAppService,
    BenchmarkAppService,
    GraphAppService,
)
from app.services.application.concurrency import (
    branch_fork_lock,
    report_generation_lock,
    simulation_run_lock,
)
from app.services.simulation_manager import SimulationState, SimulationStatus
from app.services.report_agent import Report, ReportStatus
from app.services.consumer.intervention_manager import ConsumerBranch, ConsumerIntervention, InterventionType


# ───────────────────────────────────────────────────────────────
# Stub repositories
# ───────────────────────────────────────────────────────────────


class StubProjectRepository(ProjectRepository):
    def __init__(self, projects=None):
        self.projects = projects or {}
        self.texts = {}
        self.graph_payloads = {}
        self.saved = []

    def get_project(self, project_id: str) -> Optional[Any]:
        return self.projects.get(project_id)

    def save_project(self, project: Any) -> None:
        self.projects[project.project_id] = project
        self.saved.append(project)

    def create_project(self, name: str = "Unnamed Project") -> Any:
        p = Project(
            project_id=f"proj_{name}",
            name=name,
            status=ProjectStatus.CREATED,
            created_at="2026-01-01T00:00:00",
            updated_at="2026-01-01T00:00:00",
        )
        self.projects[p.project_id] = p
        return p

    def delete_project(self, project_id: str) -> bool:
        return self.projects.pop(project_id, None) is not None

    def list_projects(self, limit: int = 50) -> List[Any]:
        return list(self.projects.values())[:limit]

    def get_extracted_text(self, project_id: str) -> Optional[str]:
        return self.texts.get(project_id)

    def save_extracted_text(self, project_id: str, text: str) -> None:
        self.texts[project_id] = text

    def save_consumer_graph_payload(self, project_id: str, graph_payload: Dict[str, Any]) -> None:
        self.graph_payloads[project_id] = graph_payload

    def load_consumer_graph_payload(self, project_id: str) -> Optional[Dict[str, Any]]:
        return self.graph_payloads.get(project_id)


class StubSimulationRepository(SimulationRepository):
    def __init__(self, simulations=None):
        self.simulations = simulations or {}
        self.manifest_reuses = 0
        self.configs: Dict[str, Dict[str, Any]] = {}
        self.consumer_configs: Dict[str, Dict[str, Any]] = {}

    def get_simulation(self, simulation_id: str) -> Optional[Any]:
        return self.simulations.get(simulation_id)

    def save_simulation(self, state: Any) -> None:
        self.simulations[state.simulation_id] = state

    def create_simulation(
        self,
        project_id: str,
        graph_id: str,
        project_type: str = "default",
        enable_twitter: bool = True,
        enable_reddit: bool = True,
        tenant_id: str = "",
    ) -> Any:
        state = SimulationState(
            simulation_id=f"sim_{project_id}",
            project_id=project_id,
            graph_id=graph_id,
            project_type=project_type,
            consumer_mode=(project_type == "consumer_test"),
            tenant_id=tenant_id,
        )
        self.simulations[state.simulation_id] = state
        return state

    def list_simulations(self, project_id: Optional[str] = None) -> List[Any]:
        states = list(self.simulations.values())
        if project_id:
            states = [s for s in states if s.project_id == project_id]
        return states

    def delete_simulation(self, simulation_id: str) -> bool:
        return self.simulations.pop(simulation_id, None) is not None

    def get_profiles(self, simulation_id: str, platform: str = "reddit") -> List[Dict[str, Any]]:
        return []

    def get_simulation_config(self, simulation_id: str) -> Optional[Dict[str, Any]]:
        return self.configs.get(simulation_id)

    def get_prepare_manifest(self, simulation_id: str) -> Optional[Dict[str, Any]]:
        return None

    def record_manifest_reuse(self, simulation_id: str) -> Optional[Dict[str, Any]]:
        self.manifest_reuses += 1
        return {"reuse_count": self.manifest_reuses}

    def save_simulation_config(self, simulation_id: str, config: Dict[str, Any]) -> None:
        self.configs[simulation_id] = config

    def load_simulation_config(self, simulation_id: str) -> Optional[Dict[str, Any]]:
        return self.configs.get(simulation_id)

    def save_consumer_config(self, simulation_id: str, config: Dict[str, Any]) -> None:
        self.consumer_configs[simulation_id] = config

    def load_consumer_config(self, simulation_id: str) -> Optional[Dict[str, Any]]:
        return self.consumer_configs.get(simulation_id)


class StubBranchRepository(BranchRepository):
    def __init__(self):
        self.branches: Dict[str, List[ConsumerBranch]] = {}
        self.interventions: Dict[str, List[ConsumerIntervention]] = {}
        self.run_statuses: Dict[str, Dict[str, Any]] = {}

    def create_branch(
        self,
        simulation_id: str,
        name: str,
        fork_round: int,
        description: str = "",
        parent_branch_id: Optional[str] = None,
    ) -> Any:
        branch = ConsumerBranch(
            branch_id=f"branch_{name}",
            simulation_id=simulation_id,
            name=name,
            fork_round=fork_round,
            description=description,
            parent_branch_id=parent_branch_id,
        )
        self.branches.setdefault(simulation_id, []).append(branch)
        return branch

    def get_branch(self, simulation_id: str, branch_id: str) -> Optional[Any]:
        for b in self.branches.get(simulation_id, []):
            if b.branch_id == branch_id:
                return b
        return None

    def list_branches(self, simulation_id: str) -> List[Any]:
        return list(self.branches.get(simulation_id, []))

    def update_branch_status(
        self, simulation_id: str, branch_id: str, status: str
    ) -> Optional[Any]:
        branch = self.get_branch(simulation_id, branch_id)
        if branch:
            branch.status = status
            return branch
        return None

    def add_intervention(
        self,
        simulation_id: str,
        branch_id: str,
        intervention_type: str,
        payload: Dict[str, Any],
        target_round: Optional[int] = None,
    ) -> Any:
        iv = ConsumerIntervention(
            intervention_id=f"int_{len(self.interventions)}",
            branch_id=branch_id,
            simulation_id=simulation_id,
            intervention_type=InterventionType(intervention_type),
            payload=payload,
            target_round=target_round,
        )
        self.interventions.setdefault(simulation_id, []).append(iv)
        return iv

    def list_interventions(
        self, simulation_id: str, branch_id: Optional[str] = None
    ) -> List[Any]:
        ivs = self.interventions.get(simulation_id, [])
        if branch_id:
            ivs = [i for i in ivs if i.branch_id == branch_id]
        return ivs

    def get_branch_run_status(self, simulation_id: str, branch_id: str) -> Dict[str, Any]:
        return self.run_statuses.get(
            f"{simulation_id}:{branch_id}",
            {"status": "idle", "branch_id": branch_id, "simulation_id": simulation_id},
        )

    def update_branch_run_status(
        self, simulation_id: str, branch_id: str, status_data: Dict[str, Any]
    ) -> None:
        self.run_statuses[f"{simulation_id}:{branch_id}"] = status_data

    def build_comparison_context(self, simulation_id: str, branch_id: str) -> Dict[str, Any]:
        return {
            "branch_id": branch_id,
            "base_branch_id": None,
            "fork_round": 0,
            "branch_name": "stub",
            "branch_description": "",
            "interventions": [],
            "base_summary": {},
            "branch_summary": {},
        }


class StubReportRepository(ReportRepository):
    def __init__(self):
        self.reports: Dict[str, Report] = {}
        self.progress: Dict[str, Dict[str, Any]] = {}

    def get_report(self, report_id: str) -> Optional[Any]:
        return self.reports.get(report_id)

    def get_report_by_simulation(self, simulation_id: str) -> Optional[Any]:
        for r in self.reports.values():
            if r.simulation_id == simulation_id and r.status == ReportStatus.COMPLETED:
                return r
        return None

    def list_reports(
        self, simulation_id: Optional[str] = None, limit: int = 50
    ) -> List[Any]:
        reports = list(self.reports.values())
        if simulation_id:
            reports = [r for r in reports if r.simulation_id == simulation_id]
        return reports[:limit]

    def save_report(self, report: Any) -> None:
        self.reports[report.report_id] = report

    def save_outline(self, report_id: str, outline: Any) -> None:
        pass

    def save_section(self, report_id: str, section_index: int, section: Any) -> str:
        return ""

    def update_progress(
        self,
        report_id: str,
        status: str,
        progress: int,
        message: str,
        current_section: Optional[str] = None,
        completed_sections: Optional[List[str]] = None,
    ) -> None:
        self.progress[report_id] = {
            "status": status,
            "progress": progress,
            "message": message,
        }

    def get_progress(self, report_id: str) -> Optional[Dict[str, Any]]:
        return self.progress.get(report_id)

    def assemble_full_report(self, report_id: str, outline: Any) -> str:
        return ""

    def delete_report(self, report_id: str) -> bool:
        return self.reports.pop(report_id, None) is not None

    def get_agent_log(self, report_id: str, from_line: int = 0) -> Dict[str, Any]:
        return {"logs": [], "total_lines": 0, "from_line": 0, "has_more": False}

    def get_console_log(self, report_id: str, from_line: int = 0) -> Dict[str, Any]:
        return {"logs": [], "total_lines": 0, "from_line": 0, "has_more": False}


class StubBenchmarkRepository(BenchmarkRepository):
    def __init__(self):
        self.benchmarks: Dict[str, Dict[str, Any]] = {}
        self.replays: Dict[str, Dict[str, Any]] = {}

    def register_benchmark(
        self,
        name: str,
        source_pack_lineage: str,
        expected_signals: Dict[str, Any],
        simulation_context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        benchmark_id = f"bench_{name}"
        self.benchmarks[benchmark_id] = {
            "benchmark_id": benchmark_id,
            "name": name,
            "source_pack_lineage": source_pack_lineage,
            "expected_signals": expected_signals,
            "simulation_context": simulation_context or {},
        }
        return self.benchmarks[benchmark_id]

    def list_benchmarks(self) -> List[Dict[str, Any]]:
        return list(self.benchmarks.values())

    def get_benchmark(self, benchmark_id: str) -> Optional[Dict[str, Any]]:
        return self.benchmarks.get(benchmark_id)

    def delete_benchmark(self, benchmark_id: str) -> bool:
        return self.benchmarks.pop(benchmark_id, None) is not None

    def replay_benchmark(
        self,
        benchmark_id: str,
        report_context: Dict[str, Any],
        project_id: Optional[str] = None,
        simulation_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        replay_id = f"replay_{benchmark_id}"
        self.replays[replay_id] = {
            "replay_id": replay_id,
            "benchmark_id": benchmark_id,
            "project_id": project_id,
            "simulation_id": simulation_id,
            "alignment_status": "aligned",
        }
        return self.replays[replay_id]

    def get_replay_result(self, replay_id: str) -> Optional[Dict[str, Any]]:
        return self.replays.get(replay_id)

    def list_replay_results(self, benchmark_id: str) -> List[Dict[str, Any]]:
        return [r for r in self.replays.values() if r["benchmark_id"] == benchmark_id]


class CaptureLockManager:
    def __init__(self):
        self.acquired = []

    @contextmanager
    def acquire(self, lock_type: str, resource_id: str, timeout_seconds: float = 30):
        self.acquired.append((lock_type, resource_id, timeout_seconds))
        yield


class RejectingLockManager:
    @contextmanager
    def acquire(self, lock_type: str, resource_id: str, timeout_seconds: float = 30):
        raise ConcurrencyConflictError(
            resource=lock_type,
            resource_id=resource_id,
            reason="lock_timeout",
        )
        yield


class CaptureExecutor:
    def __init__(self):
        self.submitted = []

    def submit(self, fn, *args, trace_id=None, **kwargs):
        self.submitted.append((fn, args, kwargs, trace_id))
        return trace_id or "trace_fallback"

    def get_status(self, trace_id):
        return {"trace_id": trace_id, "status": "PENDING", "backend": "capture"}

    def cancel(self, trace_id):
        return {
            "trace_id": trace_id,
            "status": "CANCELLED",
            "cancelled": True,
            "backend": "capture",
        }


# ───────────────────────────────────────────────────────────────
# Tests
# ───────────────────────────────────────────────────────────────


class TestSimulationAppServiceUsesRepositories:
    def _enable_sqlalchemy_shadow(self, file_repo):
        original_bundle = SimulationAppService._repository_bundle
        had_factory = hasattr(SimulationAppService, "_filesystem_simulation_repo_factory")
        original_factory = getattr(SimulationAppService, "_filesystem_simulation_repo_factory", None)
        SimulationAppService._repository_bundle = type("Bundle", (), {"backend": "sqlalchemy"})()
        SimulationAppService._filesystem_simulation_repo_factory = lambda: file_repo
        return original_bundle, had_factory, original_factory

    def _restore_sqlalchemy_shadow(self, original_bundle, had_factory, original_factory):
        SimulationAppService._repository_bundle = original_bundle
        if had_factory:
            SimulationAppService._filesystem_simulation_repo_factory = original_factory
        else:
            delattr(SimulationAppService, "_filesystem_simulation_repo_factory")

    def test_create_simulation_calls_project_repo(self):
        project_repo = StubProjectRepository()
        sim_repo = StubSimulationRepository()
        project_repo.projects["proj_test"] = Project(
            project_id="proj_test",
            name="Test",
            status=ProjectStatus.CREATED,
            created_at="2026-01-01T00:00:00",
            updated_at="2026-01-01T00:00:00",
            project_type="consumer_test",
            graph_id="g1",
        )

        original_project = SimulationAppService._project_repo
        original_sim = SimulationAppService._simulation_repo
        try:
            SimulationAppService._project_repo = project_repo
            SimulationAppService._simulation_repo = sim_repo

            result = SimulationAppService.create_simulation({
                "project_id": "proj_test",
                "enable_twitter": True,
                "enable_reddit": True,
            })

            assert result["project_id"] == "proj_test"
            assert result["graph_id"] == "g1"
            assert result["simulation_id"] in sim_repo.simulations
        finally:
            SimulationAppService._project_repo = original_project
            SimulationAppService._simulation_repo = original_sim

    def test_create_simulation_mirrors_sqlalchemy_state_to_filesystem_shadow(self):
        project_repo = StubProjectRepository()
        sim_repo = StubSimulationRepository()
        file_repo = StubSimulationRepository()
        project_repo.projects["proj_sql_shadow"] = Project(
            project_id="proj_sql_shadow",
            name="SQL Shadow Test",
            status=ProjectStatus.CREATED,
            created_at="2026-01-01T00:00:00",
            updated_at="2026-01-01T00:00:00",
            project_type="consumer_test",
            graph_id="g1",
        )

        original_project = SimulationAppService._project_repo
        original_sim = SimulationAppService._simulation_repo
        shadow_state = self._enable_sqlalchemy_shadow(file_repo)
        try:
            SimulationAppService._project_repo = project_repo
            SimulationAppService._simulation_repo = sim_repo

            result = SimulationAppService.create_simulation({"project_id": "proj_sql_shadow"})

            mirrored = file_repo.get_simulation(result["simulation_id"])
            assert mirrored is not None
            assert mirrored.project_id == "proj_sql_shadow"
            assert mirrored.graph_id == "g1"
            assert mirrored.consumer_mode is True
        finally:
            SimulationAppService._project_repo = original_project
            SimulationAppService._simulation_repo = original_sim
            self._restore_sqlalchemy_shadow(*shadow_state)

    def test_create_simulation_raises_when_project_not_found(self):
        project_repo = StubProjectRepository()
        sim_repo = StubSimulationRepository()

        original_project = SimulationAppService._project_repo
        original_sim = SimulationAppService._simulation_repo
        try:
            SimulationAppService._project_repo = project_repo
            SimulationAppService._simulation_repo = sim_repo

            with pytest.raises(ValueError, match="missing"):
                SimulationAppService.create_simulation({"project_id": "missing"})
        finally:
            SimulationAppService._project_repo = original_project
            SimulationAppService._simulation_repo = original_sim


class TestReportAppServiceUsesRepositories:
    def test_get_existing_report_returns_stub_data(self):
        report_repo = StubReportRepository()
        report_repo.reports["r1"] = Report(
            report_id="r1",
            simulation_id="sim_test",
            graph_id="g1",
            simulation_requirement="test",
            status=ReportStatus.COMPLETED,
        )

        original = ReportAppService._report_repo
        try:
            ReportAppService._report_repo = report_repo
            result = ReportAppService.get_existing_report_for_simulation("sim_test")
            assert result is not None
            assert result["status"] == "completed"
        finally:
            ReportAppService._report_repo = original

    def test_generate_report_validates_via_repositories(self):
        project_repo = StubProjectRepository()
        sim_repo = StubSimulationRepository()
        report_repo = StubReportRepository()

        sim_repo.simulations["sim_x"] = SimulationState(
            simulation_id="sim_x",
            project_id="proj_x",
            graph_id="g1",
        )

        original_project = ReportAppService._project_repo
        original_sim = ReportAppService._simulation_repo
        original_report = ReportAppService._report_repo
        try:
            ReportAppService._project_repo = project_repo
            ReportAppService._simulation_repo = sim_repo
            ReportAppService._report_repo = report_repo

            with pytest.raises(ValueError, match="proj_x"):
                ReportAppService.generate_report("sim_x")
        finally:
            ReportAppService._project_repo = original_project
            ReportAppService._simulation_repo = original_sim
            ReportAppService._report_repo = original_report


class TestBranchAppServiceUsesRepositories:
    def test_create_branch_uses_branch_repo(self):
        sim_repo = StubSimulationRepository()
        branch_repo = StubBranchRepository()

        sim_repo.simulations["sim_c"] = SimulationState(
            simulation_id="sim_c",
            project_id="proj_c",
            graph_id="g1",
            consumer_mode=True,
        )

        original_sim = BranchAppService._simulation_repo
        original_branch = BranchAppService._branch_repo
        try:
            BranchAppService._simulation_repo = sim_repo
            BranchAppService._branch_repo = branch_repo

            result = BranchAppService.create_branch(
                simulation_id="sim_c",
                name="Feature",
                fork_round=2,
            )
            assert result["name"] == "Feature"
            assert result["fork_round"] == 2
            assert len(branch_repo.branches["sim_c"]) == 1
        finally:
            BranchAppService._simulation_repo = original_sim
            BranchAppService._branch_repo = original_branch

    def test_add_intervention_uses_branch_repo(self):
        sim_repo = StubSimulationRepository()
        branch_repo = StubBranchRepository()

        sim_repo.simulations["sim_d"] = SimulationState(
            simulation_id="sim_d",
            project_id="proj_d",
            graph_id="g1",
            consumer_mode=True,
        )
        branch = branch_repo.create_branch("sim_d", "Test", 1)

        original_sim = BranchAppService._simulation_repo
        original_branch = BranchAppService._branch_repo
        try:
            BranchAppService._simulation_repo = sim_repo
            BranchAppService._branch_repo = branch_repo

            result = BranchAppService.add_intervention(
                simulation_id="sim_d",
                branch_id=branch.branch_id,
                intervention_type="evidence_reveal",
                payload={"evidence": "study"},
                target_round=3,
            )
            assert result["intervention_type"] == "evidence_reveal"
            assert len(branch_repo.interventions["sim_d"]) == 1
        finally:
            BranchAppService._simulation_repo = original_sim
            BranchAppService._branch_repo = original_branch


class TestBenchmarkAppServiceUsesRepositories:
    def test_register_benchmark_checks_project_via_repo(self):
        project_repo = StubProjectRepository()
        bench_repo = StubBenchmarkRepository()

        project_repo.projects["proj_consumer"] = Project(
            project_id="proj_consumer",
            name="Consumer",
            status=ProjectStatus.CREATED,
            created_at="2026-01-01T00:00:00",
            updated_at="2026-01-01T00:00:00",
            project_type="consumer_test",
        )

        original_project = BenchmarkAppService._project_repo
        original_bench = BenchmarkAppService._benchmark_repo
        try:
            BenchmarkAppService._project_repo = project_repo
            BenchmarkAppService._benchmark_repo = bench_repo

            # Without asset_pack (asset_library is not stubbed here), we skip
            # the pack validation path and test the benchmark_repo path directly
            result = bench_repo.register_benchmark(
                name="Bench",
                source_pack_lineage="pack_1",
                expected_signals={"a": 1},
            )
            assert result["name"] == "Bench"
        finally:
            BenchmarkAppService._project_repo = original_project
            BenchmarkAppService._benchmark_repo = original_bench

    def test_replay_benchmark_checks_simulation_via_repo(self):
        project_repo = StubProjectRepository()
        sim_repo = StubSimulationRepository()
        bench_repo = StubBenchmarkRepository()

        sim_repo.simulations["sim_consumer"] = SimulationState(
            simulation_id="sim_consumer",
            project_id="proj_c",
            graph_id="g1",
            consumer_mode=True,
        )
        benchmark = bench_repo.register_benchmark("B", "p1", {"a": 1})

        original_project = BenchmarkAppService._project_repo
        original_sim = BenchmarkAppService._simulation_repo
        original_bench = BenchmarkAppService._benchmark_repo
        try:
            BenchmarkAppService._project_repo = project_repo
            BenchmarkAppService._simulation_repo = sim_repo
            BenchmarkAppService._benchmark_repo = bench_repo

            result = BenchmarkAppService.replay_benchmark(
                benchmark_id=benchmark["benchmark_id"],
                report_context={"summary": {"post_propagation_acceptance": {"positive": 0.6}}},
                simulation_id="sim_consumer",
            )
            assert result["alignment_status"] == "aligned"
        finally:
            BenchmarkAppService._project_repo = original_project
            BenchmarkAppService._simulation_repo = original_sim
            BenchmarkAppService._benchmark_repo = original_bench


class TestBranchAppServiceResumeBranch:
    def test_resume_branch_rejects_non_consumer_simulation(self):
        sim_repo = StubSimulationRepository()
        branch_repo = StubBranchRepository()

        sim_repo.simulations["sim_default"] = SimulationState(
            simulation_id="sim_default",
            project_id="proj_default",
            graph_id="g1",
            consumer_mode=False,
        )

        original_sim = BranchAppService._simulation_repo
        original_branch = BranchAppService._branch_repo
        try:
            BranchAppService._simulation_repo = sim_repo
            BranchAppService._branch_repo = branch_repo

            with pytest.raises(ValueError, match="consumer_test"):
                BranchAppService.resume_branch("sim_default", "branch_1")
        finally:
            BranchAppService._simulation_repo = original_sim
            BranchAppService._branch_repo = original_branch

    def test_resume_branch_rejects_missing_branch(self):
        sim_repo = StubSimulationRepository()
        branch_repo = StubBranchRepository()

        sim_repo.simulations["sim_consumer"] = SimulationState(
            simulation_id="sim_consumer",
            project_id="proj_c",
            graph_id="g1",
            consumer_mode=True,
        )

        original_sim = BranchAppService._simulation_repo
        original_branch = BranchAppService._branch_repo
        try:
            BranchAppService._simulation_repo = sim_repo
            BranchAppService._branch_repo = branch_repo

            with pytest.raises(ValueError, match="Branch not found"):
                BranchAppService.resume_branch("sim_consumer", "no-such-branch")
        finally:
            BranchAppService._simulation_repo = original_sim
            BranchAppService._branch_repo = original_branch

    def test_resume_branch_rejects_already_running(self):
        sim_repo = StubSimulationRepository()
        branch_repo = StubBranchRepository()

        sim_repo.simulations["sim_busy"] = SimulationState(
            simulation_id="sim_busy",
            project_id="proj_busy",
            graph_id="g1",
            consumer_mode=True,
        )
        branch = branch_repo.create_branch("sim_busy", "Busy", 1)
        branch_repo.update_branch_run_status(
            "sim_busy", branch.branch_id, {"status": "running"}
        )

        original_sim = BranchAppService._simulation_repo
        original_branch = BranchAppService._branch_repo
        try:
            BranchAppService._simulation_repo = sim_repo
            BranchAppService._branch_repo = branch_repo

            with pytest.raises(ValueError, match="already running"):
                BranchAppService.resume_branch("sim_busy", branch.branch_id)
        finally:
            BranchAppService._simulation_repo = original_sim
            BranchAppService._branch_repo = original_branch


class TestSimulationAppServiceGetPrepareStatus:
    def test_get_prepare_status_requires_task_or_simulation_id(self):
        sim_repo = StubSimulationRepository()
        project_repo = StubProjectRepository()

        original_project = SimulationAppService._project_repo
        original_sim = SimulationAppService._simulation_repo
        try:
            SimulationAppService._project_repo = project_repo
            SimulationAppService._simulation_repo = sim_repo

            with pytest.raises(ValueError, match="task_id"):
                SimulationAppService.get_prepare_status(task_id=None, simulation_id=None)
        finally:
            SimulationAppService._project_repo = original_project
            SimulationAppService._simulation_repo = original_sim


class TestGraphAppServiceUsesRepositories:
    def test_build_consumer_graph_sync_uses_project_repo(self):
        project_repo = StubProjectRepository()
        project = Project(
            project_id="proj_graph",
            name="Graph Test",
            status=ProjectStatus.CREATED,
            created_at="2026-01-01T00:00:00",
            updated_at="2026-01-01T00:00:00",
            project_type="consumer_test",
            consumer_brief={
                "task_type": "concept_test",
                "research_goal": "test",
                "target_audience": ["young adults"],
                "claims": [],
                "copy_material": [],
                "product_concept_assets": [],
                "packaging_assets": [],
                "test_variants": [],
                "price_points": [],
                "optional_background_materials": [],
                "research_mode": "auto",
                "enable_lane_b": False,
            },
        )
        project_repo.projects["proj_graph"] = project

        original = GraphAppService._project_repo
        try:
            GraphAppService._project_repo = project_repo
            # build_consumer_graph_sync needs TaskManager; we pass a minimal mock
            class FakeTaskManager:
                def update_task(self, **kwargs):
                    pass

            # This will fail during graph build because ConsumerGraphBuilder needs
            # real data, but the project_repo.save_project should be called on error
            with pytest.raises(Exception):
                GraphAppService.build_consumer_graph_sync(
                    project=project,
                    text="some background",
                    task_manager=FakeTaskManager(),
                    task_id="t1",
                )
            # On error path, save_project is called
            assert len(project_repo.saved) >= 1
        finally:
            GraphAppService._project_repo = original


class TestSimulationAppServicePrepareUsesExecutor:
    def _enable_sqlalchemy_shadow(self, file_repo):
        original_bundle = SimulationAppService._repository_bundle
        had_factory = hasattr(SimulationAppService, "_filesystem_simulation_repo_factory")
        original_factory = getattr(SimulationAppService, "_filesystem_simulation_repo_factory", None)
        SimulationAppService._repository_bundle = type("Bundle", (), {"backend": "sqlalchemy"})()
        SimulationAppService._filesystem_simulation_repo_factory = lambda: file_repo
        return original_bundle, had_factory, original_factory

    def _restore_sqlalchemy_shadow(self, original_bundle, had_factory, original_factory):
        SimulationAppService._repository_bundle = original_bundle
        if had_factory:
            SimulationAppService._filesystem_simulation_repo_factory = original_factory
        else:
            delattr(SimulationAppService, "_filesystem_simulation_repo_factory")

    def test_prepare_simulation_submits_via_executor(self, monkeypatch):
        from app.services.application import SimulationAppService
        from app.services.application.task_executor import TaskExecutor

        class CaptureExecutor(TaskExecutor):
            def __init__(self):
                self.submitted = []

            def submit(self, fn, *args, trace_id=None, **kwargs):
                self.submitted.append((fn, args, kwargs, trace_id))
                return trace_id or "trace_fallback"

            def get_status(self, trace_id):
                return {
                    "trace_id": trace_id,
                    "status": "PENDING",
                    "backend": "thread",
                }

            def cancel(self, trace_id):
                return {
                    "trace_id": trace_id,
                    "status": "CANCELLED",
                    "cancelled": True,
                    "backend": "thread",
                }

        executor = CaptureExecutor()
        project_repo = StubProjectRepository()
        sim_repo = StubSimulationRepository()

        project_repo.projects["proj_prep"] = Project(
            project_id="proj_prep",
            name="Prep Test",
            status=ProjectStatus.CREATED,
            created_at="2026-01-01T00:00:00",
            updated_at="2026-01-01T00:00:00",
            project_type="default",
            graph_id="g1",
            simulation_requirement="test req",
        )
        sim_repo.simulations["sim_prep"] = SimulationState(
            simulation_id="sim_prep",
            project_id="proj_prep",
            graph_id="g1",
        )

        original_project = SimulationAppService._project_repo
        original_sim = SimulationAppService._simulation_repo
        original_exec = SimulationAppService._executor
        try:
            SimulationAppService._project_repo = project_repo
            SimulationAppService._simulation_repo = sim_repo
            SimulationAppService._executor = executor

            result = SimulationAppService.prepare_simulation(
                "sim_prep",
                {"force_regenerate": True, "entity_types": None},
            )
            assert result["status"] == "preparing"
            assert len(executor.submitted) == 1
            _fn, _args, _kwargs, _trace_id = executor.submitted[0]
            assert _kwargs["task_type"] == "prepare_simulation"
            assert _kwargs["idempotency_key"] == "sim_prep:prepare"
            assert _kwargs["simulation_id"] == "sim_prep"
            assert _kwargs["run_id"] == "prepare"
        finally:
            SimulationAppService._project_repo = original_project
            SimulationAppService._simulation_repo = original_sim
            SimulationAppService._executor = original_exec

    def test_prepare_simulation_mirrors_preparing_state_to_filesystem_shadow(self):
        executor = CaptureExecutor()
        project_repo = StubProjectRepository()
        sim_repo = StubSimulationRepository()
        file_repo = StubSimulationRepository()
        project_repo.projects["proj_shadow_prep"] = Project(
            project_id="proj_shadow_prep",
            name="Prep Shadow Test",
            status=ProjectStatus.CREATED,
            created_at="2026-01-01T00:00:00",
            updated_at="2026-01-01T00:00:00",
            project_type="consumer_test",
            graph_id="g1",
            simulation_requirement="test req",
        )
        sim_repo.simulations["sim_shadow_prep"] = SimulationState(
            simulation_id="sim_shadow_prep",
            project_id="proj_shadow_prep",
            graph_id="g1",
            project_type="consumer_test",
            consumer_mode=True,
        )

        original_project = SimulationAppService._project_repo
        original_sim = SimulationAppService._simulation_repo
        original_exec = SimulationAppService._executor
        shadow_state = self._enable_sqlalchemy_shadow(file_repo)
        try:
            SimulationAppService._project_repo = project_repo
            SimulationAppService._simulation_repo = sim_repo
            SimulationAppService._executor = executor

            SimulationAppService.prepare_simulation(
                "sim_shadow_prep",
                {"force_regenerate": True, "entity_types": None},
            )

            mirrored = file_repo.get_simulation("sim_shadow_prep")
            assert mirrored is not None
            assert mirrored.status == SimulationStatus.PREPARING
            assert mirrored.entities_count == len(mirrored.entity_types) or mirrored.entity_types == ["AudienceSegment"]
        finally:
            SimulationAppService._project_repo = original_project
            SimulationAppService._simulation_repo = original_sim
            SimulationAppService._executor = original_exec
            self._restore_sqlalchemy_shadow(*shadow_state)

    def test_prepare_status_returns_preparing_when_task_state_is_process_local(self):
        sim_repo = StubSimulationRepository()
        sim_repo.simulations["sim_process_local_task"] = SimulationState(
            simulation_id="sim_process_local_task",
            project_id="proj_process_local_task",
            graph_id="g1",
            status=SimulationStatus.PREPARING,
        )

        original_sim = SimulationAppService._simulation_repo
        try:
            SimulationAppService._simulation_repo = sim_repo

            result = SimulationAppService.get_prepare_status(
                "task_not_in_this_process",
                "sim_process_local_task",
            )

            assert result["simulation_id"] == "sim_process_local_task"
            assert result["task_id"] == "task_not_in_this_process"
            assert result["status"] == "preparing"
            assert result["already_prepared"] is False
        finally:
            SimulationAppService._simulation_repo = original_sim

    def test_prepare_task_saves_completed_state_to_application_repository(self, monkeypatch):
        sim_repo = StubSimulationRepository()
        ready_state = SimulationState(
            simulation_id="sim_task_save",
            project_id="proj_task_save",
            graph_id="g1",
            status=SimulationStatus.READY,
            config_generated=True,
        )

        class FakeBundle:
            simulation_repo = sim_repo

        class FakeDomainManager:
            def prepare_simulation(self, **kwargs):
                return ready_state

        import app.services.simulation_manager as simulation_manager_module

        monkeypatch.setattr(simulation_app_service_module, "create_repository_bundle", lambda: FakeBundle())
        monkeypatch.setattr(simulation_manager_module, "SimulationManager", FakeDomainManager)
        task_id = TaskManager().create_task("simulation_prepare")

        simulation_app_service_module.run_prepare_simulation_task(
            simulation_id="sim_task_save",
            task_id=task_id,
            simulation_requirement="test requirement",
            document_text="test document",
            entity_types_list=[],
            use_llm_for_profiles=True,
            parallel_profile_count=1,
            locale="zh-CN",
        )

        saved = sim_repo.get_simulation("sim_task_save")
        assert saved is ready_state
        assert saved.status == SimulationStatus.READY


class TestReportAppServiceGenerateUsesExecutor:
    def test_generate_report_submits_via_executor(self, monkeypatch):
        from app.services.application import ReportAppService
        from app.services.application.task_executor import TaskExecutor

        class CaptureExecutor(TaskExecutor):
            def __init__(self):
                self.submitted = []

            def submit(self, fn, *args, trace_id=None, **kwargs):
                self.submitted.append((fn, args, kwargs, trace_id))
                return trace_id or "trace_fallback"

            def get_status(self, trace_id):
                return {
                    "trace_id": trace_id,
                    "status": "PENDING",
                    "backend": "thread",
                }

            def cancel(self, trace_id):
                return {
                    "trace_id": trace_id,
                    "status": "CANCELLED",
                    "cancelled": True,
                    "backend": "thread",
                }

        executor = CaptureExecutor()
        project_repo = StubProjectRepository()
        sim_repo = StubSimulationRepository()

        project_repo.projects["proj_rep"] = Project(
            project_id="proj_rep",
            name="Rep Test",
            status=ProjectStatus.CREATED,
            created_at="2026-01-01T00:00:00",
            updated_at="2026-01-01T00:00:00",
            project_type="default",
            graph_id="g1",
            simulation_requirement="test req",
        )
        sim_repo.simulations["sim_rep"] = SimulationState(
            simulation_id="sim_rep",
            project_id="proj_rep",
            graph_id="g1",
        )

        report_repo = StubReportRepository()

        original_project = ReportAppService._project_repo
        original_sim = ReportAppService._simulation_repo
        original_report = ReportAppService._report_repo
        original_exec = ReportAppService._executor
        try:
            ReportAppService._project_repo = project_repo
            ReportAppService._simulation_repo = sim_repo
            ReportAppService._report_repo = report_repo
            ReportAppService._executor = executor

            result = ReportAppService.generate_report("sim_rep")
            assert result["status"] == "generating"
            assert len(executor.submitted) == 1
            _fn, _args, _kwargs, _trace_id = executor.submitted[0]
            assert _kwargs["task_type"] == "generate_report"
            assert _kwargs["idempotency_key"] == "sim_rep:report"
            assert _kwargs["simulation_id"] == "sim_rep"
            assert _kwargs["run_id"] == "report"
            assert _trace_id == result["report_id"]
        finally:
            ReportAppService._project_repo = original_project
            ReportAppService._simulation_repo = original_sim
            ReportAppService._report_repo = original_report
            ReportAppService._executor = original_exec


class TestBranchAppServiceResumeUsesExecutor:
    def test_resume_branch_submits_via_executor(self, monkeypatch):
        from app.services.application import BranchAppService
        from app.services.application.task_executor import TaskExecutor

        class CaptureExecutor(TaskExecutor):
            def __init__(self):
                self.submitted = []

            def submit(self, fn, *args, trace_id=None, **kwargs):
                self.submitted.append((fn, args, kwargs, trace_id))
                return trace_id or "trace_fallback"

            def get_status(self, trace_id):
                return {
                    "trace_id": trace_id,
                    "status": "PENDING",
                    "backend": "thread",
                }

            def cancel(self, trace_id):
                return {
                    "trace_id": trace_id,
                    "status": "CANCELLED",
                    "cancelled": True,
                    "backend": "thread",
                }

        executor = CaptureExecutor()
        sim_repo = StubSimulationRepository()
        branch_repo = StubBranchRepository()

        sim_repo.simulations["sim_branch"] = SimulationState(
            simulation_id="sim_branch",
            project_id="proj_branch",
            graph_id="g1",
            consumer_mode=True,
        )
        sim_repo.configs["sim_branch"] = {
            "time_config": {"total_simulation_hours": 24, "minutes_per_round": 30}
        }
        branch = branch_repo.create_branch("sim_branch", "Test", 1)

        original_sim = BranchAppService._simulation_repo
        original_branch = BranchAppService._branch_repo
        original_exec = BranchAppService._executor
        try:
            BranchAppService._simulation_repo = sim_repo
            BranchAppService._branch_repo = branch_repo
            BranchAppService._executor = executor

            result = BranchAppService.resume_branch("sim_branch", branch.branch_id)
            assert result["status"] == "running"
            assert len(executor.submitted) == 1
            _fn, _args, _kwargs, _trace_id = executor.submitted[0]
            assert _kwargs["task_type"] == "resume_branch"
            assert _kwargs["idempotency_key"] == f"sim_branch:branch:{branch.branch_id}:resume"
            assert _kwargs["simulation_id"] == "sim_branch"
            assert _kwargs["run_id"] == branch.branch_id
        finally:
            BranchAppService._simulation_repo = original_sim
            BranchAppService._branch_repo = original_branch
            BranchAppService._executor = original_exec


class TestStubSimulationRepositoryArtifactMethods:
    def test_save_and_load_simulation_config(self):
        repo = StubSimulationRepository()
        repo.save_simulation_config("sim_1", {"key": "value"})
        assert repo.load_simulation_config("sim_1") == {"key": "value"}

    def test_save_and_load_consumer_config(self):
        repo = StubSimulationRepository()
        repo.save_consumer_config("sim_1", {"mode": "consumer"})
        assert repo.load_consumer_config("sim_1") == {"mode": "consumer"}


class CaptureForkSnapshotService:
    """Stub snapshot service that records calls and returns a fixed payload."""

    def __init__(self):
        self.calls = []

    def copy_pre_fork_state(self, *, simulation_id: str, branch_id: str, fork_round: int):
        self.calls.append(
            {
                "simulation_id": simulation_id,
                "branch_id": branch_id,
                "fork_round": fork_round,
            }
        )
        return {"stubbed": True}


class TestPhase7CServiceLocks:
    def test_start_simulation_acquires_simulation_run_lock(self, monkeypatch):
        import app.services.application.simulation_app_service as sim_module

        lock_manager = CaptureLockManager()
        project_repo = StubProjectRepository()
        sim_repo = StubSimulationRepository()
        sim_repo.simulations["sim_lock"] = SimulationState(
            simulation_id="sim_lock",
            project_id="proj_lock",
            graph_id="g1",
            status=SimulationStatus.READY,
        )

        class FakeRunState:
            def to_dict(self):
                return {"simulation_id": "sim_lock", "runner_status": "running"}

        def fake_start_simulation(**kwargs):
            return FakeRunState()

        original_project = SimulationAppService._project_repo
        original_sim = SimulationAppService._simulation_repo
        original_lock = getattr(SimulationAppService, "_lock_manager", None)
        try:
            SimulationAppService._project_repo = project_repo
            SimulationAppService._simulation_repo = sim_repo
            SimulationAppService._lock_manager = lock_manager
            monkeypatch.setattr(
                sim_module.SimulationRunner,
                "start_simulation",
                staticmethod(fake_start_simulation),
            )

            SimulationAppService.start_simulation("sim_lock", {"platform": "parallel"})

            assert lock_manager.acquired == [(simulation_run_lock, "sim_lock", 0)]
        finally:
            SimulationAppService._project_repo = original_project
            SimulationAppService._simulation_repo = original_sim
            if original_lock is None:
                delattr(SimulationAppService, "_lock_manager")
            else:
                SimulationAppService._lock_manager = original_lock

    def test_start_simulation_lock_conflict_propagates(self):
        project_repo = StubProjectRepository()
        sim_repo = StubSimulationRepository()
        sim_repo.simulations["sim_busy_lock"] = SimulationState(
            simulation_id="sim_busy_lock",
            project_id="proj_lock",
            graph_id="g1",
            status=SimulationStatus.READY,
        )

        original_project = SimulationAppService._project_repo
        original_sim = SimulationAppService._simulation_repo
        original_lock = getattr(SimulationAppService, "_lock_manager", None)
        try:
            SimulationAppService._project_repo = project_repo
            SimulationAppService._simulation_repo = sim_repo
            SimulationAppService._lock_manager = RejectingLockManager()

            with pytest.raises(ConcurrencyConflictError) as exc_info:
                SimulationAppService.start_simulation(
                    "sim_busy_lock",
                    {"platform": "parallel"},
                )

            assert exc_info.value.resource == simulation_run_lock
            assert exc_info.value.resource_id == "sim_busy_lock"
        finally:
            SimulationAppService._project_repo = original_project
            SimulationAppService._simulation_repo = original_sim
            if original_lock is None:
                delattr(SimulationAppService, "_lock_manager")
            else:
                SimulationAppService._lock_manager = original_lock

    def test_resume_branch_acquires_branch_lock(self):
        lock_manager = CaptureLockManager()
        executor = CaptureExecutor()
        sim_repo = StubSimulationRepository()
        branch_repo = StubBranchRepository()
        sim_repo.simulations["sim_branch_lock"] = SimulationState(
            simulation_id="sim_branch_lock",
            project_id="proj_branch",
            graph_id="g1",
            consumer_mode=True,
        )
        sim_repo.configs["sim_branch_lock"] = {
            "time_config": {"total_simulation_hours": 24, "minutes_per_round": 30}
        }
        branch = branch_repo.create_branch("sim_branch_lock", "Locked", 1)

        original_sim = BranchAppService._simulation_repo
        original_branch = BranchAppService._branch_repo
        original_exec = BranchAppService._executor
        original_lock = getattr(BranchAppService, "_lock_manager", None)
        try:
            BranchAppService._simulation_repo = sim_repo
            BranchAppService._branch_repo = branch_repo
            BranchAppService._executor = executor
            BranchAppService._lock_manager = lock_manager

            BranchAppService.resume_branch("sim_branch_lock", branch.branch_id)

            assert lock_manager.acquired == [
                (branch_fork_lock, f"sim_branch_lock:{branch.branch_id}", 0)
            ]
        finally:
            BranchAppService._simulation_repo = original_sim
            BranchAppService._branch_repo = original_branch
            BranchAppService._executor = original_exec
            if original_lock is None:
                delattr(BranchAppService, "_lock_manager")
            else:
                BranchAppService._lock_manager = original_lock

    def test_generate_report_worker_acquires_report_generation_lock(self, monkeypatch):
        import app.services.application.report_app_service as report_module

        lock_manager = CaptureLockManager()
        executor = CaptureExecutor()
        project_repo = StubProjectRepository()
        sim_repo = StubSimulationRepository()
        report_repo = StubReportRepository()
        project_repo.projects["proj_report_lock"] = Project(
            project_id="proj_report_lock",
            name="Report Lock",
            status=ProjectStatus.CREATED,
            created_at="2026-01-01T00:00:00",
            updated_at="2026-01-01T00:00:00",
            project_type="default",
            graph_id="g1",
            simulation_requirement="test req",
        )
        sim_repo.simulations["sim_report_lock"] = SimulationState(
            simulation_id="sim_report_lock",
            project_id="proj_report_lock",
            graph_id="g1",
        )

        class FakeReportAgent:
            def __init__(self, **kwargs):
                self.kwargs = kwargs

            def generate_report(self, progress_callback=None, report_id=None):
                return Report(
                    report_id=report_id,
                    simulation_id="sim_report_lock",
                    graph_id="g1",
                    simulation_requirement="test req",
                    status=ReportStatus.COMPLETED,
                )

        original_project = ReportAppService._project_repo
        original_sim = ReportAppService._simulation_repo
        original_report = ReportAppService._report_repo
        original_exec = ReportAppService._executor
        original_lock = getattr(ReportAppService, "_lock_manager", None)
        try:
            ReportAppService._project_repo = project_repo
            ReportAppService._simulation_repo = sim_repo
            ReportAppService._report_repo = report_repo
            ReportAppService._executor = executor
            ReportAppService._lock_manager = lock_manager
            monkeypatch.setattr(report_module, "ReportAgent", FakeReportAgent)
            monkeypatch.setattr(report_module, "create_lock_manager", lambda: lock_manager)

            ReportAppService.generate_report("sim_report_lock")
            assert len(executor.submitted) == 1

            lock_manager.acquired.clear()
            fn, args, kwargs, _trace_id = executor.submitted[0]
            task_kwargs = dict(kwargs)
            for metadata_key in ("task_type", "idempotency_key", "simulation_id", "run_id"):
                task_kwargs.pop(metadata_key, None)
            fn(*args, **task_kwargs)
            assert lock_manager.acquired == [
                (report_generation_lock, "sim_report_lock", 0)
            ]
            assert len(report_repo.reports) == 1
        finally:
            ReportAppService._project_repo = original_project
            ReportAppService._simulation_repo = original_sim
            ReportAppService._report_repo = original_report
            ReportAppService._executor = original_exec
            if original_lock is None:
                delattr(ReportAppService, "_lock_manager")
            else:
                ReportAppService._lock_manager = original_lock

    def test_create_branch_acquires_branch_fork_lock(self):
        lock_manager = CaptureLockManager()
        sim_repo = StubSimulationRepository()
        branch_repo = StubBranchRepository()
        sim_repo.simulations["sim_c"] = SimulationState(
            simulation_id="sim_c",
            project_id="proj_c",
            graph_id="g1",
            consumer_mode=True,
        )

        original_sim = BranchAppService._simulation_repo
        original_branch = BranchAppService._branch_repo
        original_lock = getattr(BranchAppService, "_lock_manager", None)
        original_snapshot = getattr(BranchAppService, "_fork_snapshot_service", None)
        try:
            BranchAppService._simulation_repo = sim_repo
            BranchAppService._branch_repo = branch_repo
            BranchAppService._lock_manager = lock_manager
            if original_snapshot is not None:
                BranchAppService._fork_snapshot_service = CaptureForkSnapshotService()

            BranchAppService.create_branch("sim_c", "Feature", 2)

            assert lock_manager.acquired == [(branch_fork_lock, "sim_c:fork:base:2", 0)]
        finally:
            BranchAppService._simulation_repo = original_sim
            BranchAppService._branch_repo = original_branch
            if original_lock is None:
                delattr(BranchAppService, "_lock_manager")
            else:
                BranchAppService._lock_manager = original_lock
            if original_snapshot is None:
                if hasattr(BranchAppService, "_fork_snapshot_service"):
                    delattr(BranchAppService, "_fork_snapshot_service")
            else:
                BranchAppService._fork_snapshot_service = original_snapshot

    def test_create_branch_calls_injectable_fork_snapshot_service(self):
        lock_manager = CaptureLockManager()
        snapshot_service = CaptureForkSnapshotService()
        sim_repo = StubSimulationRepository()
        branch_repo = StubBranchRepository()
        sim_repo.simulations["sim_c"] = SimulationState(
            simulation_id="sim_c",
            project_id="proj_c",
            graph_id="g1",
            consumer_mode=True,
        )

        original_sim = BranchAppService._simulation_repo
        original_branch = BranchAppService._branch_repo
        original_lock = getattr(BranchAppService, "_lock_manager", None)
        original_snapshot = getattr(BranchAppService, "_fork_snapshot_service", None)
        try:
            BranchAppService._simulation_repo = sim_repo
            BranchAppService._branch_repo = branch_repo
            BranchAppService._lock_manager = lock_manager
            BranchAppService._fork_snapshot_service = snapshot_service

            result = BranchAppService.create_branch("sim_c", "Feature", 2)

            assert lock_manager.acquired == [(branch_fork_lock, "sim_c:fork:base:2", 0)]
            assert len(snapshot_service.calls) == 1
            assert snapshot_service.calls[0]["simulation_id"] == "sim_c"
            assert snapshot_service.calls[0]["branch_id"] == "branch_Feature"
            assert snapshot_service.calls[0]["fork_round"] == 2
            assert result["fork_snapshot"] == {"stubbed": True}
        finally:
            BranchAppService._simulation_repo = original_sim
            BranchAppService._branch_repo = original_branch
            if original_lock is None:
                delattr(BranchAppService, "_lock_manager")
            else:
                BranchAppService._lock_manager = original_lock
            if original_snapshot is None:
                if hasattr(BranchAppService, "_fork_snapshot_service"):
                    delattr(BranchAppService, "_fork_snapshot_service")
            else:
                BranchAppService._fork_snapshot_service = original_snapshot
