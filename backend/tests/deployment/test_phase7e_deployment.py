"""Phase 7E production deployment contract tests."""

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[3]


def test_env_example_contains_all_26_production_variables():
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
        "QUEUE_RETRY_LIMIT",
        "QUEUE_VISIBILITY_TIMEOUT_SECONDS",
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
        "MIROCONSUMER_IMAGE",
    ]

    for name in required:
        assert f"{name}=" in env_text


def test_compose_image_uses_miroconsumer_image_env_var():
    compose_text = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")

    assert "ghcr.io/666ghj/miroconsumer" not in compose_text
    assert "${MIROCONSUMER_IMAGE" in compose_text


def test_production_docker_files_exist_and_have_fixed_commands():
    backend = (ROOT / "Dockerfile.backend").read_text(encoding="utf-8")
    frontend = (ROOT / "Dockerfile.frontend").read_text(encoding="utf-8")
    worker = (ROOT / "Dockerfile.worker").read_text(encoding="utf-8")
    nginx = (ROOT / "nginx.conf").read_text(encoding="utf-8")

    assert "gunicorn" in backend
    assert "--bind 0.0.0.0:5001 --workers 2 --threads 4 --timeout 300" in backend
    assert "nginx" in frontend.lower()
    assert "FROM miroconsumer-backend" in worker
    assert "proxy_pass http://backend:5001" in nginx
    assert "client_max_body_size" in nginx


def test_production_compose_contains_required_services():
    data = yaml.safe_load((ROOT / "docker-compose.prod.yml").read_text(encoding="utf-8"))
    services = data["services"]

    assert set(services) >= {"frontend", "backend", "worker", "postgres", "redis", "minio"}
    assert services["backend"]["command"] == (
        'gunicorn "app:create_app()" --bind 0.0.0.0:5001 --workers 2 --threads 4 --timeout 300'
    )
