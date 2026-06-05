"""President Lobster orchestration service."""

from __future__ import annotations

import threading
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

from ...config import Config
from ...utils.locale import get_locale, set_locale
from ..consumer.openclaw_research_brief import (
    build_consumer_brief_from_session,
    build_exploration_plan,
    build_research_brief,
)
from .openclaw_models import OpenClawActionLogEntry, OpenClawResearchSession
from .openclaw_session_store import OpenClawSessionStore
from .openclaw_status import (
    next_action_for_session,
    session_business_state,
    status_explanation_for,
    timeline_for_session,
)
from .openclaw_tool_registry import (
    assert_confirmation_action_allowed,
    assert_tool_allowed,
    required_confirmation_for,
)
from .openclaw_evidence import (
    EXPLORATION_STRATEGIES,
    _confirmation_input_summary,
    _evidence_quality_summary,
    _normalize_risk_tags,
    _normalized_finding_text,
    _safe_float,
    _safe_top_k,
    _score_result_relevance,
)

SearchProvider = Callable[[str, int], List[Dict[str, Any]]]


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _default_search_provider(query: str, top_k: int) -> List[Dict[str, Any]]:
    import requests

    if not Config.LANE_B_HTTP_SEARCH_URL:
        return []

    response = requests.post(
        Config.LANE_B_HTTP_SEARCH_URL,
        json={"query": query, "limit": top_k, "top_k": top_k},
        headers={"Content-Type": "application/json", "Accept": "application/json"},
        timeout=30,
    )
    response.raise_for_status()
    data = response.json()
    if isinstance(data, dict):
        results = data.get("results", [])
    elif isinstance(data, list):
        results = data
    else:
        results = []

    return [item for item in results[:top_k] if isinstance(item, dict)]



class OpenClawProjectTaskMismatch(KeyError):
    def __init__(self, message: str, *, project: Any, task_project: Any):
        super().__init__(message)
        self.project = project
        self.task_project = task_project


def _resolve_project_status_target(
    project_id: Optional[str],
    task_id: Optional[str],
):
    from ...models.project import ProjectManager

    project = ProjectManager.get_project(project_id) if project_id else None
    if project_id and project is None:
        raise KeyError(f"Project {project_id} was not found.")

    if project is not None and task_id == project.graph_build_task_id:
        return project, task_id

    task_project = None
    if task_id:
        for candidate in ProjectManager.list_projects(limit=1000):
            if candidate.graph_build_task_id == task_id:
                task_project = candidate
                break

    if task_id and task_project is None:
        if project is not None:
            raise KeyError(f"Task {task_id} was not found for project {project.project_id}.")
        raise KeyError(f"Task {task_id} was not found.")
    if project is not None and task_project is not None:
        if project.project_id != task_project.project_id:
            raise OpenClawProjectTaskMismatch(
                f"Task {task_id} was not found for project {project.project_id}.",
                project=project,
                task_project=task_project,
            )
        return project, task_id
    if project is None and task_project is not None:
        return task_project, task_id
    if project is not None:
        return project, task_id or project.graph_build_task_id

    missing = project_id or task_id
    label = "Project" if project_id else "Task"
    raise KeyError(f"{label} {missing} was not found.")


