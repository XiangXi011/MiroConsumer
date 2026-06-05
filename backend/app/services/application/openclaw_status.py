"""Status view helpers for OpenClaw research sessions."""

from __future__ import annotations

from typing import Any

from .openclaw_models import OpenClawResearchSession

OPENCLAW_TIMELINE = [
    {
        "key": "understand_goal",
        "label": "Understanding research goal",
        "statuses": {"planning"},
    },
    {
        "key": "plan_research",
        "label": "Confirming research plan",
        "statuses": {"awaiting_exploration"},
    },
    {
        "key": "explore_sources",
        "label": "Exploring evidence sources",
        "statuses": {"exploring"},
    },
    {
        "key": "review_evidence",
        "label": "Reviewing evidence quality",
        "statuses": {"explored"},
    },
    {
        "key": "generate_brief",
        "label": "Generating consumer research brief",
        "statuses": {"brief_ready", "brief_confirmed"},
    },
    {
        "key": "create_project",
        "label": "Creating research project",
        "statuses": {"project_starting", "project_start_failed"},
    },
    {
        "key": "build_context",
        "label": "Building simulation context",
        "statuses": {"graph_building"},
    },
    {
        "key": "ready_for_simulation",
        "label": "Ready for simulation",
        "statuses": {"project_started", "simulation_ready"},
    },
]

_STATUS_TO_TIMELINE_INDEX = {
    status: index
    for index, item in enumerate(OPENCLAW_TIMELINE)
    for status in item["statuses"]
}

_STATUS_EXPLANATIONS = {
    "planning": "We are turning the business goal into a research plan before any external work begins.",
    "awaiting_exploration": "The research plan is ready for your confirmation, so the next step is evidence gathering.",
    "exploring": "OpenClaw is collecting sources that can support or challenge the concept.",
    "explored": "The source scan is complete and needs review before a brief is generated.",
    "brief_ready": "The consumer brief is ready for approval before a project is created.",
    "brief_confirmed": "The brief has been approved and can be turned into a project.",
    "project_starting": "The project exists and the workspace is preparing the simulation context.",
    "project_start_failed": "Project setup hit an error and can be retried after review.",
    "graph_building": "The project is organizing evidence into a context graph before simulation can begin.",
    "project_started": "The project context is available and the graph build has completed.",
    "simulation_ready": "The research workspace is ready for simulation work.",
}

_NEXT_ACTIONS = {
    "planning": {
        "kind": "confirm_research_plan",
        "label": "Confirm research plan",
    },
    "awaiting_exploration": {
        "kind": "execute_external_exploration",
        "label": "Explore evidence sources",
    },
    "exploring": {
        "kind": "wait_for_exploration",
        "label": "Wait for source exploration",
    },
    "explored": {
        "kind": "prepare_consumer_brief",
        "label": "Generate consumer research brief",
    },
    "brief_ready": {
        "kind": "confirm_brief",
        "label": "Confirm consumer brief",
    },
    "brief_confirmed": {
        "kind": "start_project",
        "label": "Create research project",
    },
    "project_starting": {
        "kind": "wait_for_context_build",
        "label": "Wait for context build",
    },
    "project_start_failed": {
        "kind": "review_project_error",
        "label": "Review project setup issue",
    },
    "graph_building": {
        "kind": "wait_for_context_build",
        "label": "Wait for context build",
    },
    "project_started": {
        "kind": "open_project",
        "label": "Open research project",
    },
    "simulation_ready": {
        "kind": "start_simulation",
        "label": "Start simulation",
    },
}


def session_timeline_index(session: OpenClawResearchSession) -> int:
    return _STATUS_TO_TIMELINE_INDEX.get(session.status, 0)


def session_progress(status: str) -> int:
    index = _STATUS_TO_TIMELINE_INDEX.get(status, 0)
    if len(OPENCLAW_TIMELINE) <= 1:
        return 0
    return round(index / (len(OPENCLAW_TIMELINE) - 1) * 100)


def session_business_state(session: OpenClawResearchSession) -> dict[str, Any]:
    index = session_timeline_index(session)
    timeline_item = OPENCLAW_TIMELINE[index]
    confidence = "needs_attention" if session.error else "normal"
    if session.status in {"project_started", "simulation_ready"}:
        confidence = "high"
    elif session.evidence_quality.get("confidence_level"):
        confidence = session.evidence_quality["confidence_level"]
    return {
        "label": timeline_item["label"],
        "technical_status": session.status,
        "progress": session_progress(session.status),
        "confidence": confidence,
    }


def timeline_for_session(session: OpenClawResearchSession) -> list[dict[str, Any]]:
    current_index = session_timeline_index(session)
    timeline = []
    for index, item in enumerate(OPENCLAW_TIMELINE):
        if index < current_index:
            status = "completed"
        elif index == current_index:
            status = "current"
        else:
            status = "pending"
        timeline.append(
            {
                "key": item["key"],
                "label": item["label"],
                "status": status,
            }
        )
    return timeline


def next_action_for_session(session: OpenClawResearchSession) -> dict[str, str]:
    return dict(
        _NEXT_ACTIONS.get(
            session.status,
            {
                "kind": "review_workspace",
                "label": "Review workspace",
            },
        )
    )


def status_explanation_for(status: str) -> str:
    return _STATUS_EXPLANATIONS.get(
        status,
        "This workspace state determines the next safe business action.",
    )
