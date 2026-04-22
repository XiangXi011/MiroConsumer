"""
Repository layer — abstracts file persistence behind explicit boundaries.

All repository interfaces are defined as ABCs so the application service
layer can depend on abstractions rather than concrete file-oriented
managers.  Filesystem-backed implementations live in
`app.repositories.filesystem`.

This batch intentionally keeps the implementations thin: they delegate to
existing manager/storage modules.  Deeper cleanup (e.g. collapsing
manager/repository duplication) is deferred to later batches.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class ProjectRepository(ABC):
    """Abstract project persistence."""

    @abstractmethod
    def get_project(self, project_id: str) -> Optional[Any]:
        """Return Project or None."""

    @abstractmethod
    def save_project(self, project: Any) -> None:
        """Persist project metadata."""

    @abstractmethod
    def create_project(self, name: str = "Unnamed Project") -> Any:
        """Create and persist a new project."""

    @abstractmethod
    def delete_project(self, project_id: str) -> bool:
        """Delete project and all associated files."""

    @abstractmethod
    def list_projects(self, limit: int = 50) -> List[Any]:
        """List projects, newest first."""

    @abstractmethod
    def get_extracted_text(self, project_id: str) -> Optional[str]:
        """Return extracted document text or None."""

    @abstractmethod
    def save_extracted_text(self, project_id: str, text: str) -> None:
        """Persist extracted document text."""

    @abstractmethod
    def save_consumer_graph_payload(self, project_id: str, graph_payload: Dict[str, Any]) -> None:
        """Persist consumer graph payload separately from project metadata."""

    @abstractmethod
    def load_consumer_graph_payload(self, project_id: str) -> Optional[Dict[str, Any]]:
        """Load consumer graph payload or None."""


class SimulationRepository(ABC):
    """Abstract simulation state persistence."""

    @abstractmethod
    def get_simulation(self, simulation_id: str) -> Optional[Any]:
        """Return SimulationState or None."""

    @abstractmethod
    def save_simulation(self, state: Any) -> None:
        """Persist simulation state."""

    @abstractmethod
    def create_simulation(
        self,
        project_id: str,
        graph_id: str,
        project_type: str = "default",
        enable_twitter: bool = True,
        enable_reddit: bool = True,
    ) -> Any:
        """Create and persist a new simulation."""

    @abstractmethod
    def list_simulations(self, project_id: Optional[str] = None) -> List[Any]:
        """List simulations, optionally filtered by project."""

    @abstractmethod
    def delete_simulation(self, simulation_id: str) -> bool:
        """Delete simulation and all associated files."""

    @abstractmethod
    def get_profiles(self, simulation_id: str, platform: str = "reddit") -> List[Dict[str, Any]]:
        """Return generated profiles for a platform."""

    @abstractmethod
    def get_simulation_config(self, simulation_id: str) -> Optional[Dict[str, Any]]:
        """Return simulation config dict or None."""

    @abstractmethod
    def get_prepare_manifest(self, simulation_id: str) -> Optional[Dict[str, Any]]:
        """Return prepare manifest dict or None."""

    @abstractmethod
    def record_manifest_reuse(self, simulation_id: str) -> Optional[Dict[str, Any]]:
        """Increment manifest reuse count and return updated manifest."""


class BranchRepository(ABC):
    """Abstract branch and intervention persistence."""

    @abstractmethod
    def create_branch(
        self,
        simulation_id: str,
        name: str,
        fork_round: int,
        description: str = "",
        parent_branch_id: Optional[str] = None,
    ) -> Any:
        """Create and persist a branch."""

    @abstractmethod
    def get_branch(self, simulation_id: str, branch_id: str) -> Optional[Any]:
        """Return branch or None."""

    @abstractmethod
    def list_branches(self, simulation_id: str) -> List[Any]:
        """List branches for a simulation."""

    @abstractmethod
    def update_branch_status(
        self, simulation_id: str, branch_id: str, status: str
    ) -> Optional[Any]:
        """Update branch status and return updated branch."""

    @abstractmethod
    def add_intervention(
        self,
        simulation_id: str,
        branch_id: str,
        intervention_type: str,
        payload: Dict[str, Any],
        target_round: Optional[int] = None,
    ) -> Any:
        """Create and persist an intervention."""

    @abstractmethod
    def list_interventions(
        self, simulation_id: str, branch_id: Optional[str] = None
    ) -> List[Any]:
        """List interventions, optionally filtered by branch."""

    @abstractmethod
    def get_branch_run_status(self, simulation_id: str, branch_id: str) -> Dict[str, Any]:
        """Return branch run status."""

    @abstractmethod
    def update_branch_run_status(
        self, simulation_id: str, branch_id: str, status_data: Dict[str, Any]
    ) -> None:
        """Persist branch run status."""

    @abstractmethod
    def build_comparison_context(self, simulation_id: str, branch_id: str) -> Dict[str, Any]:
        """Return base-vs-branch comparison context."""


class ReportRepository(ABC):
    """Abstract report persistence."""

    @abstractmethod
    def get_report(self, report_id: str) -> Optional[Any]:
        """Return Report or None."""

    @abstractmethod
    def get_report_by_simulation(self, simulation_id: str) -> Optional[Any]:
        """Return the most recent completed report for a simulation, or None."""

    @abstractmethod
    def list_reports(
        self, simulation_id: Optional[str] = None, limit: int = 50
    ) -> List[Any]:
        """List reports, optionally filtered by simulation."""

    @abstractmethod
    def save_report(self, report: Any) -> None:
        """Persist report metadata and content."""

    @abstractmethod
    def save_outline(self, report_id: str, outline: Any) -> None:
        """Persist report outline."""

    @abstractmethod
    def save_section(self, report_id: str, section_index: int, section: Any) -> str:
        """Persist a single section and return file path."""

    @abstractmethod
    def update_progress(
        self,
        report_id: str,
        status: str,
        progress: int,
        message: str,
        current_section: Optional[str] = None,
        completed_sections: Optional[List[str]] = None,
    ) -> None:
        """Persist report generation progress."""

    @abstractmethod
    def get_progress(self, report_id: str) -> Optional[Dict[str, Any]]:
        """Return progress dict or None."""

    @abstractmethod
    def assemble_full_report(self, report_id: str, outline: Any) -> str:
        """Assemble and persist full markdown report."""

    @abstractmethod
    def delete_report(self, report_id: str) -> bool:
        """Delete report artifacts."""

    @abstractmethod
    def get_agent_log(self, report_id: str, from_line: int = 0) -> Dict[str, Any]:
        """Return agent log entries."""

    @abstractmethod
    def get_console_log(self, report_id: str, from_line: int = 0) -> Dict[str, Any]:
        """Return console log entries."""


class BenchmarkRepository(ABC):
    """Abstract benchmark and replay persistence."""

    @abstractmethod
    def register_benchmark(
        self,
        name: str,
        source_pack_lineage: str,
        expected_signals: Dict[str, Any],
        simulation_context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Register a new benchmark case."""

    @abstractmethod
    def list_benchmarks(self) -> List[Dict[str, Any]]:
        """List all registered benchmarks."""

    @abstractmethod
    def get_benchmark(self, benchmark_id: str) -> Optional[Dict[str, Any]]:
        """Return benchmark dict or None."""

    @abstractmethod
    def delete_benchmark(self, benchmark_id: str) -> bool:
        """Delete a benchmark."""

    @abstractmethod
    def replay_benchmark(
        self,
        benchmark_id: str,
        report_context: Dict[str, Any],
        project_id: Optional[str] = None,
        simulation_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Replay a benchmark against current report context."""

    @abstractmethod
    def get_replay_result(self, replay_id: str) -> Optional[Dict[str, Any]]:
        """Return replay result or None."""

    @abstractmethod
    def list_replay_results(self, benchmark_id: str) -> List[Dict[str, Any]]:
        """List replay results for a benchmark."""


__all__ = [
    "ProjectRepository",
    "SimulationRepository",
    "BranchRepository",
    "ReportRepository",
    "BenchmarkRepository",
]
