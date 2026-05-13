"""Phase 7E production deployment contract tests."""

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[3]


def test_env_example_contains_required_production_variables():
    env_text = (ROOT / ".env.example").read_text(encoding="utf-8")
    required = [
        "LLM_API_KEY",
        "LLM_BASE_URL",
        "LLM_MODEL_NAME",
        "ZEP_API_KEY",
        "DB_URL",
        "DB_POOL_SIZE",
        "DB_MAX_OVERFLOW",
        "DB_STATEMENT_TIMEOUT_SECONDS",
        "QUEUE_BACKEND",
        "REDIS_URL",
        "LOCK_BACKEND",
        "QUEUE_RETRY_LIMIT",
        "QUEUE_VISIBILITY_TIMEOUT_SECONDS",
        "GUNICORN_WORKERS",
        "GUNICORN_THREADS",
        "GUNICORN_TIMEOUT",
        "STORAGE_BACKEND",
        "S3_ENDPOINT",
        "S3_BUCKET",
        "S3_ACCESS_KEY",
        "S3_SECRET_KEY",
        "S3_REGION",
        "MAX_AGENTS",
        "MAX_ROUNDS",
        "LLM_BUDGET_LIMIT",
        "LLM_DEEP_REASONING_RATIO",
        "ENABLE_DETERMINISTIC_FALLBACK",
        "ENABLE_SOCIETY_MODE",
        "ENABLE_GRAPH_MEMORY_WRITEBACK",
        "FLASK_DEBUG",
        "SECRET_KEY",
        "CORS_ALLOWED_ORIGINS",
        "MIROCONSUMER_IMAGE",
    ]

    for name in required:
        assert f"{name}=" in env_text


def test_env_example_production_safe_defaults():
    env_text = (ROOT / ".env.example").read_text(encoding="utf-8")

    assert "ENABLE_SOCIETY_MODE=true" in env_text
    assert "ENABLE_GRAPH_MEMORY_WRITEBACK=false" in env_text
    assert "FLASK_DEBUG=false" in env_text
    assert "CORS_ALLOWED_ORIGINS=http://localhost:3000" in env_text


def test_compose_image_uses_miroconsumer_image_env_var():
    compose_text = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")

    assert "ghcr.io/666ghj/miroconsumer" not in compose_text
    assert "${MIROCONSUMER_IMAGE" in compose_text


def test_production_docker_files_exist_and_use_configurable_commands():
    backend = (ROOT / "Dockerfile.backend").read_text(encoding="utf-8")
    frontend = (ROOT / "Dockerfile.frontend").read_text(encoding="utf-8")
    worker = (ROOT / "Dockerfile.worker").read_text(encoding="utf-8")
    nginx = (ROOT / "nginx.conf").read_text(encoding="utf-8")

    assert "gunicorn" in backend
    assert "--workers ${GUNICORN_WORKERS:-2}" in backend
    assert "--threads ${GUNICORN_THREADS:-4}" in backend
    assert "--timeout ${GUNICORN_TIMEOUT:-300}" in backend
    assert "FROM runtime AS worker" in backend
    assert "nginx" in frontend.lower()
    assert "FROM miroconsumer-backend" not in worker
    assert 'CMD ["python", "-m", "app.worker"]' in worker
    assert "proxy_pass http://backend:5001" in nginx
    assert "client_max_body_size" in nginx


def test_production_compose_contains_required_services():
    data = yaml.safe_load((ROOT / "docker-compose.prod.yml").read_text(encoding="utf-8"))
    services = data["services"]

    assert set(services) >= {"frontend", "backend", "worker", "postgres", "redis", "minio"}
    backend = services["backend"]
    assert "GUNICORN_WORKERS" in backend["environment"]
    assert "GUNICORN_THREADS" in backend["environment"]
    assert "LOCK_BACKEND" in backend["environment"]
    assert "$${GUNICORN_WORKERS:-4}" in backend["command"]
    assert "$${GUNICORN_THREADS:-4}" in backend["command"]
    assert "$${GUNICORN_TIMEOUT:-300}" in backend["command"]
