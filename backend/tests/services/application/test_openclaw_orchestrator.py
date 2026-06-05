import pytest

from app.api import graph as graph_api
from app.models.project import ProjectManager, ProjectStatus
from app.models.task import TaskManager
from app.services.application.openclaw_orchestrator import OpenClawOrchestrator
from app.services.application.openclaw_session_store import OpenClawSessionStore
from app.services.consumer.openclaw_research_brief import build_exploration_plan
from app.services.consumer.document_ingest import DocumentIngestService
from app.services.consumer.models import ResearchSourceLane
from app.services.consumer.source_registry import SourceRegistry


def _provider(query, top_k):
    return [
        {
            "title": "Parent concern source",
            "url": "https://example.com/parent-concern",
            "snippet": "Parents ask for safety proof before buying kids toothpaste.",
        }
    ]


def test_shuke_magic_toothpaste_plan_uses_structured_research_queries():
    goal = (
        "请用 OpenClaw 自主调研舒客宝贝魔法变色牙膏，目标是判断儿童牙膏的"
        "低氟安全、魔法变色泡沫、家长顾虑和电商评价。"
    )

    plan = build_exploration_plan(goal)
    queries = [item["query"] for item in plan]
    evidence_types = {item["evidence_type"] for item in plan}

    assert len(plan) >= 6
    assert {
        "product_fact",
        "category_safety",
        "claim_risk",
        "ecommerce_reviews",
        "parent_objections",
        "regulatory",
    }.issubset(evidence_types)
    assert any("舒客宝贝" in query and "牙膏" in query for query in queries)
    assert any("儿童牙膏" in query and "安全" in query for query in queries)
    assert any("魔法变色" in query and "色素" in query for query in queries)
    assert any("评价" in query and ("京东" in query or "天猫" in query) for query in queries)
    assert all(goal not in query for query in queries)


def test_orchestrator_filters_irrelevant_search_results_and_records_rejected_evidence(tmp_path):
    calls = []

    def mixed_provider(query, top_k):
        calls.append(query)
        if "国家标准" in query or "法规" in query:
            relevant = {
                "title": "儿童牙膏含氟国家标准与安全提示",
                "url": f"https://gov.example.com/kids-toothpaste-{len(calls)}",
                "snippet": "儿童牙膏、含氟安全、国家标准和儿童口腔护理合规边界。",
            }
        elif "评价" in query or "京东" in query:
            relevant = {
                "title": "舒客宝贝魔法变色牙膏京东评价",
                "url": f"https://jd.example.com/shuke-review-{len(calls)}",
                "snippet": "家长评价关注儿童是否愿意刷牙、变色泡沫趣味和价格。",
            }
        elif "色素" in query or "误读" in query:
            relevant = {
                "title": "儿童变色牙膏色素安全顾虑讨论",
                "url": f"https://example.com/claim-risk-{len(calls)}",
                "snippet": "魔法变色、色素、安全证明和家长误读是儿童牙膏传播风险。",
            }
        else:
            relevant = {
                "title": "舒客宝贝儿童魔法变色牙膏低氟安全说明",
                "url": f"https://example.com/shuke-kids-toothpaste-{len(calls)}",
                "snippet": "儿童牙膏、低氟、刷牙习惯和家长安全顾虑是购买决策重点。",
            }
        return [
            relevant,
            {
                "title": "Formula 1 race calendar",
                "url": "https://www.formula1.com/en/racing/2026.html",
                "snippet": "Grand Prix schedule and driver standings.",
            },
            {
                "title": "ESPN basketball scoreboard",
                "url": "https://www.espn.com/nba/scoreboard",
                "snippet": "Live sports scores and highlights.",
            },
        ]

    store = OpenClawSessionStore(upload_root=str(tmp_path / "uploads"))
    orchestrator = OpenClawOrchestrator(store=store, search_provider=mixed_provider)
    session = orchestrator.create_session("舒客宝贝魔法变色牙膏 儿童牙膏 家长顾虑")
    orchestrator.confirm_action(session.research_session_id, action_type="confirm_research_plan")

    explored = orchestrator.execute_external_exploration(session.research_session_id)

    assert explored.external_findings
    assert all("formula1" not in item["url"] for item in explored.external_findings)
    assert all("espn" not in item["url"] for item in explored.external_findings)
    assert explored.rejected_external_findings
    assert any("blocked_domain" in item["reject_reason"] for item in explored.rejected_external_findings)
    assert explored.evidence_quality["status"] == "sufficient"
    assert explored.evidence_quality["rejected_count"] >= 2


