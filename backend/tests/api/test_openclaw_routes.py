from flask import Flask, g
import pytest
import time

from app.api import openclaw_bp
from app.api import openclaw as openclaw_api
from app.auth.models import User
from app.config import Config
from app.models.project import ProjectManager, ProjectStatus
from app.models.task import TaskManager
from app.services.application.openclaw_session_store import OpenClawSessionStore


def _user(user_id, tenant_id, role="researcher"):
    return User(
        user_id=user_id,
        username=user_id,
        email=f"{user_id}@example.com",
        role=role,
        tenant_id=tenant_id,
        workspace_id=f"workspace-{tenant_id}",
    )


def _create_app(user=None):
    app = Flask(__name__)
    app.config["TESTING"] = True
    app.config["AUTH_BYPASS_IN_TESTING"] = True
    app.config["TEST_USER"] = user

    @app.before_request
    def _inject_test_user():
        test_user = app.config.get("TEST_USER")
        if test_user is not None:
            g.current_user = test_user
            g.current_tenant = test_user.tenant_id

    app.register_blueprint(openclaw_bp, url_prefix="/api/openclaw")
    return app


def _empty_provider(query, top_k):
    return []


@pytest.fixture
def auth_headers():
    return {}


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(
        openclaw_api,
        "_session_store",
        OpenClawSessionStore(upload_root=str(tmp_path / "uploads")),
    )
    monkeypatch.setattr(openclaw_api, "_search_provider", _empty_provider)
    app = _create_app(user=_user("owner", "tenant_a"))
    return app.test_client()


def test_create_openclaw_session_returns_plan(tmp_path, monkeypatch):
    monkeypatch.setattr(
        openclaw_api,
        "_session_store",
        OpenClawSessionStore(upload_root=str(tmp_path / "uploads")),
    )
    monkeypatch.setattr(openclaw_api, "_search_provider", _empty_provider)
    app = _create_app()

    response = app.test_client().post(
        "/api/openclaw/sessions",
        json={"user_goal": "Evaluate kids toothpaste"},
    )

    assert response.status_code == 200
    payload = response.get_json()["data"]
    assert payload["research_session_id"].startswith("rsess_")
    assert payload["exploration_plan"]


def test_create_openclaw_session_persists_request_user_owner(tmp_path, monkeypatch):
    monkeypatch.setattr(
        openclaw_api,
        "_session_store",
        OpenClawSessionStore(upload_root=str(tmp_path / "uploads")),
    )
    monkeypatch.setattr(openclaw_api, "_search_provider", _empty_provider)
    app = _create_app(user=_user("user_a", "tenant_a"))

    response = app.test_client().post(
        "/api/openclaw/sessions",
        json={"user_goal": "Evaluate kids toothpaste"},
    )

    assert response.status_code == 200
    payload = response.get_json()["data"]
    assert payload["user_id"] == "user_a"
    assert payload["tenant_id"] == "tenant_a"


def test_cross_tenant_user_cannot_read_or_mutate_session(tmp_path, monkeypatch):
    store = OpenClawSessionStore(upload_root=str(tmp_path / "uploads"))
    monkeypatch.setattr(openclaw_api, "_session_store", store)
    monkeypatch.setattr(openclaw_api, "_search_provider", _empty_provider)
    app = _create_app(user=_user("owner", "tenant_a"))
    client = app.test_client()
    created = client.post(
        "/api/openclaw/sessions", json={"user_goal": "Evaluate toothpaste"}
    ).get_json()["data"]
    sid = created["research_session_id"]

    app.config["TEST_USER"] = _user("intruder", "tenant_b")

    get_response = client.get(f"/api/openclaw/sessions/{sid}")
    confirm_response = client.post(
        f"/api/openclaw/sessions/{sid}/confirm",
        json={"action_type": "confirm_research_plan", "payload": {"approved": True}},
    )
    explore_response = client.post(f"/api/openclaw/sessions/{sid}/explore")
    persisted = store.get(sid)

    assert get_response.status_code == 403
    assert confirm_response.status_code == 403
    assert explore_response.status_code == 403
    assert "tenant mismatch" in get_response.get_json()["error"]
    assert "tenant mismatch" in confirm_response.get_json()["error"]
    assert "tenant mismatch" in explore_response.get_json()["error"]
    assert persisted.status == "planning"
    assert persisted.confirmed_actions == []


