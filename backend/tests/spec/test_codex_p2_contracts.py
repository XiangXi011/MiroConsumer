from pydantic import ValidationError

import inspect
import sys
import types
from pathlib import Path

import app as app_module
from app import create_app
from app.config import Config
from app.services.consumer.contracts.consumer_contracts import ConsumerOutputContract
from app.utils.request_validator import validate_json


ROOT = Path(__file__).resolve().parents[2]


def test_consumer_output_contract_requires_methodology_and_disclaimer():
    payload = {
        "report_id": "report_123",
        "simulation_id": "sim_123",
        "status": "completed",
        "methodology_limits": {"confidence_level": "medium"},
        "methodology_page": "# Methodology Page\nAgent-based consumer propagation simulation.",
        "disclaimer": "Simulation output is not a market forecast.",
    }

    contract = ConsumerOutputContract(**payload)

    assert contract.methodology_page.startswith("# Methodology Page")
    assert contract.disclaimer


def test_consumer_output_contract_rejects_missing_methodology_page():
    payload = {
        "report_id": "report_123",
        "simulation_id": "sim_123",
        "status": "completed",
        "methodology_limits": {"confidence_level": "medium"},
        "disclaimer": "Simulation output is not a market forecast.",
    }

    try:
        ConsumerOutputContract(**payload)
    except ValidationError as exc:
        assert "methodology_page" in str(exc)
    else:
        raise AssertionError("ConsumerOutputContract must require methodology_page")


def test_api_routes_do_not_use_bare_request_get_json():
    api_root = ROOT / "app" / "api"
    offenders = []
    for path in api_root.glob("*.py"):
        text = path.read_text(encoding="utf-8")
        if "request.get_json()" in text:
            offenders.append(str(path.relative_to(ROOT)))

    assert offenders == []


def test_validate_json_returns_standard_422_payload():
    from flask import Flask
    from pydantic import BaseModel

    class DemoRequest(BaseModel):
        simulation_id: str

    app = Flask(__name__)
    with app.test_request_context(json={}):
        response, status = validate_json(DemoRequest, {})

    payload = response.get_json()
    assert status == 422
    assert payload["error_code"] == "REQUEST_VALIDATION_FAILED"
    assert payload["error_message"] == "Request validation failed"
    assert payload["field"] == "simulation_id"
    assert payload["suggestion"]


def test_create_app_is_split_into_single_responsibility_factories():
    source = inspect.getsource(app_module.create_app)
    meaningful_lines = [
        line for line in source.splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]

    assert len(meaningful_lines) < 50
    for name in (
        "create_flask_app",
        "init_extensions",
        "register_blueprints",
        "init_observability",
        "register_health_routes",
    ):
        assert hasattr(app_module, name)


def test_service_split_assessment_document_exists():
    doc_path = ROOT.parent / "docs" / "architecture" / "service_split_assessment.md"
    text = doc_path.read_text(encoding="utf-8")

    for phrase in ("Simulation Engine Service", "Report Generation Service", "Authentication Service"):
        assert phrase in text
    assert "Constructor Injection" in text


class _DefaultRateLimitConfig(Config):
    TESTING = True
    DEBUG = True
    SECRET_KEY = "default-rate-limit-secret-key-32"
    JWT_SECRET_KEY = "default-rate-limit-jwt-secret-key-32"
    LOG_FORMAT = "text"
    CORS_ALLOWED_ORIGINS = "http://localhost:3000"
    RATE_LIMIT_BACKEND = "memory"

    @classmethod
    def validate(cls):
        return []


def test_rate_limiting_defaults_to_enabled_and_health_reports_state():
    assert Config.RATE_LIMIT_ENABLED is True

    app = create_app(_DefaultRateLimitConfig)
    response = app.test_client().get("/health")

    assert response.status_code == 200
    assert response.get_json()["rate_limiter"] == "enabled"


def test_mc_error_code_maps_to_status_and_standard_payload():
    from app.core.errors import MCErrCode, build_error_payload

    assert MCErrCode.BRIEF_VALIDATION_FAILED.to_http_status() == 422
    assert MCErrCode.PERMISSION_DENIED.to_http_status() == 403
    assert MCErrCode.SIMULATION_LLM_TIMEOUT.to_http_status() == 503

    payload = build_error_payload(
        MCErrCode.TENANT_ISOLATION_VIOLATION,
        field="project_id",
        suggestion="Request a project that belongs to the active tenant.",
        request_id="req_123",
    )

    assert payload["error_code"] == "TENANT_ISOLATION_VIOLATION"
    assert payload["error_message"]
    assert payload["field"] == "project_id"
    assert payload["request_id"] == "req_123"
    assert payload["suggestion"]


