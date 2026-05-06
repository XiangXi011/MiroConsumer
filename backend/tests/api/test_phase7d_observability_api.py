"""Phase 7D run estimate and audit-chain API tests."""

from flask import Flask

from app.api import consumer_bp, graph_bp, report_bp, simulation_bp
from app.services.report_agent import Report, ReportStatus


def _create_test_app():
    app = Flask(__name__)
    app.config["TESTING"] = True
    if hasattr(app, "json") and hasattr(app.json, "ensure_ascii"):
        app.json.ensure_ascii = False
    app.register_blueprint(graph_bp, url_prefix="/api/graph")
    app.register_blueprint(simulation_bp, url_prefix="/api/simulation")
    app.register_blueprint(report_bp, url_prefix="/api/report")
    app.register_blueprint(consumer_bp, url_prefix="/api/consumer")
    return app


def test_run_estimate_api_returns_fixed_structure(monkeypatch):
    from app.config import Config

    monkeypatch.setattr(Config, "_llm_budget_limit_cache", 500, raising=False)
    monkeypatch.setattr(Config, "_llm_deep_reasoning_ratio_cache", 0.1, raising=False)
    monkeypatch.setattr(Config, "_max_agents_cache", 1000, raising=False)
    monkeypatch.setattr(Config, "_max_rounds_cache", 10, raising=False)

    response = _create_test_app().test_client().post(
        "/api/consumer/simulations/sim_1/run-estimate",
        json={"society_max_agents": 200, "max_rounds": 4},
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["success"] is True
    data = payload["data"]
    assert data["agents_count"] == 200
    assert data["rounds_count"] == 4
    assert data["estimated_llm_calls"] == 80
    assert data["cost_level"] in {"low", "medium", "high", "blocked"}
    assert data["estimated_duration_seconds"] > 0


def test_audit_chain_api_returns_chain(monkeypatch):
    import app.services.application.audit_chain_service as audit_module

    report = Report(
        report_id="report_api",
        simulation_id="sim_1",
        graph_id="g1",
        simulation_requirement="req",
        status=ReportStatus.COMPLETED,
    )
    report.audit_chain = {
        "finding_id": "finding_1",
        "source_id": "source_1",
        "round_snapshot_id": "round_1",
        "event_id": "event_1",
        "agent_id": "agent_1",
        "channel_id": "xiaohongshu",
        "task_id": "task_1",
        "trace_id": "trace_1",
    }

    class StubRepo:
        def get_report(self, report_id):
            return report

    monkeypatch.setattr(
        audit_module,
        "create_repository_bundle",
        lambda: type("Bundle", (), {"report_repo": StubRepo()})(),
    )

    response = _create_test_app().test_client().get(
        "/api/consumer/reports/report_api/audit-chain"
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["success"] is True
    assert payload["data"]["report_id"] == "report_api"
    assert payload["data"]["complete"] is True
    assert payload["data"]["chain"][-1]["type"] == "trace"
    assert payload["data"]["chain"][-1]["resource_id"] == "trace_1"