def test_explore_route_requires_confirmation(tmp_path, monkeypatch):
    monkeypatch.setattr(
        openclaw_api,
        "_session_store",
        OpenClawSessionStore(upload_root=str(tmp_path / "uploads")),
    )
    monkeypatch.setattr(openclaw_api, "_search_provider", _empty_provider)
    app = _create_app()
    client = app.test_client()
    created = client.post(
        "/api/openclaw/sessions", json={"user_goal": "Evaluate toothpaste"}
    ).get_json()["data"]

    response = client.post(
        f"/api/openclaw/sessions/{created['research_session_id']}/explore"
    )

    assert response.status_code == 403
    assert "confirm_research_plan" in response.get_json()["error"]


def test_confirm_explore_then_prepare_brief_route(tmp_path, monkeypatch):
    monkeypatch.setattr(
        openclaw_api,
        "_session_store",
        OpenClawSessionStore(upload_root=str(tmp_path / "uploads")),
    )
    monkeypatch.setattr(openclaw_api, "_search_provider", _empty_provider)
    app = _create_app()
    client = app.test_client()
    created = client.post(
        "/api/openclaw/sessions", json={"user_goal": "Evaluate toothpaste"}
    ).get_json()["data"]
    sid = created["research_session_id"]

    confirm = client.post(
        f"/api/openclaw/sessions/{sid}/confirm",
        json={"action_type": "confirm_research_plan", "payload": {"approved": True}},
    )
    explore = client.post(f"/api/openclaw/sessions/{sid}/explore")
    brief = client.post(f"/api/openclaw/sessions/{sid}/brief")

    assert confirm.status_code == 200
    assert explore.status_code == 200
    assert explore.get_json()["data"]["evidence_quality"]["gate"] == "blocked"
    assert brief.status_code == 200
    assert brief.get_json()["data"]["consumer_brief"]["task_type"] == "concept_test"
    assert (
        brief.get_json()["data"]["consumer_brief"]["source_quality_summary"]["gate"]
        == "blocked"
    )


def test_explore_route_uploaded_only_strategy_skips_external_search(tmp_path, monkeypatch):
    def fail_if_called(query, top_k):
        raise AssertionError("uploaded_only should not call external search")

    monkeypatch.setattr(
        openclaw_api,
        "_session_store",
        OpenClawSessionStore(upload_root=str(tmp_path / "uploads")),
    )
    monkeypatch.setattr(openclaw_api, "_search_provider", fail_if_called)
    app = _create_app()
    client = app.test_client()
    created = client.post(
        "/api/openclaw/sessions", json={"user_goal": "Evaluate toothpaste"}
    ).get_json()["data"]
    sid = created["research_session_id"]
    client.post(
        f"/api/openclaw/sessions/{sid}/confirm",
        json={"action_type": "confirm_research_plan", "payload": {"approved": True}},
    )

    response = client.post(
        f"/api/openclaw/sessions/{sid}/explore",
        json={"strategy": "uploaded_only"},
    )

    assert response.status_code == 200
    payload = response.get_json()["data"]
    assert payload["external_findings"] == []
    assert payload["evidence_quality"]["exploration_strategy"] == "uploaded_only"
    assert payload["evidence_quality"]["gate"] == "review"
    assert "上传" in payload["evidence_quality"]["user_visible_warnings"][0]


def test_explore_route_broaden_search_strategy_requests_more_results(tmp_path, monkeypatch):
    calls = []

    def provider(query, top_k):
        calls.append((query, top_k))
        return []

    monkeypatch.setattr(
        openclaw_api,
        "_session_store",
        OpenClawSessionStore(upload_root=str(tmp_path / "uploads")),
    )
    monkeypatch.setattr(openclaw_api, "_search_provider", provider)
    app = _create_app()
    client = app.test_client()
    created = client.post(
        "/api/openclaw/sessions", json={"user_goal": "舒客宝贝魔法变色牙膏"}
    ).get_json()["data"]
    sid = created["research_session_id"]
    client.post(
        f"/api/openclaw/sessions/{sid}/confirm",
        json={"action_type": "confirm_research_plan", "payload": {"approved": True}},
    )

    response = client.post(
        f"/api/openclaw/sessions/{sid}/explore",
        json={"strategy": "broaden_search"},
    )

    assert response.status_code == 200
    assert calls
    assert max(top_k for _, top_k in calls) == 5
    payload = response.get_json()["data"]
    assert payload["evidence_quality"]["exploration_strategy"] == "broaden_search"


