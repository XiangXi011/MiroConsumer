import json
from pathlib import Path

from app.services.consumer.persona_pack import load_default_persona_pack
from app.services.consumer.society.population_models import ConsumerSocietyRunConfig
from app.services.consumer.society.society_runtime import ConsumerSocietyRuntime


def _config(seed=7) -> ConsumerSocietyRunConfig:
    return ConsumerSocietyRunConfig(
        mode="standard",
        core_persona_count=12,
        expanded_persona_count=40,
        shadow_agent_count=200,
        max_rounds=2,
        random_seed=seed,
        llm_budget_limit=12,
        audit_sample_size=4,
    )


class SpyReasoningEngine:
    def __init__(self):
        self.calls = []

    def reason(
        self,
        *,
        agent,
        base_event,
        brief_context,
        research_findings,
        reasoning_mode,
    ):
        self.calls.append((agent.agent_id, agent.layer, reasoning_mode))
        event = dict(base_event)
        event["quote"] = f"{agent.layer} reasoned about {base_event['claim']}"
        event["reasoning_method"] = reasoning_mode
        return event


def test_society_runtime_mock_mode_is_deterministic(tmp_path, monkeypatch):
    monkeypatch.setenv("SOCIETY_DETERMINISTIC_MODE", "mock")
    runtime = ConsumerSocietyRuntime(base_dir=tmp_path)
    personas = load_default_persona_pack()

    first = runtime.run(
        simulation_id="sim-runtime",
        run_id="run-a",
        config=_config(seed=9),
        persona_pack=personas,
        brief_context={"claims": ["0糖"], "price_points": ["29.9"]},
        research_findings=[],
    )
    second = runtime.run(
        simulation_id="sim-runtime",
        run_id="run-a",
        config=_config(seed=9),
        persona_pack=personas,
        brief_context={"claims": ["0糖"], "price_points": ["29.9"]},
        research_findings=[],
    )

    assert first == second
    society_dir = tmp_path / "sim-runtime" / "society"
    assert (society_dir / "population.json").exists()
    assert (society_dir / "society_config.json").exists()
    assert (society_dir / "society_rounds.jsonl").exists()
    assert (society_dir / "society_metrics.json").exists()

    rounds = [
        json.loads(line)
        for line in (society_dir / "society_rounds.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert len(rounds) == 2
    assert rounds[0]["agents_count"] == 252
    assert "society_metrics" in first


def test_society_runtime_production_mode_schema_ranges(tmp_path, monkeypatch):
    monkeypatch.delenv("SOCIETY_DETERMINISTIC_MODE", raising=False)
    runtime = ConsumerSocietyRuntime(base_dir=tmp_path)
    result = runtime.run(
        simulation_id="sim-prod",
        run_id="run-prod",
        config=_config(seed=10),
        persona_pack=load_default_persona_pack(),
        brief_context={"claims": ["高蛋白"]},
        research_findings=[],
    )

    assert result["society_mode"] == "standard"
    assert result["society_agents_count"] == 252
    assert isinstance(result["society_metrics"], dict)
    convergence = result["society_metrics"]["convergence"]
    assert convergence["stopped"] is False
    assert convergence["reason"] == "max_rounds_completed"
    assert "event_type_distribution_change_rate" in convergence["metrics"]
    assert "community_coverage_ratio" in convergence["metrics"]
    for key, value in result["society_metrics"].items():
        if key not in {"cascade_depth", "convergence"}:
            assert 0.0 <= value <= 1.0


def test_society_runtime_distributes_claims_across_events(tmp_path, monkeypatch):
    monkeypatch.setenv("SOCIETY_DETERMINISTIC_MODE", "mock")
    runtime = ConsumerSocietyRuntime(base_dir=tmp_path)
    claims = ["7天白4度", "一次去黄提亮226%", "冷光修白，以紫修黄", "双专利美白科技"]

    runtime.run(
        simulation_id="sim-claim-diversity",
        run_id="run-claim-diversity",
        config=ConsumerSocietyRunConfig(
            mode="standard",
            core_persona_count=8,
            expanded_persona_count=8,
            shadow_agent_count=8,
            max_rounds=1,
            random_seed=11,
            llm_budget_limit=8,
            audit_sample_size=2,
        ),
        persona_pack=load_default_persona_pack(),
        brief_context={"claims": claims},
        research_findings=[],
    )

    society_dir = tmp_path / "sim-claim-diversity" / "society"
    rounds = [
        json.loads(line)
        for line in (society_dir / "society_rounds.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    event_claims = {
        event.get("claim")
        for snapshot in rounds
        for event in snapshot.get("events", [])
        if event.get("claim")
    }

    assert len(event_claims) > 1
    assert event_claims.issubset(set(claims))


def test_society_runtime_calls_layered_reasoning_for_core_and_expanded_only(tmp_path):
    config = ConsumerSocietyRunConfig(
        mode="standard",
        core_persona_count=2,
        expanded_persona_count=2,
        shadow_agent_count=2,
        max_rounds=1,
        random_seed=42,
        llm_budget_limit=10,
        audit_sample_size=1,
        enabled_channels=["xiaohongshu", "wechat_group", "ecommerce_review"],
        channel_seed=42,
    )
    spy = SpyReasoningEngine()
    runtime = ConsumerSocietyRuntime(base_dir=tmp_path, reasoning_engine=spy)

    runtime.run(
        simulation_id="sim-layered",
        run_id="run-layered",
        config=config,
        persona_pack=load_default_persona_pack(),
        brief_context={"claims": ["low sugar"]},
        research_findings=[],
    )

    called_layers = [layer for _, layer, _ in spy.calls]
    assert called_layers.count("core") == 2
    assert called_layers.count("expanded") == 2
    assert "shadow" not in called_layers

    rounds_path = tmp_path / "sim-layered" / "society" / "society_rounds.jsonl"
    first_round = json.loads(rounds_path.read_text(encoding="utf-8").splitlines()[0])
    reasoned = [event for event in first_round["events"] if event["layer"] in {"core", "expanded"}]
    assert all(event["reasoning_method"] in {"llm_deep_reasoning", "lightweight_llm"} for event in reasoned)
