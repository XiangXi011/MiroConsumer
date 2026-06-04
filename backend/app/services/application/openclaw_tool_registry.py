"""Tool policy for President Lobster controlled execution."""

from __future__ import annotations


CONFIRMATION_GATES = {
    "execute_external_exploration": "confirm_research_plan",
    "start_project": "confirm_brief",
    "start_simulation": "confirm_start_simulation",
    "generate_report": "confirm_generate_report",
    "export_results": "confirm_export",
}


CONFIRMATION_ACTIONS = frozenset(CONFIRMATION_GATES.values()) | {
    "confirm_low_evidence_continue",
}


ALLOWED_TOOLS = {
    "research.plan",
    "research.explore",
    "research.brief",
    "project.start",
    "status.explain",
}


def required_confirmation_for(tool_action: str) -> str | None:
    return CONFIRMATION_GATES.get(tool_action)


def assert_confirmation_action_allowed(action_type: str) -> None:
    if action_type not in CONFIRMATION_ACTIONS:
        raise ValueError(f"Unknown confirmation action: {action_type}")


def assert_tool_allowed(tool_name: str) -> None:
    if tool_name not in ALLOWED_TOOLS:
        raise PermissionError(f"Tool is not allowed: {tool_name}")
