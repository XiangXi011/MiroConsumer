"""Tests for the generated OpenAPI route inventory."""

from pathlib import Path

from app import create_app
from app.config import Config


class TestConfig(Config):
    TESTING = True
    DEBUG = True
    SECRET_KEY = "test-secret-key-for-openapi"
    LOG_FORMAT = "text"
    CORS_ALLOWED_ORIGINS = "http://localhost:3000"
    _db_url_cache = ""
    _queue_backend_cache = "thread"

    @classmethod
    def validate(cls):
        return []


class AuthRequiredTestConfig(TestConfig):
    AUTH_BYPASS_IN_TESTING = False


def test_v1_auth_register_and_login_routes_are_public():
    app = create_app(AuthRequiredTestConfig)
    client = app.test_client()

    register_response = client.post("/api/v1/auth/register", json={
        "username": "v1-user",
        "email": "v1@example.com",
        "role": "researcher",
        "tenant_id": "tenant-v1",
    })
    assert register_response.status_code == 201
    user_id = register_response.get_json()["data"]["user_id"]

    login_response = client.post("/api/v1/auth/login", json={"user_id": user_id})
    assert login_response.status_code == 200
    payload = login_response.get_json()
    assert payload["success"] is True
    assert payload["data"]["token"]


def test_openapi_spec_documents_v1_resource_paths():
    app = create_app(TestConfig)
    client = app.test_client()

    response = client.get("/api/openapi.json")
    assert response.status_code == 200
    spec = response.get_json()

    paths = spec["paths"]
    assert "/api/v1/consumer/simulation/{simulation_id}/consumer-summary" in paths
    assert "/api/v1/consumer/reports/{report_id}/evidence-graph" in paths
    assert "/api/v1/graph/project/list" in paths
    assert "/api/v1/report/generate" in paths
    assert "/api/v1/auth/register" in paths
    assert "/api/v1/auth/login" in paths
    assert "/api/v1/auth/me" in paths
    assert "/api/v1/auth/api-keys" in paths
    assert "/api/v1/consumer/task-queue/dead-letters" in paths
    assert "/health" in paths
    assert "/api/consumer/simulation/{simulation_id}/consumer-summary" not in paths


def test_openapi_v1_paths_match_registered_flask_routes():
    app = create_app(TestConfig)
    client = app.test_client()

    response = client.get("/api/openapi.json")
    assert response.status_code == 200
    spec = response.get_json()

    registered_rules = {
        rule.rule
        for rule in app.url_map.iter_rules()
        if rule.rule.startswith("/api/v1/")
    }
    documented_rules = {
        path.replace("{", "<").replace("}", ">")
        for path in spec["paths"]
        if path.startswith("/api/v1/")
    }

    assert documented_rules <= registered_rules


def test_api_versioning_policy_documents_legacy_deprecation_window():
    policy_path = Path(__file__).resolve().parents[2] / "docs" / "API_VERSIONING_POLICY.md"
    text = policy_path.read_text(encoding="utf-8")

    assert "/api/v1/" in text
    assert "Legacy `/api/*` routes" in text
    assert "two minor releases" in text
    assert "Deprecation" in text


def test_openapi_spec_exposes_core_request_and_response_schemas():
    app = create_app(TestConfig)
    client = app.test_client()

    response = client.get("/api/openapi.json")
    assert response.status_code == 200
    spec = response.get_json()

    schemas = spec["components"]["schemas"]
    for name in [
        "RegisterUserRequest",
        "LoginRequest",
        "CreateApiKeyRequest",
        "GenerateReportRequest",
        "GenerateReportStatusRequest",
        "DeadLetterListResponse",
        "EvidenceGraphResponse",
        "StartSimulationRequest",
    ]:
        assert name in schemas

    assert schemas["RegisterUserRequest"]["required"] == ["username", "email"]
    assert "tenant_id" in schemas["RegisterUserRequest"]["properties"]
    assert "role" in schemas["RegisterUserRequest"]["properties"]
    assert "scopes" in schemas["CreateApiKeyRequest"]["properties"]
    assert "simulation_id" in schemas["GenerateReportRequest"]["required"]
    assert "nodes" in schemas["EvidenceGraphResponse"]["properties"]
    assert "edges" in schemas["EvidenceGraphResponse"]["properties"]
