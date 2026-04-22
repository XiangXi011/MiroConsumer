"""Consumer report context assembly for Phase 1."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional

from .scoring import ConsumerPhase2Summary, ConsumerScoringService


def _build_source_catalog(snapshot: Any) -> List[Dict[str, Any]]:
    """Build a readable source catalog from a research snapshot."""
    from .models import ResearchSnapshot

    if not isinstance(snapshot, ResearchSnapshot):
        return []

    doc_counts: Dict[str, int] = Counter()
    chunk_counts: Dict[str, int] = Counter()
    for doc in snapshot.documents:
        doc_counts[doc.source_id] += 1
    for chunk in snapshot.chunks:
        chunk_counts[chunk.source_id] += 1

    catalog: List[Dict[str, Any]] = []
    for source in snapshot.sources:
        lane_val = source.lane.value if hasattr(source.lane, "value") else str(source.lane)
        type_val = source.source_type.value if hasattr(source.source_type, "value") else str(source.source_type)
        catalog.append({
            "source_id": source.source_id,
            "label": source.label,
            "uri": source.uri,
            "lane": lane_val,
            "source_type": type_val,
            "trust_tier": source.trust_tier,
            "document_count": doc_counts.get(source.source_id, 0),
            "chunk_count": chunk_counts.get(source.source_id, 0),
            "metadata": source.metadata,
        })
    return catalog


def _enrich_finding(
    finding: Any,
    source_by_id: Dict[str, Any],
    chunk_by_id: Dict[str, Any],
) -> Dict[str, Any]:
    """Enrich a finding with readable provenance fields."""
    result: Dict[str, Any] = {
        "finding_id": finding.finding_id if hasattr(finding, "finding_id") else finding.get("finding_id", ""),
        "finding_type": finding.finding_type if hasattr(finding, "finding_type") else finding.get("finding_type", ""),
        "summary": finding.summary if hasattr(finding, "summary") else finding.get("summary", ""),
        "evidence_snippets": (
            finding.evidence_snippets if hasattr(finding, "evidence_snippets") else finding.get("evidence_snippets", [])
        ),
        "source_label": (
            finding.source_label if hasattr(finding, "source_label") else finding.get("source_label", "")
        ),
        "visibility": (
            finding.visibility.value if hasattr(finding, "visibility") and hasattr(finding.visibility, "value")
            else str(finding.visibility) if hasattr(finding, "visibility")
            else finding.get("visibility", "")
        ),
        "confidence": finding.confidence if hasattr(finding, "confidence") else finding.get("confidence", 0),
        "source_id": finding.source_id if hasattr(finding, "source_id") else finding.get("source_id", ""),
        "snippet_id": finding.snippet_id if hasattr(finding, "snippet_id") else finding.get("snippet_id", ""),
        "retrieval_trace_id": (
            finding.retrieval_trace_id if hasattr(finding, "retrieval_trace_id")
            else finding.get("retrieval_trace_id", "")
        ),
    }

    source_id = result["source_id"]
    source = source_by_id.get(source_id) if source_id else None
    if source:
        result["source_title"] = source.label
        result["source_uri"] = source.uri
        result["source_lane"] = (
            source.lane.value if hasattr(source.lane, "value") else str(source.lane)
        )
        result["source_type"] = (
            source.source_type.value if hasattr(source.source_type, "value") else str(source.source_type)
        )
        result["trust_tier"] = source.trust_tier

    preview = ""
    evidence_snippets = result["evidence_snippets"]
    if evidence_snippets:
        preview = evidence_snippets[0]
    elif result["snippet_id"] and result["snippet_id"] in chunk_by_id:
        preview = chunk_by_id[result["snippet_id"]].text
    if preview:
        result["evidence_preview"] = preview[:300] + "..." if len(preview) > 300 else preview

    return result


def _enrich_trace(
    trace: Any,
    chunk_by_id: Dict[str, Any],
    source_by_id: Dict[str, Any],
) -> Dict[str, Any]:
    """Enrich a retrieval trace with readable provenance fields."""
    result: Dict[str, Any] = {
        "trace_id": trace.trace_id if hasattr(trace, "trace_id") else trace.get("trace_id", ""),
        "query": trace.query if hasattr(trace, "query") else trace.get("query", ""),
        "lane": (
            trace.lane.value if hasattr(trace, "lane") and hasattr(trace.lane, "value")
            else str(trace.lane) if hasattr(trace, "lane")
            else trace.get("lane", "")
        ),
        "chunk_ids": trace.chunk_ids if hasattr(trace, "chunk_ids") else trace.get("chunk_ids", []),
        "scores": trace.scores if hasattr(trace, "scores") else trace.get("scores", []),
        "retrieved_at": trace.retrieved_at if hasattr(trace, "retrieved_at") else trace.get("retrieved_at", ""),
    }

    chunk_previews: List[Dict[str, str]] = []
    seen_source_ids: set = set()
    primary_source = None

    chunk_ids = result["chunk_ids"]
    for chunk_id in chunk_ids:
        chunk = chunk_by_id.get(chunk_id)
        if not chunk:
            continue
        text = chunk.text
        preview_text = text[:200] + "..." if len(text) > 200 else text
        chunk_previews.append({"chunk_id": chunk_id, "text_preview": preview_text})
        if chunk.source_id and chunk.source_id not in seen_source_ids:
            seen_source_ids.add(chunk.source_id)
            source = source_by_id.get(chunk.source_id)
            if source and primary_source is None:
                primary_source = source

    if primary_source:
        result["source_title"] = primary_source.label
        result["source_uri"] = primary_source.uri
        result["source_type"] = (
            primary_source.source_type.value if hasattr(primary_source.source_type, "value")
            else str(primary_source.source_type)
        )
        result["trust_tier"] = primary_source.trust_tier

    result["chunk_previews"] = chunk_previews
    result["source_count"] = len(seen_source_ids)

    return result


def enrich_report_context_with_snapshot(
    context: Dict[str, Any],
    findings: Iterable[Any],
    traces: Optional[Iterable[Any]],
    snapshot: Any,
) -> Dict[str, Any]:
    """Enrich report context with readable provenance from a snapshot.

    Args:
        context: The report context dict to enrich in-place.
        findings: ResearchFinding objects or dicts.
        traces: Optional RetrievalTrace objects or dicts.
        snapshot: A ResearchSnapshot object.

    Returns:
        The enriched context dict.
    """
    from .models import ResearchFinding, ResearchSnapshot, RetrievalTrace

    if not isinstance(snapshot, ResearchSnapshot):
        return context

    typed_findings: List[ResearchFinding] = []
    for f in findings:
        if isinstance(f, ResearchFinding):
            typed_findings.append(f)
        elif isinstance(f, dict):
            typed_findings.append(ResearchFinding(**f))

    typed_traces: List[RetrievalTrace] = []
    if traces:
        for t in traces:
            if isinstance(t, RetrievalTrace):
                typed_traces.append(t)
            elif isinstance(t, dict):
                typed_traces.append(RetrievalTrace(**t))
            else:
                typed_traces.append(t)

    source_by_id = {s.source_id: s for s in snapshot.sources}
    chunk_by_id = {c.chunk_id: c for c in snapshot.chunks}

    context["source_catalog"] = _build_source_catalog(snapshot)
    context["enriched_findings"] = [
        _enrich_finding(f, source_by_id, chunk_by_id) for f in typed_findings
    ]
    if typed_traces:
        context["enriched_traces"] = [
            _enrich_trace(t, chunk_by_id, source_by_id) for t in typed_traces
        ]

    return context


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
    snapshot: Optional[Any] = None,
    report_confidence: Optional[Dict[str, Any]] = None,
    evidence_validation_summary: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Build structured report context with causal chains from events and findings.

    Args:
        summary: A ConsumerPhase2Summary or compatible object.
        findings: ResearchFinding objects or dicts.
        events: PropagationEvent objects or dicts.
        traces: Optional RetrievalTrace objects or dicts for provenance enrichment.
        snapshot: Optional ResearchSnapshot for source catalog and provenance enrichment.

    Returns:
        Dict with causal_chains, event_led_reversals, persona_group_signals,
        and optional retrieval_provenance, source_catalog, enriched_findings,
        and enriched_traces.
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
        "cascade_metrics": summary_dict.get("cascade_metrics", {}),
    }

    typed_traces = []
    if traces is not None:
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

    if snapshot is not None:
        enrich_report_context_with_snapshot(
            context, typed_findings, typed_traces or None, snapshot
        )

    # Phase 4A: expose confidence and validation fields when available
    if report_confidence is not None:
        context["report_confidence"] = report_confidence
    if evidence_validation_summary is not None:
        context["evidence_validation_summary"] = evidence_validation_summary

    return context


__all__ = [
    "ConsumerReportContextBuilder",
    "build_consumer_report_context",
    "enrich_report_context_with_snapshot",
]
