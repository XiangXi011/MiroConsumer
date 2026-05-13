from __future__ import annotations

import json
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app import create_app
from app.config import Config
from app.services.consumer.experiment.doe import ExperimentDesigner
from app.services.consumer.experiment.enterprise_runtime import (
    EnterpriseExperimentRuntime,
    ExperimentGroupPlan,
)
from app.services.consumer.persona_pack_registry import PersonaPackRegistry
from app.services.consumer.society.branch_manager import BranchManager
from app.services.consumer.society.consumer_roles import ConsumerRole
from app.services.consumer.society.intervention import InterventionEngine
from app.services.consumer.society.population_models import ConsumerSocietyAgent
from app.services.consumer.society.reasoning_engine import LayeredSocietyReasoningEngine
from app.services.consumer.society.state_store import PostgreSQLStateStore
from app.repositories.sqlalchemy import graph_snapshots, metadata
from app.utils.error_codes import ErrorCode, error_payload


class _RuntimeConfig(Config):
    TESTING = True
    DEBUG = True
    SECRET_KEY = "runtime-spec-secret-key-that-is-long-enough-32"
    JWT_SECRET_KEY = "runtime-spec-jwt-secret-key-that-is-long-enough-32"
    CORS_ALLOWED_ORIGINS = "http://localhost:3000"
    CORS_ALLOW_ORIGINS = "http://localhost:3000"
    LOG_FORMAT = "text"
    _db_url_cache = ""
    _queue_backend_cache = "thread"

    @classmethod
    def validate(cls):
        return []


def _persona_payload(persona_id: str = "p1") -> dict:
    return {
        "persona_id": persona_id,
        "label": "Pragmatic parent",
        "attention_drivers": ["price", "health"],
        "risk_sensitivities": ["sugar"],
        "expression_style": "plainspoken",
        "search_propensity": "medium",
        "cognition_level": "medium",
        "herd_tendency": "medium",
        "influence_weight": 0.4,
        "demographics": {"income_level": "middle"},
        "psychographics": {"price_sensitivity": "medium"},
        "version": 1,
    }


def test_p3_026_error_codes_are_global_and_api_errors_are_normalized() -> None:
    assert len(list(ErrorCode)) >= 20
    payload = error_payload(
        ErrorCode.BRIEF_VALIDATION_FAILED,
        field="price_points",
        message="Invalid price ladder",
    )
    assert payload["error_code"] == "BRIEF_VALIDATION_FAILED"
    assert payload["error_message"] == "Invalid price ladder"
    assert payload["field"] == "price_points"
    assert payload["suggestion"]

    api_dir = Path(__file__).resolve().parents[2] / "app" / "api"
    raw_get_json = [
        path for path in api_dir.rglob("*.py")
        if "request.get_json(" in path.read_text(encoding="utf-8")
    ]
    assert raw_get_json == []

    app = create_app(_RuntimeConfig)

    @app.route("/api/manual-error")
    def manual_error():
        return {"success": False, "error": "manual failure"}, 400

    response = app.test_client().get("/api/manual-error")
    data = response.get_json()
    assert data["error_code"] == "INVALID_REQUEST"
    assert data["error_message"] == "manual failure"
    assert data["suggestion"]


def test_p3_027_persona_pack_patch_updates_fields_and_audit_log(tmp_path: Path) -> None:
    registry = PersonaPackRegistry(project_persona_dir=tmp_path)
    registry.register_custom_pack(
        json.dumps([_persona_payload()], ensure_ascii=False),
        pack_id="custom_pack",
        label="Custom Pack",
    )

    result = registry.patch_persona(
        "custom_pack",
        "p1",
        {"demographics": {"income_level": "upper_middle"}},
    )

    assert result["persona_id"] == "p1"
    assert result["demographics"]["income_level"] == "upper_middle"
    assert result["psychographics"]["price_sensitivity"] == "medium"
    assert result["version"] == 2
    assert result["updated_at"]

    history = registry.list_persona_audit_log("custom_pack", "p1")
    assert history[-1]["changed_fields"] == ["demographics.income_level"]
    assert history[-1]["version_after"] == 2