def test_start_project_route_returns_project_starting_while_graph_build_continues(tmp_path, monkeypatch):
    uploads_dir = tmp_path / "uploads"
    monkeypatch.setattr(
        openclaw_api,
        "_session_store",
        OpenClawSessionStore(upload_root=str(uploads_dir)),
    )
    monkeypatch.setattr(openclaw_api, "_search_provider", _empty_provider)
    monkeypatch.setattr(Config, "UPLOAD_FOLDER", str(uploads_dir))
    monkeypatch.setattr(ProjectManager, "PROJECTS_DIR", str(uploads_dir / "projects"))

    def fake_build(project, text, task_manager, task_id):
        time.sleep(0.25)
        project.graph_id = f"consumer_{project.project_id}"
        project.status = ProjectStatus.GRAPH_COMPLETED
        ProjectManager.save_project(project)
        return {"graph_id": project.graph_id, "nodes": [], "edges": []}

    monkeypatch.setattr(
        "app.services.application.graph_app_service.GraphAppService.build_consumer_graph_sync",
        fake_build,
    )
    app = _create_app(user=_user("owner", "tenant_a"))
    client = app.test_client()
    created = client.post(
        "/api/openclaw/sessions", json={"user_goal": "Evaluate toothpaste"}
    ).get_json()["data"]
    sid = created["research_session_id"]
    client.post(
        f"/api/openclaw/sessions/{sid}/confirm",
        json={"action_type": "confirm_research_plan", "payload": {"approved": True}},
    )
    client.post(f"/api/openclaw/sessions/{sid}/explore")
    client.post(f"/api/openclaw/sessions/{sid}/brief")
    client.post(
        f"/api/openclaw/sessions/{sid}/confirm",
        json={"action_type": "confirm_brief", "payload": {"approved": True}},
    )

    blocked = client.post(f"/api/openclaw/sessions/{sid}/project")
    assert blocked.status_code == 403
    assert "low evidence" in blocked.get_json()["error"]

    client.post(
        f"/api/openclaw/sessions/{sid}/confirm",
        json={
            "action_type": "confirm_low_evidence_continue",
            "payload": {"approved": True},
        },
    )
    response = client.post(f"/api/openclaw/sessions/{sid}/project")

    assert response.status_code == 200
    payload = response.get_json()["data"]
    assert payload["status"] == "project_starting"
    assert payload["project_id"]
    assert payload["graph_build_task_id"]
    assert not payload.get("graph_id")

    deadline = time.time() + 2
    persisted = None
    while time.time() < deadline:
        persisted = openclaw_api._session_store.get(sid)
        if persisted and persisted.status == "project_started":
            break
        time.sleep(0.05)

    assert persisted is not None
    assert persisted.status == "project_started"
    assert persisted.graph_id == f"consumer_{payload['project_id']}"


def test_status_explain_returns_404_for_missing_project(tmp_path, monkeypatch):
    monkeypatch.setattr(
        openclaw_api,
        "_session_store",
        OpenClawSessionStore(upload_root=str(tmp_path / "uploads")),
    )
    app = _create_app(user=_user("owner", "tenant_a"))

    response = app.test_client().get(
        "/api/openclaw/status/explain?project_id=missing-project"
    )

    assert response.status_code == 404
    assert "missing-project" in response.get_json()["error"]


def test_status_explain_accepts_task_id_and_returns_structured_progress(
    tmp_path, monkeypatch
):
    uploads_dir = tmp_path / "uploads"
    monkeypatch.setattr(
        openclaw_api,
        "_session_store",
        OpenClawSessionStore(upload_root=str(uploads_dir)),
    )
    monkeypatch.setattr(Config, "UPLOAD_FOLDER", str(uploads_dir))
    monkeypatch.setattr(ProjectManager, "PROJECTS_DIR", str(uploads_dir / "projects"))
    app = _create_app(user=_user("owner", "tenant_a"))

    project = ProjectManager.create_project("Explain me", tenant_id="tenant_a")
    project.status = ProjectStatus.GRAPH_BUILDING
    project.graph_build_task_id = "task-explain-123"
    ProjectManager.save_project(project)

    response = app.test_client().get(
        "/api/openclaw/status/explain?task_id=task-explain-123"
    )

    assert response.status_code == 200
    payload = response.get_json()["data"]
    assert payload["project_id"] == project.project_id
    assert payload["task_id"] == "task-explain-123"
    assert payload["project_status"] == "graph_building"
    assert payload["task_status"] == "processing"
    assert payload["progress"] == 15
    assert payload["recoverable"] is True
    assert "task-explain-123" in payload["explanation"]