def test_orchestrator_does_not_let_relevant_query_text_rescue_irrelevant_results(tmp_path):
    def noisy_provider(query, top_k):
        return [
            {
                "title": "Sheraton Grand Seattle | Downtown Hotel by Convention Center",
                "url": "https://www.marriott.com/en-us/hotels/seasi-sheraton-grand-seattle/overview/",
                "snippet": "Book a downtown hotel near the convention center with meeting rooms.",
                "confidence": 0.95,
            },
            {
                "title": "Dom Space : A Place For Dominants, By Dominants - Reddit",
                "url": "https://www.reddit.com/r/domspace/wiki/faq/",
                "snippet": "A community FAQ about moderation, roles, and posting rules.",
                "confidence": 0.95,
            },
        ]

    store = OpenClawSessionStore(upload_root=str(tmp_path / "uploads"))
    orchestrator = OpenClawOrchestrator(store=store, search_provider=noisy_provider)
    session = orchestrator.create_session("舒客宝贝魔法变色牙膏 儿童牙膏 家长顾虑 含氟安全")
    orchestrator.confirm_action(session.research_session_id, action_type="confirm_research_plan")

    explored = orchestrator.execute_external_exploration(session.research_session_id)

    assert explored.external_findings == []
    assert len(explored.rejected_external_findings) >= 2
    assert all(item["reject_reason"] == "low_relevance" for item in explored.rejected_external_findings)
    assert explored.evidence_quality["gate"] == "blocked"


def test_orchestrator_requires_explicit_low_evidence_ack_before_project_start(
    tmp_path, monkeypatch
):
    uploads_dir = tmp_path / "uploads"
    monkeypatch.setattr(graph_api.Config, "UPLOAD_FOLDER", str(uploads_dir))
    monkeypatch.setattr(ProjectManager, "PROJECTS_DIR", str(uploads_dir / "projects"))
    monkeypatch.setattr(
        "app.services.application.openclaw_orchestrator.Config.UPLOAD_FOLDER",
        str(uploads_dir),
    )

    def irrelevant_provider(query, top_k):
        return [
            {
                "title": "Chinese dictionary entry",
                "url": "https://dict.example.com/word",
                "snippet": "A dictionary page unrelated to consumer oral care research.",
            }
        ]

    def fake_build(project, text, task_manager, task_id):
        project.graph_id = f"consumer_{project.project_id}"
        project.status = ProjectStatus.GRAPH_COMPLETED
        ProjectManager.save_project(project)
        return {"graph_id": project.graph_id}

    monkeypatch.setattr(
        "app.services.application.graph_app_service.GraphAppService.build_consumer_graph_sync",
        fake_build,
    )
    store = OpenClawSessionStore(upload_root=str(uploads_dir))
    orchestrator = OpenClawOrchestrator(store=store, search_provider=irrelevant_provider)
    session = orchestrator.create_session("舒客宝贝魔法变色牙膏 儿童牙膏 家长顾虑")
    orchestrator.confirm_action(session.research_session_id, action_type="confirm_research_plan")
    explored = orchestrator.execute_external_exploration(session.research_session_id)
    orchestrator.prepare_consumer_brief(session.research_session_id)
    orchestrator.confirm_action(session.research_session_id, action_type="confirm_brief")

    assert explored.evidence_quality["gate"] == "blocked"
    with pytest.raises(PermissionError, match="low evidence"):
        orchestrator.start_project(session.research_session_id)

    orchestrator.confirm_action(
        session.research_session_id,
        action_type="confirm_low_evidence_continue",
        payload={"approved": True},
    )
    started = orchestrator.start_project(session.research_session_id)

    assert started.status == "project_started"


def test_orchestrator_requires_confirmation_before_external_exploration(tmp_path):
    store = OpenClawSessionStore(upload_root=str(tmp_path / "uploads"))
    orchestrator = OpenClawOrchestrator(store=store, search_provider=_provider)
    session = orchestrator.create_session("Test kids toothpaste")

    with pytest.raises(PermissionError, match="confirm_research_plan"):
        orchestrator.execute_external_exploration(session.research_session_id)


