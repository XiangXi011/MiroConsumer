"""Security response header tests for the real Flask app factory."""

from app import create_app
from app.config import Config


class _BaseSecurityConfig(Config):
    SECRET_KEY = "test-secret-key-for-security-headers-123456"
    LLM_API_KEY = "test-llm-key"
    ZEP_API_KEY = "test-zep-key"
    CORS_ALLOWED_ORIGINS = "http://localhost:3000"
    LOG_FORMAT = "text"
    SECURITY_HEADERS_ENABLED = True
    DB_URL = ""


def _get_health_csp(config_class):
    app = create_app(config_class=config_class)
    with app.test_client() as client:
        response = client.get("/health")
    assert response.status_code == 200
    return response.headers.get("Content-Security-Policy", "")


def test_production_csp_is_complete_and_strict_by_default():
    class ProductionConfig(_BaseSecurityConfig):
        DEBUG = False

    csp = _get_health_csp(ProductionConfig)

    required_directives = [
        "default-src 'self'",
        "script-src 'self'",
        "style-src 'self'",
        "img-src 'self' data: blob:",
        "font-src 'self' data:",
        "connect-src 'self'",
        "object-src 'none'",
        "base-uri 'self'",
        "frame-ancestors 'none'",
        "form-action 'self'",
    ]
    for directive in required_directives:
        assert directive in csp
    assert "'unsafe-inline'" not in csp
    assert "'unsafe-eval'" not in csp


def test_csp_policy_can_be_overridden_explicitly():
    custom_policy = "default-src 'self'; script-src 'self' 'unsafe-inline'; connect-src 'self' ws://localhost:3000"

    class DevelopmentConfig(_BaseSecurityConfig):
        DEBUG = True
        CSP_POLICY = custom_policy

    assert _get_health_csp(DevelopmentConfig) == custom_policy
