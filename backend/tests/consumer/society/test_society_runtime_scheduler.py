"""Tests for Phase7H runtime scheduler compatibility shell."""

from __future__ import annotations

import json
import time
from typing import Any, Dict, List
from unittest.mock import MagicMock

import pytest

from app.services.consumer.society.agent_step_executor import AgentStepExecutor
from app.services.consumer.society.population_models import (
    ConsumerSocietyAgent,
    ConsumerSocietyRunConfig,
)
from app.services.consumer.society.progress_buffer import ProgressBuffer
from app.services.consumer.society.round_scheduler import RoundScheduler
from app.services.consumer.society.run_controller import RunController
from app.services.consumer.society.society_runtime import ConsumerSocietyRuntime
from app.services.consumer.society.state_store import SocietyStateStore


class FakeStore:
    """Minimal fake store for ProgressBuffer tests."""

    def __init__(self):
        self.progress_writes: List[Dict[str, Any]] = []

    def write_progress(self, simulation_id: str, progress: dict) -> None:
        self.progress_writes.append({"simulation_id": simulation_id, "progress": dict(progress)})


def _progress_base() -> dict:
    return {
        "status": "running",
        "phase": "agent_reasoning",
        "simulation_id": "sim-test",
        "run_id": "run-test",
        "mode": "standard",
        "current_round": 0,
        "total_rounds": 2,
        "completed_agents": 0,
        "total_agents": 8,
        "current_agent_id": "",
        "current_layer": "",
        "reasoning_backend": "",
        "llm_invoked_count": 0,
        "rules_count": 0,
        "template_fallback_count": 0,
        "failed_count": 0,
        "started_at": "2024-01-01T00:00:00",
        "updated_at": "2024-01-01T00:00:00",
    }


def test_progress_buffer_flushes_every_8_steps():
    store = FakeStore()
    buf = ProgressBuffer(store, "sim-test", _progress_base())

    for i in range(7):
        buf.step_completed(completed_agents=i + 1)
    assert len(store.progress_writes) == 0

    buf.step_completed(completed_agents=8)
    assert len(store.progress_writes) == 1
    assert store.progress_writes[0]["progress"]["completed_agents"] == 8


def test_progress_buffer_flushes_on_time_interval():
    store = FakeStore()
    buf = ProgressBuffer(store, "sim-test", _progress_base(), flush_interval_seconds=0.05)

    buf.step_completed(completed_agents=1)
    assert len(store.progress_writes) == 0

    time.sleep(0.07)
    buf.maybe_time_flush()
    assert len(store.progress_writes) == 1
    assert store.progress_writes[0]["progress"]["completed_agents"] == 1


def test_progress_buffer_flushes_on_final():
    store = FakeStore()
    buf = ProgressBuffer(store, "sim-test", _progress_base())

    buf.step_completed(completed_agents=1)
    assert len(store.progress_writes) == 0

    buf.final(status="completed", completed_agents=4)
    assert len(store.progress_writes) == 1
    assert store.progress_writes[0]["progress"]["status"] == "completed"
    assert store.progress_writes[0]["progress"]["phase"] == "completed"


def test_progress_buffer_flushes_on_final_failed():
    store = FakeStore()
    buf = ProgressBuffer(store, "sim-test", _progress_base())

    buf.final(status="failed", completed_agents=2, failed_count=1)
    assert len(store.progress_writes) == 1
    assert store.progress_writes[0]["progress"]["status"] == "failed"


def test_progress_buffer_flushes_on_final_cancelled():
    store = FakeStore()
    buf = ProgressBuffer(store, "sim-test", _progress_base())

    buf.final(status="cancelled", completed_agents=0)
    assert len(store.progress_writes) == 1
    assert store.progress_writes[0]["progress"]["status"] == "cancelled"


def test_progress_buffer_multiple_step_flushes():
    store = FakeStore()
    buf = ProgressBuffer(store, "sim-test", _progress_base())

    for i in range(20):
        buf.step_completed(completed_agents=i + 1)

    # Should flush at 8, 16, and the 20th step doesn't trigger (no auto flush after last)
    assert len(store.progress_writes) == 2
    assert store.progress_writes[0]["progress"]["completed_agents"] == 8
    assert store.progress_writes[1]["progress"]["completed_agents"] == 16


class FakeEventMapper:
    def map_agent_event(self, *, agent, round_index, visible_claims, previous_events, brief_context, research_findings):
        return {
            "event_id": f"{agent.agent_id}:r{round_index}:FIRST_IMPRESSION",
            "round_index": round_index,
            "agent_id": agent.agent_id,
            "segment": agent.segment,
            "role": agent.role.value,
            "layer": agent.layer,
            "consumer_event_type": "FIRST_IMPRESSION",
            "claim": "test claim",
            "trust": 0.5,
            "purchase_intent": 0.5,
            "quote": "test quote",
        }


