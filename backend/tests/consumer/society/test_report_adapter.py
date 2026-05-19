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


def test_report_adapter_extracts_society_voc_quotes_and_points(tmp_path):
    store = SocietyStateStore(base_dir=tmp_path)
    simulation_id = "sim-society-voc"
    store.write_config(simulation_id, ConsumerSocietyRunConfig(mode="standard"))
    store.write_rounds(
        simulation_id,
        [
            ConsumerSocietySnapshot(
                simulation_id=simulation_id,
                run_id="run-1",
                round_index=0,
                agents_count=4,
                events=[
                    {
                        "event_id": "e1",
                        "agent_id": "a1",
                        "segment": "理性比较型消费者",
                        "consumer_event_type": "FIRST_IMPRESSION",
                        "claim": "7天白4度",
                        "quote": "我第一眼会注意到7天白4度，但还要看场景是否真实。",
                        "purchase_intent": 0.62,
                        "quote_metadata": {"source": "llm", "template_generated": False},
                    },
                    {
                        "event_id": "e2",
                        "agent_id": "a2",
                        "segment": "社交种草型消费者",
                        "consumer_event_type": "ASK_PROOF",
                        "claim": "7天白4度",
                        "quote": "我想看到7天白4度的检测证明，尤其要解释清楚可信度。",
                        "trust": 0.42,
                        "quote_metadata": {"source": "llm", "template_generated": False},
                    },
                    {
                        "event_id": "e3",
                        "agent_id": "a3",
                        "segment": "价格敏感型消费者",
                        "consumer_event_type": "MISREAD_CLAIM",
                        "claim": "7天白4度",
                        "quote": "7天白4度如果说得太满，我可能会误以为是全场景承诺。",
                        "quote_metadata": {"source": "template", "template_generated": True},
                    },
                    {
                        "event_id": "e4",
                        "agent_id": "a4",
                        "segment": "价格敏感型消费者",
                        "consumer_event_type": "PRICE_RESISTANCE",
                        "claim": "7天白4度",
                        "quote": "如果贵太多，我会先和同类产品仔细比价格。",
                        "price_sensitivity": 0.8,
                    },
                ],
            )
        ],
    )

    context = SocietyReportAdapter(base_dir=tmp_path).build_report_context(simulation_id)

    quotes = context["society_representative_voc_quotes"]
    assert quotes["resonance"][0]["quote"].startswith("我第一眼会注意到7天白4度")
    assert quotes["resonance"][0]["quote_metadata"]["template_generated"] is False
    assert quotes["risk"][0]["quote"].startswith("我想看到7天白4度的检测证明")
    assert quotes["misread"][0]["quote"].startswith("7天白4度如果说得太满")
    assert "7天白4度有第一眼记忆点" in context["society_top_resonance_points"][0]
    assert any("检测证明" in point for point in context["society_top_risk_points"])
    assert any("全场景" in point for point in context["society_top_misreads"])