def test_openapi_error_response_documents_standard_fields():
    app = create_app(_DefaultRateLimitConfig)
    spec = app.test_client().get("/api/openapi.json").get_json()

    error_schema = spec["components"]["schemas"]["ErrorResponse"]
    for field in ("error_code", "error_message", "field", "request_id", "suggestion"):
        assert field in error_schema["properties"]


def test_sentry_observability_uses_flask_celery_sqlalchemy_and_priority_sampler(monkeypatch):
    init_calls = []

    sentry_sdk = types.ModuleType("sentry_sdk")
    sentry_sdk.init = lambda **kwargs: init_calls.append(kwargs)
    monkeypatch.setitem(sys.modules, "sentry_sdk", sentry_sdk)

    for module_name, class_name in (
        ("sentry_sdk.integrations.flask", "FlaskIntegration"),
        ("sentry_sdk.integrations.celery", "CeleryIntegration"),
        ("sentry_sdk.integrations.sqlalchemy", "SqlalchemyIntegration"),
    ):
        module = types.ModuleType(module_name)
        integration_cls = type(class_name, (), {})
        setattr(module, class_name, integration_cls)
        monkeypatch.setitem(sys.modules, module_name, module)

    class SentryConfig(_DefaultRateLimitConfig):
        SENTRY_DSN = "https://example@sentry.invalid/1"
        SENTRY_ENVIRONMENT = "test"
        SENTRY_TRACES_SAMPLE_RATE = 0.05

    create_app(SentryConfig)

    assert len(init_calls) == 1
    call = init_calls[0]
    names = {integration.__class__.__name__ for integration in call["integrations"]}
    assert {"FlaskIntegration", "CeleryIntegration", "SqlalchemyIntegration"} <= names
    assert call["environment"] == "test"
    sampler = call["traces_sampler"]
    assert sampler({"wsgi_environ": {"PATH_INFO": "/api/simulation/start"}}) == 1.0
    assert sampler({"wsgi_environ": {"PATH_INFO": "/api/graph/project/list"}}) == 0.05


def test_health_exposes_performance_slo_metrics():
    app = create_app(_DefaultRateLimitConfig)
    payload = app.test_client().get("/health").get_json()

    assert "performance" in payload
    performance = payload["performance"]
    assert set(performance) >= {"p95_response_ms", "cache_hit_rate", "llm_avg_latency_ms"}
    assert isinstance(performance["p95_response_ms"], (int, float))
    assert isinstance(performance["cache_hit_rate"], (int, float))
    assert isinstance(performance["llm_avg_latency_ms"], (int, float))


def test_p2_012_benchmark_dependencies_are_declared():
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")

    assert "pytest-benchmark" in pyproject
    assert "locust" in pyproject


def test_p2_012_benchmark_suite_and_locust_script_exist():
    benchmark_dir = ROOT / "tests" / "benchmark"
    assert benchmark_dir.is_dir()
    benchmark_tests = list(benchmark_dir.glob("test_*.py"))
    assert benchmark_tests
    combined = "\n".join(path.read_text(encoding="utf-8") for path in benchmark_tests)
    for marker in ("benchmark", "concept-tests", "simulation/start", "report", "pdf"):
        assert marker in combined

    locustfile = ROOT / "tests" / "benchmark" / "locustfile.py"
    text = locustfile.read_text(encoding="utf-8")
    assert "P99_TARGET_MS = 500" in text
    assert text.count("@task") >= 10
    for endpoint in (
        "/health",
        "/ready",
        "/api/v1/consumer/concept-tests",
        "/api/v1/simulation/start",
        "/api/v1/report/generate",
        "/api/v1/report/generate/status",
        "/api/v1/consumer/comparisons",
        "/api/v1/consumer/research-assets",
        "/api/v1/auth/me",
        "/api/version",
    ):
        assert endpoint in text


def test_p2_012_ci_benchmark_job_blocks_performance_regressions():
    workflow = (ROOT.parent / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")

    benchmark_job = workflow.split("  benchmark:", 1)[1]
    assert "python-version: \"3.12\"" in benchmark_job
    assert "astral-sh/setup-uv" in benchmark_job
    assert "continue-on-error" not in benchmark_job
    assert "pytest tests/benchmark" in benchmark_job
    assert "--benchmark-json" in benchmark_job
    assert "scripts/check_benchmark_regression.py" in benchmark_job
    assert "15" in benchmark_job


def test_p2_012_benchmark_regression_checker_uses_15_percent_gate():
    script = ROOT / "scripts" / "check_benchmark_regression.py"
    text = script.read_text(encoding="utf-8")

    assert "MAX_REGRESSION_RATIO = 0.15" in text
    assert "stats" in text
    assert "mean" in text
