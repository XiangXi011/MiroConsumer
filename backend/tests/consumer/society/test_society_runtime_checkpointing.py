import json

from app.services.consumer.society.population_models import ConsumerSocietyRunConfig
from app.services.consumer.society.society_runtime import ConsumerSocietyRuntime


def _config() -> ConsumerSocietyRunConfig:
    return ConsumerSocietyRunConfig(
        mode="standard",
        core_persona_count=2,
        expanded_persona_count=1,
        shadow_agent_count=1,
        max_rounds=1,
        random_seed=4,
        llm_budget_limit=3,
        audit_sample_size=1,
        enabled_channels=["xiaohongshu", "ecommerce_review"],
    )


class OneFailureReasoningEngine:
    def __init__(self):
        self.calls = 0

    def reason(self, *, agent, base_event, brief_context, research_findings, reasoning_mode):
        self.calls += 1
        if self.calls == 1:
            raise TimeoutError("llm timed out")
        event = dict(base_event)
        event["reasoning_backend"] = "llm"
        event["reasoning_method"] = reasoning_mode
        event["llm_invoked"] = True
        event["quote"] = f"{agent.segment} 完成推理"
        return event


def test_runtime_writes_checkpoint_progress_events_errors_and_round_files(tmp_path):
    runtime = ConsumerSocietyRuntime(
        base_dir=tmp_path,
        reasoning_engine=OneFailureReasoningEngine(),
    )

    result = runtime.run(
        simulation_id="sim-checkpoint",
        run_id="run-checkpoint",
        config=_config(),
        persona_pack=[],
        brief_context={
            "product_category": "kitchenware",
            "task_type": "concept_test",
            "claims": ["316不锈钢"],
            "research_goal": "验证卖点传播",
        },
        research_findings=[],
    )

    society_dir = tmp_path / "sim-checkpoint" / "society"
    assert society_dir.exists()
    assert (society_dir / "profile_snapshot.json").exists()
    assert (society_dir / "population.json").exists()
    assert (society_dir / "progress.json").exists()
    assert (society_dir / "runtime_events.jsonl").exists()
    assert (society_dir / "errors.jsonl").exists()
    assert (society_dir / "rounds" / "round_0.json").exists()
    assert (society_dir / "network_topology.json").exists()

    progress = json.loads((society_dir / "progress.json").read_text(encoding="utf-8"))
    assert progress["status"] == "completed_with_errors"
    assert progress["phase"] == "completed"
    assert progress["completed_agents"] == 4
    assert progress["total_agents"] == 4
    assert progress["failed_count"] == 1
    assert progress["template_fallback_count"] >= 1
    assert progress["llm_invoked_count"] >= 1

    runtime_events = (society_dir / "runtime_events.jsonl").read_text(encoding="utf-8")
    errors = (society_dir / "errors.jsonl").read_text(encoding="utf-8")
    assert "agent_reasoning_failed" in runtime_events
    assert "TimeoutError" in runtime_events
    assert "template_fallback" in runtime_events
    assert "llm timed out" in errors
    assert result["society_agents_count"] == 4
    assert result["society_network_summary"]["node_count"] == 4
    assert result["society_network_summary"]["edge_count"] > 0