def test_orchestrator_create_session_passes_owner_metadata(tmp_path):
    store = OpenClawSessionStore(upload_root=str(tmp_path / "uploads"))
    orchestrator = OpenClawOrchestrator(store=store, search_provider=_provider)

    session = orchestrator.create_session(
        " Test kids toothpaste ",
        user_id=" user_a ",
        tenant_id=" tenant_a ",
    )

    persisted = orchestrator.get_session(session.research_session_id)
    assert persisted.user_goal == "Test kids toothpaste"
    assert persisted.user_id == "user_a"
    assert persisted.tenant_id == "tenant_a"


def test_orchestrator_rejects_unknown_confirmation_action(tmp_path):
    store = OpenClawSessionStore(upload_root=str(tmp_path / "uploads"))
    orchestrator = OpenClawOrchestrator(store=store, search_provider=_provider)
    session = orchestrator.create_session("Test kids toothpaste")

    with pytest.raises((PermissionError, ValueError), match="Unknown confirmation"):
        orchestrator.confirm_action(
            session.research_session_id,
            action_type="confirm_everything",
            payload={"approved": True},
        )

    persisted = orchestrator.get_session(session.research_session_id)
    assert "confirm_everything" not in persisted.confirmed_actions


def test_orchestrator_rejects_brief_confirmation_before_brief_ready(tmp_path):
    store = OpenClawSessionStore(upload_root=str(tmp_path / "uploads"))
    orchestrator = OpenClawOrchestrator(store=store, search_provider=_provider)
    session = orchestrator.create_session("Test kids toothpaste")

    with pytest.raises(PermissionError, match="brief_ready"):
        orchestrator.confirm_action(
            session.research_session_id,
            action_type="confirm_brief",
            payload={"approved": True},
        )

    persisted = orchestrator.get_session(session.research_session_id)
    assert "confirm_brief" not in persisted.confirmed_actions


def test_orchestrator_explores_after_confirmation_and_logs_action(tmp_path):
    store = OpenClawSessionStore(upload_root=str(tmp_path / "uploads"))
    orchestrator = OpenClawOrchestrator(store=store, search_provider=_provider)
    session = orchestrator.create_session("Test kids toothpaste")
    payload = {
        "approved": True,
        "approved_queries": session.exploration_plan,
        "raw_provider_payload": {"token": "secret", "body": "x" * 1000},
    }

    orchestrator.confirm_action(
        session.research_session_id,
        action_type="confirm_research_plan",
        payload=payload,
    )
    explored = orchestrator.execute_external_exploration(session.research_session_id)

    assert explored.status == "explored"
    assert explored.external_findings[0]["url"] == "https://example.com/parent-concern"
    assert explored.external_findings[0]["source"] == "external_exploration"
    confirmation_entry = next(
        entry
        for entry in explored.action_log
        if entry.action_type == "confirm_research_plan"
    )
    assert confirmation_entry.input_summary == {
        "approved": True,
        "approved_query_count": len(session.exploration_plan),
    }
    assert any(
        entry.action_type == "execute_external_exploration"
        for entry in explored.action_log
    )


def test_orchestrator_clamps_exploration_top_k_and_normalizes_risk_tags(tmp_path):
    calls = []

    def provider(query, top_k):
        calls.append((query, top_k))
        return [
            {
                "title": "Parent concern source",
                "url": "https://example.com/parent-concern",
                "snippet": "Parents ask for safety proof before buying kids toothpaste.",
                "risk_tags": "privacy",
            }
        ]

    store = OpenClawSessionStore(upload_root=str(tmp_path / "uploads"))
    orchestrator = OpenClawOrchestrator(store=store, search_provider=provider)
    session = orchestrator.create_session("Test kids toothpaste")
    session.exploration_plan = [
        {"query": "too many results", "max_results": 99},
        {"query": "invalid results", "max_results": "many"},
        {"query": "zero results", "max_results": 0},
    ]
    store.save(session)
    orchestrator.confirm_action(
        session.research_session_id,
        action_type="confirm_research_plan",
        payload={"approved_queries": session.exploration_plan},
    )

    explored = orchestrator.execute_external_exploration(session.research_session_id)

    assert calls == [
        ("too many results", 5),
        ("invalid results", 3),
        ("zero results", 1),
    ]
    assert explored.external_findings[0]["risk_tags"] == []


