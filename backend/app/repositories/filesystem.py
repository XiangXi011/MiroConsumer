"""
Filesystem-backed repository implementations.

These are thin adapters over existing manager/storage modules.  They do
not change file formats or storage locations — the boundary is explicit
so that later batches can swap in database-backed implementations without
touching application service code.
"""

from typing import Any, Dict, List, Optional

from ..models.project import ProjectManager
from ..services.simulation_manager import SimulationManager
from ..services.report_agent import ReportManager
from ..services.consumer.intervention_manager import ConsumerInterventionManager
from ..services.consumer.simulation_state_accessor import ConsumerSimulationStateAccessor
from ..services.consumer import benchmark_registry, benchmark_replay
from . import (
    ProjectRepository,
    ConsumerStateRepository,
    SimulationRepository,
    BranchRepository,
    ReportRepository,
    BenchmarkRepository,
)


class FilesystemProjectRepository(ProjectRepository):
    """Delegates to ProjectManager."""

    def get_project(self, project_id: str) -> Optional[Any]:
        return ProjectManager.get_project(project_id)

    def save_project(self, project: Any) -> None:
        ProjectManager.save_project(project)

    def create_project(self, name: str = "Unnamed Project") -> Any:
        return ProjectManager.create_project(name)

    def delete_project(self, project_id: str) -> bool:
        return ProjectManager.delete_project(project_id)

    def list_projects(self, limit: int = 50) -> List[Any]:
        return ProjectManager.list_projects(limit)

    def get_extracted_text(self, project_id: str) -> Optional[str]:
        return ProjectManager.get_extracted_text(project_id)

    def save_extracted_text(self, project_id: str, text: str) -> None:
        ProjectManager.save_extracted_text(project_id, text)

    def save_consumer_graph_payload(self, project_id: str, graph_payload: Dict[str, Any]) -> None:
        ProjectManager.save_consumer_graph_payload(project_id, graph_payload)

    def load_consumer_graph_payload(self, project_id: str) -> Optional[Dict[str, Any]]:
        return ProjectManager.load_consumer_graph_payload(project_id)


class FilesystemConsumerStateRepository(ConsumerStateRepository):
    """Delegates to ConsumerSimulationStateAccessor."""

    def load_consumer_config(self, simulation_id: str) -> Dict[str, Any]:
        return ConsumerSimulationStateAccessor.load_consumer_config(simulation_id)

    def load_consumer_rounds(self, simulation_id: str) -> List[Dict[str, Any]]:
        return ConsumerSimulationStateAccessor.load_consumer_rounds(simulation_id)

    def load_brief(self, simulation_id: str) -> Optional[Any]:
        return ConsumerSimulationStateAccessor.load_brief(simulation_id)

    def load_research_findings(self, simulation_id: str) -> List[Dict[str, Any]]:
        return ConsumerSimulationStateAccessor.load_research_findings(simulation_id)


class FilesystemSimulationRepository(SimulationRepository):
    """Delegates to SimulationManager."""

    def __init__(self) -> None:
        self._manager = SimulationManager()

    def get_simulation(self, simulation_id: str) -> Optional[Any]:
        return self._manager.get_simulation(simulation_id)

    def save_simulation(self, state: Any) -> None:
        self._manager._save_simulation_state(state)

    def create_simulation(
        self,
        project_id: str,
        graph_id: str,
        project_type: str = "default",
        enable_twitter: bool = True,
        enable_reddit: bool = True,
    ) -> Any:
        return self._manager.create_simulation(
            project_id=project_id,
            graph_id=graph_id,
            project_type=project_type,
            enable_twitter=enable_twitter,
            enable_reddit=enable_reddit,
        )

    def list_simulations(self, project_id: Optional[str] = None) -> List[Any]:
        return self._manager.list_simulations(project_id)

    def delete_simulation(self, simulation_id: str) -> bool:
        import os
        import shutil

        sim_dir = self._manager._get_simulation_dir(simulation_id)
        if os.path.exists(sim_dir):
            shutil.rmtree(sim_dir)
            return True
        return False

    def get_profiles(self, simulation_id: str, platform: str = "reddit") -> List[Dict[str, Any]]:
        return self._manager.get_profiles(simulation_id, platform)

    def get_simulation_config(self, simulation_id: str) -> Optional[Dict[str, Any]]:
        return self._manager.get_simulation_config(simulation_id)

    def get_prepare_manifest(self, simulation_id: str) -> Optional[Dict[str, Any]]:
        return self._manager.get_prepare_manifest(simulation_id)

    def record_manifest_reuse(self, simulation_id: str) -> Optional[Dict[str, Any]]:
        return self._manager.record_manifest_reuse(simulation_id)


