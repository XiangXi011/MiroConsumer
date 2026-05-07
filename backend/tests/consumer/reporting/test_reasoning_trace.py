"""ReasoningTrace schema, normalization, and persistence coverage."""

import json
import pytest

from app.services.consumer.reasoning_trace import (
    ReasoningTrace,
    normalize_legacy_trace,
    write_reasoning_traces,
    read_reasoning_traces,
)


class TestReasoningTraceSchema:
    def test_trace_has_all_required_fields(self):
        trace = ReasoningTrace(
            reasoning_backend="llm",
            llm_invoked=True,
            source="society_runtime",
            fallback_reason="",
            model="claude-opus",
            latency_ms=120.5,
        )
        assert trace.reasoning_backend == "llm"
        assert trace.llm_invoked is True
        assert trace.source == "society_runtime"
        assert trace.fallback_reason == ""
        assert trace.model == "claude-opus"
        assert trace.latency_ms == 120.5

    def test_trace_defaults(self):
        trace = ReasoningTrace()
        assert trace.reasoning_backend == ""
        assert trace.llm_invoked is False
        assert trace.source == ""
        assert trace.fallback_reason == ""
        assert trace.model == ""
        assert trace.latency_ms == 0.0

    def test_trace_to_dict(self):
        trace = ReasoningTrace(
            reasoning_backend="rules",
            llm_invoked=False,
            source="focus_group",
            fallback_reason="budget_exhausted",
            model="",
            latency_ms=5.0,
        )
        d = trace.to_dict()
        assert d["reasoning_backend"] == "rules"
        assert d["llm_invoked"] is False
        assert d["source"] == "focus_group"
        assert d["fallback_reason"] == "budget_exhausted"
        assert d["model"] == ""
        assert d["latency_ms"] == 5.0

    def test_trace_from_dict(self):
        d = {
            "reasoning_backend": "template_fallback",
            "llm_invoked": False,
            "source": "interview",
            "fallback_reason": "timeout",
            "model": "",
            "latency_ms": 0.0,
        }
        trace = ReasoningTrace.from_dict(d)
        assert trace.reasoning_backend == "template_fallback"
        assert trace.source == "interview"
        assert trace.fallback_reason == "timeout"

    def test_trace_backend_enum_validation(self):
        # Valid backends
        for backend in ["llm", "rules", "template_fallback", "mock"]:
            trace = ReasoningTrace(reasoning_backend=backend)
            assert trace.reasoning_backend == backend

        # Unknown backend is allowed (no strict enum)
        trace = ReasoningTrace(reasoning_backend="custom_backend")
        assert trace.reasoning_backend == "custom_backend"

    def test_trace_source_enum_validation(self):
        for source in ["society_runtime", "focus_group", "interview", "report"]:
            trace = ReasoningTrace(source=source)
            assert trace.source == source


class TestLegacyNormalization:
    def test_normalize_llm_moderator_to_focus_group(self):
        raw = {
            "reasoning_backend": "llm",
            "llm_invoked": True,
            "source": "llm_moderator",
            "fallback_reason": "",
            "model": "gpt-4",
            "latency_ms": 100.0,
        }
        trace = normalize_legacy_trace(raw)
        assert trace.source == "focus_group"
        assert trace.reasoning_backend == "llm"
        assert trace.llm_invoked is True

    def test_normalize_llm_participant_to_focus_group(self):
        raw = {
            "reasoning_backend": "llm",
            "llm_invoked": True,
            "source": "llm_participant",
            "fallback_reason": "",
            "model": "gpt-4",
            "latency_ms": 80.0,
        }
        trace = normalize_legacy_trace(raw)
        assert trace.source == "focus_group"

    def test_normalize_template_fallback_variants(self):
        for variant in ["template_llm_fallback", "template_rules_fallback", "template_mock_fallback"]:
            raw = {
                "reasoning_backend": variant,
                "llm_invoked": False,
                "source": "society_runtime",
                "fallback_reason": "error",
                "model": "",
                "latency_ms": 0.0,
            }
            trace = normalize_legacy_trace(raw)
            assert trace.reasoning_backend == "template_fallback"
            assert trace.fallback_reason == "error"

    def test_normalize_preserves_society_runtime(self):
        raw = {
            "reasoning_backend": "llm",
            "llm_invoked": True,
            "source": "society_runtime",
            "fallback_reason": "",
            "model": "claude",
            "latency_ms": 50.0,
        }
        trace = normalize_legacy_trace(raw)
        assert trace.source == "society_runtime"
        assert trace.reasoning_backend == "llm"

    def test_normalize_preserves_canonical_focus_group(self):
        raw = {
            "reasoning_backend": "llm",
            "llm_invoked": True,
            "source": "focus_group",
            "fallback_reason": "",
            "model": "claude",
            "latency_ms": 50.0,
        }
        trace = normalize_legacy_trace(raw)
        assert trace.source == "focus_group"

    def test_normalize_unknown_source_passthrough(self):
        raw = {
            "reasoning_backend": "llm",
            "llm_invoked": True,
            "source": "some_custom_source",
            "fallback_reason": "",
            "model": "claude",
            "latency_ms": 50.0,
        }
        trace = normalize_legacy_trace(raw)
        assert trace.source == "some_custom_source"

    def test_normalize_partial_dict(self):
        raw = {"reasoning_backend": "llm", "source": "llm_moderator"}
        trace = normalize_legacy_trace(raw)
        assert trace.source == "focus_group"
        assert trace.llm_invoked is False  # default
        assert trace.latency_ms == 0.0  # default


