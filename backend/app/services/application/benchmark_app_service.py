"""
Benchmark application service

Thin wrapper around benchmark registry and replay for route-level orchestration.
"""

from typing import Any, Dict, List, Optional

from ...repositories import BenchmarkRepository, ProjectRepository, SimulationRepository
from ...repositories.filesystem import (
    FilesystemBenchmarkRepository,
    FilesystemProjectRepository,
    FilesystemSimulationRepository,
)
from ...services.consumer.api_guard import ConsumerApiGuard
from ...services.consumer.asset_library import get_asset
from ...utils.locale import t


class BenchmarkAppService:
    """Application service for benchmark registration and replay."""

    _project_repo: ProjectRepository = FilesystemProjectRepository()
    _simulation_repo: SimulationRepository = FilesystemSimulationRepository()
    _benchmark_repo: BenchmarkRepository = FilesystemBenchmarkRepository()

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
            project = cls._project_repo.get_project(pack_project_id)
            ok, error = ConsumerApiGuard.check_consumer_project(project)
            if not ok:
                raise ValueError(error)

        return cls._benchmark_repo.register_benchmark(
            name=name,
            source_pack_lineage=source_pack_lineage,
            expected_signals=expected_signals,
            simulation_context=simulation_context,
        )

    @classmethod
    def list_benchmarks(cls) -> List[dict]:
        """List all registered benchmarks."""
        return cls._benchmark_repo.list_benchmarks()

    @classmethod
    def get_benchmark(cls, benchmark_id: str) -> Optional[dict]:
        """Get a single benchmark by ID."""
        return cls._benchmark_repo.get_benchmark(benchmark_id)

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
            project = cls._project_repo.get_project(project_id)
            ok, error = ConsumerApiGuard.check_consumer_project(project)
            if not ok:
                raise ValueError(error)
        elif simulation_id:
            state = cls._simulation_repo.get_simulation(simulation_id)
            ok, error = ConsumerApiGuard.check_consumer_simulation(state)
            if not ok:
                raise ValueError(error)
        else:
            raise ValueError("project_id or simulation_id is required")

        return cls._benchmark_repo.replay_benchmark(
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
        replay = cls._benchmark_repo.get_replay_result(replay_id)
        if not replay:
            raise ValueError(f"Replay not found: {replay_id}")

        replay_project_id = replay.get("project_id")
        replay_simulation_id = replay.get("simulation_id")
        if replay_project_id:
            project = cls._project_repo.get_project(replay_project_id)
            if project is not None:
                ok, error = ConsumerApiGuard.check_consumer_project(project)
                if not ok:
                    raise ValueError(error)
        elif replay_simulation_id:
            state = cls._simulation_repo.get_simulation(replay_simulation_id)
            if state is not None:
                ok, error = ConsumerApiGuard.check_consumer_simulation(state)
                if not ok:
                    raise ValueError(error)

        return replay
