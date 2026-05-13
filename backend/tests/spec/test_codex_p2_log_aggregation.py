"""SPEC-P2-016 structured log aggregation contract."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from types import SimpleNamespace

from flask import Flask, g

from app import create_app
from app.utils.structured_logger import StructuredFormatter
from tests.ops.test_health_readiness import ReadyConfig

BACKEND_ROOT = Path(__file__).resolve().parents[2]
REPO_ROOT = BACKEND_ROOT.parent

REQUIRED_FIELDS = {
    "timestamp",
    "level",
    "logger",
    "message",
    "trace_id",
    "span_id",
    "service",
    "tenant_id",
    "user_id",
}


def test_structured_formatter_emits_required_aggregation_fields():
    app = Flask(__name__)
    formatter = StructuredFormatter(service="backend")
    record = logging.LogRecord(
        name="miroconsumer.request",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="request completed",
        args=(),
        exc_info=None,
    )

    with app.test_request_context("/api/v1/consumer/projects", headers={"X-Request-ID": "trace-header"}):
        g.trace_id = "trace-header"
        g.span_id = "span-abc"
        g.current_tenant = "tenant-a"
        g.current_user = SimpleNamespace(user_id="user-a")
        payload = json.loads(formatter.format(record))

    assert REQUIRED_FIELDS.issubset(payload)
    assert payload["trace_id"] == "trace-header"
    assert payload["span_id"] == "span-abc"
    assert payload["tenant_id"] == "tenant-a"
    assert payload["user_id"] == "user-a"
    assert payload["service"] == "backend"
    assert payload["method"] == "GET"
    assert payload["path"] == "/api/v1/consumer/projects"


def test_flask_request_hook_injects_trace_id_and_span_id_from_header():
    class JsonReadyConfig(ReadyConfig):
        LOG_FORMAT = "json"

    app = create_app(JsonReadyConfig)

    @app.route("/trace-contract")
    def trace_contract():
        return {"trace_id": g.trace_id, "span_id": g.span_id}

    response = app.test_client().get("/trace-contract", headers={"X-Request-ID": "trace-123"})

    assert response.status_code == 200
    assert response.headers["X-Request-ID"] == "trace-123"
    payload = response.get_json()
    assert payload["trace_id"] == "trace-123"
    assert len(payload["span_id"]) >= 12


def test_production_compose_includes_promtail_sidecar_and_config():
    compose_text = (REPO_ROOT / "docker-compose.prod.yml").read_text(encoding="utf-8")
    promtail_config = REPO_ROOT / "ops" / "promtail-config.yml"

    assert "promtail:" in compose_text
    assert "grafana/promtail" in compose_text
    assert "LOKI_URL" in compose_text
    assert "promtail-config.yml" in compose_text

    config_text = promtail_config.read_text(encoding="utf-8")
    assert "docker_sd_configs" in config_text
    assert "json" in config_text
    assert "trace_id" in config_text


def test_log_aggregation_runbook_and_query_templates_exist():
    runbook = REPO_ROOT / "docs" / "operations" / "log_aggregation.md"
    queries = REPO_ROOT / "ops" / "loki_queries.json"

    runbook_text = runbook.read_text(encoding="utf-8")
    query_text = queries.read_text(encoding="utf-8")

    assert "trace_id" in runbook_text
    assert "tenant_id" in runbook_text
    assert "Grafana Loki" in runbook_text
    assert "Kibana" in runbook_text
    assert "trace_id" in query_text
    assert "tenant_id" in query_text
    assert "error_code" in query_text