class TestReasoningTracePersistence:
    def test_write_and_read_traces(self, tmp_path):
        traces = [
            ReasoningTrace(
                reasoning_backend="llm",
                llm_invoked=True,
                source="society_runtime",
                fallback_reason="",
                model="claude-opus",
                latency_ms=120.0,
            ),
            ReasoningTrace(
                reasoning_backend="rules",
                llm_invoked=False,
                source="society_runtime",
                fallback_reason="",
                model="",
                latency_ms=5.0,
            ),
            ReasoningTrace(
                reasoning_backend="template_fallback",
                llm_invoked=False,
                source="society_runtime",
                fallback_reason="timeout",
                model="",
                latency_ms=0.0,
            ),
        ]
        sim_dir = str(tmp_path / "sim")
        path = write_reasoning_traces(sim_dir, traces)
        import os
        assert path.endswith(os.path.join("society", "reasoning_traces.jsonl"))

        loaded = read_reasoning_traces(sim_dir)
        assert len(loaded) == 3
        assert loaded[0].reasoning_backend == "llm"
        assert loaded[0].llm_invoked is True
        assert loaded[1].reasoning_backend == "rules"
        assert loaded[2].fallback_reason == "timeout"

    def test_read_missing_file_returns_empty(self, tmp_path):
        sim_dir = str(tmp_path / "sim")
        loaded = read_reasoning_traces(sim_dir)
        assert loaded == []

    def test_read_malformed_line_skips_gracefully(self, tmp_path):
        sim_dir = tmp_path / "sim" / "society"
        sim_dir.mkdir(parents=True, exist_ok=True)
        path = sim_dir / "reasoning_traces.jsonl"
        with path.open("w", encoding="utf-8") as f:
            f.write(json.dumps({"reasoning_backend": "llm", "source": "society_runtime"}) + "\n")
            f.write("not json\n")
            f.write(json.dumps({"reasoning_backend": "rules", "source": "society_runtime"}) + "\n")

        loaded = read_reasoning_traces(str(tmp_path / "sim"))
        assert len(loaded) == 2
        assert loaded[0].reasoning_backend == "llm"
        assert loaded[1].reasoning_backend == "rules"

    def test_write_traces_normalizes_legacy(self, tmp_path):
        raw_traces = [
            {"reasoning_backend": "llm", "source": "llm_moderator", "llm_invoked": True},
            {"reasoning_backend": "template_llm_fallback", "source": "society_runtime", "llm_invoked": False},
        ]
        sim_dir = str(tmp_path / "sim")
        write_reasoning_traces(sim_dir, raw_traces)

        loaded = read_reasoning_traces(sim_dir)
        assert loaded[0].source == "focus_group"
        assert loaded[1].reasoning_backend == "template_fallback"


class TestTraceCoverageFiltering:
    def test_counts_society_runtime_llm_no_fallback(self):
        traces = [
            ReasoningTrace(reasoning_backend="llm", llm_invoked=True, source="society_runtime", fallback_reason=""),
            ReasoningTrace(reasoning_backend="llm", llm_invoked=True, source="society_runtime", fallback_reason=""),
            ReasoningTrace(reasoning_backend="rules", llm_invoked=False, source="society_runtime", fallback_reason=""),
        ]
        covered = [t for t in traces if t.source == "society_runtime" and t.llm_invoked and t.fallback_reason == ""]
        assert len(covered) == 2

    def test_excludes_focus_group_from_coverage(self):
        traces = [
            ReasoningTrace(reasoning_backend="llm", llm_invoked=True, source="society_runtime", fallback_reason=""),
            ReasoningTrace(reasoning_backend="llm", llm_invoked=True, source="focus_group", fallback_reason=""),
        ]
        covered = [t for t in traces if t.source == "society_runtime" and t.llm_invoked and t.fallback_reason == ""]
        assert len(covered) == 1

    def test_excludes_interview_from_coverage(self):
        traces = [
            ReasoningTrace(reasoning_backend="llm", llm_invoked=True, source="interview", fallback_reason=""),
        ]
        covered = [t for t in traces if t.source == "society_runtime" and t.llm_invoked and t.fallback_reason == ""]
        assert len(covered) == 0

    def test_excludes_report_from_coverage(self):
        traces = [
            ReasoningTrace(reasoning_backend="llm", llm_invoked=True, source="report", fallback_reason=""),
        ]
        covered = [t for t in traces if t.source == "society_runtime" and t.llm_invoked and t.fallback_reason == ""]
        assert len(covered) == 0

    def test_excludes_traces_with_fallback_reason(self):
        traces = [
            ReasoningTrace(reasoning_backend="llm", llm_invoked=True, source="society_runtime", fallback_reason="timeout"),
        ]
        covered = [t for t in traces if t.source == "society_runtime" and t.llm_invoked and t.fallback_reason == ""]
        assert len(covered) == 0

    def test_excludes_non_llm_invoked(self):
        traces = [
            ReasoningTrace(reasoning_backend="rules", llm_invoked=False, source="society_runtime", fallback_reason=""),
        ]
        covered = [t for t in traces if t.source == "society_runtime" and t.llm_invoked and t.fallback_reason == ""]
        assert len(covered) == 0
