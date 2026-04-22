"""Retrieval evidence validator for consumer_test findings."""

from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel


class EvidenceValidationResult(BaseModel):
    finding_id: str
    validation_status: Literal["supported", "weak_support", "insufficient_support"]
    evidence_sufficiency: float
    aligned_snippet_ids: List[str]
    missing_support_reasons: List[str]
    validator_notes: str


def _has_evidence_snippets(finding: Any) -> bool:
    snippets = (
        finding.evidence_snippets
        if hasattr(finding, "evidence_snippets")
        else finding.get("evidence_snippets", [])
    )
    return bool(snippets and any(str(s).strip() for s in snippets))


def _has_snippet_id(finding: Any) -> bool:
    sid = finding.snippet_id if hasattr(finding, "snippet_id") else finding.get("snippet_id", "")
    return bool(sid)


def _has_retrieval_trace(finding: Any) -> bool:
    tid = (
        finding.retrieval_trace_id
        if hasattr(finding, "retrieval_trace_id")
        else finding.get("retrieval_trace_id", "")
    )
    return bool(tid)


def _snippet_id_from_finding(finding: Any) -> str:
    return finding.snippet_id if hasattr(finding, "snippet_id") else finding.get("snippet_id", "")


def _trace_id_from_finding(finding: Any) -> str:
    return (
        finding.retrieval_trace_id
        if hasattr(finding, "retrieval_trace_id")
        else finding.get("retrieval_trace_id", "")
    )


def _evidence_snippets_from_finding(finding: Any) -> List[str]:
    snippets = (
        finding.evidence_snippets
        if hasattr(finding, "evidence_snippets")
        else finding.get("evidence_snippets", [])
    )
    return [s for s in snippets if isinstance(s, str) and s.strip()]


def validate_finding(
    finding: Any,
    traces: Optional[List[Any]] = None,
    chunks: Optional[List[Any]] = None,
) -> EvidenceValidationResult:
    """Validate whether a finding is supported by its cited evidence."""
    finding_id = finding.finding_id if hasattr(finding, "finding_id") else finding.get("finding_id", "")

    has_snippets = _has_evidence_snippets(finding)
    has_snippet_id = _has_snippet_id(finding)
    has_trace = _has_retrieval_trace(finding)

    trace_by_id: Dict[str, Any] = {}
    if traces:
        for t in traces:
            tid = t.trace_id if hasattr(t, "trace_id") else t.get("trace_id", "")
            if tid:
                trace_by_id[tid] = t

    chunk_by_id: Dict[str, Any] = {}
    if chunks:
        for c in chunks:
            cid = c.chunk_id if hasattr(c, "chunk_id") else c.get("chunk_id", "")
            if cid:
                chunk_by_id[cid] = c

    snippet_id = _snippet_id_from_finding(finding)
    trace_id = _trace_id_from_finding(finding)
    evidence_snippets = _evidence_snippets_from_finding(finding)

    aligned_snippet_ids: List[str] = []
    missing_support_reasons: List[str] = []

    # Check snippet alignment
    if has_snippet_id and snippet_id in chunk_by_id:
        aligned_snippet_ids.append(snippet_id)
    elif has_snippet_id and snippet_id not in chunk_by_id:
        missing_support_reasons.append("referenced_snippet_not_found_in_chunks")

    # Check trace alignment
    trace_aligned = False
    if has_trace and trace_id in trace_by_id:
        trace = trace_by_id[trace_id]
        trace_chunk_ids = trace.chunk_ids if hasattr(trace, "chunk_ids") else trace.get("chunk_ids", [])
        for tcid in trace_chunk_ids:
            if tcid in chunk_by_id:
                trace_aligned = True
                if tcid not in aligned_snippet_ids:
                    aligned_snippet_ids.append(tcid)
    elif has_trace and trace_id not in trace_by_id:
        missing_support_reasons.append("referenced_trace_not_found")

    # Compute evidence sufficiency
    sufficiency = 0.0
    if has_snippets:
        snippet_text = " ".join(evidence_snippets)
        text_score = min(1.0, len(snippet_text) / 200)
        sufficiency += 0.3 * text_score

    if aligned_snippet_ids:
        sufficiency += 0.3 * min(1.0, len(aligned_snippet_ids))

    if has_trace and trace_aligned:
        sufficiency += 0.2

    if has_snippet_id:
        sufficiency += 0.1
    else:
        missing_support_reasons.append("no_snippet_id")

    if not has_trace:
        missing_support_reasons.append("no_retrieval_trace")

    # Determine validation status
    if sufficiency >= 0.6 and trace_aligned:
        validation_status: Literal["supported", "weak_support", "insufficient_support"] = "supported"
    elif sufficiency >= 0.3:
        validation_status = "weak_support"
    else:
        validation_status = "insufficient_support"

    # Build validator notes
    notes_parts: List[str] = []
    notes_parts.append(f"Evidence sufficiency: {round(sufficiency, 2)}")
    notes_parts.append(f"Aligned snippets: {len(aligned_snippet_ids)}")
    if missing_support_reasons:
        notes_parts.append(f"Missing: {', '.join(missing_support_reasons)}")

    return EvidenceValidationResult(
        finding_id=finding_id,
        validation_status=validation_status,
        evidence_sufficiency=round(sufficiency, 4),
        aligned_snippet_ids=aligned_snippet_ids,
        missing_support_reasons=missing_support_reasons,
        validator_notes="; ".join(notes_parts),
    )


def validate_findings(
    findings: List[Any],
    traces: Optional[List[Any]] = None,
    chunks: Optional[List[Any]] = None,
) -> List[EvidenceValidationResult]:
    """Validate a list of findings."""
    return [validate_finding(f, traces=traces, chunks=chunks) for f in findings]


def build_evidence_validation_summary(results: List[EvidenceValidationResult]) -> Dict[str, Any]:
    """Build a machine-readable summary of validation results."""
    if not results:
        return {
            "finding_count": 0,
            "supported_count": 0,
            "weak_support_count": 0,
            "insufficient_support_count": 0,
            "average_evidence_sufficiency": 0.0,
        }

    status_counts: Dict[str, int] = {"supported": 0, "weak_support": 0, "insufficient_support": 0}
    for r in results:
        status_counts[r.validation_status] = status_counts.get(r.validation_status, 0) + 1

    avg_sufficiency = sum(r.evidence_sufficiency for r in results) / len(results)

    return {
        "finding_count": len(results),
        "supported_count": status_counts.get("supported", 0),
        "weak_support_count": status_counts.get("weak_support", 0),
        "insufficient_support_count": status_counts.get("insufficient_support", 0),
        "average_evidence_sufficiency": round(avg_sufficiency, 4),
    }
