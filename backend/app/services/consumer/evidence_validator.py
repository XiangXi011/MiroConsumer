"""Retrieval evidence validator for consumer_test findings."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Literal, Mapping, Optional

from pydantic import BaseModel


class EvidenceValidationResult(BaseModel):
    finding_id: str
    validation_status: Literal["supported", "weak_support", "insufficient_support"]
    evidence_sufficiency: float
    aligned_snippet_ids: List[str]
    missing_support_reasons: List[str]
    validator_notes: str
    contradiction_flags: List[str] = []
    evidence_gap: List[str] = []


class EvidenceGatekeepingResult(BaseModel):
    finding_id: str
    gatekeeping_status: Literal["allowed", "downgraded", "blocked"]
    policy_violations: List[str]
    gatekeeping_notes: str


@dataclass
class EvidenceGatekeepingPolicy:
    """Policy configuration for evidence gatekeeping.

    Defaults enforce:
    - At least 1 evidence snippet per finding
    - At least 1 aligned snippet for high-stakes finding types
    - Retrieval trace required for high-stakes findings
    - Source trust tier limits by finding type (lower tier = more trusted)
    - insufficient_support findings are blocked from summaries
    - weak_support findings are downgraded
    """

    min_evidence_snippets: int = 1
    min_aligned_snippets: int = 1
    require_retrieval_trace: bool = True
    source_tier_maximums: Dict[str, int] = field(default_factory=lambda: {
        "risk_signal": 2,
        "competitor_signal": 2,
        "trend_signal": 3,
        "category_context": 3,
    })
    blocked_statuses: set = field(default_factory=lambda: {"insufficient_support"})
    downgraded_statuses: set = field(default_factory=lambda: {"weak_support"})
    high_stakes_finding_types: set = field(default_factory=lambda: {"risk_signal", "competitor_signal"})
    blocking_violations: set = field(default_factory=lambda: {
        "missing_retrieval_trace_for_high_stakes",
        "missing_source_for_high_stakes",
    })
    # Phase 5C: per-type evidence-count thresholds (higher for high-stakes)
    min_evidence_by_type: Dict[str, int] = field(default_factory=lambda: {
        "risk_signal": 2,
        "competitor_signal": 2,
    })
    min_aligned_by_type: Dict[str, int] = field(default_factory=lambda: {
        "risk_signal": 1,
        "competitor_signal": 1,
    })


def _field_from(item: Any, key: str, default: Any = "") -> Any:
    if isinstance(item, Mapping):
        return item.get(key, default)
    return getattr(item, key, default)


def _has_evidence_snippets(finding: Any) -> bool:
    snippets = _field_from(finding, "evidence_snippets", [])
    return bool(snippets and any(str(s).strip() for s in snippets))


def _has_snippet_id(finding: Any) -> bool:
    sid = _field_from(finding, "snippet_id", "")
    return bool(sid)


def _has_retrieval_trace(finding: Any) -> bool:
    tid = _field_from(finding, "retrieval_trace_id", "")
    return bool(tid)


def _snippet_id_from_finding(finding: Any) -> str:
    return _field_from(finding, "snippet_id", "")


def _trace_id_from_finding(finding: Any) -> str:
    return _field_from(finding, "retrieval_trace_id", "")


def _evidence_snippets_from_finding(finding: Any) -> List[str]:
    snippets = _field_from(finding, "evidence_snippets", [])
    return [s for s in snippets if isinstance(s, str) and s.strip()]
def _detect_contradictions(atoms) -> List[str]:
    """检测证据矛盾"""
    contradictions = []
    dict_atoms = [a for a in atoms if isinstance(a, dict)]
    positive = [a for a in dict_atoms if a.get("support_level") in ("strong", "moderate")]
    negative = [a for a in dict_atoms if a.get("support_level") in ("weak", "insufficient")]
    if positive and negative:
        contradictions.append("mixed_evidence")
    return contradictions


def _identify_gaps(atoms, claim: str = "") -> List[str]:
    """识别证据缺口"""
    gaps = []
    if not atoms:
        gaps.append("no_evidence")
    elif len(atoms) < 2:
        gaps.append("insufficient_evidence_count")
    dict_atoms = [a for a in atoms if isinstance(a, dict)]
    has_source_type = any(a.get("source_type") for a in dict_atoms)
    if not has_source_type:
        gaps.append("missing_source_type")
    return gaps



def validate_finding(
    finding: Any,
    traces: Optional[List[Any]] = None,
    chunks: Optional[List[Any]] = None,
) -> EvidenceValidationResult:
    """Validate whether a finding is supported by its cited evidence."""
    finding_id = _field_from(finding, "finding_id", "")

    has_snippets = _has_evidence_snippets(finding)
    has_snippet_id = _has_snippet_id(finding)
    has_trace = _has_retrieval_trace(finding)

    trace_by_id: Dict[str, Any] = {}
    if traces:
        for t in traces:
            tid = _field_from(t, "trace_id", "")
            if tid:
                trace_by_id[tid] = t

    chunk_by_id: Dict[str, Any] = {}
    if chunks:
        for c in chunks:
            cid = _field_from(c, "chunk_id", "")
            if cid:
                chunk_by_id[cid] = c

    snippet_id = _snippet_id_from_finding(finding)
    trace_id = _trace_id_from_finding(finding)
    evidence_snippets = _evidence_snippets_from_finding(finding)

    aligned_snippet_ids: List[str] = []
    missing_support_reasons: List[str] = []

    # Check snippet alignment (only flag missing refs when chunks were provided)
    if has_snippet_id and snippet_id in chunk_by_id:
        aligned_snippet_ids.append(snippet_id)
    elif has_snippet_id and snippet_id not in chunk_by_id and chunks is not None:
        missing_support_reasons.append("referenced_snippet_not_found_in_chunks")

    # Check trace alignment (only flag missing refs when traces were provided)
    trace_aligned = False
    if has_trace and trace_id in trace_by_id:
        trace = trace_by_id[trace_id]
        trace_chunk_ids = _field_from(trace, "chunk_ids", [])
        for tcid in trace_chunk_ids:
            if tcid in chunk_by_id:
                trace_aligned = True
                if tcid not in aligned_snippet_ids:
                    aligned_snippet_ids.append(tcid)
    elif has_trace and trace_id not in trace_by_id and traces is not None:
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
    # Compute contradiction_flags and evidence_gap
    atoms = evidence_snippets if evidence_snippets else []
    claim = _field_from(finding, "finding_text", "") or _field_from(finding, "summary", "")
    contradiction_flags = _detect_contradictions(atoms)
    evidence_gap = _identify_gaps(atoms, claim)

    return EvidenceValidationResult(
        finding_id=finding_id,
        validation_status=validation_status,
        evidence_sufficiency=round(sufficiency, 4),
        aligned_snippet_ids=aligned_snippet_ids,
        missing_support_reasons=missing_support_reasons,
        validator_notes="; ".join(notes_parts),
        contradiction_flags=contradiction_flags,
        evidence_gap=evidence_gap,
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


def _source_from_finding(finding: Any, sources: Optional[List[Any]] = None) -> Optional[Any]:
    """Look up a finding's source from the provided source list."""
    if not sources:
        return None
    source_id = _field_from(finding, "source_id", "")
    if not source_id:
        return None
    for s in sources:
        sid = _field_from(s, "source_id", "")
        if sid == source_id:
            return s
    return None


