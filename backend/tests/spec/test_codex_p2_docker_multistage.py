"""SPEC-P2-019 Docker multi-stage build contract."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_backend_dockerfile_has_builder_runtime_and_worker_targets():
    text = _read("Dockerfile.backend")

    assert "FROM python:3.12-slim AS builder" in text
    assert "FROM python:3.12-slim AS runtime" in text
    assert "FROM runtime AS worker" in text
    assert "COPY --from=builder" in text
    assert "uv sync --frozen --no-dev" in text
    assert "USER miroconsumer" in text
    assert "gunicorn" in text
    assert 'CMD ["python", "-m", "app.worker"]' in text


def test_frontend_dockerfile_builds_with_node_and_serves_dist_from_nginx():
    text = _read("Dockerfile.frontend")

    assert "FROM node:24-alpine AS builder" in text
    assert "npm ci" in text
    assert "npm run build" in text
    assert "FROM nginx:" in text
    assert "alpine" in text
    assert "COPY --from=builder /app/frontend/dist /usr/share/nginx/html" in text


def test_worker_dockerfile_no_longer_depends_on_implicit_local_backend_alias():
    text = _read("Dockerfile.worker")

    assert "FROM miroconsumer-backend" not in text
    assert "python:3.12-slim" in text
    assert "app.worker" in text


def test_docker_workflow_builds_backend_frontend_and_worker_targets():
    text = _read(".github/workflows/docker-image.yml")

    backend_index = text.index("name: Build backend runtime image")
    worker_index = text.index("name: Build worker image")
    frontend_index = text.index("name: Build frontend image")
    trivy_index = text.index("name: Run Trivy vulnerability scanner")

    assert backend_index < worker_index < frontend_index < trivy_index
    assert "file: ./Dockerfile.backend" in text
    assert "target: runtime" in text
    assert "target: worker" in text
    assert "file: ./Dockerfile.frontend" in text
    assert "file: ./Dockerfile.worker" not in text