class FilesystemBranchRepository(BranchRepository):
    """Delegates to ConsumerInterventionManager."""

    def __init__(self) -> None:
        self._manager = ConsumerInterventionManager()

    def create_branch(
        self,
        simulation_id: str,
        name: str,
        fork_round: int,
        description: str = "",
        parent_branch_id: Optional[str] = None,
    ) -> Any:
        return self._manager.create_branch(
            simulation_id=simulation_id,
            name=name,
            fork_round=fork_round,
            description=description,
            parent_branch_id=parent_branch_id,
        )

    def get_branch(self, simulation_id: str, branch_id: str) -> Optional[Any]:
        return self._manager.get_branch(simulation_id, branch_id)

    def list_branches(self, simulation_id: str) -> List[Any]:
        return self._manager.list_branches(simulation_id)

    def update_branch_status(
        self, simulation_id: str, branch_id: str, status: str
    ) -> Optional[Any]:
        return self._manager.update_branch_status(simulation_id, branch_id, status)

    def add_intervention(
        self,
        simulation_id: str,
        branch_id: str,
        intervention_type: str,
        payload: Dict[str, Any],
        target_round: Optional[int] = None,
    ) -> Any:
        return self._manager.add_intervention(
            simulation_id=simulation_id,
            branch_id=branch_id,
            intervention_type=intervention_type,
            payload=payload,
            target_round=target_round,
        )

    def list_interventions(
        self, simulation_id: str, branch_id: Optional[str] = None
    ) -> List[Any]:
        return self._manager.list_interventions(simulation_id, branch_id)

    def get_branch_run_status(self, simulation_id: str, branch_id: str) -> Dict[str, Any]:
        return self._manager.get_branch_run_status(simulation_id, branch_id)

    def update_branch_run_status(
        self, simulation_id: str, branch_id: str, status_data: Dict[str, Any]
    ) -> None:
        self._manager.update_branch_run_status(simulation_id, branch_id, status_data)

    def build_comparison_context(self, simulation_id: str, branch_id: str) -> Dict[str, Any]:
        return self._manager.build_comparison_context(simulation_id, branch_id)


class FilesystemReportRepository(ReportRepository):
    """Delegates to ReportManager."""

    def get_report(self, report_id: str) -> Optional[Any]:
        return ReportManager.get_report(report_id)

    def get_report_by_simulation(self, simulation_id: str) -> Optional[Any]:
        return ReportManager.get_report_by_simulation(simulation_id)

    def list_reports(
        self, simulation_id: Optional[str] = None, limit: int = 50
    ) -> List[Any]:
        return ReportManager.list_reports(simulation_id, limit)

    def save_report(self, report: Any) -> None:
        ReportManager.save_report(report)

    def save_outline(self, report_id: str, outline: Any) -> None:
        ReportManager.save_outline(report_id, outline)

    def save_section(self, report_id: str, section_index: int, section: Any) -> str:
        return ReportManager.save_section(report_id, section_index, section)

    def update_progress(
        self,
        report_id: str,
        status: str,
        progress: int,
        message: str,
        current_section: Optional[str] = None,
        completed_sections: Optional[List[str]] = None,
    ) -> None:
        ReportManager.update_progress(
            report_id,
            status,
            progress,
            message,
            current_section=current_section,
            completed_sections=completed_sections,
        )

    def get_progress(self, report_id: str) -> Optional[Dict[str, Any]]:
        return ReportManager.get_progress(report_id)

    def assemble_full_report(self, report_id: str, outline: Any) -> str:
        return ReportManager.assemble_full_report(report_id, outline)

    def delete_report(self, report_id: str) -> bool:
        return ReportManager.delete_report(report_id)

    def get_agent_log(self, report_id: str, from_line: int = 0) -> Dict[str, Any]:
        return ReportManager.get_agent_log(report_id, from_line)

    def get_console_log(self, report_id: str, from_line: int = 0) -> Dict[str, Any]:
        return ReportManager.get_console_log(report_id, from_line)


class FilesystemBenchmarkRepository(BenchmarkRepository):
    """Delegates to benchmark_registry and benchmark_replay modules."""

    def register_benchmark(
        self,
        name: str,
        source_pack_lineage: str,
        expected_signals: Dict[str, Any],
        simulation_context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        return benchmark_registry.register_benchmark(
            name=name,
            source_pack_lineage=source_pack_lineage,
            expected_signals=expected_signals,
            simulation_context=simulation_context,
        )

    def list_benchmarks(self) -> List[Dict[str, Any]]:
        return benchmark_registry.list_benchmarks()

    def get_benchmark(self, benchmark_id: str) -> Optional[Dict[str, Any]]:
        return benchmark_registry.get_benchmark(benchmark_id)

    def delete_benchmark(self, benchmark_id: str) -> bool:
        return benchmark_registry.delete_benchmark(benchmark_id)

    def replay_benchmark(
        self,
        benchmark_id: str,
        report_context: Dict[str, Any],
        project_id: Optional[str] = None,
        simulation_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        return benchmark_replay.replay_benchmark(
            benchmark_id=benchmark_id,
            report_context=report_context,
            project_id=project_id,
            simulation_id=simulation_id,
        )

    def get_replay_result(self, replay_id: str) -> Optional[Dict[str, Any]]:
        return benchmark_replay.get_replay_result(replay_id)

    def list_replay_results(self, benchmark_id: str) -> List[Dict[str, Any]]:
        return benchmark_replay.list_replay_results(benchmark_id)


__all__ = [
    "FilesystemProjectRepository",
    "FilesystemConsumerStateRepository",
    "FilesystemSimulationRepository",
    "FilesystemBranchRepository",
    "FilesystemReportRepository",
    "FilesystemBenchmarkRepository",
]