def test_status_explain_prefers_completed_task_over_stale_project(
    tmp_path, monkeypatch
):
    uploads_dir = tmp_path / "uploads"
    monkeypatch.setattr(
        openclaw_api,
        "_session_store",
        OpenClawSessionStore(upload_root=str(uploads_dir)),
    )
    monkeypatch.setattr(Config, "UPLOAD_FOLDER", str(uploads_dir))
    monkeypatch.setattr(ProjectManager, "PROJECTS_DIR", str(uploads_dir / "projects"))
    app = _create_app(user=_user("owner", "tenant_a"))

    project = ProjectManager.create_project("Explain completed task", tenant_id="tenant_a")
    task_id = TaskManager().create_task("consumer_graph_build")
    TaskManager().complete_task(
        task_id,
        {"project_id": project.project_id, "graph_id": f"consumer_{project.project_id}"},
    )
    project.status = ProjectStatus.GRAPH_BUILDING
    project.graph_build_task_id = task_id
    ProjectManager.save_project(project)

    response = app.test_client().get(f"/api/openclaw/status/explain?task_id={task_id}")

    assert response.status_code == 200
    payload = response.get_json()["data"]
    assert payload["project_status"] == "graph_completed"
    assert payload["task_status"] == "completed"
    assert payload["progress"] == 100
    assert payload["recoverable"] is False
    assert payload["graph_id"] == f"consumer_{project.project_id}"


def test_status_explain_rejects_cross_tenant_project_id(tmp_path, monkeypatch):
    uploads_dir = tmp_path / "uploads"
    monkeypatch.setattr(Config, "UPLOAD_FOLDER", str(uploads_dir))
    monkeypatch.setattr(ProjectManager, "PROJECTS_DIR", str(uploads_dir / "projects"))
    app = _create_app(user=_user("owner", "tenant_a"))

    project = ProjectManager.create_project("Other tenant project", tenant_id="tenant_b")
    project.status = ProjectStatus.GRAPH_BUILDING
    ProjectManager.save_project(project)

    response = app.test_client().get(
        f"/api/openclaw/status/explain?project_id={project.project_id}"
    )

    assert response.status_code == 403
    assert "tenant mismatch" in response.get_json()["error"]


def test_status_explain_rejects_cross_tenant_task_id(tmp_path, monkeypatch):
    uploads_dir = tmp_path / "uploads"
    monkeypatch.setattr(Config, "UPLOAD_FOLDER", str(uploads_dir))
    monkeypatch.setattr(ProjectManager, "PROJECTS_DIR", str(uploads_dir / "projects"))
    app = _create_app(user=_user("owner", "tenant_a"))

    project = ProjectManager.create_project("Other tenant task", tenant_id="tenant_b")
    project.status = ProjectStatus.GRAPH_BUILDING
    project.graph_build_task_id = "task-other-tenant-123"
    ProjectManager.save_project(project)

    response = app.test_client().get(
        "/api/openclaw/status/explain?task_id=task-other-tenant-123"
    )

    assert response.status_code == 403
    assert "tenant mismatch" in response.get_json()["error"]


