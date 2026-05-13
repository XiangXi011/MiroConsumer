from unittest.mock import MagicMock, patch

from app import create_app
from app.config import Config


class ReadyConfig(Config):
    TESTING = True
    DEBUG = True
    SECRET_KEY = "ready-secret-key-that-is-long-enough-32"
    JWT_SECRET_KEY = "ready-jwt-secret-key-that-is-long-enough-32"
    LOG_FORMAT = "text"
    CORS_ALLOWED_ORIGINS = "http://localhost:3000"
    RATE_LIMIT_ENABLED = True
    RATE_LIMIT_BACKEND = "redis"
    STORAGE_BACKEND = "local"
    _redis_url_cache = "redis://localhost:6379/0"
    _db_url_cache = ""
    _queue_backend_cache = "thread"

    @classmethod
    def validate(cls):
        return []


def test_health_does_not_leak_sensitive_information():
    app = create_app(ReadyConfig)
    response = app.test_client().get("/health")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["status"] == "ok"
    assert payload["rate_limiter"] == "enabled"
    assert set(payload["performance"]) >= {"p95_response_ms", "cache_hit_rate", "llm_avg_latency_ms"}
    text = response.get_data(as_text=True).lower()
    for forbidden in ["secret", "key", "model", "path", "version"]:
        assert forbidden not in text


def test_ready_returns_ready_when_dependencies_are_ok():
    redis_conn = MagicMock()

    with patch("app.redis.health.redis.Redis.from_url", return_value=redis_conn):
        app = create_app(ReadyConfig)
        redis_conn.ping.reset_mock()
        response = app.test_client().get("/ready")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["status"] == "ready"
    assert payload["checks"]["redis"] == "ok"
    redis_conn.ping.assert_called_once()


def test_ready_returns_503_when_redis_is_unavailable():
    redis_conn = MagicMock()
    redis_conn.ping.side_effect = RuntimeError("redis down")

    with patch("app.redis.health.redis.Redis.from_url", return_value=redis_conn):
        app = create_app(ReadyConfig)
        redis_conn.ping.reset_mock()
        response = app.test_client().get("/ready")

    assert response.status_code == 503
    payload = response.get_json()
    assert payload["status"] == "not_ready"
    assert payload["checks"]["redis"] == "error"


