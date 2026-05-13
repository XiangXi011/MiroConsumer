from unittest.mock import MagicMock, patch

import pytest
from flask import Flask, jsonify

from app.config import Config
from app.middleware.rate_limiter import RateLimiter, auth_rate_limit, configure_rate_limiter


def test_memory_rate_limiter_blocks_after_limit_and_isolates_keys():
    limiter = RateLimiter(backend="memory", window_seconds=60)

    assert limiter.check("tenant:a:user:1", limit=2).allowed is True
    assert limiter.check("tenant:a:user:1", limit=2).allowed is True
    blocked = limiter.check("tenant:a:user:1", limit=2)
    assert blocked.allowed is False
    assert blocked.retry_after > 0

    assert limiter.check("tenant:b:user:1", limit=2).allowed is True


def test_redis_rate_limiter_sets_ttl_on_first_increment():
    redis_client = MagicMock()
    redis_client.incr.return_value = 1
    redis_client.ttl.return_value = 60

    limiter = RateLimiter(
        backend="redis",
        redis_url="redis://localhost:6379/0",
        redis_client=redis_client,
        window_seconds=60,
    )

    result = limiter.check("login:127.0.0.1:demo", limit=5)

    assert result.allowed is True
    redis_client.incr.assert_called_once()
    redis_client.expire.assert_called_once()


def test_production_redis_rate_limit_requires_redis_url():
    class ProductionConfig(Config):
        DEBUG = False
        TESTING = False
        SECRET_KEY = "valid-secret-key-that-is-long-enough-32"
        RATE_LIMIT_ENABLED = True
        RATE_LIMIT_BACKEND = "redis"
        _redis_url_cache = ""

    errors = ProductionConfig.validate()

    assert any("REDIS_URL" in error and "RATE_LIMIT_BACKEND=redis" in error for error in errors)


def test_production_memory_rate_limit_is_rejected():
    class ProductionConfig(Config):
        DEBUG = False
        TESTING = False
        ENVIRONMENT = "production"
        SECRET_KEY = "valid-secret-key-that-is-long-enough-32"
        RATE_LIMIT_ENABLED = True
        RATE_LIMIT_BACKEND = "memory"

    errors = ProductionConfig.validate()

    assert any("memory rate limiter" in error.lower() for error in errors)


def test_auth_rate_limit_returns_429_after_threshold():
    app = Flask(__name__)
    app.config.update(
        TESTING=True,
        RATE_LIMIT_ENABLED=True,
        RATE_LIMIT_BACKEND="memory",
        AUTH_RATE_LIMIT_PER_MINUTE=1,
    )
    configure_rate_limiter(app)

    @app.route("/api/auth/login", methods=["POST"])
    @auth_rate_limit
    def login():
        return jsonify({"success": False, "error": "AUTH_FAILED"}), 401

    client = app.test_client()

    assert client.post("/api/auth/login", json={"username": "demo"}).status_code == 401
    response = client.post("/api/auth/login", json={"username": "demo"})

    assert response.status_code == 429
    assert response.get_json()["error"] == "RATE_LIMITED"