def test_status_explain_rejects_mixed_authorized_project_and_cross_tenant_task(
    tmp_path, monkeypatch
):
    uploads_dir = tmp_path / "uploads"
    monkeypatch.setattr(Config, "UPLOAD_FOLDER", str(uploads_dir))
    monkeypatch.setattr(ProjectManager, "PROJECTS_DIR", str(uploads_dir / "projects"))
    app = _create_app(user=_user("owner", "tenant_a"))

    tenant_a_project = ProjectManager.create_project(
        "Tenant A project without task",
        tenant_id="tenant_a",
    )
    tenant_a_project.status = ProjectStatus.GRAPH_BUILDING
    ProjectManager.save_project(tenant_a_project)

    tenant_b_project = ProjectManager.create_project(
        "Tenant B task project",
        tenant_id="tenant_b",
    )
    tenant_b_project.status = ProjectStatus.GRAPH_BUILDING
    tenant_b_project.graph_build_task_id = "task-tenant-b"
    ProjectManager.save_project(tenant_b_project)

    response = app.test_client().get(
        "/api/openclaw/status/explain"
        f"?project_id={tenant_a_project.project_id}&task_id=task-tenant-b"
    )

    assert response.status_code == 403
    assert "tenant mismatch" in response.get_json()["error"]


def test_status_explain_rejects_cross_tenant_project_with_authorized_task(
    tmp_path, monkeypatch
):
    uploads_dir = tmp_path / "uploads"
    monkeypatch.setattr(Config, "UPLOAD_FOLDER", str(uploads_dir))
    monkeypatch.setattr(ProjectManager, "PROJECTS_DIR", str(uploads_dir / "projects"))
    app = _create_app(user=_user("owner", "tenant_a"))

    tenant_b_project = ProjectManager.create_project(
        "Tenant B project",
        tenant_id="tenant_b",
    )
    tenant_b_project.status = ProjectStatus.GRAPH_BUILDING
    ProjectManager.save_project(tenant_b_project)

    tenant_a_project = ProjectManager.create_project(
        "Tenant A task project",
        tenant_id="tenant_a",
    )
    tenant_a_project.status = ProjectStatus.GRAPH_BUILDING
    tenant_a_project.graph_build_task_id = "task-tenant-a"
    ProjectManager.save_project(tenant_a_project)

    response = app.test_client().get(
        "/api/openclaw/status/explain"
        f"?project_id={tenant_b_project.project_id}&task_id=task-tenant-a"
    )

    assert response.status_code == 403
    assert "tenant mismatch" in response.get_json()["error"]


def test_status_explain_rejects_cross_tenant_project_before_missing_task(
    tmp_path, monkeypatch
):
    uploads_dir = tmp_path / "uploads"
    monkeypatch.setattr(Config, "UPLOAD_FOLDER", str(uploads_dir))
    monkeypatch.setattr(ProjectManager, "PROJECTS_DIR", str(uploads_dir / "projects"))
    app = _create_app(user=_user("owner", "tenant_a"))

    tenant_b_project = ProjectManager.create_project(
        "Tenant B project without task",
        tenant_id="tenant_b",
    )
    tenant_b_project.status = ProjectStatus.GRAPH_BUILDING
    ProjectManager.save_project(tenant_b_project)

    response = app.test_client().get(
        "/api/openclaw/status/explain"
        f"?project_id={tenant_b_project.project_id}&task_id=missing-task"
    )

    assert response.status_code == 403
    assert "tenant mismatch" in response.get_json()["error"]


def test_status_explain_allows_matching_project_and_task_params(tmp_path, monkeypatch):
    uploads_dir = tmp_path / "uploads"
    monkeypatch.setattr(Config, "UPLOAD_FOLDER", str(uploads_dir))
    monkeypatch.setattr(ProjectManager, "PROJECTS_DIR", str(uploads_dir / "projects"))
    app = _create_app(user=_user("owner", "tenant_a"))

    project = ProjectManager.create_project("Tenant A task project", tenant_id="tenant_a")
    project.status = ProjectStatus.GRAPH_BUILDING
    project.graph_build_task_id = "task-tenant-a"
    ProjectManager.save_project(project)

    response = app.test_client().get(
        "/api/openclaw/status/explain"
        f"?project_id={project.project_id}&task_id=task-tenant-a"
    )

    assert response.status_code == 200
    payload = response.get_json()["data"]
    assert payload["project_id"] == project.project_id
    assert payload["task_id"] == "task-tenant-a"