def test_p3_028_enterprise_runtime_isolates_groups_and_aggregates_results() -> None:
    runtime = EnterpriseExperimentRuntime(max_parallel_groups=3)
    groups = [
        ExperimentGroupPlan(group_id="g1", llm_budget_quota=10, parameters={"price": 9.9}),
        ExperimentGroupPlan(group_id="g2", llm_budget_quota=10, parameters={"price": 12.9}),
        ExperimentGroupPlan(group_id="g3", llm_budget_quota=10, parameters={"price": 15.9}),
    ]

    def runner(group: ExperimentGroupPlan, state: dict) -> dict:
        state["agent_a"] = {"attitude": group.parameters["price"]}
        return {
            "acceptance_rate": 1.0 - group.parameters["price"] / 20.0,
            "purchase_intent": 1.0 - group.parameters["price"] / 25.0,
            "state": state,
        }

    results = runtime.run_groups(groups, runner)
    assert len({item["state_isolation_key"] for item in results}) == 3
    assert all(item["llm_budget_quota"] == 10 for item in results)
    assert results[0]["state"]["agent_a"]["attitude"] != results[1]["state"]["agent_a"]["attitude"]

    aggregate = runtime.aggregate_results(results, objective_metric="acceptance_rate")
    assert aggregate["best_group_id"] == "g1"
    assert "anova" in aggregate["statistical_tests"]
    assert aggregate["recommended_parameters"]["price"] == 9.9

    sequential = ExperimentDesigner().create_sequential_design(
        name="price sequence",
        prior_results=results,
        candidate_parameters=[{"price": 8.9}, {"price": 10.9}],
        objective_metric="acceptance_rate",
    )
    assert sequential.metadata["sequential"] is True
    assert sequential.metadata["next_candidate"]["price"] == 8.9


def test_p3_029_graph_snapshot_persists_and_resumes_from_checkpoint() -> None:
    engine = create_engine("sqlite:///:memory:")
    metadata.create_all(engine)
    store = PostgreSQLStateStore(sessionmaker(bind=engine))

    assert graph_snapshots.name == "graph_snapshots"
    store.write_graph_snapshot("sim_1", 0, {"nodes": ["a"], "edges": []})
    store.write_graph_snapshot("sim_1", 1, {"nodes": ["a", "b"], "edges": ["a:b"]})

    restarted_store = PostgreSQLStateStore(sessionmaker(bind=engine))
    latest = restarted_store.resume_from_checkpoint("sim_1")
    assert latest["round_index"] == 1
    assert latest["snapshot_data"]["nodes"] == ["a", "b"]
    assert restarted_store.read_graph_snapshot("sim_1", 0)["snapshot_data"]["nodes"] == ["a"]


def test_p3_030_reasoning_engine_partial_retry_then_success(monkeypatch) -> None:
    monkeypatch.setenv("SOCIETY_REASONING_BACKEND", "llm")
    attempts: list[int] = []
    waits: list[float] = []

    class FlakyClient:
        def chat_json(self, **_kwargs):
            attempts.append(1)
            if len(attempts) < 3:
                raise TimeoutError("temporary timeout")
            return {
                "consumer_event_type": "resonance",
                "quote": "This is worth trying.",
                "trust": 0.7,
                "purchase_intent": 0.8,
                "reasoning_summary": "Recovered after retry",
            }

    engine = LayeredSocietyReasoningEngine(
        llm_client_factory=lambda: FlakyClient(),
        llm_max_retries=3,
        llm_retry_backoff_base=1.0,
        sleep_fn=waits.append,
    )
    agent = ConsumerSocietyAgent(
        agent_id="a1",
        parent_persona_id="p1",
        layer="core",
        segment="value seekers",
        role=ConsumerRole.Advocate,
    )

    event = engine.reason(
        agent=agent,
        base_event={"claim": "14g protein", "consumer_event_type": "resonance"},
        brief_context={},
        research_findings=[],
        reasoning_mode="lightweight_llm",
    )

    assert len(attempts) == 3
    assert waits == [1.0, 2.0]
    assert event["reasoning_backend"] == "llm"
    assert event["retry_attempts"] == 2
    assert event["fallback_reason"] == "llm_retry_recovered"


