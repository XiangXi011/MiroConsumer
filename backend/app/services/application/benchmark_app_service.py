"""
Benchmark application service

Thin wrapper around benchmark registry and replay for route-level orchestration.
"""

from typing import Any, Dict, List, Optional

from ...models.project import ProjectManager
from ...services.consumer.asset_library import get_asset
from ...services.consumer.benchmark_registry import (
    register_benchmark,
    list_benchmarks,
    get_benchmark,
)
from ...services.consumer.benchmark_replay import (
    replay_benchmark,
    get_replay_result,
)
from ...services.simulation_manager import SimulationManager
from ...utils.locale import t


class BenchmarkAppService:
    """Application service for benchmark registration and replay."""

    @classmethod
    def register_benchmark(
        cls,
        name: str,
        source_pack_lineage: str,
        expected_signals: dict,
        simulation_context: Optional[dict] = None,
    ) -> dict:
        """
        Register a new benchmark case after validating the source asset pack.

        Raises ValueError on validation failure.
        """
        if not name:
            raise ValueError("name is required")
        if not source_pack_lineage:
            raise ValueError("source_pack_lineage is required")
        if not expected_signals:
            raise ValueError("expected_signals is required")

        asset_pack = get_asset(source_pack_lineage)
        if not asset_pack:
            raise ValueError(f"Asset pack not found: {source_pack_lineage}")

        pack_project_id = asset_pack.get("project_id")
        if pack_project_id:
            project = ProjectManager.get_project(pack_project_id)
            if not project:
                raise ValueError(t("api.projectNotFound", id=pack_project_id))
            if project.project_type != "consumer_test":
                raise ValueError("Benchmarks are only available for consumer_test projects")

        return register_benchmark(
            name=name,
            source_pack_lineage=source_pack_lineage,
            expected_signals=expected_signals,
            simulation_context=simulation_context,
        )

    @classmethod
    def list_benchmarks(cls) -> List[dict]:
        """List all registered benchmarks."""
        return list_benchmarks()

    @classmethod
    def get_benchmark(cls, benchmark_id: str) -> Optional[dict]:
        """Get a single benchmark by ID."""
        return get_benchmark(benchmark_id)

    @classmethod
    def replay_benchmark(
        cls,
        benchmark_id: str,
        report_context: dict,
        project_id: Optional[str] = None,
        simulation_id: Optional[str] = None,
    ) -> dict:
        """
        Replay a benchmark against the current simulation report context.

        Raises ValueError on validation failure.
        """
        if not report_context:
            raise ValueError("report_context is required")

        if project_id:
            project = ProjectManager.get_project(project_id)
            if not project:
                raise ValueError(t("api.projectNotFound", id=project_id))
            if project.project_type != "consumer_test":
                raise ValueError("Benchmark replays are only available for consumer_test projects")
        elif simulation_id:
            manager = SimulationManager()
            state = manager.get_simulation(simulation_id)
            if not state:
                raise ValueError(t("api.simulationNotFound", id=simulation_id))
            if not state.consumer_mode:
                raise ValueError("Benchmark replays are only available for consumer_test simulations")
        else:
            raise ValueError("project_id or simulation_id is required")

        return replay_benchmark(
            benchmark_id=benchmark_id,
            report_context=report_context,
            project_id=project_id,
            simulation_id=simulation_id,
        )

    @classmethod
    def get_replay_result(cls, replay_id: str) -> dict:
        """
        Get a single replay result by ID after validating consumer_test gating.

        Raises ValueError if replay not found or not consumer_test.
        """
        replay = get_replay_result(replay_id)
        if not replay:
            raise ValueError(f"Replay not found: {replay_id}")

        replay_project_id = replay.get("project_id")
        replay_simulation_id = replay.get("simulation_id")
        if replay_project_id:
            project = ProjectManager.get_project(replay_project_id)
            if project and project.project_type != "consumer_test":
                raise ValueError("Benchmark replay results are only available for consumer_test projects")
        elif replay_simulation_id:
            manager = SimulationManager()
            state = manager.get_simulation(replay_simulation_id)
            if state and not state.consumer_mode:
                raise ValueError("Benchmark replay results are only available for consumer_test simulations")

        return replay
