from app.services.consumer.society.report_adapter import SocietyReportAdapter


def test_report_adapter_loads_empty_shell_when_no_society_files(tmp_path):
    context = SocietyReportAdapter(base_dir=tmp_path).build_report_context("sim-missing")

    assert context["society_mode"] == "quick"
    assert context["society_agents_count"] == 0
    assert context["society_metrics"] == {}
    assert context["representative_agents"] == []


def test_report_adapter_merges_runtime_context():
    context = SocietyReportAdapter().merge_into_context(
        {"existing": True},
        {
            "society_mode": "standard",
            "society_agents_count": 200,
            "society_metrics": {"reach_rate": 0.5},
            "representative_agents": ["a1"],
            "society_event_summary": {"ASK_PROOF": 2},
            "society_risk_summary": {"misread_rate": 0.1},
            "society_purchase_intent_summary": {"purchase_intent_delta": 0.2},
        },
    )

    assert context["existing"] is True
    assert context["society_mode"] == "standard"
    assert context["society_metrics"]["reach_rate"] == 0.5