def test_orchestrator_rejects_brief_preparation_before_exploration(tmp_path):
    store = OpenClawSessionStore(upload_root=str(tmp_path / "uploads"))
    orchestrator = OpenClawOrchestrator(store=store, search_provider=_provider)
    session = orchestrator.create_session("Evaluate Shuke kids toothpaste for moms")

    with pytest.raises(PermissionError, match="explored"):
        orchestrator.prepare_consumer_brief(session.research_session_id)


def test_orchestrator_prepares_brief_after_exploration(tmp_path):
    store = OpenClawSessionStore(upload_root=str(tmp_path / "uploads"))
    orchestrator = OpenClawOrchestrator(store=store, search_provider=_provider)
    session = orchestrator.create_session("Evaluate Shuke kids toothpaste for moms")
    orchestrator.confirm_action(
        session.research_session_id,
        action_type="confirm_research_plan",
        payload={"approved_queries": session.exploration_plan},
    )
    session = orchestrator.execute_external_exploration(session.research_session_id)

    briefed = orchestrator.prepare_consumer_brief(session.research_session_id)

    assert briefed.status == "brief_ready"
    assert briefed.research_brief["source_count"] > 0
    assert briefed.consumer_brief["task_type"] == "concept_test"
    assert "confirm_brief" not in briefed.confirmed_actions


def test_orchestrator_start_project_requires_confirmed_brief(tmp_path, monkeypatch):
    uploads_dir = tmp_path / "uploads"
    monkeypatch.setattr(graph_api.Config, "UPLOAD_FOLDER", str(uploads_dir))
    monkeypatch.setattr(ProjectManager, "PROJECTS_DIR", str(uploads_dir / "projects"))
    store = OpenClawSessionStore(upload_root=str(uploads_dir))
    orchestrator = OpenClawOrchestrator(store=store, search_provider=_provider)
    session = orchestrator.create_session("Evaluate Shuke kids toothpaste")
    orchestrator.confirm_action(
        session.research_session_id,
        action_type="confirm_research_plan",
        payload={"approved": True},
    )
    orchestrator.execute_external_exploration(session.research_session_id)
    orchestrator.prepare_consumer_brief(session.research_session_id)

    with pytest.raises(PermissionError, match="confirm_brief"):
        orchestrator.start_project(session.research_session_id)


def test_orchestrator_start_project_creates_consumer_project_and_ingests_sources(
    tmp_path, monkeypatch
):
    uploads_dir = tmp_path / "uploads"
    monkeypatch.setattr(graph_api.Config, "UPLOAD_FOLDER", str(uploads_dir))
    monkeypatch.setattr(ProjectManager, "PROJECTS_DIR", str(uploads_dir / "projects"))
    monkeypatch.setattr(
        "app.services.application.openclaw_orchestrator.Config.UPLOAD_FOLDER",
        str(uploads_dir),
    )

    def fake_build(project, text, task_manager, task_id):
        project.graph_id = f"consumer_{project.project_id}"
        project.status = ProjectStatus.GRAPH_COMPLETED
        ProjectManager.save_project(project)
        return {
            "graph_id": project.graph_id,
            "nodes": [],
            "edges": [],
            "node_count": 0,
            "edge_count": 0,
        }

    monkeypatch.setattr(
        "app.services.application.graph_app_service.GraphAppService.build_consumer_graph_sync",
        fake_build,
    )
    store = OpenClawSessionStore(upload_root=str(uploads_dir))
    orchestrator = OpenClawOrchestrator(store=store, search_provider=_provider)
    session = orchestrator.create_session("Evaluate Shuke kids toothpaste for moms")
    orchestrator.confirm_action(session.research_session_id, action_type="confirm_research_plan")
    session = orchestrator.execute_external_exploration(session.research_session_id)
    orchestrator.prepare_consumer_brief(session.research_session_id)
    orchestrator.confirm_action(session.research_session_id, action_type="confirm_brief")

    started = orchestrator.start_project(session.research_session_id)
    project = ProjectManager.get_project(started.project_id)

    assert started.status == "project_started"
    assert project is not None
    assert project.project_type == "consumer_test"
    assert project.consumer_brief["enable_lane_b"] is True
    assert project.graph_build_task_id == started.graph_build_task_id

    registry = SourceRegistry(project.project_id, upload_root=str(uploads_dir))
    assert registry.source_count(lane=ResearchSourceLane.LaneB) >= 1

    task = TaskManager().get_task(started.graph_build_task_id)
    assert task is not None
    assert task.task_type == "consumer_graph_build"


