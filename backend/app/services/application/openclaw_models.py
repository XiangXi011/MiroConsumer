"""Data contracts for the President Lobster orchestration layer."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional


_last_now: Optional[datetime] = None


def _now_iso() -> str:
    global _last_now
    now = datetime.now(timezone.utc)
    if _last_now is not None and now <= _last_now:
        now = _last_now + timedelta(microseconds=1)
    _last_now = now
    return now.isoformat()


@dataclass
class OpenClawActionLogEntry:
    action_id: str
    action_type: str
    actor: str
    tool_name: str
    input_summary: Dict[str, Any]
    result_status: str
    created_at: str
    result_summary: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def create(
        cls,
        *,
        action_type: str,
        actor: str,
        tool_name: str,
        input_summary: Optional[Dict[str, Any]] = None,
        result_status: str,
        result_summary: Optional[Dict[str, Any]] = None,
    ) -> "OpenClawActionLogEntry":
        return cls(
            action_id=f"ocact_{uuid.uuid4().hex[:12]}",
            action_type=action_type,
            actor=actor,
            tool_name=tool_name,
            input_summary=input_summary or {},
            result_status=result_status,
            result_summary=result_summary or {},
            created_at=_now_iso(),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "action_id": self.action_id,
            "action_type": self.action_type,
            "actor": self.actor,
            "tool_name": self.tool_name,
            "input_summary": self.input_summary,
            "result_status": self.result_status,
            "result_summary": self.result_summary,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "OpenClawActionLogEntry":
        return cls(
            action_id=data["action_id"],
            action_type=data["action_type"],
            actor=data["actor"],
            tool_name=data["tool_name"],
            input_summary=data.get("input_summary", {}),
            result_status=data["result_status"],
            result_summary=data.get("result_summary", {}),
            created_at=data["created_at"],
        )


@dataclass
class OpenClawResearchSession:
    research_session_id: str
    status: str
    user_goal: str
    created_at: str
    updated_at: str
    user_id: str = ""
    tenant_id: str = ""
    exploration_plan: List[Dict[str, Any]] = field(default_factory=list)
    external_findings: List[Dict[str, Any]] = field(default_factory=list)
    rejected_external_findings: List[Dict[str, Any]] = field(default_factory=list)
    evidence_quality: Dict[str, Any] = field(default_factory=dict)
    research_brief: Dict[str, Any] = field(default_factory=dict)
    consumer_brief: Dict[str, Any] = field(default_factory=dict)
    confirmed_actions: List[str] = field(default_factory=list)
    action_log: List[OpenClawActionLogEntry] = field(default_factory=list)
    project_id: Optional[str] = None
    graph_build_task_id: Optional[str] = None
    graph_id: Optional[str] = None
    error: Optional[str] = None

    @classmethod
    def create(
        cls,
        *,
        user_goal: str,
        user_id: Optional[str] = None,
        tenant_id: Optional[str] = None,
    ) -> "OpenClawResearchSession":
        now = _now_iso()
        return cls(
            research_session_id=f"rsess_{uuid.uuid4().hex[:12]}",
            status="planning",
            user_goal=user_goal.strip(),
            created_at=now,
            updated_at=now,
            user_id=str(user_id or "").strip(),
            tenant_id=str(tenant_id or "").strip(),
        )

    def touch(self) -> None:
        self.updated_at = _now_iso()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "research_session_id": self.research_session_id,
            "status": self.status,
            "user_goal": self.user_goal,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "user_id": self.user_id,
            "tenant_id": self.tenant_id,
            "exploration_plan": self.exploration_plan,
            "external_findings": self.external_findings,
            "rejected_external_findings": self.rejected_external_findings,
            "evidence_quality": self.evidence_quality,
            "research_brief": self.research_brief,
            "consumer_brief": self.consumer_brief,
            "confirmed_actions": self.confirmed_actions,
            "action_log": [entry.to_dict() for entry in self.action_log],
            "project_id": self.project_id,
            "graph_build_task_id": self.graph_build_task_id,
            "graph_id": self.graph_id,
            "error": self.error,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "OpenClawResearchSession":
        return cls(
            research_session_id=data["research_session_id"],
            status=data["status"],
            user_goal=data["user_goal"],
            created_at=data["created_at"],
            updated_at=data["updated_at"],
            user_id=str(data.get("user_id") or "").strip(),
            tenant_id=str(data.get("tenant_id") or "").strip(),
            exploration_plan=data.get("exploration_plan", []),
            external_findings=data.get("external_findings", []),
            rejected_external_findings=data.get("rejected_external_findings", []),
            evidence_quality=data.get("evidence_quality", {}),
            research_brief=data.get("research_brief", {}),
            consumer_brief=data.get("consumer_brief", {}),
            confirmed_actions=data.get("confirmed_actions", []),
            action_log=[
                OpenClawActionLogEntry.from_dict(item)
                for item in data.get("action_log", [])
            ],
            project_id=data.get("project_id"),
            graph_build_task_id=data.get("graph_build_task_id"),
            graph_id=data.get("graph_id"),
            error=data.get("error"),
        )