def test_status_explain_allows_direct_project_task_when_scan_is_empty(
    tmp_path, monkeypatch
):
    uploads_dir = tmp_path / "uploads"
    monkeypatch.setattr(Config, "UPLOAD_FOLDER", str(uploads_dir))
    monkeypatch.setattr(ProjectManager, "PROJECTS_DIR", str(uploads_dir / "projects"))
    app = _create_app(user=_user("owner", "tenant_a"))

    project = ProjectManager.create_project("Direct route task", tenant_id="tenant_a")
    project.status = ProjectStatus.GRAPH_BUILDING
    project.graph_build_task_id = "task-direct-route"
    ProjectManager.save_project(project)
    monkeypatch.setattr(ProjectManager, "list_projects", lambda limit=1000: [])

    response = app.test_client().get(
        "/api/openclaw/status/explain"
        f"?project_id={project.project_id}&task_id=task-direct-route"
    )

    assert response.status_code == 200
    payload = response.get_json()["data"]
    assert payload["project_id"] == project.project_id
    assert payload["task_id"] == "task-direct-route"


def test_status_explain_rejects_same_tenant_unrelated_project_and_task(
    tmp_path, monkeypatch
):
    uploads_dir = tmp_path / "uploads"
    monkeypatch.setattr(Config, "UPLOAD_FOLDER", str(uploads_dir))
    monkeypatch.setattr(ProjectManager, "PROJECTS_DIR", str(uploads_dir / "projects"))
    app = _create_app(user=_user("owner", "tenant_a"))

    project_a = ProjectManager.create_project("Tenant A project A", tenant_id="tenant_a")
    project_a.status = ProjectStatus.GRAPH_BUILDING
    ProjectManager.save_project(project_a)

    project_b = ProjectManager.create_project("Tenant A project B", tenant_id="tenant_a")
    project_b.status = ProjectStatus.GRAPH_BUILDING
    project_b.graph_build_task_id = "task-project-b"
    ProjectManager.save_project(project_b)

    response = app.test_client().get(
        "/api/openclaw/status/explain"
        f"?project_id={project_a.project_id}&task_id=task-project-b"
    )

    assert response.status_code == 404
    payload = response.get_json()
    assert "data" not in payload
    assert "task-project-b" in payload["error"]
    assert project_b.project_id not in payload["error"]


def test_cross_tenant_user_cannot_read_session_workspace(tmp_path, monkeypatch):
    store = OpenClawSessionStore(upload_root=str(tmp_path / "uploads"))
    monkeypatch.setattr(openclaw_api, "_session_store", store)
    monkeypatch.setattr(openclaw_api, "_search_provider", _empty_provider)
    app = _create_app(user=_user("owner", "tenant_a"))
    client = app.test_client()
    created = client.post(
        "/api/openclaw/sessions", json={"user_goal": "Evaluate toothpaste"}
    ).get_json()["data"]
    sid = created["research_session_id"]

    app.config["TEST_USER"] = _user("intruder", "tenant_b")
    response = client.get(f"/api/openclaw/sessions/{sid}/workspace")

    assert response.status_code == 403
    assert "tenant mismatch" in response.get_json()["error"]


def test_cross_tenant_user_cannot_explain_session(tmp_path, monkeypatch):
    store = OpenClawSessionStore(upload_root=str(tmp_path / "uploads"))
    monkeypatch.setattr(openclaw_api, "_session_store", store)
    monkeypatch.setattr(openclaw_api, "_search_provider", _empty_provider)
    app = _create_app(user=_user("owner", "tenant_a"))
    client = app.test_client()
    created = client.post(
        "/api/openclaw/sessions", json={"user_goal": "Evaluate toothpaste"}
    ).get_json()["data"]
    sid = created["research_session_id"]

    app.config["TEST_USER"] = _user("intruder", "tenant_b")
    response = client.get(f"/api/openclaw/sessions/{sid}/explain")

    assert response.status_code == 403
    assert "tenant mismatch" in response.get_json()["error"]


def test_sessions_route_hides_other_tenant_sessions_after_user_switch(
    tmp_path, monkeypatch
):
    store = OpenClawSessionStore(upload_root=str(tmp_path / "uploads"))
    monkeypatch.setattr(openclaw_api, "_session_store", store)
    monkeypatch.setattr(openclaw_api, "_search_provider", _empty_provider)
    app = _create_app(user=_user("owner", "tenant_a"))
    client = app.test_client()
    client.post(
        "/api/openclaw/sessions",
        json={"user_goal": "Tenant A OpenClaw task"},
    )

    app.config["TEST_USER"] = _user("intruder", "tenant_b")
    client.post(
        "/api/openclaw/sessions",
        json={"user_goal": "Tenant B OpenClaw task"},
    )
    response = client.get("/api/openclaw/sessions?limit=10")

    assert response.status_code == 200
    sessions = response.get_json()["data"]["sessions"]
    assert [session["user_goal"] for session in sessions] == [
        "Tenant B OpenClaw task"
    ]


