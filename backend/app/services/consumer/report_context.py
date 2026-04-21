"""Consumer report context assembly for Phase 1."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional

from .scoring import ConsumerPhase2Summary, ConsumerScoringService


class ConsumerReportContextBuilder:
    """Build structured report context from consumer round snapshots."""

    def __init__(self, scoring_service: ConsumerScoringService | None = None):
        self.scoring_service = scoring_service or ConsumerScoringService()

    def load_events(self, file_path: str | Path) -> List[Dict[str, Any]]:
        path = Path(file_path)
        if not path.exists():
            return []

        events: List[Dict[str, Any]] = []
        for line in path.read_text(encoding="utf-8").splitlines():
            text = line.strip()
            if not text:
                continue
            events.append(json.loads(text))
        return events

    def build(self, events: Iterable[Mapping[str, Any]]) -> Dict[str, Any]:
        normalized = [self._normalize_event(event) for event in events]
        normalized.sort(key=lambda item: (item["round_num"], str(item["agent_id"])))

        initial_labels = [event["attitude_label"] for event in normalized if event["round_num"] == 0]
        final_labels = list(self._latest_labels(normalized).values())
        summary = self.scoring_service.summarize(initial_labels, final_labels)
        evidence = self.scoring_service.build_evidence_bundle(normalized)

        return {
            "summary": summary.to_dict(),
            "initial_acceptance": summary.initial_acceptance,
            "post_propagation_acceptance": summary.post_propagation_acceptance,
            "attitude_shift_rate": summary.attitude_shift_rate,
            "top_resonance_points": self._top_points(normalized, {"resonance"}),
            "top_risk_points": self._top_points(normalized, {"risk"}),
            "top_misreads": self._top_points(normalized, {"misread", "question"}),
            "representative_voc_quotes": {
                "resonance": evidence.top_resonance_quotes,
                "risk": evidence.top_risk_quotes,
                "misread": evidence.top_misread_quotes,
            },
            "evidence_bundle": evidence.to_dict(),
            "events_count": len(normalized),
        }

    def _normalize_event(self, event: Mapping[str, Any]) -> Dict[str, Any]:
        visible_nodes = event.get("visible_nodes", [])
        if not isinstance(visible_nodes, list):
            visible_nodes = []
        return {
            "round_num": int(event.get("round_num", 0) or 0),
            "agent_id": str(event.get("agent_id", "")).strip(),
            "attitude_label": str(event.get("attitude_label", "neutral")).strip().lower() or "neutral",
            "bucket": str(event.get("bucket", "question")).strip().lower() or "question",
            "engagement": int(event.get("engagement", 0) or 0),
            "quote": str(event.get("quote", "")).strip(),
            "visible_nodes": visible_nodes,
        }

    def _latest_labels(self, events: Iterable[Mapping[str, Any]]) -> Dict[str, str]:
        latest: Dict[str, tuple[int, str]] = {}
        for event in events:
            agent_id = str(event.get("agent_id", "")).strip()
            if not agent_id:
                continue
            round_num = int(event.get("round_num", 0) or 0)
            attitude_label = str(event.get("attitude_label", "neutral")).strip().lower() or "neutral"
            previous = latest.get(agent_id)
            if previous is None or round_num >= previous[0]:
                latest[agent_id] = (round_num, attitude_label)
        return {agent_id: label for agent_id, (_, label) in latest.items()}

    def _top_points(self, events: Iterable[Mapping[str, Any]], buckets: set[str], limit: int = 3) -> List[str]:
        counter = Counter()
        first_seen: Dict[str, int] = {}

        for index, event in enumerate(events):
            if event["bucket"] not in buckets:
                continue
            point = self._extract_point(event)
            if not point:
                continue
            counter[point] += 1
            first_seen.setdefault(point, index)

        ranked = sorted(counter.items(), key=lambda item: (-item[1], first_seen[item[0]], item[0].casefold()))
        return [point for point, _ in ranked[:limit]]

    def _extract_point(self, event: Mapping[str, Any]) -> str:
        visible_nodes = event.get("visible_nodes", [])
        bucket = str(event.get("bucket", "question")).strip().lower()

        preferred_type = "RiskPoint" if bucket == "risk" else None
        if preferred_type:
            for node in visible_nodes:
                if node.get("type") == preferred_type and node.get("text"):
                    return str(node["text"]).strip()

        for node in visible_nodes:
            text = str(node.get("text", "")).strip()
            if text:
                return text

        return str(event.get("quote", "")).strip()


def _build_provenance_summary(
    findings: List[Any],
    traces: List[Any],
) -> Dict[str, Any]:
    """Build a provenance summary from findings and retrieval traces."""
    trace_by_id: Dict[str, Any] = {}
    for t in traces:
        tid = t.trace_id if hasattr(t, "trace_id") else t.get("trace_id", "")
        if tid:
            trace_by_id[tid] = t

    lane_counts: Dict[str, int] = {"lane_a": 0, "lane_b": 0, "unknown": 0}
    provenance_entries: List[Dict[str, Any]] = []

    for f in findings:
        source_label = (
            f.source_label if hasattr(f, "source_label") else f.get("source_label", "")
        )
        trace_id = (
            f.retrieval_trace_id if hasattr(f, "retrieval_trace_id") else f.get("retrieval_trace_id", "")
        )

        if source_label == "public_web":
            lane_counts["lane_b"] += 1
        elif source_label in {"ingested_document", "brief_background"}:
            lane_counts["lane_a"] += 1
        else:
            lane_counts["unknown"] += 1

        entry: Dict[str, Any] = {
            "finding_id": f.finding_id if hasattr(f, "finding_id") else f.get("finding_id", ""),
            "finding_type": f.finding_type if hasattr(f, "finding_type") else f.get("finding_type", ""),
            "source_label": source_label,
            "snippet_id": f.snippet_id if hasattr(f, "snippet_id") else f.get("snippet_id", ""),
            "retrieval_trace_id": trace_id,
        }
        if trace_id and trace_id in trace_by_id:
            trace = trace_by_id[trace_id]
            entry["retrieval_query"] = (
                trace.query if hasattr(trace, "query") else trace.get("query", "")
            )
            entry["retrieval_lane"] = (
                trace.lane if hasattr(trace, "lane") else trace.get("lane", "")
            )
        provenance_entries.append(entry)

    return {
        "lane_counts": lane_counts,
        "trace_count": len(traces),
        "provenanced_finding_count": len(provenance_entries),
        "findings": provenance_entries,
    }


def build_consumer_report_context(
    summary: Any,
    findings: Iterable[Any],
    events: Iterable[Any],
    traces: Optional[Iterable[Any]] = None,
) -> Dict[str, Any]:
    """Build structured report context with causal chains from events and findings.

    Args:
        summary: A ConsumerPhase2Summary or compatible object.
        findings: ResearchFinding objects or dicts.
        events: PropagationEvent objects or dicts.
        traces: Optional RetrievalTrace objects or dicts for provenance enrichment.

    Returns:
        Dict with causal_chains, event_led_reversals, persona_group_signals,
        and optional retrieval_provenance.
    """
    from .models import PropagationEvent, ResearchFinding

    # Normalize events
    typed_events: List[PropagationEvent] = []
    for e in events:
        if isinstance(e, PropagationEvent):
            typed_events.append(e)
        elif isinstance(e, dict):
            typed_events.append(PropagationEvent(**e))

    # Normalize findings
    typed_findings: List[ResearchFinding] = []
    for f in findings:
        if isinstance(f, ResearchFinding):
            typed_findings.append(f)
        elif isinstance(f, dict):
            typed_findings.append(ResearchFinding(**f))

    # Build causal chains: group events by trigger finding
    finding_events: Dict[str, List[str]] = {}
    for event in typed_events:
        for fid in event.trigger_finding_ids:
            finding_events.setdefault(fid, []).append(event.event_id)

    causal_chains: List[Dict[str, Any]] = []
    for finding in typed_findings:
        if finding.finding_id in finding_events:
            related_events = [e for e in typed_events if finding.finding_id in e.trigger_finding_ids]
            causal_chains.append({
                "trigger_finding_ids": [finding.finding_id],
                "finding_type": finding.finding_type,
                "finding_summary": finding.summary,
                "event_ids": finding_events[finding.finding_id],
                "event_types": list({e.event_type for e in related_events}),
            })

    # Event-led attitude reversals
    reversals = [
        {
            "event_id": e.event_id,
            "event_type": e.event_type,
            "actor_id": e.actor_id,
            "round_index": e.round_index,
            "quote": e.supporting_quote,
        }
        for e in typed_events
        if e.event_type in {"misread_amplification", "risk_discovery", "clarification_recovery"}
    ]

    # Persona group amplification/blocking signals
    persona_events: Dict[str, Dict[str, Any]] = {}
    for event in typed_events:
        actor = event.actor_id
        if actor not in persona_events:
            persona_events[actor] = {"amplified": [], "blocked": []}
        if event.event_type in {"positive_relay", "risk_discovery", "misread_amplification"}:
            persona_events[actor]["amplified"].append(event.event_type)
        elif event.event_type in {"skeptical_challenge", "clarification_recovery"}:
            persona_events[actor]["blocked"].append(event.event_type)

    summary_dict = summary.to_dict() if hasattr(summary, "to_dict") else dict(summary)

    context: Dict[str, Any] = {
        "phase2_summary": summary_dict,
        "causal_chains": causal_chains,
        "event_led_reversals": reversals,
        "persona_group_signals": persona_events,
        "trigger_finding_count": len(causal_chains),
        "event_count": len(typed_events),
    }

    if traces is not None:
        typed_traces = []
        for t in traces:
            if hasattr(t, "model_dump"):
                typed_traces.append(t)
            elif isinstance(t, dict):
                from .models import RetrievalTrace
                typed_traces.append(RetrievalTrace(**t))
            else:
                typed_traces.append(t)
        context["retrieval_provenance"] = _build_provenance_summary(typed_findings, typed_traces)
        context["retrieval_traces"] = [
            t.model_dump() if hasattr(t, "model_dump") else dict(t) for t in typed_traces
        ]

    return context


__all__ = ["ConsumerReportContextBuilder", "build_consumer_report_context"]
