import json
from datetime import datetime

import pytest

from app import create_app
from app.auth.middleware import create_jwt_token, get_auth_repository, register_api_key, register_user
from app.auth.models import APIKey, User, generate_api_key, hash_password
from app.config import Config
from app.models.project import ProjectManager
from app.repositories.filesystem import FilesystemSimulationRepository
from app.services.report_agent import Report, ReportManager, ReportStatus
from app.services.simulation_manager import SimulationManager


class _ApiTestConfig(Config):
    TESTING = True
    AUTH_BYPASS_IN_TESTING = False
    DEBUG = True
    SECRET_KEY = "tenant-api-test-secret-key-1234567890"
    JWT_SECRET_KEY = "tenant-api-test-jwt-secret-key-123456789"
    LLM_API_KEY = "test-llm-key"
    ZEP_API_KEY = "test-zep-key"
    RATE_LIMIT_ENABLED = False
    RATE_LIMIT_BACKEND = "memory"
    CORS_ALLOWED_ORIGINS = "http://localhost:3000"
    LOG_FORMAT = "plain"
    _db_url_cache = ""
    _redis_url_cache = ""
    _queue_backend_cache = "thread"
    _lock_backend_cache = "file"


@pytest.fixture()
def api_app(tmp_path, monkeypatch):
    upload_root = tmp_path / "uploads"
    projects_dir = upload_root / "projects"
    simulations_dir = upload_root / "simulations"
    reports_dir = upload_root / "reports"
    audit_path = tmp_path / "audit" / "audit.jsonl"

    for path in (projects_dir, simulations_dir, reports_dir):
        path.mkdir(parents=True, exist_ok=True)

    _ApiTestConfig.UPLOAD_FOLDER = str(upload_root)
    _ApiTestConfig.OASIS_SIMULATION_DATA_DIR = str(simulations_dir)
    _ApiTestConfig.AUDIT_LOG_PATH = str(audit_path)

    monkeypatch.setattr(Config, "UPLOAD_FOLDER", str(upload_root))
    monkeypatch.setattr(Config, "OASIS_SIMULATION_DATA_DIR", str(simulations_dir))
    monkeypatch.setattr(ProjectManager, "PROJECTS_DIR", str(projects_dir))
    monkeypatch.setattr(SimulationManager, "SIMULATION_DATA_DIR", str(simulations_dir))
    monkeypatch.setattr(ReportManager, "REPORTS_DIR", str(reports_dir))

    app = create_app(_ApiTestConfig)
    app.config["AUDIT_LOG_PATH"] = str(audit_path)
    app.config["AUTH_BYPASS_IN_TESTING"] = False
    app.config["RATE_LIMIT_ENABLED"] = False
    app.extensions.pop("audit_logger", None)
    app.extensions["audit_path"] = audit_path

    yield app

    get_auth_repository().clear_all()


@pytest.fixture()
def client(api_app):
    return api_app.test_client()


@pytest.fixture()
def tenant_b_resources(api_app):
    project = ProjectManager.create_project("tenant-b-project", tenant_id="tenant_b")
    project.graph_id = "graph_tenant_b"
    ProjectManager.save_project(project)

    simulation = FilesystemSimulationRepository().create_simulation(
        project_id=project.project_id,
        graph_id=project.graph_id,
        project_type="consumer_test",
        tenant_id="tenant_b",
    )

    now = datetime.now().isoformat()
    report = Report(
        report_id="report_tenant_b",
        simulation_id=simulation.simulation_id,
        graph_id=project.graph_id,
        simulation_requirement="tenant isolation report",
        status=ReportStatus.COMPLETED,
        markdown_content="# Tenant B Report\n",
        created_at=now,
        completed_at=now,
    )
    ReportManager.save_report(report)

    return {
        "project": project,
        "simulation": simulation,
        "report": report,
    }


def _register_user(app, *, user_id: str, role: str, tenant_id: str) -> str:
    user = User(
        user_id=user_id,
        username=user_id,
        email=f"{user_id}@example.com",
        role=role,
        tenant_id=tenant_id,
        workspace_id=f"ws_{tenant_id}",
        password_hash=hash_password("StrongPassword123!"),
    )
    with app.app_context():
        register_user(user)
        return create_jwt_token(user)


