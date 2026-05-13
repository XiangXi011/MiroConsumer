"""SPEC-P2-012 API path microbenchmarks.

These benchmarks intentionally avoid real LLM/network work. They exercise Flask
routing, auth/validation middleware, and response serialization for the key API
paths that are expensive in production when backed by real services.
"""

from __future__ import annotations

import pytest

pytest.importorskip("pytest_benchmark")

from app import create_app
from app.config import Config


class BenchmarkConfig(Config):
    TESTING = True
    DEBUG = True
    SECRET_KEY = "benchmark-secret-key-that-is-long-enough-32"
    JWT_SECRET_KEY = "benchmark-jwt-secret-key-that-is-long-enough-32"
    LOG_FORMAT = "text"
    CORS_ALLOWED_ORIGINS = "http://localhost:3000"
    RATE_LIMIT_ENABLED = False
    RATE_LIMIT_BACKEND = "memory"

    @classmethod
    def validate(cls):
        return []


@pytest.fixture(scope="module")
def client():
    app = create_app(BenchmarkConfig)
    return app.test_client()


def _assert_no_server_error(response):
    assert response.status_code < 500
    return response


def test_benchmark_create_concept_test_path(client, benchmark):
    payload = {
        "task_type": "concept_test",
        "product_concept_assets": ["Protein breakfast pouch"],
        "research_goal": "Benchmark concept creation request path",
    }

    response = benchmark(lambda: client.post("/api/v1/consumer/concept-tests", json=payload))

    _assert_no_server_error(response)


def test_benchmark_start_simulation_path(client, benchmark):
    payload = {"simulation_id": "bench_sim", "force_restart": False}

    response = benchmark(lambda: client.post("/api/v1/simulation/start", json=payload))

    _assert_no_server_error(response)


def test_benchmark_generate_report_path(client, benchmark):
    payload = {"simulation_id": "bench_sim", "force_regenerate": False}

    response = benchmark(lambda: client.post("/api/v1/report/generate", json=payload))

    _assert_no_server_error(response)


def test_benchmark_export_pdf_path(client, benchmark):
    response = benchmark(lambda: client.get("/api/v1/report/bench_report/download?format=pdf"))

    _assert_no_server_error(response)


def test_benchmark_health_readiness_paths(client, benchmark):
    response = benchmark(lambda: (client.get("/health"), client.get("/ready")))

    for item in response:
        _assert_no_server_error(item)
