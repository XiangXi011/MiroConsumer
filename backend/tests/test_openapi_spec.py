"""Tests for the generated OpenAPI route inventory."""

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


def test_openapi_spec_documents_v1_resource_paths():
    app = create_app(TestConfig)
    client = app.test_client()

    response = client.get("/api/openapi.json")
    assert response.status_code == 200
    spec = response.get_json()

    paths = spec["paths"]
    assert "/api/v1/consumer/simulation/{simulation_id}/consumer-summary" in paths
    assert "/api/v1/graph/projects" in paths
    assert "/api/v1/report/generate" in paths
    assert "/api/consumer/simulation/{simulation_id}/consumer-summary" not in paths