def test_orchestrator_start_project_is_idempotent_after_project_is_recorded(
    tmp_path, monkeypatch
):
    uploads_dir = tmp_path / "uploads"
    monkeypatch.setattr(graph_api.Config, "UPLOAD_FOLDER", str(uploads_dir))
    monkeypatch.setattr(ProjectManager, "PROJECTS_DIR", str(uploads_dir / "projects"))
    monkeypatch.setattr(
        "app.services.application.openclaw_orchestrator.Config.UPLOAD_FOLDER",
        str(uploads_dir),
    )
    build_calls = []

    def fake_build(project, text, task_manager, task_id):
        build_calls.append((project.project_id, task_id))
        project.graph_id = f"consumer_{project.project_id}"
        project.status = ProjectStatus.GRAPH_COMPLETED
        ProjectManager.save_project(project)
        return {"graph_id": project.graph_id}

    monkeypatch.setattr(
        "app.services.application.graph_app_service.GraphAppService.build_consumer_graph_sync",
        fake_build,
    )
    store = OpenClawSessionStore(upload_root=str(uploads_dir))
    orchestrator = OpenClawOrchestrator(store=store, search_provider=_provider)
    session = orchestrator.create_session("Evaluate Shuke kids toothpaste for moms")
    orchestrator.confirm_action(session.research_session_id, action_type="confirm_research_plan")
    orchestrator.execute_external_exploration(session.research_session_id)
    orchestrator.prepare_consumer_brief(session.research_session_id)
    orchestrator.confirm_action(session.research_session_id, action_type="confirm_brief")

    first = orchestrator.start_project(session.research_session_id)
    second = orchestrator.start_project(session.research_session_id)

    assert second.project_id == first.project_id
    assert second.graph_build_task_id == first.graph_build_task_id
    assert build_calls == [(first.project_id, first.graph_build_task_id)]


def test_orchestrator_start_project_persists_recovery_state_when_graph_build_fails(
    tmp_path, monkeypatch
):
    uploads_dir = tmp_path / "uploads"
    monkeypatch.setattr(graph_api.Config, "UPLOAD_FOLDER", str(uploads_dir))
    monkeypatch.setattr(ProjectManager, "PROJECTS_DIR", str(uploads_dir / "projects"))
    monkeypatch.setattr(
        "app.services.application.openclaw_orchestrator.Config.UPLOAD_FOLDER",
        str(uploads_dir),
    )

    def fake_build(project, text, task_manager, task_id):
        raise RuntimeError("graph service unavailable")

    monkeypatch.setattr(
        "app.services.application.graph_app_service.GraphAppService.build_consumer_graph_sync",
        fake_build,
    )
    store = OpenClawSessionStore(upload_root=str(uploads_dir))
    orchestrator = OpenClawOrchestrator(store=store, search_provider=_provider)
    session = orchestrator.create_session("Evaluate Shuke kids toothpaste for moms")
    orchestrator.confirm_action(session.research_session_id, action_type="confirm_research_plan")
    orchestrator.execute_external_exploration(session.research_session_id)
    orchestrator.prepare_consumer_brief(session.research_session_id)
    orchestrator.confirm_action(session.research_session_id, action_type="confirm_brief")

    with pytest.raises(RuntimeError, match="graph service unavailable"):
        orchestrator.start_project(session.research_session_id)

    persisted = orchestrator.get_session(session.research_session_id)
    assert persisted.project_id
    assert persisted.graph_build_task_id
    assert persisted.status == "project_start_failed"
    assert persisted.error
    failure_entry = persisted.action_log[-1]
    assert failure_entry.action_type == "start_project"
    assert failure_entry.result_status == "failed"
    assert failure_entry.result_summary == {
        "project_id": persisted.project_id,
        "task_id": persisted.graph_build_task_id,
    }


