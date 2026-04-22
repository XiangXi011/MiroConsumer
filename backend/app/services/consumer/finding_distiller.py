"""Finding distiller: turn ingested document chunks into provenance-ready findings."""

from __future__ import annotations

import hashlib
from typing import Callable, List, Optional

from .lane_b_provider import GovernedDocumentChunk
from .models import (
    DocumentChunk,
    GraphVisibility,
    ResearchFinding,
    ResearchSourceLane,
    RetrievalTrace,
)


def _deterministic_finding_id(text: str, prefix: str = "fd") -> str:
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()[:12]
    return f"{prefix}_{digest}"


def _classify_finding_type(text: str) -> str:
    lowered = text.casefold()

    risk_markers = (
        "controvers",
        "technical",
        "manufactur",
        "defect",
        "contamination",
        "safety",
        "lawsuit",
        "recall",
        "privacy",
        "regulator",
        "negative",
        "risk",
        "concern",
        "debate",
        "warn",
    )
    competitor_markers = ("competitor", "rival", "vs ", "versus", "compared to", "alternative")
    trend_markers = (
        "trend",
        "trending",
        "viral",
        "buzz",
        "hot topic",
        "growing",
        "rising",
        "surge",
    )
    propagation_markers = (
        "spread",
        "rumor",
        "creator",
        "group chat",
        "word of mouth",
        "talking point",
        "repeat",
        "discuss",
        "share",
    )

    if any(marker in lowered for marker in risk_markers):
        return "risk_signal"
    if any(marker in lowered for marker in competitor_markers):
        return "competitor_signal"
    if any(marker in lowered for marker in trend_markers):
        return "trend_signal"
    if any(marker in lowered for marker in propagation_markers):
        return "trend_signal"
    return "category_context"


def _classify_visibility(text: str) -> GraphVisibility:
    lowered = text.casefold()

    restricted_markers = (
        "controvers",
        "technical",
        "manufactur",
        "defect",
        "contamination",
        "safety",
        "lawsuit",
        "recall",
        "privacy",
        "regulator",
        "competitor",
        "negative",
        "risk",
        "deep",
    )
    propagation_markers = (
        "spread",
        "rumor",
        "buzz",
        "creator",
        "group chat",
        "word of mouth",
        "talking point",
        "repeat",
        "discuss",
    )

    if any(marker in lowered for marker in restricted_markers):
        return GraphVisibility.Restricted
    if any(marker in lowered for marker in propagation_markers):
        return GraphVisibility.Propagation_Only
    return GraphVisibility.Propagation_Only


def _is_chunk_accepted(chunk: DocumentChunk) -> bool:
    """Return True if the chunk is accepted by Lane B governance (or not governed)."""
    if isinstance(chunk, GovernedDocumentChunk):
        return chunk.governance_status == "accepted"
    return True


def _chunk_confidence(chunk: DocumentChunk, base: float = 0.6) -> float:
    """Return adjusted confidence for a chunk, lowering it if downgraded."""
    if isinstance(chunk, GovernedDocumentChunk) and chunk.downgraded:
        return round(base * 0.75, 2)
    return base


def _chunk_governance_reasons(chunk: DocumentChunk) -> List[str]:
    """Return governance reasons attached to a governed chunk."""
    if isinstance(chunk, GovernedDocumentChunk):
        return list(chunk.governance_reasons)
    return []


def distill_findings_from_chunks(
    chunks: List[DocumentChunk],
    lane: ResearchSourceLane = ResearchSourceLane.LaneA,
    trace_id: Optional[str] = None,
) -> List[ResearchFinding]:
    """Deterministically distill findings from document chunks.

    Each chunk becomes a candidate finding.  Provenance is attached
    via source_id, snippet_id (= chunk_id), and retrieval_trace_id.

    Lane B governed chunks that are rejected are skipped.
    """
    findings: List[ResearchFinding] = []
    seen: set[str] = set()

    for chunk in chunks:
        # Skip rejected governed chunks
        if not _is_chunk_accepted(chunk):
            continue

        text = chunk.text.strip()
        if not text:
            continue
        # Deduplicate by text content
        key = text.casefold()
        if key in seen:
            continue
        seen.add(key)

        finding_type = _classify_finding_type(text)
        visibility = _classify_visibility(text)
        confidence = _chunk_confidence(chunk)
        gov_reasons = _chunk_governance_reasons(chunk)
        support_summary = ""
        if gov_reasons:
            support_summary = "Governance: " + "; ".join(gov_reasons)

        findings.append(
            ResearchFinding(
                finding_id=_deterministic_finding_id(text, prefix="chunk"),
                finding_type=finding_type,  # type: ignore[arg-type]
                summary=text[:200],
                evidence_snippets=[text],
                source_label="ingested_document" if lane == ResearchSourceLane.LaneA else "public_web",
                visibility=visibility,
                confidence=confidence,
                source_id=chunk.source_id,
                snippet_id=chunk.chunk_id,
                retrieval_trace_id=trace_id or "",
                confidence_reasons=gov_reasons,
                support_summary=support_summary,
            )
        )

    return findings


# Provider hook type: takes chunks, returns findings.
FindingDistillerProvider = Callable[[List[DocumentChunk], ResearchSourceLane, Optional[str]], List[ResearchFinding]]


def run_distiller_with_provider(
    chunks: List[DocumentChunk],
    provider: FindingDistillerProvider,
    lane: ResearchSourceLane = ResearchSourceLane.LaneA,
    trace_id: Optional[str] = None,
) -> List[ResearchFinding]:
    """Invoke an external finding distiller provider and return its findings."""
    return provider(chunks, lane, trace_id)


def build_retrieval_trace(
    query: str,
    lane: ResearchSourceLane,
    chunk_ids: List[str],
    scores: Optional[List[float]] = None,
    trace_id: Optional[str] = None,
) -> RetrievalTrace:
    """Build a retrieval trace for auditability."""
    from datetime import datetime, timezone

    return RetrievalTrace(
        trace_id=trace_id or f"trace_{hashlib.sha256(query.encode()).hexdigest()[:12]}",
        query=query,
        lane=lane,
        chunk_ids=list(chunk_ids),
        scores=list(scores) if scores else [],
        retrieved_at=datetime.now(timezone.utc).isoformat(),
    )
