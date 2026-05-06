"""API mapping tests for Phase 7C concurrency conflicts."""

from flask import Flask

from app.api import consumer_bp, graph_bp, report_bp, simulation_bp
from app.contracts.errors import ConcurrencyConflictError


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


def test_simulation_start_conflict_returns_fixed_409(monkeypatch):
    from app.services.application.simulation_app_service import SimulationAppService

    def raise_conflict(simulation_id, data):
        raise ConcurrencyConflictError(
            resource="simulation",
            resource_id=simulation_id,
            reason="lock_timeout",
        )

    monkeypatch.setattr(SimulationAppService, "start_simulation", raise_conflict)

    response = _create_test_app().test_client().post(
        "/api/simulation/start",
        json={"simulation_id": "sim_1"},
    )

    assert response.status_code == 409
    assert response.get_json() == {
        "error": "conflict",
        "resource": "simulation",
        "resource_id": "sim_1",
        "reason": "lock_timeout",
    }


def test_report_generate_conflict_returns_fixed_409(monkeypatch):
    from app.services.application.report_app_service import ReportAppService

    def raise_conflict(simulation_id, force_regenerate=False):
        raise ConcurrencyConflictError(
            resource="report",
            resource_id=simulation_id,
            reason="duplicate_operation",
        )

    monkeypatch.setattr(ReportAppService, "generate_report", raise_conflict)

    response = _create_test_app().test_client().post(
        "/api/report/generate",
        json={"simulation_id": "sim_1"},
    )

    assert response.status_code == 409
    assert response.get_json() == {
        "error": "conflict",
        "resource": "report",
        "resource_id": "sim_1",
        "reason": "duplicate_operation",
    }


def test_consumer_branch_resume_conflict_returns_fixed_409(monkeypatch):
    from app.services.application.branch_app_service import BranchAppService

    def raise_conflict(simulation_id, branch_id, max_rounds=None):
        raise ConcurrencyConflictError(
            resource="branch",
            resource_id=f"{simulation_id}:{branch_id}",
            reason="lock_timeout",
        )

    monkeypatch.setattr(BranchAppService, "resume_branch", raise_conflict)

    response = _create_test_app().test_client().post(
        "/api/consumer/simulations/sim_1/branches/branch_1/resume",
        json={},
    )

    assert response.status_code == 409
    assert response.get_json() == {
        "error": "conflict",
        "resource": "branch",
        "resource_id": "sim_1:branch_1",
        "reason": "lock_timeout",
    }


def test_legacy_simulation_branch_resume_conflict_returns_fixed_409(monkeypatch):
    from app.services.application.branch_app_service import BranchAppService

    def raise_conflict(simulation_id, branch_id, max_rounds=None):
        raise ConcurrencyConflictError(
            resource="branch",
            resource_id=f"{simulation_id}:{branch_id}",
            reason="lock_timeout",
        )

    monkeypatch.setattr(BranchAppService, "resume_branch", raise_conflict)

    response = _create_test_app().test_client().post(
        "/api/simulation/sim_1/branches/branch_1/resume",
        json={},
    )

    assert response.status_code == 409
    assert response.get_json() == {
        "error": "conflict",
        "resource": "branch",
        "resource_id": "sim_1:branch_1",
        "reason": "lock_timeout",
    }