def test_orchestrator_start_project_deduplicates_and_skips_blank_lane_b_findings(
    tmp_path, monkeypatch
):
    uploads_dir = tmp_path / "uploads"
    monkeypatch.setattr(graph_api.Config, "UPLOAD_FOLDER", str(uploads_dir))
    monkeypatch.setattr(ProjectManager, "PROJECTS_DIR", str(uploads_dir / "projects"))
    monkeypatch.setattr(
        "app.services.application.openclaw_orchestrator.Config.UPLOAD_FOLDER",
        str(uploads_dir),
    )

    def fake_build(project, text, task_manager, task_id):
        project.graph_id = f"consumer_{project.project_id}"
        project.status = ProjectStatus.GRAPH_COMPLETED
        ProjectManager.save_project(project)
        return {"graph_id": project.graph_id}

    monkeypatch.setattr(
        "app.services.application.graph_app_service.GraphAppService.build_consumer_graph_sync",
        fake_build,
    )
    store = OpenClawSessionStore(upload_root=str(uploads_dir))
    orchestrator = OpenClawOrchestrator(store=store, search_provider=_provider)
    session = orchestrator.create_session("Evaluate Shuke kids toothpaste for moms")
    orchestrator.confirm_action(session.research_session_id, action_type="confirm_research_plan")
    session = orchestrator.execute_external_exploration(session.research_session_id)
    session.external_findings = [
        {
            "title": "Safety evidence",
            "url": "https://example.com/safety",
            "snippet": "Parents want clinical proof.",
            "query": "kids toothpaste safety",
            "evidence_type": "category_context",
            "source": "external_exploration",
        },
        {
            "title": "Safety evidence copy",
            "url": "https://example.com/safety",
            "snippet": "Repeated URL should not create another document.",
            "query": "kids toothpaste safety",
            "evidence_type": "category_context",
            "source": "external_exploration",
        },
        {
            "title": "  ",
            "url": "  ",
            "snippet": "  ",
            "query": "kids toothpaste safety",
            "evidence_type": "category_context",
            "source": "external_exploration",
        },
        {
            "title": "  ",
            "url": "https://example.com/url-only",
            "snippet": "  ",
            "query": "kids toothpaste safety",
            "evidence_type": "category_context",
            "source": "external_exploration",
        },
        {
            "title": "Habit proof",
            "url": "https://example.com/habit-a",
            "snippet": "Parents want brushing routines that stick.",
            "query": "kids toothpaste habits",
            "evidence_type": "category_context",
            "source": "external_exploration",
        },
        {
            "title": "Habit proof",
            "url": "https://example.com/habit-b",
            "snippet": "Parents want brushing routines that stick.",
            "query": "kids toothpaste habits",
            "evidence_type": "category_context",
            "source": "external_exploration",
        },
        {
            "title": "Ingredient trust",
            "url": "",
            "snippet": "Parents compare ingredient lists.",
            "query": "kids toothpaste ingredients",
            "evidence_type": "category_context",
            "source": "external_exploration",
        },
        {
            "title": "Ingredient trust",
            "url": "",
            "snippet": "Parents compare ingredient lists.",
            "query": "kids toothpaste ingredients",
            "evidence_type": "category_context",
            "source": "external_exploration",
        },
    ]
    store.save(session)
    orchestrator.prepare_consumer_brief(session.research_session_id)
    orchestrator.confirm_action(session.research_session_id, action_type="confirm_brief")

    started = orchestrator.start_project(session.research_session_id)

    registry = SourceRegistry(started.project_id, upload_root=str(uploads_dir))
    documents = DocumentIngestService(
        started.project_id,
        upload_root=str(uploads_dir),
    ).list_documents()
    assert registry.source_count(lane=ResearchSourceLane.LaneB) == 3
    assert len(documents) == 3