def test_p3_030_reasoning_engine_partial_retry_exhausts_to_template(monkeypatch) -> None:
    monkeypatch.setenv("SOCIETY_REASONING_BACKEND", "llm")
    waits: list[float] = []

    class TimeoutClient:
        def chat_json(self, **_kwargs):
            raise TimeoutError("provider timeout")

    engine = LayeredSocietyReasoningEngine(
        llm_client_factory=lambda: TimeoutClient(),
        llm_max_retries=3,
        llm_retry_backoff_base=1.0,
        sleep_fn=waits.append,
    )
    agent = ConsumerSocietyAgent(
        agent_id="a2",
        parent_persona_id="p1",
        layer="core",
        segment="skeptics",
        role=ConsumerRole.Skeptic,
    )

    event = engine.reason(
        agent=agent,
        base_event={"claim": "low sugar", "consumer_event_type": "risk"},
        brief_context={},
        research_findings=[],
        reasoning_mode="lightweight_llm",
    )

    assert waits == [1.0, 2.0]
    assert event["reasoning_backend"] == "template_fallback"
    assert event["retry_attempts"] == 3
    assert event["fallback_reason"] == "llm_retry_exhausted"
    assert "provider timeout" in event["reasoning_error"]


def test_p3_031_branch_diff_covers_four_dimensions() -> None:
    manager = BranchManager()
    left = {
        "branch_id": "left",
        "events": [
            {"event_id": "e1", "agent_id": "a1", "attitude": 0.2, "quote": "Too sweet", "confidence_score": 0.6},
        ],
    }
    right = {
        "branch_id": "right",
        "events": [
            {"event_id": "e1", "agent_id": "a1", "attitude": 0.7, "quote": "Balanced protein", "confidence_score": 0.8},
            {"event_id": "e2", "agent_id": "a2", "attitude": 0.5, "quote": "I would share it", "confidence_score": 0.7},
        ],
    }

    empty = manager.diff_branches(left, left)
    assert empty["is_empty"] is True

    diff = manager.diff_branches(left, right)
    assert diff["is_empty"] is False
    assert diff["attitude_delta"]["a1"] == pytest.approx(0.5)
    assert diff["event_delta"]["added_event_ids"] == ["e2"]
    assert "balanced" in diff["voc_delta"]["right_keywords"]
    assert diff["confidence_delta"]["average_delta"] == pytest.approx(0.15)


def test_p3_032_intervention_replay_round_trip_and_delta() -> None:
    engine = InterventionEngine()
    sequence = engine.record_intervention(
        [],
        target="claim.low_sugar",
        round_index=1,
        parameters={"message": "Low sugar, no compromise"},
    )
    sequence = engine.record_intervention(
        sequence,
        target="price",
        round_index=2,
        parameters={"value": 12.9},
    )

    initial_state = {"claim": {"low_sugar": "Low sugar"}, "price": 14.9}
    replay = engine.replay(initial_state, sequence)
    assert replay["final_state"]["price"] == 12.9
    assert replay["applied_count"] == 2

    sensitivity = engine.replay(
        initial_state,
        sequence,
        parameter_overrides={sequence[1]["intervention_id"]: {"value": 10.9}},
    )
    assert sensitivity["final_state"]["price"] == 10.9
    assert sensitivity["delta"]["price"]["after"] == 10.9

    exported = engine.export_sequence(sequence)
    imported = engine.import_sequence(exported)
    assert imported == sequence