class OpenClawOrchestrator:
    def __init__(
        self,
        *,
        store: Optional[OpenClawSessionStore] = None,
        search_provider: Optional[SearchProvider] = None,
    ):
        self.store = store or OpenClawSessionStore()
        self.search_provider = search_provider or _default_search_provider

    def create_session(
        self,
        user_goal: str,
        user_id: Optional[str] = None,
        tenant_id: Optional[str] = None,
    ) -> OpenClawResearchSession:
        assert_tool_allowed("research.plan")
        session = OpenClawResearchSession.create(
            user_goal=user_goal,
            user_id=user_id,
            tenant_id=tenant_id,
        )
        session.exploration_plan = build_exploration_plan(user_goal)
        session.action_log.append(
            OpenClawActionLogEntry.create(
                action_type="create_session",
                actor="orchestrator",
                tool_name="research.plan",
                input_summary={"user_goal": session.user_goal},
                result_status="planned",
                result_summary={"query_count": len(session.exploration_plan)},
            )
        )
        self.store.save(session)
        return session

    def get_session(self, research_session_id: str) -> OpenClawResearchSession:
        session = self.store.get(research_session_id)
        if session is None:
            raise KeyError(f"OpenClaw research session not found: {research_session_id}")
        return session

    def list_recent_sessions(
        self,
        limit: int = 10,
        user_id: Optional[str] = None,
        tenant_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        return [
            self.get_workspace_snapshot(session.research_session_id, compact=True)
            for session in self.store.list_recent(
                limit=limit,
                tenant_id=tenant_id,
                user_id=user_id,
            )
        ]

    def get_workspace_snapshot(
        self, research_session_id: str, compact: bool = False
    ) -> Dict[str, Any]:
        session = self.get_session(research_session_id)
        if compact:
            data = {
                "research_session_id": session.research_session_id,
                "user_goal": session.user_goal,
                "status": session.status,
                "created_at": session.created_at,
                "updated_at": session.updated_at,
                "user_id": session.user_id,
                "tenant_id": session.tenant_id,
                "project_id": session.project_id,
                "graph_build_task_id": session.graph_build_task_id,
                "graph_id": session.graph_id,
                "error": session.error,
            }
        else:
            data = session.to_dict()
        data.update(
            {
                "business_state": session_business_state(session),
                "timeline": timeline_for_session(session),
                "next_recommended_action": next_action_for_session(session),
                "can_leave_and_return": True,
                "technical_details": {
                    "research_session_id": session.research_session_id,
                    "status": session.status,
                    "project_id": session.project_id,
                    "graph_build_task_id": session.graph_build_task_id,
                    "graph_id": session.graph_id,
                    "updated_at": session.updated_at,
                },
            }
        )
        return data

    def explain_session_status(self, research_session_id: str) -> Dict[str, Any]:
        session = self.get_session(research_session_id)
        timeline = timeline_for_session(session)
        completed_steps = [
            item["label"] for item in timeline if item["status"] == "completed"
        ]
        business_state = session_business_state(session)
        return {
            "current_step": business_state["label"],
            "why_this_matters": status_explanation_for(session.status),
            "completed_steps": completed_steps,
            "blocked_reason": session.error,
            "next_recommended_action": next_action_for_session(session),
            "can_leave_and_return": True,
            "technical_details": {
                "research_session_id": session.research_session_id,
                "status": session.status,
                "progress": business_state["progress"],
                "project_id": session.project_id,
                "graph_build_task_id": session.graph_build_task_id,
                "graph_id": session.graph_id,
                "updated_at": session.updated_at,
            },
        }

    def confirm_action(
        self,
        research_session_id: str,
        *,
        action_type: str,
        payload: Optional[Dict[str, Any]] = None,
    ) -> OpenClawResearchSession:
        session = self.get_session(research_session_id)
        assert_confirmation_action_allowed(action_type)
        if action_type == "confirm_brief" and session.status != "brief_ready":
            raise PermissionError("confirm_brief requires status brief_ready")

        if action_type not in session.confirmed_actions:
            session.confirmed_actions.append(action_type)
        if action_type == "confirm_research_plan":
            session.status = "awaiting_exploration"
        elif action_type == "confirm_brief":
            session.status = "brief_confirmed"
        elif action_type == "confirm_low_evidence_continue":
            quality = dict(session.evidence_quality or {})
            quality["override_acknowledged"] = True
            quality["override_acknowledged_at"] = _now_iso()
            session.evidence_quality = quality
        session.action_log.append(
            OpenClawActionLogEntry.create(
                action_type=action_type,
                actor="user",
                tool_name="status.explain",
                input_summary=_confirmation_input_summary(payload),
                result_status="confirmed",
            )
        )
        self.store.save(session)
        return session

    def _assert_confirmed(
        self, session: OpenClawResearchSession, tool_action: str
    ) -> None:
        required_action = required_confirmation_for(tool_action)
        if required_action and required_action not in session.confirmed_actions:
            raise PermissionError(
                f"{tool_action} requires confirmation: {required_action}"
            )

    def execute_external_exploration(
        self,
        research_session_id: str,
        *,
        strategy: str = "retry_refined",
    ) -> OpenClawResearchSession:
        assert_tool_allowed("research.explore")
        session = self.get_session(research_session_id)
        self._assert_confirmed(session, "execute_external_exploration")
        strategy = str(strategy or "retry_refined").strip() or "retry_refined"
        if strategy not in EXPLORATION_STRATEGIES:
            raise ValueError(f"Unsupported exploration strategy: {strategy}")

        if strategy == "uploaded_only":
            session.external_findings = []
            session.rejected_external_findings = []
            session.evidence_quality = {
                "status": "manual_only",
                "gate": "review",
                "confidence_level": "low",
                "recoverable": True,
                "exploration_strategy": strategy,
                "raw_count": 0,
                "relevant_count": 0,
                "rejected_count": 0,
                "source_type_coverage": [],
                "average_relevance": 0.0,
                "user_visible_warnings": [
                    "已选择仅使用上传/手动材料，外部资料不会进入项目上下文。"
                ],
            }
            session.status = "explored"
            session.action_log.append(
                OpenClawActionLogEntry.create(
                    action_type="execute_external_exploration",
                    actor="orchestrator",
                    tool_name="research.explore",
                    input_summary={"query_count": 0, "strategy": strategy},
                    result_status="explored",
                    result_summary={
                        "finding_count": 0,
                        "rejected_count": 0,
                        "evidence_quality": session.evidence_quality.get("status"),
                        "strategy": strategy,
                    },
                )
            )
            self.store.save(session)
            return session

        findings: List[Dict[str, Any]] = []
        rejected_findings: List[Dict[str, Any]] = []
        raw_count = 0
        seen_urls = set()
        seen_texts = set()
        plan_limit = len(session.exploration_plan) if strategy == "broaden_search" else 6
        for plan_item in session.exploration_plan[:plan_limit]:
            query = str(plan_item.get("query", "")).strip()
            if not query:
                continue
            top_k = _safe_top_k(plan_item.get("max_results", 3))
            if strategy == "broaden_search":
                top_k = min(5, top_k + 2)
            evidence_type = str(
                plan_item.get("evidence_type") or "category_context"
            )
            for result in self.search_provider(query, top_k):
                raw_count += 1
                title = str(result.get("title", "")).strip()
                url = str(result.get("url", result.get("href", ""))).strip()
                snippet = str(
                    result.get(
                        "snippet",
                        result.get("content", result.get("abstract", "")),
                    )
                ).strip()
                confidence = _safe_float(result.get("confidence", 0.5), 0.5)
                finding = {
                    "title": title,
                    "url": url,
                    "snippet": snippet,
                    "query": query,
                    "evidence_type": evidence_type,
                    "confidence": confidence,
                    "risk_tags": _normalize_risk_tags(result.get("risk_tags")),
                    "retrieved_at": _now_iso(),
                    "source": "external_exploration",
                }
                text_key = _normalized_finding_text(title, snippet).lower()
                url_key = url.lower()
                if url_key and url_key in seen_urls:
                    rejected_findings.append(
                        {**finding, "reject_reason": "duplicate_url", "relevance_score": 0.0, "source_type": "rejected"}
                    )
                    continue
                if text_key and text_key in seen_texts:
                    rejected_findings.append(
                        {**finding, "reject_reason": "duplicate_text", "relevance_score": 0.0, "source_type": "rejected"}
                    )
                    continue

                quality = _score_result_relevance(
                    user_goal=session.user_goal,
                    query=query,
                    title=title,
                    url=url,
                    snippet=snippet,
                    evidence_type=evidence_type,
                    confidence=confidence,
                )
                finding["relevance_score"] = quality["score"]
                finding["source_type"] = quality["source_type"]
                if quality["accepted"]:
                    findings.append(finding)
                    if url_key:
                        seen_urls.add(url_key)
                    if text_key:
                        seen_texts.add(text_key)
                else:
                    rejected_findings.append(
                        {**finding, "reject_reason": quality["reject_reason"]}
                    )

        session.external_findings = findings
        session.rejected_external_findings = rejected_findings
        session.evidence_quality = _evidence_quality_summary(
            findings,
            rejected_findings,
            raw_count,
            strategy=strategy,
        )
        session.status = "explored"
        session.action_log.append(
            OpenClawActionLogEntry.create(
                action_type="execute_external_exploration",
                actor="orchestrator",
                tool_name="research.explore",
                input_summary={"query_count": min(len(session.exploration_plan), plan_limit), "strategy": strategy},
                result_status="explored",
                result_summary={
                    "finding_count": len(findings),
                    "rejected_count": len(rejected_findings),
                    "evidence_quality": session.evidence_quality.get("status"),
                    "strategy": strategy,
                },
            )
        )
        self.store.save(session)
        return session

    def prepare_consumer_brief(
        self, research_session_id: str
    ) -> OpenClawResearchSession:
        assert_tool_allowed("research.brief")
        session = self.get_session(research_session_id)
        if session.status != "explored":
            raise PermissionError("prepare_consumer_brief requires status explored")
        session.research_brief = build_research_brief(
            user_goal=session.user_goal,
            external_findings=session.external_findings,
        )
        session.research_brief["evidence_quality"] = session.evidence_quality or {}
        session.research_brief["rejected_source_count"] = len(
            session.rejected_external_findings
        )
        session.consumer_brief = build_consumer_brief_from_session(session.to_dict())
        session.status = "brief_ready"
        session.action_log.append(
            OpenClawActionLogEntry.create(
                action_type="prepare_consumer_brief",
                actor="orchestrator",
                tool_name="research.brief",
                input_summary={"finding_count": len(session.external_findings)},
                result_status="brief_ready",
                result_summary={
                    "source_count": session.research_brief.get("source_count", 0)
                },
            )
        )
        self.store.save(session)
        return session

    def start_project(
        self,
        research_session_id: str,
        *,
        background: bool = False,
    ) -> OpenClawResearchSession:
        assert_tool_allowed("project.start")
        session = self.get_session(research_session_id)
        self._assert_confirmed(session, "start_project")
        if session.project_id:
            return session
        if not session.consumer_brief:
            raise ValueError("consumer_brief is required before project start")
        evidence_quality = session.evidence_quality or {}
        if (
            evidence_quality.get("gate") == "blocked"
            and "confirm_low_evidence_continue" not in session.confirmed_actions
        ):
            raise PermissionError(
                "low evidence requires confirmation: confirm_low_evidence_continue"
            )

        from ...models.project import ProjectManager, ProjectStatus
        from ...models.task import TaskManager

        project = ProjectManager.create_project(
            name=f"President Lobster - {session.user_goal[:40]}",
            tenant_id=session.tenant_id or "",
        )
        project.project_type = "consumer_test"
        project.consumer_brief = session.consumer_brief
        project.status = ProjectStatus.ONTOLOGY_GENERATED
        project.ontology = {
            "entity_types": [{"name": "ProductConcept", "attributes": []}],
            "edge_types": [],
        }
        project.analysis_summary = session.research_brief.get("summary", "")
        ProjectManager.save_project(project)
        ProjectManager.save_extracted_text(project.project_id, self._project_text(session))
        self._ingest_external_findings(project.project_id, session)

        task_manager = TaskManager()
        task_id = task_manager.create_task(
            "consumer_graph_build",
            metadata={
                "research_session_id": session.research_session_id,
                "project_id": project.project_id,
            },
        )
        project.status = ProjectStatus.GRAPH_BUILDING
        project.graph_build_task_id = task_id
        ProjectManager.save_project(project)
        session.project_id = project.project_id
        session.graph_build_task_id = task_id
        session.status = "project_starting"
        session.error = None
        self.store.save(session)

        if background:
            self._spawn_project_graph_build(
                session=session,
                project=project,
                task_manager=task_manager,
                task_id=task_id,
                locale=get_locale(),
            )
            return session

        return self._run_project_graph_build(
            session=session,
            project=project,
            task_manager=task_manager,
            task_id=task_id,
            raise_errors=True,
        )

    def _spawn_project_graph_build(
        self,
        *,
        session: OpenClawResearchSession,
        project,
        task_manager,
        task_id: str,
        locale: str,
    ) -> None:
        def build_task() -> None:
            set_locale(locale)
            latest = self.store.get(session.research_session_id) or session
            self._run_project_graph_build(
                session=latest,
                project=project,
                task_manager=task_manager,
                task_id=task_id,
                raise_errors=False,
            )

        thread = threading.Thread(
            target=build_task,
            name=f"openclaw-project-{session.research_session_id}",
            daemon=True,
        )
        thread.start()

    def _run_project_graph_build(
        self,
        *,
        session: OpenClawResearchSession,
        project,
        task_manager,
        task_id: str,
        raise_errors: bool,
    ) -> OpenClawResearchSession:
        from ...models.project import ProjectManager, ProjectStatus
        from ...services.application.graph_app_service import GraphAppService

        try:
            graph_data = GraphAppService.build_consumer_graph_sync(
                project,
                ProjectManager.get_extracted_text(project.project_id) or session.user_goal,
                task_manager,
                task_id,
            )
        except Exception as exc:
            project.status = ProjectStatus.FAILED
            project.error = str(exc) or exc.__class__.__name__
            ProjectManager.save_project(project)
            latest = self.store.get(session.research_session_id) or session
            latest.project_id = latest.project_id or project.project_id
            latest.graph_build_task_id = latest.graph_build_task_id or task_id
            latest.status = "project_start_failed"
            latest.error = str(exc) or exc.__class__.__name__
            latest.action_log.append(
                OpenClawActionLogEntry.create(
                    action_type="start_project",
                    actor="orchestrator",
                    tool_name="project.start",
                    input_summary={"project_type": "consumer_test"},
                    result_status="failed",
                    result_summary={
                        "project_id": project.project_id,
                        "task_id": task_id,
                    },
                )
            )
            self.store.save(latest)
            if raise_errors:
                raise
            return latest

        latest = self.store.get(session.research_session_id) or session
        latest.project_id = latest.project_id or project.project_id
        latest.graph_build_task_id = latest.graph_build_task_id or task_id
        latest.graph_id = graph_data.get("graph_id")
        latest.status = "project_started"
        latest.error = None
        project.graph_id = latest.graph_id
        project.status = ProjectStatus.GRAPH_COMPLETED
        project.error = None
        ProjectManager.save_project(project)
        latest.action_log.append(
            OpenClawActionLogEntry.create(
                action_type="start_project",
                actor="orchestrator",
                tool_name="project.start",
                input_summary={"project_type": "consumer_test"},
                result_status="completed",
                result_summary={"project_id": project.project_id, "task_id": task_id},
            )
        )
        self.store.save(latest)
        return latest

    def _project_text(self, session: OpenClawResearchSession) -> str:
        source_lines = [
            f"- [{item.get('evidence_type')}] {item.get('title')}: {item.get('snippet')} ({item.get('url')})"
            for item in session.external_findings
        ]
        return "\n".join(
            [session.user_goal, session.research_brief.get("summary", ""), *source_lines]
        )

    def _ingest_external_findings(
        self, project_id: str, session: OpenClawResearchSession
    ) -> None:
        from ...services.consumer.document_ingest import DocumentIngestService
        from ...services.consumer.models import ResearchSourceLane, ResearchSourceType
        from ...services.consumer.source_registry import SourceRegistry

        registry = SourceRegistry(project_id, upload_root=Config.UPLOAD_FOLDER)
        ingest = DocumentIngestService(project_id, upload_root=Config.UPLOAD_FOLDER)
        seen_texts = set()
        seen_urls = set()
        for item in session.external_findings:
            url = str(item.get("url", "")).strip()
            title = str(item.get("title", "")).strip()
            text = _normalized_finding_text(item.get("snippet")) or title
            if not text:
                continue

            text_key = _normalized_finding_text(text).lower()
            if text_key in seen_texts:
                continue

            url_key = url.lower()
            if url_key and url_key in seen_urls:
                continue

            seen_texts.add(text_key)
            if url_key:
                seen_urls.add(url_key)

            source = registry.get_or_register_source(
                lane=ResearchSourceLane.LaneB,
                source_type=ResearchSourceType.PublicWeb,
                label=title or "President Lobster source",
                uri=url,
                metadata={
                    "research_session_id": session.research_session_id,
                    "query": item.get("query", ""),
                    "evidence_type": item.get("evidence_type", ""),
                    "source": item.get("source", "external_exploration"),
                },
            )
            ingest.ingest_text(
                source_id=source.source_id,
                text=text,
                title=title or "President Lobster source",
            )

    def explain_project_status(
        self, *, project_id: Optional[str] = None, task_id: Optional[str] = None
    ) -> Dict[str, Any]:
        assert_tool_allowed("status.explain")
        from ...models.project import ProjectStatus
        from ...models.task import TaskManager

        project, task_id = _resolve_project_status_target(project_id, task_id)

        project_status = (
            project.status.value if hasattr(project.status, "value") else project.status
        )
        graph_id = project.graph_id
        task = TaskManager().get_task(task_id) if task_id else None

        if task:
            task_status = task.status.value if hasattr(task.status, "value") else task.status
            progress = task.progress
            progress_message = task.message
            task_updated_at = task.updated_at.isoformat()
            if task_status == "completed":
                project_status = ProjectStatus.GRAPH_COMPLETED.value
                progress = 100
                progress_message = progress_message or "Graph build completed."
                if isinstance(task.result, dict):
                    graph_id = task.result.get("graph_id") or graph_id
            elif task_status == "failed":
                project_status = ProjectStatus.FAILED.value
                progress = 0
                progress_message = task.error or progress_message or "Graph build failed."
        elif project_status == ProjectStatus.GRAPH_COMPLETED.value and project.graph_id:
            task_status = "completed"
            progress = 100
            progress_message = "Graph build completed."
            task_updated_at = project.updated_at
        elif project_status == ProjectStatus.FAILED.value:
            task_status = "failed"
            progress = 0
            progress_message = project.error or "Graph build failed."
            task_updated_at = project.updated_at
        elif project_status == ProjectStatus.GRAPH_BUILDING.value:
            task_status = "processing"
            progress = 15
            progress_message = "Building research context. You can leave this page and return later."
            task_updated_at = project.updated_at
        else:
            task_status = "pending"
            progress = 0
            progress_message = "OpenClaw project context is waiting for the next step."
            task_updated_at = project.updated_at

        explanation_parts = [
            f"Project {project.project_id} is currently {project_status}.",
        ]
        if task_id:
            explanation_parts.append(
                f"Task {task_id} is {task_status} at {progress}%."
            )
        if progress_message:
            explanation_parts.append(progress_message)

        if project_status == ProjectStatus.GRAPH_BUILDING.value:
            current_step = "Building simulation context"
            why_this_matters = "The project is organizing evidence into a context graph before simulation can begin."
            next_action = {
                "kind": "wait_for_context_build",
                "label": "Wait for context build",
            }
            completed_steps = ["Research project created"]
            blocked_reason = None
        elif project_status == ProjectStatus.GRAPH_COMPLETED.value:
            current_step = "Ready for simulation"
            why_this_matters = "The context graph is ready, so the project can move into simulation work."
            next_action = {"kind": "start_simulation", "label": "Start simulation"}
            completed_steps = ["Research project created", "Simulation context built"]
            blocked_reason = None
        elif project_status == ProjectStatus.FAILED.value:
            current_step = "Project needs attention"
            why_this_matters = "The project cannot continue until the recorded failure is reviewed."
            next_action = {
                "kind": "review_project_error",
                "label": "Review project issue",
            }
            completed_steps = ["Research project created"]
            blocked_reason = progress_message
        else:
            current_step = "Waiting for next project step"
            why_this_matters = "This project is saved and can be resumed from its current status."
            next_action = {"kind": "review_project", "label": "Review project"}
            completed_steps = []
            blocked_reason = None

        return {
            "explanation": " ".join(explanation_parts),
            "project_id": project.project_id,
            "task_id": task_id,
            "project_status": project_status,
            "task_status": task_status,
            "progress": progress,
            "progress_message": progress_message,
            "recoverable": project_status == ProjectStatus.GRAPH_BUILDING.value,
            "graph_id": graph_id,
            "updated_at": task_updated_at,
            "current_step": current_step,
            "why_this_matters": why_this_matters,
            "completed_steps": completed_steps,
            "blocked_reason": blocked_reason,
            "next_recommended_action": next_action,
            "can_leave_and_return": True,
            "technical_details": {
                "project_id": project.project_id,
                "task_id": task_id,
                "project_status": project_status,
                "task_status": task_status,
                "graph_id": graph_id,
                "updated_at": task_updated_at,
            },
        }