class FakeReasoningEngine:
    def reason(self, *, agent, base_event, brief_context, research_findings, reasoning_mode):
        event = dict(base_event)
        event["reasoning_backend"] = "llm"
        event["reasoning_method"] = reasoning_mode
        event["llm_invoked"] = True
        event["quote"] = f"{agent.layer} reasoned"
        return event


class SlowReasoningEngine:
    def __init__(self, sleep_seconds: float = 0.08):
        self.sleep_seconds = sleep_seconds

    def reason(self, *, agent, base_event, brief_context, research_findings, reasoning_mode):
        time.sleep(self.sleep_seconds)
        event = dict(base_event)
        event["reasoning_backend"] = "llm"
        event["reasoning_method"] = reasoning_mode
        event["llm_invoked"] = True
        event["quote"] = f"{agent.agent_id} reasoned"
        return event


class FakeBudgetManager:
    def __init__(self):
        self.used_llm_calls = 0

    def record_llm_call(self, layer: str) -> bool:
        if layer == "shadow":
            return False
        self.used_llm_calls += 1
        return True


def _make_agent(agent_id: str, layer: str) -> ConsumerSocietyAgent:
    from app.services.consumer.society.consumer_roles import ConsumerRole
    return ConsumerSocietyAgent(
        agent_id=agent_id,
        parent_persona_id="p1",
        layer=layer,
        segment="segment",
        role=ConsumerRole.Lurker,
    )


def test_agent_step_executor_exposes_max_concurrency():
    store = MagicMock()
    executor = AgentStepExecutor(FakeEventMapper(), FakeReasoningEngine(), store, "sim")
    assert executor.max_concurrency == 8

    executor_custom = AgentStepExecutor(FakeEventMapper(), FakeReasoningEngine(), store, "sim", max_concurrency=4)
    assert executor_custom.max_concurrency == 4


def test_agent_step_executor_core_uses_llm():
    store = MagicMock()
    executor = AgentStepExecutor(FakeEventMapper(), FakeReasoningEngine(), store, "sim")
    agent = _make_agent("a1", "core")
    budget = FakeBudgetManager()

    event, trace = executor.execute(agent, 0, [], {}, [], [], budget)
    assert event["reasoning_backend"] == "llm"
    assert event["llm_invoked"] is True
    assert trace.llm_invoked is True


def test_agent_step_executor_shadow_uses_rules():
    store = MagicMock()
    executor = AgentStepExecutor(FakeEventMapper(), FakeReasoningEngine(), store, "sim")
    agent = _make_agent("a1", "shadow")
    budget = FakeBudgetManager()

    event, trace = executor.execute(agent, 0, [], {}, [], [], budget)
    assert event["reasoning_backend"] == "rules"
    assert event["llm_invoked"] is False
    assert trace.llm_invoked is False


def test_agent_step_executor_shadow_batch_no_llm():
    store = MagicMock()
    executor = AgentStepExecutor(FakeEventMapper(), FakeReasoningEngine(), store, "sim")
    agents = [_make_agent(f"s{i}", "shadow") for i in range(3)]

    events, traces = executor.execute_shadow_batch(agents, 0, [], {}, [], [])
    assert len(events) == 3
    assert len(traces) == 1
    assert traces[0].reasoning_backend == "rules"
    assert traces[0].source == "society_runtime"
    assert "3" in traces[0].reasoning_summary
    for event in events:
        assert event["reasoning_backend"] == "rules"
        assert event["llm_invoked"] is False
    assert traces[0].llm_invoked is False
    # No LLM calls should have been made
    store.append_runtime_event.assert_called()


def test_round_scheduler_orders_core_before_expanded_before_shadow():
    store = MagicMock()
    executor = AgentStepExecutor(FakeEventMapper(), FakeReasoningEngine(), store, "sim")
    population = [
        _make_agent("shadow1", "shadow"),
        _make_agent("core1", "core"),
        _make_agent("expanded1", "expanded"),
        _make_agent("core2", "core"),
        _make_agent("shadow2", "shadow"),
    ]
    config = ConsumerSocietyRunConfig(
        mode="standard",
        core_persona_count=2,
        expanded_persona_count=1,
        shadow_agent_count=2,
        max_rounds=1,
    )
    scheduler = RoundScheduler(executor, population, config)
    progress = MagicMock()
    budget = FakeBudgetManager()
    counters = {"completed_agents": 0, "failed_count": 0, "template_fallback_count": 0, "llm_invoked_count": 0, "rules_count": 0}

    round_events, traces = scheduler.run_round(0, [], {}, [], [], budget, progress, counters)

    # Core agents should come first
    assert round_events[0]["layer"] == "core"
    assert round_events[1]["layer"] == "core"
    # Then expanded
    assert round_events[2]["layer"] == "expanded"
    # Then shadow
    assert round_events[3]["layer"] == "shadow"
    assert round_events[4]["layer"] == "shadow"


