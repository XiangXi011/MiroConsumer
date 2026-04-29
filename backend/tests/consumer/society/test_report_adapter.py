from app.services.consumer.society.report_adapter import SocietyReportAdapter
from app.services.consumer.society.population_models import ConsumerSocietyRunConfig, ConsumerSocietySnapshot
from app.services.consumer.society.state_store import SocietyStateStore


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


def test_report_adapter_exposes_reasoning_backend_and_calibration_status(tmp_path):
    store = SocietyStateStore(base_dir=tmp_path)
    simulation_id = "sim-reasoning-summary"
    store.write_config(simulation_id, ConsumerSocietyRunConfig(mode="standard", llm_budget_limit=2))
    config_path = store.society_dir(simulation_id) / "society_config.json"
    config_payload = {
        "mode": "standard",
        "llm_budget_used": 2,
        "reasoning_backend_counts": {"template": 2, "rules": 1},
        "reasoning_calibration_status": "golden_case_not_run",
    }
    config_path.write_text(__import__("json").dumps(config_payload), encoding="utf-8")

    context = SocietyReportAdapter(base_dir=tmp_path).build_report_context(simulation_id)

    summary = context["society_reasoning_summary"]
    assert summary["backend_counts"] == {"template": 2, "rules": 1}
    assert summary["calibration_status"] == "golden_case_not_run"
    assert summary["production_readiness"] == "requires_golden_case_calibration"


def test_report_adapter_counts_reasoning_backends_from_rounds_when_config_lacks_summary(tmp_path):
    store = SocietyStateStore(base_dir=tmp_path)
    simulation_id = "sim-round-reasoning"
    store.write_config(simulation_id, ConsumerSocietyRunConfig(mode="standard"))
    store.write_rounds(
        simulation_id,
        [
            ConsumerSocietySnapshot(
                simulation_id=simulation_id,
                run_id="run-1",
                round_index=0,
                agents_count=2,
                events=[
                    {"event_id": "e1", "reasoning_backend": "template", "llm_invoked": True},
                    {"event_id": "e2", "reasoning_backend": "rules", "llm_invoked": False},
                    {"event_id": "e3", "reasoning_backend": "template", "llm_invoked": True},
                ],
            )
        ],
    )

    context = SocietyReportAdapter(base_dir=tmp_path).build_report_context(simulation_id)

    assert context["society_reasoning_summary"]["backend_counts"] == {"template": 2, "rules": 1}
    assert context["society_reasoning_summary"]["llm_invoked_count"] == 2
