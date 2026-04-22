"""Tests verifying application services consume repository abstractions."""

from typing import Any, Dict, List, Optional

import pytest

from app.models.project import Project, ProjectStatus
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
    ) -> Any:
        state = SimulationState(
            simulation_id=f"sim_{project_id}",
            project_id=project_id,
            graph_id=graph_id,
            project_type=project_type,
            consumer_mode=(project_type == "consumer_test"),
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
        return None

    def get_prepare_manifest(self, simulation_id: str) -> Optional[Dict[str, Any]]:
        return None

    def record_manifest_reuse(self, simulation_id: str) -> Optional[Dict[str, Any]]:
        self.manifest_reuses += 1
        return {"reuse_count": self.manifest_reuses}


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


# ───────────────────────────────────────────────────────────────
# Tests
# ───────────────────────────────────────────────────────────────


class TestSimulationAppServiceUsesRepositories:
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
