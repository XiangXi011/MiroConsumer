"""Redis cache decorators for repository read paths."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from ..models.project import Project
from ..services.simulation_manager import SimulationState, SimulationStatus
from . import ProjectRepository, SimulationRepository


def _simulation_from_dict(data: dict) -> SimulationState:
    payload = dict(data)
    status = payload.get("status", SimulationStatus.CREATED)
    if isinstance(status, str):
        payload["status"] = SimulationStatus(status)
    return SimulationState(**payload)


class CachedProjectRepository(ProjectRepository):
    """Cache project reads while delegating writes to the wrapped repository."""

    cache_ttl_seconds = 600
    list_cache_ttl_seconds = 300

    def __init__(self, wrapped: ProjectRepository, cache) -> None:
        self.wrapped = wrapped
        self.cache = cache

    @staticmethod
    def _project_key(project_id: str) -> str:
        return f"project:{project_id}"

    @staticmethod
    def _list_key(limit: int) -> str:
        return f"project:list:{limit}"

    def get_project(self, project_id: str) -> Optional[Any]:
        cached = self.cache.get(self._project_key(project_id))
        if isinstance(cached, dict):
            return Project.from_dict(cached)
        project = self.wrapped.get_project(project_id)
        if project is not None and hasattr(project, "to_dict"):
            self.cache.set(self._project_key(project_id), project.to_dict(), ttl=self.cache_ttl_seconds)
        return project

    def save_project(self, project: Any) -> None:
        self.wrapped.save_project(project)
        if hasattr(project, "to_dict"):
            self.cache.set(self._project_key(project.project_id), project.to_dict(), ttl=self.cache_ttl_seconds)

    def create_project(self, name: str = "Unnamed Project") -> Any:
        project = self.wrapped.create_project(name)
        if hasattr(project, "to_dict"):
            self.cache.set(self._project_key(project.project_id), project.to_dict(), ttl=self.cache_ttl_seconds)
        return project

    def delete_project(self, project_id: str) -> bool:
        deleted = self.wrapped.delete_project(project_id)
        self.cache.delete(self._project_key(project_id))
        return deleted

    def list_projects(self, limit: int = 50) -> List[Any]:
        cached = self.cache.get(self._list_key(limit))
        if isinstance(cached, list):
            return [Project.from_dict(item) for item in cached if isinstance(item, dict)]
        projects = self.wrapped.list_projects(limit)
        self.cache.set(
            self._list_key(limit),
            [item.to_dict() for item in projects if hasattr(item, "to_dict")],
            ttl=self.list_cache_ttl_seconds,
        )
        return projects

    def get_extracted_text(self, project_id: str) -> Optional[str]:
        return self.wrapped.get_extracted_text(project_id)

    def save_extracted_text(self, project_id: str, text: str) -> None:
        self.wrapped.save_extracted_text(project_id, text)

    def save_consumer_graph_payload(self, project_id: str, graph_payload: Dict[str, Any]) -> None:
        self.wrapped.save_consumer_graph_payload(project_id, graph_payload)

    def load_consumer_graph_payload(self, project_id: str) -> Optional[Dict[str, Any]]:
        return self.wrapped.load_consumer_graph_payload(project_id)


class CachedSimulationRepository(SimulationRepository):
    """Cache simulation reads while delegating writes to the wrapped repository."""

    cache_ttl_seconds = 600
    list_cache_ttl_seconds = 300

    def __init__(self, wrapped: SimulationRepository, cache) -> None:
        self.wrapped = wrapped
        self.cache = cache

    @staticmethod
    def _simulation_key(simulation_id: str) -> str:
        return f"simulation:{simulation_id}"

    @staticmethod
    def _list_key(project_id: Optional[str]) -> str:
        return f"simulation:list:{project_id or 'all'}"

    def get_simulation(self, simulation_id: str) -> Optional[Any]:
        cached = self.cache.get(self._simulation_key(simulation_id))
        if isinstance(cached, dict):
            return _simulation_from_dict(cached)
        simulation = self.wrapped.get_simulation(simulation_id)
        if simulation is not None and hasattr(simulation, "to_dict"):
            self.cache.set(self._simulation_key(simulation_id), simulation.to_dict(), ttl=self.cache_ttl_seconds)
        return simulation

    def save_simulation(self, state: Any) -> None:
        self.wrapped.save_simulation(state)
        if hasattr(state, "to_dict"):
            self.cache.set(self._simulation_key(state.simulation_id), state.to_dict(), ttl=self.cache_ttl_seconds)

    def create_simulation(
        self,
        project_id: str,
        graph_id: str,
        project_type: str = "default",
        enable_twitter: bool = True,
        enable_reddit: bool = True,
        tenant_id: str = "",
    ) -> Any:
        simulation = self.wrapped.create_simulation(
            project_id=project_id,
            graph_id=graph_id,
            project_type=project_type,
            enable_twitter=enable_twitter,
            enable_reddit=enable_reddit,
            tenant_id=tenant_id,
        )
        if hasattr(simulation, "to_dict"):
            self.cache.set(self._simulation_key(simulation.simulation_id), simulation.to_dict(), ttl=self.cache_ttl_seconds)
        return simulation

    def list_simulations(self, project_id: Optional[str] = None) -> List[Any]:
        cached = self.cache.get(self._list_key(project_id))
        if isinstance(cached, list):
            return [_simulation_from_dict(item) for item in cached if isinstance(item, dict)]
        simulations = self.wrapped.list_simulations(project_id)
        self.cache.set(
            self._list_key(project_id),
            [item.to_dict() for item in simulations if hasattr(item, "to_dict")],
            ttl=self.list_cache_ttl_seconds,
        )
        return simulations

    def delete_simulation(self, simulation_id: str) -> bool:
        deleted = self.wrapped.delete_simulation(simulation_id)
        self.cache.delete(self._simulation_key(simulation_id))
        return deleted

    def get_profiles(self, simulation_id: str, platform: str = "reddit") -> List[Dict[str, Any]]:
        return self.wrapped.get_profiles(simulation_id, platform)

    def get_simulation_config(self, simulation_id: str) -> Optional[Dict[str, Any]]:
        return self.wrapped.get_simulation_config(simulation_id)

    def get_prepare_manifest(self, simulation_id: str) -> Optional[Dict[str, Any]]:
        return self.wrapped.get_prepare_manifest(simulation_id)

    def record_manifest_reuse(self, simulation_id: str) -> Optional[Dict[str, Any]]:
        return self.wrapped.record_manifest_reuse(simulation_id)

    def save_simulation_config(self, simulation_id: str, config: Dict[str, Any]) -> None:
        self.wrapped.save_simulation_config(simulation_id, config)

    def load_simulation_config(self, simulation_id: str) -> Optional[Dict[str, Any]]:
        return self.wrapped.load_simulation_config(simulation_id)

    def save_consumer_config(self, simulation_id: str, config: Dict[str, Any]) -> None:
        self.wrapped.save_consumer_config(simulation_id, config)

    def load_consumer_config(self, simulation_id: str) -> Optional[Dict[str, Any]]:
        return self.wrapped.load_consumer_config(simulation_id)

