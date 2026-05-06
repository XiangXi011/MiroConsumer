"""Phase 7D trace logging tests."""


def test_normalize_trace_fields_always_outputs_fixed_10_fields():
    from app.services.application.trace_logging import TRACE_FIELDS, normalize_trace_fields

    fields = normalize_trace_fields({"trace_id": "trace_1", "simulation_id": "sim_1"})

    assert list(fields.keys()) == TRACE_FIELDS
    assert fields["trace_id"] == "trace_1"
    assert fields["simulation_id"] == "sim_1"
    for key in TRACE_FIELDS:
        assert key in fields
        assert fields[key] is not None


def test_trace_events_can_filter_by_trace_run_and_simulation():
    from app.services.application.trace_logging import filter_trace_events

    events = [
        {"trace_id": "t1", "run_id": "r1", "simulation_id": "s1"},
        {"trace_id": "t2", "run_id": "r1", "simulation_id": "s2"},
        {"trace_id": "t1", "run_id": "r2", "simulation_id": "s1"},
    ]

    assert len(filter_trace_events(events, trace_id="t1")) == 2
    assert len(filter_trace_events(events, run_id="r1")) == 2
    assert len(filter_trace_events(events, simulation_id="s1")) == 2
    assert filter_trace_events(events, trace_id="t1", run_id="r2")[0]["run_id"] == "r2"


def test_log_trace_event_returns_structured_application_log(tmp_path):
    from app.services.application.trace_logging import TRACE_FIELDS, TraceLogStore

    store = TraceLogStore(log_path=tmp_path / "trace.jsonl")
    event = store.log_event("budget_blocked", trace_id="t1", simulation_id="s1")

    assert event["event_name"] == "budget_blocked"
    assert list(event["trace"].keys()) == TRACE_FIELDS
    assert event["trace"]["trace_id"] == "t1"
    assert event["trace"]["run_id"] == ""
    assert (tmp_path / "trace.jsonl").exists()