def test_openclaw_workspace_snapshot_uses_business_state_language(tmp_path):
    store = OpenClawSessionStore(upload_root=str(tmp_path / "uploads"))
    orchestrator = OpenClawOrchestrator(store=store)
    session = orchestrator.create_session(
        "Evaluate Shuke kids magic color changing toothpaste for parents"
    )

    snapshot = orchestrator.get_workspace_snapshot(session.research_session_id)

    assert snapshot["research_session_id"] == session.research_session_id
    assert snapshot["business_state"]["label"] == "Understanding research goal"
    assert snapshot["business_state"]["technical_status"] == "planning"
    assert snapshot["next_recommended_action"]["kind"] == "confirm_research_plan"
    assert snapshot["can_leave_and_return"] is True
    assert snapshot["timeline"][0]["key"] == "understand_goal"
    assert snapshot["timeline"][0]["status"] == "current"


def test_openclaw_workspace_snapshot_treats_started_project_as_ready(tmp_path):
    store = OpenClawSessionStore(upload_root=str(tmp_path / "uploads"))
    orchestrator = OpenClawOrchestrator(store=store)
    session = orchestrator.create_session(
        "Evaluate Shuke kids magic color changing toothpaste for parents"
    )
    session.status = "project_started"
    session.project_id = "proj_ready"
    session.graph_build_task_id = "task_ready"
    session.graph_id = "consumer_proj_ready"
    store.save(session)

    snapshot = orchestrator.get_workspace_snapshot(session.research_session_id)
    timeline_by_key = {item["key"]: item for item in snapshot["timeline"]}

    assert snapshot["business_state"]["label"] == "Ready for simulation"
    assert snapshot["business_state"]["progress"] == 100
    assert snapshot["next_recommended_action"]["kind"] == "open_project"
    assert timeline_by_key["build_context"]["status"] == "completed"
    assert timeline_by_key["ready_for_simulation"]["status"] == "current"


def test_openclaw_session_explanation_answers_business_questions(tmp_path):
    store = OpenClawSessionStore(upload_root=str(tmp_path / "uploads"))
    orchestrator = OpenClawOrchestrator(store=store)
    session = orchestrator.create_session("Test a children toothpaste concept")

    explanation = orchestrator.explain_session_status(session.research_session_id)

    assert explanation["current_step"]
    assert explanation["why_this_matters"]
    assert isinstance(explanation["completed_steps"], list)
    assert explanation["next_recommended_action"]["kind"] == "confirm_research_plan"
    assert explanation["technical_details"]["research_session_id"] == session.research_session_id


def test_explain_project_status_rejects_unrelated_project_and_task(
    tmp_path, monkeypatch
):
    uploads_dir = tmp_path / "uploads"
    monkeypatch.setattr(ProjectManager, "PROJECTS_DIR", str(uploads_dir / "projects"))
    orchestrator = OpenClawOrchestrator(
        store=OpenClawSessionStore(upload_root=str(uploads_dir))
    )
    project_a = ProjectManager.create_project("Project A", tenant_id="tenant_a")
    project_a.status = ProjectStatus.GRAPH_BUILDING
    ProjectManager.save_project(project_a)
    project_b = ProjectManager.create_project("Project B", tenant_id="tenant_a")
    project_b.status = ProjectStatus.GRAPH_BUILDING
    project_b.graph_build_task_id = "task-project-b"
    ProjectManager.save_project(project_b)

    with pytest.raises(KeyError, match="task-project-b"):
        orchestrator.explain_project_status(
            project_id=project_a.project_id,
            task_id="task-project-b",
        )


def test_explain_project_status_accepts_direct_project_task_when_scan_is_empty(
    tmp_path, monkeypatch
):
    uploads_dir = tmp_path / "uploads"
    monkeypatch.setattr(ProjectManager, "PROJECTS_DIR", str(uploads_dir / "projects"))
    orchestrator = OpenClawOrchestrator(
        store=OpenClawSessionStore(upload_root=str(uploads_dir))
    )
    project = ProjectManager.create_project("Direct task project", tenant_id="tenant_a")
    project.status = ProjectStatus.GRAPH_BUILDING
    project.graph_build_task_id = "task-direct-project"
    ProjectManager.save_project(project)
    monkeypatch.setattr(ProjectManager, "list_projects", lambda limit=1000: [])

    explanation = orchestrator.explain_project_status(
        project_id=project.project_id,
        task_id="task-direct-project",
    )

    assert explanation["project_id"] == project.project_id
    assert explanation["task_id"] == "task-direct-project"
