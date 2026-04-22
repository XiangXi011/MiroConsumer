"""Consumer API access guard — validates consumer-boundary gating in one place."""

from typing import Any, Optional, Tuple


class ConsumerApiGuard:
    """Centralizes consumer_test gating rules so API routes and app services
    share the same policy vocabulary instead of repeating inline checks.
    """

    @staticmethod
    def check_consumer_simulation(state: Optional[Any]) -> Tuple[bool, Optional[str]]:
        """Return (ok, error_message) for a simulation state."""
        if state is None:
            return False, "Simulation not found"
        if not getattr(state, "consumer_mode", False):
            return False, "Simulation is not a consumer_test simulation"
        return True, None

    @staticmethod
    def check_consumer_project(project: Optional[Any]) -> Tuple[bool, Optional[str]]:
        """Return (ok, error_message) for a project."""
        if project is None:
            return False, "Project not found"
        if getattr(project, "project_type", None) != "consumer_test":
            return False, "Project is not a consumer_test project"
        return True, None

    @staticmethod
    def is_consumer_context(
        state: Optional[Any] = None,
        project: Optional[Any] = None,
    ) -> bool:
        """Determine whether a state/project pair represents a consumer flow.

        This encapsulates the fallback rule: a simulation is treated as
        consumer-bound if either the state flag or the project type says so.
        """
        if state is not None and getattr(state, "consumer_mode", False):
            return True
        if project is not None and getattr(project, "project_type", None) == "consumer_test":
            return True
        if state is not None and getattr(state, "project_type", None) == "consumer_test":
            return True
        return False