def test_round_scheduler_runs_expanded_with_bounded_concurrency():
    store = MagicMock()
    executor = AgentStepExecutor(
        FakeEventMapper(),
        SlowReasoningEngine(sleep_seconds=0.08),
        store,
        "sim",
        max_concurrency=2,
    )
    population = [_make_agent(f"expanded{i}", "expanded") for i in range(4)]
    config = ConsumerSocietyRunConfig(
        mode="standard",
        core_persona_count=0,
        expanded_persona_count=4,
        shadow_agent_count=0,
        max_rounds=1,
        llm_budget_limit=4,
    )
    scheduler = RoundScheduler(executor, population, config)
    progress = MagicMock()
    budget = FakeBudgetManager()
    counters = {
        "completed_agents": 0,
        "failed_count": 0,
        "template_fallback_count": 0,
        "llm_invoked_count": 0,
        "rules_count": 0,
    }

    started = time.monotonic()
    round_events, traces = scheduler.run_round(0, [], {}, [], [], budget, progress, counters)
    elapsed = time.monotonic() - started

    assert elapsed < 0.28
    assert [event["agent_id"] for event in round_events] == [
        "expanded0",
        "expanded1",
        "expanded2",
        "expanded3",
    ]
    assert len(traces) == 4
    assert counters["llm_invoked_count"] == 4


def test_runtime_delegates_to_run_controller_preserving_signature(tmp_path):
    """ConsumerSocietyRuntime.run delegates to RunController without changing public signature."""
    runtime = ConsumerSocietyRuntime(base_dir=tmp_path)

    config = ConsumerSocietyRunConfig(
        mode="quick",
        core_persona_count=2,
        expanded_persona_count=1,
        shadow_agent_count=1,
        max_rounds=1,
        random_seed=42,
        llm_budget_limit=10,
        audit_sample_size=1,
    )

    result = runtime.run(
        simulation_id="sim-delegate",
        run_id="run-delegate",
        config=config,
        persona_pack=[],
        brief_context={"claims": ["test claim"]},
        research_findings=[],
    )

    # Verify all artifacts are preserved
    society_dir = tmp_path / "sim-delegate" / "society"
    assert society_dir.exists()
    assert (society_dir / "progress.json").exists()
    assert (society_dir / "runtime_events.jsonl").exists()
    assert (society_dir / "rounds" / "round_0.json").exists()

    progress = json.loads((society_dir / "progress.json").read_text(encoding="utf-8"))
    assert progress["status"] in {"completed", "completed_with_errors"}
    assert progress["phase"] == "completed"

    # Verify runtime_events.jsonl has agent_completed entries
    events = (society_dir / "runtime_events.jsonl").read_text(encoding="utf-8").strip().split("\n")
    assert len(events) >= 4  # at least 4 agents completed

    # Verify result shape (report context)
    assert "society_agents_count" in result
    assert result["society_agents_count"] == 4


def test_run_controller_end_to_end_with_failure(tmp_path):
    """RunController handles reasoning failures like the original runtime."""

    class FailingEngine:
        def __init__(self):
            self.calls = 0

        def reason(self, *, agent, base_event, brief_context, research_findings, reasoning_mode):
            self.calls += 1
            if self.calls == 1:
                raise TimeoutError("llm timed out")
            event = dict(base_event)
            event["reasoning_backend"] = "llm"
            event["llm_invoked"] = True
            return event

    runtime = ConsumerSocietyRuntime(
        base_dir=tmp_path,
        reasoning_engine=FailingEngine(),
    )
    config = ConsumerSocietyRunConfig(
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

    result = runtime.run(
        simulation_id="sim-ctrl-fail",
        run_id="run-ctrl-fail",
        config=config,
        persona_pack=[],
        brief_context={
            "product_category": "kitchenware",
            "task_type": "concept_test",
            "claims": ["316不锈钢"],
            "research_goal": "验证卖点传播",
        },
        research_findings=[],
    )

    society_dir = tmp_path / "sim-ctrl-fail" / "society"
    progress = json.loads((society_dir / "progress.json").read_text(encoding="utf-8"))
    assert progress["status"] == "completed_with_errors"
    assert progress["failed_count"] == 1
    assert progress["template_fallback_count"] >= 1
    assert progress["llm_invoked_count"] >= 1

    runtime_events = (society_dir / "runtime_events.jsonl").read_text(encoding="utf-8")
    errors = (society_dir / "errors.jsonl").read_text(encoding="utf-8")
    assert "agent_reasoning_failed" in runtime_events
    assert "TimeoutError" in runtime_events
    assert result["society_agents_count"] == 4


def test_progress_buffer_preserves_progress_state_between_flushes():
    store = FakeStore()
    base = _progress_base()
    buf = ProgressBuffer(store, "sim-test", base)

    buf.step_completed(completed_agents=1, llm_invoked_count=1)
    buf.step_completed(completed_agents=2, rules_count=1)
    buf.flush()

    assert len(store.progress_writes) == 1
    written = store.progress_writes[0]["progress"]
    assert written["completed_agents"] == 2
    assert written["llm_invoked_count"] == 1
    assert written["rules_count"] == 1
    # Original base keys should still be present
    assert written["simulation_id"] == "sim-test"
    assert written["status"] == "running"
