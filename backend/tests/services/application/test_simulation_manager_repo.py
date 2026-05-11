"""Tests verifying SimulationManager delegates artifact I/O to repository."""

from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock

import pytest

from app.repositories import SimulationRepository
from app.services.simulation_manager import SimulationManager, SimulationState, SimulationStatus


class SpySimulationRepository(SimulationRepository):
    """Records all persistence calls for inspection."""

    def __init__(self):
        self.simulations: Dict[str, SimulationState] = {}
        self.configs: Dict[str, Dict[str, Any]] = {}
        self.consumer_configs: Dict[str, Dict[str, Any]] = {}
        self.calls: List[str] = []

    def get_simulation(self, simulation_id: str) -> Optional[Any]:
        self.calls.append(f"get_simulation:{simulation_id}")
        return self.simulations.get(simulation_id)

    def save_simulation(self, state: Any) -> None:
        self.calls.append(f"save_simulation:{state.simulation_id}")
        self.simulations[state.simulation_id] = state

    def create_simulation(
        self,
        project_id: str,
        graph_id: str,
        project_type: str = "default",
        enable_twitter: bool = True,
        enable_reddit: bool = True,
    ) -> Any:
        self.calls.append(f"create_simulation:{project_id}")
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
        self.calls.append("list_simulations")
        states = list(self.simulations.values())
        if project_id:
            states = [s for s in states if s.project_id == project_id]
        return states

    def delete_simulation(self, simulation_id: str) -> bool:
        self.calls.append(f"delete_simulation:{simulation_id}")
        return self.simulations.pop(simulation_id, None) is not None

    def get_profiles(self, simulation_id: str, platform: str = "reddit") -> List[Dict[str, Any]]:
        self.calls.append(f"get_profiles:{simulation_id}")
        return []

    def get_simulation_config(self, simulation_id: str) -> Optional[Dict[str, Any]]:
        return self.configs.get(simulation_id)

    def get_prepare_manifest(self, simulation_id: str) -> Optional[Dict[str, Any]]:
        return None

    def record_manifest_reuse(self, simulation_id: str) -> Optional[Dict[str, Any]]:
        return None

    def save_simulation_config(self, simulation_id: str, config: Dict[str, Any]) -> None:
        self.calls.append(f"save_simulation_config:{simulation_id}")
        self.configs[simulation_id] = config

    def load_simulation_config(self, simulation_id: str) -> Optional[Dict[str, Any]]:
        self.calls.append(f"load_simulation_config:{simulation_id}")
        return self.configs.get(simulation_id)

    def save_consumer_config(self, simulation_id: str, config: Dict[str, Any]) -> None:
        self.calls.append(f"save_consumer_config:{simulation_id}")
        self.consumer_configs[simulation_id] = config

    def load_consumer_config(self, simulation_id: str) -> Optional[Dict[str, Any]]:
        self.calls.append(f"load_consumer_config:{simulation_id}")
        return self.consumer_configs.get(simulation_id)


class TestSimulationManagerDelegatesToRepo:
    def test_create_simulation_delegates_to_repo(self):
        repo = SpySimulationRepository()
        manager = SimulationManager(repo=repo)

        state = manager.create_simulation("proj_1", "g1")

        assert state.simulation_id in repo.simulations
        assert "create_simulation:proj_1" in repo.calls

    def test_save_and_load_state_delegates_to_repo(self):
        repo = SpySimulationRepository()
        manager = SimulationManager(repo=repo)

        state = manager.create_simulation("proj_1", "g1")
        state.status = SimulationStatus.READY
        manager._save_simulation_state(state)

        # First load hits cache (no repo call)
        loaded = manager._load_simulation_state(state.simulation_id)
        assert loaded is not None
        assert loaded.status == SimulationStatus.READY
        assert "save_simulation:" + state.simulation_id in repo.calls

        # Evict cache and reload to verify repo delegation
        manager._simulations.pop(state.simulation_id, None)
        loaded2 = manager._load_simulation_state(state.simulation_id)
        assert loaded2 is not None
        assert "get_simulation:" + state.simulation_id in repo.calls

    def test_get_simulation_config_delegates_to_repo(self):
        repo = SpySimulationRepository()
        manager = SimulationManager(repo=repo)

        manager.get_simulation_config("sim_1")

        assert "load_simulation_config:sim_1" in repo.calls

    def test_get_simulation_config_uses_redis_cache_when_configured(self, monkeypatch):
        repo = SpySimulationRepository()
        manager = SimulationManager(repo=repo)
        cache = MagicMock()
        cache.get_or_set.return_value = {"cached": True}

        monkeypatch.setattr(manager, "_get_cache", lambda: cache)

        data = manager.get_simulation_config("sim_cache")

        assert data == {"cached": True}
        cache.get_or_set.assert_called_once()
        args, kwargs = cache.get_or_set.call_args
        assert args[0] == "simulation_config:v1:sim_cache"
        assert kwargs["ttl"] == SimulationManager.CONFIG_CACHE_TTL_SECONDS

    def test_list_simulations_delegates_to_repo(self):
        repo = SpySimulationRepository()
        manager = SimulationManager(repo=repo)

        manager.list_simulations()

        assert "list_simulations" in repo.calls

    def test_get_profiles_delegates_to_repo(self):
        repo = SpySimulationRepository()
        manager = SimulationManager(repo=repo)

        state = manager.create_simulation("proj_1", "g1")
        manager.get_profiles(state.simulation_id)

        assert f"get_profiles:{state.simulation_id}" in repo.calls
