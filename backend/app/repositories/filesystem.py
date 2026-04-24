"""
Filesystem-backed repository implementations.

These are thin adapters over existing manager/storage modules.  They do
not change file formats or storage locations — the boundary is explicit
so that later batches can swap in database-backed implementations without
touching application service code.
"""

import csv
import json
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

from ..config import Config
from ..models.project import ProjectManager
from ..services.report_agent import ReportManager
from ..services.simulation_manager import SimulationState, SimulationStatus
from ..services.consumer.intervention_manager import ConsumerInterventionManager
from ..services.consumer.simulation_state_accessor import ConsumerSimulationStateAccessor
from ..services.consumer import benchmark_registry, benchmark_replay
from . import (
    ConsumerProjectResearchContext,
    ConsumerProjectResearchProvider,
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


class FilesystemConsumerProjectResearchProvider(ConsumerProjectResearchProvider):
    """Filesystem-backed provider for consumer project research context.

    Delegates to ProjectManager for project metadata and to
    project_research_persistence for snapshot loading.  This is the
    repository boundary: ConsumerAppService must not import either
    directly.
    """

    def get_context(self, project_id: str) -> ConsumerProjectResearchContext:
        project = ProjectManager.get_project(project_id)
        if project is None or getattr(project, "project_type", None) != "consumer_test":
            return ConsumerProjectResearchContext(is_consumer_project=False)

        brief_payload = getattr(project, "consumer_brief", None)

        from ..services.consumer.project_research_persistence import (
            load_persisted_snapshot,
        )

        snapshot = load_persisted_snapshot(project_id)
        if snapshot is None:
            return ConsumerProjectResearchContext(
                is_consumer_project=True,
                brief_payload=brief_payload,
            )

        return ConsumerProjectResearchContext(
            is_consumer_project=True,
            brief_payload=brief_payload,
            traces=snapshot.retrieval_traces or [],
            chunks=snapshot.chunks or [],
            sources=snapshot.sources or [],
        )


class FilesystemSimulationRepository(SimulationRepository):
    """Filesystem-backed simulation persistence."""

    def _get_simulation_dir(self, simulation_id: str) -> str:
        sim_dir = os.path.join(Config.OASIS_SIMULATION_DATA_DIR, simulation_id)
        os.makedirs(sim_dir, exist_ok=True)
        return sim_dir

    def _load_state_dict(self, simulation_id: str) -> Optional[Dict[str, Any]]:
        sim_dir = self._get_simulation_dir(simulation_id)
        state_file = os.path.join(sim_dir, "state.json")
        if not os.path.exists(state_file):
            return None
        with open(state_file, "r", encoding="utf-8") as f:
            return json.load(f)

    def _state_from_dict(self, simulation_id: str, data: Dict[str, Any]) -> SimulationState:
        return SimulationState(
            simulation_id=simulation_id,
            project_id=data.get("project_id", ""),
            graph_id=data.get("graph_id", ""),
            project_type=data.get("project_type", "default"),
            consumer_mode=data.get("consumer_mode", False),
            enable_twitter=data.get("enable_twitter", True),
            enable_reddit=data.get("enable_reddit", True),
            status=SimulationStatus(data.get("status", "created")),
            entities_count=data.get("entities_count", 0),
            profiles_count=data.get("profiles_count", 0),
            entity_types=data.get("entity_types", []),
            config_generated=data.get("config_generated", False),
            config_reasoning=data.get("config_reasoning", ""),
            persona_pack_id=data.get("persona_pack_id", ""),
            pinned_brief_summary=data.get("pinned_brief_summary", ""),
            enable_lane_b=data.get("enable_lane_b", False),
            current_round=data.get("current_round", 0),
            twitter_status=data.get("twitter_status", "not_started"),
            reddit_status=data.get("reddit_status", "not_started"),
            created_at=data.get("created_at", datetime.now().isoformat()),
            updated_at=data.get("updated_at", datetime.now().isoformat()),
            error=data.get("error"),
        )

    def get_simulation(self, simulation_id: str) -> Optional[Any]:
        data = self._load_state_dict(simulation_id)
        if data is None:
            return None
        return self._state_from_dict(simulation_id, data)

    def save_simulation(self, state: Any) -> None:
        sim_dir = self._get_simulation_dir(state.simulation_id)
        state_file = os.path.join(sim_dir, "state.json")
        state.updated_at = datetime.now().isoformat()
        with open(state_file, "w", encoding="utf-8") as f:
            json.dump(state.to_dict(), f, ensure_ascii=False, indent=2)

    def create_simulation(
        self,
        project_id: str,
        graph_id: str,
        project_type: str = "default",
        enable_twitter: bool = True,
        enable_reddit: bool = True,
    ) -> Any:
        import uuid

        simulation_id = f"sim_{uuid.uuid4().hex[:12]}"
        normalized_project_type = project_type or "default"
        state = SimulationState(
            simulation_id=simulation_id,
            project_id=project_id,
            graph_id=graph_id,
            project_type=normalized_project_type,
            consumer_mode=(normalized_project_type == "consumer_test"),
            enable_twitter=enable_twitter,
            enable_reddit=enable_reddit,
            status=SimulationStatus.CREATED,
        )
        self.save_simulation(state)
        return state

    def list_simulations(self, project_id: Optional[str] = None) -> List[Any]:
        simulations = []
        if os.path.exists(Config.OASIS_SIMULATION_DATA_DIR):
            for sim_id in os.listdir(Config.OASIS_SIMULATION_DATA_DIR):
                sim_path = os.path.join(Config.OASIS_SIMULATION_DATA_DIR, sim_id)
                if sim_id.startswith(".") or not os.path.isdir(sim_path):
                    continue
                state = self.get_simulation(sim_id)
                if state and (project_id is None or state.project_id == project_id):
                    simulations.append(state)
        return simulations

    def delete_simulation(self, simulation_id: str) -> bool:
        import shutil

        sim_dir = self._get_simulation_dir(simulation_id)
        if os.path.exists(sim_dir):
            shutil.rmtree(sim_dir)
            return True
        return False

    def get_profiles(self, simulation_id: str, platform: str = "reddit") -> List[Dict[str, Any]]:
        sim_dir = self._get_simulation_dir(simulation_id)
        profile_path = os.path.join(sim_dir, f"{platform}_profiles.json")
        if not os.path.exists(profile_path):
            return []
        with open(profile_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def get_simulation_config(self, simulation_id: str) -> Optional[Dict[str, Any]]:
        return self.load_simulation_config(simulation_id)

    def get_prepare_manifest(self, simulation_id: str) -> Optional[Dict[str, Any]]:
        from ..services.prepare_manifest import read_manifest

        sim_dir = self._get_simulation_dir(simulation_id)
        manifest = read_manifest(sim_dir)
        return manifest.to_dict() if manifest else None

    def record_manifest_reuse(self, simulation_id: str) -> Optional[Dict[str, Any]]:
        from ..services.prepare_manifest import touch_reuse

        sim_dir = self._get_simulation_dir(simulation_id)
        manifest = touch_reuse(sim_dir)
        return manifest.to_dict() if manifest else None

    def save_simulation_config(self, simulation_id: str, config: Dict[str, Any]) -> None:
        sim_dir = self._get_simulation_dir(simulation_id)
        config_path = os.path.join(sim_dir, "simulation_config.json")
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False, indent=2)

    def load_simulation_config(self, simulation_id: str) -> Optional[Dict[str, Any]]:
        sim_dir = self._get_simulation_dir(simulation_id)
        config_path = os.path.join(sim_dir, "simulation_config.json")
        if not os.path.exists(config_path):
            return None
        with open(config_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def save_consumer_config(self, simulation_id: str, config: Dict[str, Any]) -> None:
        sim_dir = self._get_simulation_dir(simulation_id)
        config_path = os.path.join(sim_dir, "consumer_config.json")
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False, indent=2)

    def load_consumer_config(self, simulation_id: str) -> Optional[Dict[str, Any]]:
        sim_dir = self._get_simulation_dir(simulation_id)
        config_path = os.path.join(sim_dir, "consumer_config.json")
        if not os.path.exists(config_path):
            return None
        with open(config_path, "r", encoding="utf-8") as f:
            return json.load(f)


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
    "FilesystemConsumerProjectResearchProvider",
    "FilesystemSimulationRepository",
    "FilesystemBranchRepository",
    "FilesystemReportRepository",
    "FilesystemBenchmarkRepository",
]
