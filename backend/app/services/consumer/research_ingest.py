"""Consumer research ingest: typed findings from manual background and auto-enrich."""

from __future__ import annotations

import hashlib
from typing import Any, Callable, Dict, List, Mapping, Optional, Tuple

from .models import (
    ConsumerBusinessBrief,
    GraphVisibility,
    ResearchFinding,
    ResearchSnapshot,
    ResearchSourceLane,
    RetrievalTrace,
)
from .document_ingest import DocumentIngestService
from .finding_distiller import distill_findings_from_chunks
from .retrieval import PublicWebSearchProvider, RetrievalService
from .source_registry import SourceRegistry


def _deterministic_finding_id(text: str, prefix: str = "mf") -> str:
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


def build_research_findings(brief: ConsumerBusinessBrief) -> List[ResearchFinding]:
    """Convert manual background materials into typed ResearchFinding objects."""
    findings: List[ResearchFinding] = []
    seen: set[str] = set()

    for material in brief.optional_background_materials:
        text = material.strip()
        if not text:
            continue
        # Skip URLs — they are ingested into Lane A workspace separately
        if text.startswith(("http://", "https://")):
            continue
        key = text.casefold()
        if key in seen:
            continue
        seen.add(key)

        finding_type = _classify_finding_type(text)
        visibility = _classify_visibility(text)

        findings.append(
            ResearchFinding(
                finding_id=_deterministic_finding_id(text, prefix="bg"),
                finding_type=finding_type,  # type: ignore[arg-type]
                summary=text,
                evidence_snippets=[text],
                source_label="brief_background",
                visibility=visibility,
                confidence=0.6,
            )
        )

    return findings


def run_auto_research(
    brief: ConsumerBusinessBrief,
    provider: Callable[[ConsumerBusinessBrief], List[ResearchFinding]],
) -> List[ResearchFinding]:
    """Invoke an external research provider and return its findings."""
    return provider(brief)


def default_auto_research_provider(brief: ConsumerBusinessBrief) -> List[ResearchFinding]:
    """Deterministic default provider that synthesizes findings from the brief itself.

    Produces typed ResearchFinding objects with source_label='auto_enrich' so
    downstream steps can distinguish auto-generated findings from manual background.
    """
    findings: List[ResearchFinding] = []

    # Derive a category-context finding from the research goal
    if brief.research_goal:
        goal_text = brief.research_goal.strip()
        if goal_text:
            findings.append(
                ResearchFinding(
                    finding_id=_deterministic_finding_id(goal_text, prefix="ae_goal"),
                    finding_type="category_context",
                    summary=f"Research objective: {goal_text}",
                    evidence_snippets=[goal_text],
                    source_label="auto_enrich",
                    visibility=GraphVisibility.Initial,
                    confidence=0.7,
                )
            )

    # Derive findings from product concepts
    for concept in brief.product_concept_assets:
        text = concept.strip()
        if not text:
            continue
        findings.append(
            ResearchFinding(
                finding_id=_deterministic_finding_id(text, prefix="ae_prod"),
                finding_type="category_context",
                summary=f"Product concept: {text}",
                evidence_snippets=[text],
                source_label="auto_enrich",
                visibility=GraphVisibility.Initial,
                confidence=0.7,
            )
        )

    # Derive findings from claims (risk-classify if applicable)
    for claim in brief.claims:
        text = claim.strip()
        if not text:
            continue
        claim_type = _classify_finding_type(text)
        claim_visibility = _classify_visibility(text)
        findings.append(
            ResearchFinding(
                finding_id=_deterministic_finding_id(text, prefix="ae_claim"),
                finding_type=claim_type,  # type: ignore[arg-type]
                summary=f"Claim: {text}",
                evidence_snippets=[text],
                source_label="auto_enrich",
                visibility=claim_visibility,
                confidence=0.6,
            )
        )

    # Derive findings from target audience
    for audience in brief.target_audience:
        text = audience.strip()
        if not text:
            continue
        findings.append(
            ResearchFinding(
                finding_id=_deterministic_finding_id(text, prefix="ae_aud"),
                finding_type="category_context",
                summary=f"Target audience: {text}",
                evidence_snippets=[text],
                source_label="auto_enrich",
                visibility=GraphVisibility.Propagation_Only,
                confidence=0.6,
            )
        )

    return findings


def build_research_summary(findings: List[ResearchFinding]) -> str:
    """Build a pinned research summary string from findings."""
    if not findings:
        return "No background research findings available."
    lines: List[str] = []
    for finding in findings:
        lines.append(f"[{finding.finding_type}] {finding.summary}")
    return "\n".join(lines)


def build_workspace_findings(
    project_id: str,
    upload_root: Optional[str] = None,
) -> List[ResearchFinding]:
    """Load findings from the project research workspace (Lane A ingested docs).

    If no research workspace exists, returns an empty list.
    """
    registry = SourceRegistry(project_id, upload_root=upload_root)
    ingest = DocumentIngestService(project_id, upload_root=upload_root)

    lane_a_sources = registry.list_sources(lane=ResearchSourceLane.LaneA)
    if not lane_a_sources:
        return []

    findings: List[ResearchFinding] = []
    seen_ids: set[str] = set()

    for source in lane_a_sources:
        chunks = ingest.load_chunks(source_id=source.source_id)
        if not chunks:
            continue
        source_findings = distill_findings_from_chunks(
            chunks=chunks,
            lane=ResearchSourceLane.LaneA,
        )
        for finding in source_findings:
            if finding.finding_id not in seen_ids:
                findings.append(finding)
                seen_ids.add(finding.finding_id)

    return findings