def test_prepare_brief_before_exploration_returns_403(tmp_path, monkeypatch):
    monkeypatch.setattr(
        openclaw_api,
        "_session_store",
        OpenClawSessionStore(upload_root=str(tmp_path / "uploads")),
    )
    monkeypatch.setattr(openclaw_api, "_search_provider", _empty_provider)
    app = _create_app(user=_user("owner", "tenant_a"))
    client = app.test_client()
    created = client.post(
        "/api/openclaw/sessions", json={"user_goal": "Evaluate toothpaste"}
    ).get_json()["data"]

    response = client.post(
        f"/api/openclaw/sessions/{created['research_session_id']}/brief"
    )

    assert response.status_code == 403
    assert "status explored" in response.get_json()["error"]


def test_invalid_confirm_action_returns_400(tmp_path, monkeypatch):
    monkeypatch.setattr(
        openclaw_api,
        "_session_store",
        OpenClawSessionStore(upload_root=str(tmp_path / "uploads")),
    )
    monkeypatch.setattr(openclaw_api, "_search_provider", _empty_provider)
    app = _create_app(user=_user("owner", "tenant_a"))
    client = app.test_client()
    created = client.post(
        "/api/openclaw/sessions", json={"user_goal": "Evaluate toothpaste"}
    ).get_json()["data"]

    response = client.post(
        f"/api/openclaw/sessions/{created['research_session_id']}/confirm",
        json={"action_type": "confirm_everything"},
    )

    assert response.status_code == 400
    assert "Unknown confirmation" in response.get_json()["error"]


def test_openclaw_workspace_route_returns_snapshot(client, auth_headers):
    created = client.post(
        "/api/openclaw/sessions",
        json={"user_goal": "Evaluate Shuke kids magic color changing toothpaste"},
        headers=auth_headers,
    )
    assert created.status_code == 200
    sid = created.get_json()["data"]["research_session_id"]

    response = client.get(
        f"/api/openclaw/sessions/{sid}/workspace",
        headers=auth_headers,
    )

    assert response.status_code == 200
    payload = response.get_json()["data"]
    assert payload["research_session_id"] == sid
    assert payload["business_state"]["label"] == "Understanding research goal"
    assert payload["business_state"]["technical_status"] == "planning"
    assert payload["next_recommended_action"]["kind"] == "confirm_research_plan"
    assert payload["can_leave_and_return"] is True
    assert payload["timeline"][0]["key"] == "understand_goal"
    assert payload["timeline"][0]["status"] == "current"


def test_openclaw_sessions_route_lists_recent_authorized_sessions(client, auth_headers):
    client.post(
        "/api/openclaw/sessions",
        json={"user_goal": "First OpenClaw task"},
        headers=auth_headers,
    )
    client.post(
        "/api/openclaw/sessions",
        json={"user_goal": "Second OpenClaw task"},
        headers=auth_headers,
    )

    response = client.get("/api/openclaw/sessions?limit=1", headers=auth_headers)

    assert response.status_code == 200
    sessions = response.get_json()["data"]["sessions"]
    assert len(sessions) == 1
    assert sessions[0]["user_goal"] == "Second OpenClaw task"


def test_openclaw_session_explain_route_returns_structured_answer(client, auth_headers):
    created = client.post(
        "/api/openclaw/sessions",
        json={"user_goal": "Explain this OpenClaw task"},
        headers=auth_headers,
    )
    sid = created.get_json()["data"]["research_session_id"]

    response = client.get(
        f"/api/openclaw/sessions/{sid}/explain",
        headers=auth_headers,
    )

    assert response.status_code == 200
    payload = response.get_json()["data"]
    assert payload["current_step"]
    assert payload["why_this_matters"]
    assert isinstance(payload["completed_steps"], list)
    assert payload["next_recommended_action"]["kind"] == "confirm_research_plan"
    assert payload["technical_details"]["research_session_id"] == sid
