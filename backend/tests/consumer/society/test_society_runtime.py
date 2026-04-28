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
    for key, value in result["society_metrics"].items():
        if key != "cascade_depth":
            assert 0.0 <= value <= 1.0
