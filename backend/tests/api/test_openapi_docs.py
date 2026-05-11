from app import create_app
from app.config import Config


class OpenApiDocsConfig(Config):
    TESTING = True
    DEBUG = True
    SECRET_KEY = "openapi-docs-secret-key-123456789"
    JWT_SECRET_KEY = "openapi-docs-jwt-secret-key-123456"
    LOG_FORMAT = "text"
    CORS_ALLOWED_ORIGINS = "http://localhost:3000"
    _db_url_cache = ""
    _queue_backend_cache = "thread"

    @classmethod
    def validate(cls):
        return []


def test_openapi_documents_password_login_and_auth_schemes():
    app = create_app(OpenApiDocsConfig)
    spec = app.test_client().get("/api/openapi.json").get_json()

    register = spec["components"]["schemas"]["RegisterUserRequest"]
    login = spec["components"]["schemas"]["LoginRequest"]
    schemes = spec["components"]["securitySchemes"]

    assert "password" in register["required"]
    assert register["properties"]["password"]["format"] == "password"
    assert login["required"] == ["password"]
    assert {"username", "email", "user_id", "password"}.issubset(login["properties"])
    assert schemes["BearerAuth"]["scheme"] == "bearer"
    assert schemes["ApiKeyAuth"]["name"] == "X-API-Key"
