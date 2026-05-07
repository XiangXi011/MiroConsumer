"""ReasoningTrace schema, normalization, and persistence.

Unified trace format for all reasoning backends across society runtime,
focus group, interview, and report generation stages.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Mapping, Optional


@dataclass
class ReasoningTrace:
    """A single reasoning trace entry.

    Attributes:
        reasoning_backend: Which backend produced the reasoning.
            One of: llm, rules, template_fallback, mock.
        llm_invoked: Whether an LLM was actually invoked for this trace.
        source: Which stage produced this trace.
            One of: society_runtime, focus_group, interview, report.
        fallback_reason: Empty when no fallback occurred; otherwise describes
            why fallback happened (e.g. "timeout", "budget_exhausted", "error").
        model: The specific model identifier when llm_invoked is True.
        latency_ms: Latency in milliseconds for the reasoning call.
    """

    reasoning_backend: str = ""
    llm_invoked: bool = False
    source: str = ""
    fallback_reason: str = ""
    model: str = ""
    latency_ms: float = 0.0
    reasoning_summary: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "reasoning_backend": self.reasoning_backend,
            "llm_invoked": self.llm_invoked,
            "source": self.source,
            "fallback_reason": self.fallback_reason,
            "model": self.model,
            "latency_ms": self.latency_ms,
            "reasoning_summary": self.reasoning_summary,
        }

    @classmethod
    def from_dict(cls, d: Mapping[str, Any]) -> "ReasoningTrace":
        raw_llm_invoked = d.get("llm_invoked", False)
        if isinstance(raw_llm_invoked, str):
            llm_invoked = raw_llm_invoked.strip().lower() in {"1", "true", "yes"}
        else:
            llm_invoked = bool(raw_llm_invoked)
        return cls(
            reasoning_backend=str(d.get("reasoning_backend", "")),
            llm_invoked=llm_invoked,
            source=str(d.get("source", "")),
            fallback_reason=str(d.get("fallback_reason", "")),
            model=str(d.get("model", "")),
            latency_ms=float(d.get("latency_ms", 0.0)) if d.get("latency_ms") is not None else 0.0,
            reasoning_summary=str(d.get("reasoning_summary", "")),
        )


# Legacy source markers that map to canonical sources.
_LEGACY_SOURCE_MAP: Dict[str, str] = {
    "llm_moderator": "focus_group",
    "llm_participant": "focus_group",
    "template_moderator": "focus_group",
    "template_participant": "focus_group",
    "template_moderator_fallback": "focus_group",
    "template_participant_fallback": "focus_group",
    "legacy_live_interview": "interview",
    "snapshot_template": "interview",
}

# Legacy reasoning_backend markers that map to canonical backends.
_LEGACY_BACKEND_MAP: Dict[str, str] = {
    "template_llm_fallback": "template_fallback",
    "template_rules_fallback": "template_fallback",
    "template_mock_fallback": "template_fallback",
    "template_moderator_fallback": "template_fallback",
    "template_participant_fallback": "template_fallback",
    "snapshot_template": "template_fallback",
}


def normalize_legacy_trace(raw: Mapping[str, Any]) -> ReasoningTrace:
    """Normalize a raw trace dict into a canonical ReasoningTrace.

    Handles legacy source markers (llm_moderator, llm_participant) and
    legacy backend markers (template_*_fallback) by mapping them to
    canonical values.
    """
    d = dict(raw)
    source = str(d.get("source", ""))
    backend = str(d.get("reasoning_backend", ""))

    d["source"] = _LEGACY_SOURCE_MAP.get(source, source)
    d["reasoning_backend"] = _LEGACY_BACKEND_MAP.get(backend, backend)

    return ReasoningTrace.from_dict(d)


def write_reasoning_traces(
    simulation_dir: str,
    traces: List[Any],
) -> str:
    """Persist reasoning traces to society/reasoning_traces.jsonl.

    Args:
        simulation_dir: The simulation workspace directory.
        traces: List of ReasoningTrace objects or raw dicts.

    Returns:
        The path to the written file.
    """
    path = os.path.join(simulation_dir, "society", "reasoning_traces.jsonl")
    os.makedirs(os.path.dirname(path), exist_ok=True)

    with open(path, "w", encoding="utf-8") as f:
        for t in traces:
            if isinstance(t, ReasoningTrace):
                trace = t
            elif isinstance(t, dict):
                trace = normalize_legacy_trace(t)
            else:
                trace = ReasoningTrace()
            f.write(json.dumps(trace.to_dict(), ensure_ascii=False, sort_keys=True) + "\n")

    return path


def append_reasoning_traces(
    simulation_dir: str,
    traces: Iterable[Any],
) -> str:
    """Append canonical reasoning traces to society/reasoning_traces.jsonl."""
    path = os.path.join(simulation_dir, "society", "reasoning_traces.jsonl")
    os.makedirs(os.path.dirname(path), exist_ok=True)

    with open(path, "a", encoding="utf-8") as f:
        for t in traces:
            if isinstance(t, ReasoningTrace):
                trace = t
            elif isinstance(t, dict):
                trace = normalize_legacy_trace(t)
            else:
                trace = ReasoningTrace()
            f.write(json.dumps(trace.to_dict(), ensure_ascii=False, sort_keys=True) + "\n")

    return path


def read_reasoning_traces(simulation_dir: str) -> List[ReasoningTrace]:
    """Read reasoning traces from society/reasoning_traces.jsonl.

    Returns an empty list if the file does not exist.
    Malformed lines are skipped gracefully.
    """
    path = os.path.join(simulation_dir, "society", "reasoning_traces.jsonl")
    if not os.path.exists(path):
        return []

    traces: List[ReasoningTrace] = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                data = json.loads(line)
                if isinstance(data, dict):
                    traces.append(ReasoningTrace.from_dict(data))
            except (json.JSONDecodeError, TypeError, ValueError):
                continue

    return traces


__all__ = [
    "ReasoningTrace",
    "normalize_legacy_trace",
    "write_reasoning_traces",
    "append_reasoning_traces",
    "read_reasoning_traces",
]