def build_lane_b_findings(
    project_id: str,
    brief: ConsumerBusinessBrief,
    upload_root: Optional[str] = None,
    lane_b_provider: Optional[PublicWebSearchProvider] = None,
) -> Tuple[List[ResearchFinding], List[RetrievalTrace]]:
    """Build Lane B findings via dual-lane retrieval.

    Uses the brief's research_goal, claims, and product concepts as
    retrieval queries.  Retrieved chunks are distilled into findings
    with full provenance (source_id, snippet_id, retrieval_trace_id).

    Lane B findings are gap-fillers; they never override Lane A.
    """
    retrieval = RetrievalService(project_id, upload_root=upload_root)

    queries: List[str] = []
    if brief.research_goal:
        queries.append(brief.research_goal)
    for claim in brief.claims:
        claim = claim.strip()
        if claim:
            queries.append(claim)
    for concept in brief.product_concept_assets:
        concept = concept.strip()
        if concept:
            queries.append(concept)

    findings: List[ResearchFinding] = []
    traces: List[RetrievalTrace] = []
    seen_ids: set[str] = set()

    for query in queries:
        result = retrieval.retrieve_dual(query, top_k_a=0, top_k_b=5, provider=lane_b_provider)
        lane_b_results = result["lane_b"]
        lane_b_trace = result["traces"][1] if len(result["traces"]) > 1 else None

        if lane_b_trace is not None:
            traces.append(lane_b_trace)

        chunks = [chunk for chunk, score in lane_b_results if score > 0]
        if not chunks:
            continue

        query_findings = distill_findings_from_chunks(
            chunks=chunks,
            lane=ResearchSourceLane.LaneB,
            trace_id=lane_b_trace.trace_id if lane_b_trace else None,
        )
        for finding in query_findings:
            if finding.finding_id not in seen_ids:
                findings.append(finding)
                seen_ids.add(finding.finding_id)

    return findings, traces


def resolve_research_findings(
    brief: ConsumerBusinessBrief,
    provider: Optional[Callable[[ConsumerBusinessBrief], List[ResearchFinding]]] = None,
    project_id: Optional[str] = None,
    upload_root: Optional[str] = None,
    enable_lane_b: bool = False,
    lane_b_provider: Optional[PublicWebSearchProvider] = None,
) -> List[ResearchFinding]:
    """Resolve the final research findings list for a brief.

    Rules:
    - Always include manual background findings.
    - When project_id is provided, also include findings from the project
      research workspace (Lane A ingested documents).
    - When research_mode is 'auto_enrich', also invoke the provider.
    - Provider results are appended after manual/workspace findings.
    - Deduplication is by finding_id.
    """
    manual = build_research_findings(brief)
    seen_ids = {f.finding_id for f in manual}
    result: List[ResearchFinding] = list(manual)

    if project_id is not None:
        workspace = build_workspace_findings(project_id, upload_root=upload_root)
        for finding in workspace:
            if finding.finding_id not in seen_ids:
                result.append(finding)
                seen_ids.add(finding.finding_id)

    if brief.research_mode == "auto_enrich" and provider is not None:
        auto = run_auto_research(brief, provider)
        for finding in auto:
            if finding.finding_id not in seen_ids:
                result.append(finding)
                seen_ids.add(finding.finding_id)

    if enable_lane_b and project_id is not None:
        lane_b_findings, _ = build_lane_b_findings(
            project_id=project_id,
            brief=brief,
            upload_root=upload_root,
            lane_b_provider=lane_b_provider,
        )
        for finding in lane_b_findings:
            if finding.finding_id not in seen_ids:
                result.append(finding)
                seen_ids.add(finding.finding_id)

    return result


def build_research_snapshot(
    project_id: str,
    brief: Optional[ConsumerBusinessBrief] = None,
    upload_root: Optional[str] = None,
    provider: Optional[Callable[[ConsumerBusinessBrief], List[ResearchFinding]]] = None,
    enable_lane_b: bool = False,
    lane_b_provider: Optional[PublicWebSearchProvider] = None,
) -> ResearchSnapshot:
    """Build a research snapshot for a project from its research workspace.

    If no workspace exists, returns an empty snapshot.
    """
    from datetime import datetime, timezone

    registry = SourceRegistry(project_id, upload_root=upload_root)
    ingest = DocumentIngestService(project_id, upload_root=upload_root)

    sources = registry.list_sources()
    documents = ingest.list_documents()
    chunks = ingest.load_chunks()

    findings: List[ResearchFinding] = []
    retrieval_traces: List[RetrievalTrace] = []
    if brief is not None:
        findings = resolve_research_findings(
            brief=brief,
            provider=provider,
            project_id=project_id,
            upload_root=upload_root,
            enable_lane_b=enable_lane_b,
            lane_b_provider=lane_b_provider,
        )
    else:
        # No brief provided: just return workspace findings
        findings = build_workspace_findings(project_id, upload_root=upload_root)

    # Load any persisted retrieval traces
    retrieval = RetrievalService(project_id, upload_root=upload_root)
    retrieval_traces = retrieval.load_traces()

    return ResearchSnapshot(
        snapshot_id=f"rsnap_{project_id}",
        project_id=project_id,
        created_at=datetime.now(timezone.utc).isoformat(),
        sources=sources,
        documents=documents,
        chunks=chunks,
        findings=findings,
        retrieval_traces=retrieval_traces,
        summary=build_research_summary(findings),
    )