def apply_evidence_gatekeeping(
    finding: Any,
    validation_result: EvidenceValidationResult,
    source: Optional[Any] = None,
    policy: Optional[EvidenceGatekeepingPolicy] = None,
) -> EvidenceGatekeepingResult:
    """Apply evidence gatekeeping policy to a single finding.

    Returns a gatekeeping result indicating whether the finding is allowed,
    downgraded, or blocked from executive summary and high-level outputs.
    """
    finding_id = validation_result.finding_id
    policy = policy or EvidenceGatekeepingPolicy()

    violations: List[str] = []

    finding_type = _field_from(finding, "finding_type", "")
    is_high_stakes = finding_type in policy.high_stakes_finding_types

    # 1. Check validation status gates
    if validation_result.validation_status in policy.blocked_statuses:
        violations.append(f"validation_status:{validation_result.validation_status}")

    # 2. Check evidence count thresholds (per-type or global fallback)
    min_evidence = policy.min_evidence_by_type.get(finding_type, policy.min_evidence_snippets)
    min_aligned = policy.min_aligned_by_type.get(finding_type, policy.min_aligned_snippets)

    evidence_snippets = _evidence_snippets_from_finding(finding)
    if len(evidence_snippets) < min_evidence:
        violations.append(f"insufficient_evidence_snippets:{len(evidence_snippets)}<{min_evidence}")

    aligned_count = len(validation_result.aligned_snippet_ids)
    if aligned_count < min_aligned:
        violations.append(f"insufficient_aligned_snippets:{aligned_count}<{min_aligned}")

    # 3. Check retrieval trace requirement
    has_trace = _has_retrieval_trace(finding)

    if policy.require_retrieval_trace and is_high_stakes and not has_trace:
        violations.append("missing_retrieval_trace_for_high_stakes")

    # 4. Check source-tier minimums
    if source is not None:
        trust_tier = _field_from(source, "trust_tier", 3)
        max_tier = policy.source_tier_maximums.get(finding_type)
        if max_tier is not None and trust_tier > max_tier:
            violations.append(f"source_tier_too_low:tier_{trust_tier}>max_{max_tier}")
    elif is_high_stakes:
        # High-stakes findings without a source are blocked
        violations.append("missing_source_for_high_stakes")

    # Determine gatekeeping status
    has_blocking_violation = bool(policy.blocking_violations) and any(
        any(v.startswith(bv) for bv in policy.blocking_violations)
        for v in violations
    )

    # Block insufficient_support unconditionally
    if validation_result.validation_status in policy.blocked_statuses:
        status: Literal["allowed", "downgraded", "blocked"] = "blocked"
    # Blocking violations (e.g. missing trace for high-stakes) always block
    elif has_blocking_violation:
        status = "blocked"
    # Downgrade weak_support unconditionally; block if additional violations exist
    elif validation_result.validation_status in policy.downgraded_statuses:
        status = "blocked" if violations else "downgraded"
    # Other findings with policy violations are downgraded
    elif violations:
        status = "downgraded"
    else:
        status = "allowed"

    notes_parts: List[str] = []
    notes_parts.append(f"Gatekeeping status: {status}")
    if violations:
        notes_parts.append(f"Violations: {', '.join(violations)}")
    else:
        notes_parts.append("All policy checks passed")

    return EvidenceGatekeepingResult(
        finding_id=finding_id,
        gatekeeping_status=status,
        policy_violations=violations,
        gatekeeping_notes="; ".join(notes_parts),
    )


