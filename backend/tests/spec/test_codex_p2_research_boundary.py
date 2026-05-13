"""SPEC-P2-025 research boundary enforcement and report disclosure."""

from __future__ import annotations

from flask import Flask

from app.api import report_bp
from app.services.consumer.persona_pack import load_default_persona_pack
from app.services.consumer.society.population_models import ConsumerSocietyRunConfig
from app.services.consumer.society.society_runtime import ConsumerSocietyRuntime
from app.services.report_agent import Report, ReportStatus


def _small_config() -> ConsumerSocietyRunConfig:
    return ConsumerSocietyRunConfig(
        mode="quick",
        core_persona_count=1,
        expanded_persona_count=0,
        shadow_agent_count=0,
        max_rounds=1,
        random_seed=3,
    )


def test_runtime_blocks_high_risk_brief_before_simulation_starts(tmp_path, monkeypatch):
    from app.services.consumer.research_boundary import ResearchBoundaryViolation

    monkeypatch.setenv("SOCIETY_DETERMINISTIC_MODE", "mock")
    runtime = ConsumerSocietyRuntime(base_dir=tmp_path)

    try:
        runtime.run(
            simulation_id="sim-risk",
            run_id="run-risk",
            config=_small_config(),
            persona_pack=load_default_persona_pack(),
            brief_context={
                "product_category": "financial services",
                "claims": ["Give users investment advice with guaranteed returns."],
            },
            research_findings=[],
        )
    except ResearchBoundaryViolation as exc:
        assert exc.details["error_code"] == "BOUNDARY_VIOLATION"
        assert exc.details["blocked_domain"] == "financial_advice"
    else:
        raise AssertionError("high-risk financial advice brief should be blocked")

    assert not (tmp_path / "sim-risk" / "society" / "progress.json").exists()


def test_runtime_warns_and_audits_persona_category_mismatch(tmp_path, monkeypatch):
    from app.services.consumer import research_boundary

    audit_events = []
    monkeypatch.setenv("SOCIETY_DETERMINISTIC_MODE", "mock")
    monkeypatch.setattr(research_boundary, "audit_event", lambda **event: audit_events.append(event))

    result = ConsumerSocietyRuntime(base_dir=tmp_path).run(
        simulation_id="sim-boundary-warning",
        run_id="run-boundary-warning",
        config=_small_config(),
        persona_pack=load_default_persona_pack(),
        brief_context={
            "product_category": "enterprise SaaS",
            "target_market": "B2B procurement teams",
            "claims": ["Automate internal ticket routing."],
        },
        research_findings=[],
    )

    boundary = result["applicability_boundary"]
    assert boundary["confidence_level"] == "low"
    assert "enterprise SaaS" in boundary["not_recommended_scenarios"]
    assert any(event["event_type"] == "boundary_warning" for event in audit_events)
    stored = tmp_path / "sim-boundary-warning" / "society" / "research_boundary.json"
    assert stored.exists()


def test_report_api_includes_applicability_boundary(monkeypatch):
    from app.api import report as report_module

    app = Flask(__name__)
    app.config.update(TESTING=True, AUTH_BYPASS_IN_TESTING=True)
    app.register_blueprint(report_bp, url_prefix="/api/report")

    boundary = {
        "applicable_categories": ["FMCG"],
        "applicable_markets": ["urban consumers"],
        "confidence_level": "medium",
        "not_recommended_scenarios": ["medical advice", "investment advice"],
    }
    report = Report(
        report_id="report_boundary",
        simulation_id="sim_boundary",
        graph_id="graph_boundary",
        simulation_requirement="consumer test",
        status=ReportStatus.COMPLETED,
        report_context={"applicability_boundary": boundary},
    )

    monkeypatch.setattr(report_module.ReportManager, "get_report", lambda report_id: report)
    monkeypatch.setattr(report_module.ReportAppService, "_build_methodology_page", lambda *args, **kwargs: "methodology")

    payload = app.test_client().get("/api/report/report_boundary").get_json()

    assert payload["applicability_boundary"] == boundary
    assert payload["data"]["applicability_boundary"] == boundary
