"""SPEC-P2-024 LLM fallback diagnostics in report responses."""

from __future__ import annotations

from flask import Flask

from app.api import report_bp
from app.services.report_agent import Report, ReportStatus


def _app() -> Flask:
    app = Flask(__name__)
    app.config.update(TESTING=True, AUTH_BYPASS_IN_TESTING=True)
    app.register_blueprint(report_bp, url_prefix="/api/report")
    return app


def test_report_api_exposes_llm_diagnostics_and_quality_warning(monkeypatch):
    from app.api import report as report_module

    report = Report(
        report_id="report_diag",
        simulation_id="sim_diag",
        graph_id="graph_diag",
        simulation_requirement="consumer concept test",
        status=ReportStatus.COMPLETED,
        markdown_content="## Representative quotes\n\n- Existing body",
        report_context={
            "evidence_bundle": {
                "quote_metadata": [
                    {
                        "quote": "LLM quote",
                        "reasoning_backend": "llm",
                        "llm_invoked": True,
                        "quote_metadata": {"template_generated": False},
                    },
                    {
                        "quote": "Template quote",
                        "reasoning_backend": "template_fallback",
                        "llm_invoked": False,
                        "fallback_reason": "timeout",
                        "quote_metadata": {"template_generated": True},
                    },
                    {
                        "quote": "Unknown quote",
                        "reasoning_backend": "unknown",
                    },
                ],
            }
        },
    )

    monkeypatch.setattr(report_module.ReportManager, "get_report", lambda report_id: report)
    monkeypatch.setattr(report_module.ReportAppService, "_build_methodology_page", lambda *args, **kwargs: "methodology")

    response = _app().test_client().get("/api/report/report_diag")

    assert response.status_code == 200
    payload = response.get_json()
    diagnostics = payload["llm_diagnostics"]
    assert diagnostics["llm_coverage_rate"] == 0.3333
    assert diagnostics["template_fallback_rate"] == 0.3333
    assert diagnostics["unknown_rate"] == 0.3333
    assert diagnostics["fallback_reasons"] == ["timeout"]
    assert payload["quality_warning_banner"]["visible"] is True
    assert payload["data"]["llm_diagnostics"] == diagnostics


def test_template_quotes_use_explicit_non_llm_marker():
    from app.services.report_agent import ReportAgent

    agent = ReportAgent(
        graph_id="g1",
        simulation_id="sim_1",
        simulation_requirement="test req",
        llm_client=None,
        zep_tools=None,
        project_type="consumer_test",
    )

    rendered = agent._format_quotes([
        {
            "quote": "Template quote",
            "engagement": 2,
            "quote_metadata": {"template_generated": True},
        }
    ])

    assert "[\u6a21\u62df\u751f\u6210\uff0c\u975eLLM\u63a8\u7406]" in rendered