def apply_evidence_gatekeeping_to_findings(
    findings: List[Any],
    validation_results: List[EvidenceValidationResult],
    sources: Optional[List[Any]] = None,
    policy: Optional[EvidenceGatekeepingPolicy] = None,
) -> List[EvidenceGatekeepingResult]:
    """Apply evidence gatekeeping policy to a list of findings."""
    validation_by_id = {v.finding_id: v for v in validation_results}
    results: List[EvidenceGatekeepingResult] = []
    for finding in findings:
        finding_id = _field_from(finding, "finding_id", "")
        validation = validation_by_id.get(finding_id)
        if validation is None:
            validation = EvidenceValidationResult(
                finding_id=finding_id,
                validation_status="insufficient_support",
                evidence_sufficiency=0.0,
                aligned_snippet_ids=[],
                missing_support_reasons=["no_validation_performed"],
                validator_notes="Validation not performed for this finding",
            )
        source = _source_from_finding(finding, sources)
        results.append(apply_evidence_gatekeeping(finding, validation, source=source, policy=policy))
    return results


def build_gatekeeping_summary(results: List[EvidenceGatekeepingResult]) -> Dict[str, Any]:
    """Build a machine-readable summary of gatekeeping results."""
    if not results:
        return {
            "finding_count": 0,
            "allowed_count": 0,
            "downgraded_count": 0,
            "blocked_count": 0,
        }

    status_counts: Dict[str, int] = {"allowed": 0, "downgraded": 0, "blocked": 0}
    for r in results:
        status_counts[r.gatekeeping_status] = status_counts.get(r.gatekeeping_status, 0) + 1

    return {
        "finding_count": len(results),
        "allowed_count": status_counts.get("allowed", 0),
        "downgraded_count": status_counts.get("downgraded", 0),
        "blocked_count": status_counts.get("blocked", 0),
    }


def filter_allowed_findings(
    findings: List[Any],
    gatekeeping_results: List[EvidenceGatekeepingResult],
    include_downgraded: bool = False,
) -> List[Any]:
    """Filter findings to only those allowed (and optionally downgraded) by gatekeeping."""
    allowed_ids = {
        r.finding_id for r in gatekeeping_results
        if r.gatekeeping_status == "allowed" or (include_downgraded and r.gatekeeping_status == "downgraded")
    }
    return [
        f for f in findings
        if _field_from(f, "finding_id", "") in allowed_ids
    ]


__all__ = [
    "EvidenceValidationResult",
    "EvidenceGatekeepingResult",
    "EvidenceGatekeepingPolicy",
    "apply_evidence_gatekeeping",
    "apply_evidence_gatekeeping_to_findings",
    "build_evidence_validation_summary",
    "build_gatekeeping_summary",
    "filter_allowed_findings",
    "validate_finding",
    "validate_findings",
]