def _tenant_headers(app, *, role: str, tenant_id: str = "tenant_a") -> dict:
    token = _register_user(app, user_id=f"{role}_{tenant_id}", role=role, tenant_id=tenant_id)
    return {"Authorization": f"Bearer {token}"}


def _api_key_headers(app, *, role: str, scopes: set[str], tenant_id: str = "tenant_a") -> dict:
    user_id = f"api_key_{role}_{tenant_id}"
    raw_key, key_id, key_hash = generate_api_key()
    user = User(
        user_id=user_id,
        username=user_id,
        email=f"{user_id}@example.com",
        role=role,
        tenant_id=tenant_id,
        workspace_id=f"ws_{tenant_id}",
        password_hash=hash_password("StrongPassword123!"),
    )
    with app.app_context():
        register_user(user)
        register_api_key(APIKey(
            key_id=key_id,
            key_hash=key_hash,
            user_id=user_id,
            tenant_id=tenant_id,
            scopes=scopes,
        ))
    return {"X-API-Key": raw_key}


def _resource_endpoints(resources):
    project_id = resources["project"].project_id
    simulation_id = resources["simulation"].simulation_id
    report_id = resources["report"].report_id
    return [
        ("project", f"/api/graph/project/{project_id}"),
        ("simulation", f"/api/simulation/{simulation_id}"),
        ("report", f"/api/report/{report_id}"),
        ("simulation_export", f"/api/simulation/{simulation_id}/export"),
        ("report_export", f"/api/report/{report_id}/download"),
    ]


@pytest.mark.parametrize("role", ["researcher", "admin"])
def test_tenant_a_and_admin_cannot_access_tenant_b_resources(api_app, client, tenant_b_resources, role):
    headers = _tenant_headers(api_app, role=role, tenant_id="tenant_a")

    for target_type, url in _resource_endpoints(tenant_b_resources):
        response = client.get(url, headers=headers)

        assert response.status_code == 403, target_type
        assert response.get_json()["error"] == "FORBIDDEN"


def test_super_admin_can_cross_tenant_and_writes_audit(api_app, client, tenant_b_resources):
    headers = _tenant_headers(api_app, role="super_admin", tenant_id="tenant_a")

    for target_type, url in _resource_endpoints(tenant_b_resources):
        response = client.get(url, headers=headers)

        assert response.status_code == 200, target_type

    audit_path = api_app.extensions["audit_path"]
    events = [json.loads(line) for line in audit_path.read_text(encoding="utf-8").splitlines()]
    cross_events = [event for event in events if event["event_type"] == "tenant.cross_access"]

    assert {event["target_type"] for event in cross_events} >= {
        "project",
        "simulation",
        "report",
    }
    assert all(event["actor_tenant_id"] == "tenant_a" for event in cross_events)
    assert all(event["details"]["target_tenant_id"] == "tenant_b" for event in cross_events)


def test_no_token_on_runtime_api_returns_401(client):
    response = client.post("/api/simulation/start", json={"simulation_id": "sim_missing"})

    assert response.status_code == 401
    assert response.get_json()["error"] == "AUTH_REQUIRED"


def test_viewer_calling_simulation_run_returns_403(api_app, client):
    headers = _tenant_headers(api_app, role="viewer", tenant_id="tenant_a")

    response = client.post("/api/simulation/start", json={"simulation_id": "sim_missing"}, headers=headers)

    assert response.status_code == 403
    assert response.get_json()["error"] == "FORBIDDEN"


def test_researcher_calling_simulation_run_reaches_business_validation(api_app, client):
    headers = _tenant_headers(api_app, role="researcher", tenant_id="tenant_a")

    response = client.post("/api/simulation/start", json={"simulation_id": "sim_missing"}, headers=headers)

    assert response.status_code in {400, 404}
    assert response.get_json()["error"] not in {"AUTH_REQUIRED", "FORBIDDEN"}


def test_api_key_with_insufficient_scope_returns_403(api_app, client):
    headers = _api_key_headers(api_app, role="researcher", scopes={"simulation.read"}, tenant_id="tenant_a")

    response = client.post("/api/simulation/start", json={"simulation_id": "sim_missing"}, headers=headers)

    assert response.status_code == 403
    assert response.get_json()["error"] == "FORBIDDEN"
