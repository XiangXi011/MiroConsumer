"""Consumer research ingest: typed findings from manual background and auto-enrich."""

from __future__ import annotations

import hashlib
import logging
from typing import Callable, Dict, List, Mapping, Optional, Tuple

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
from .project_research_persistence import persist_source_quality
from .retrieval import PublicWebSearchProvider, RetrievalService
from .source_quality import (
    apply_source_quality_to_findings,
    build_source_quality_summary,
    evaluate_sources,
)
from .source_registry import SourceRegistry

logger = logging.getLogger(__name__)

MAX_LANE_B_QUERIES_PER_BUILD = 6
LLM_AUTO_RESEARCH_TIMEOUT_SECONDS = 30


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


def _append_unique_query(queries: List[str], seen: set[str], value: str, max_queries: int) -> None:
    text = value.strip()
    if not text or len(queries) >= max_queries:
        return
    key = text.casefold()
    if key in seen:
        return
    queries.append(text)
    seen.add(key)


def _build_lane_b_queries(
    brief: ConsumerBusinessBrief,
    max_queries: int = MAX_LANE_B_QUERIES_PER_BUILD,
) -> List[str]:
    """Select a small, representative query set for public-web gap filling."""
    queries: List[str] = []
    seen: set[str] = set()

    if brief.research_goal:
        _append_unique_query(queries, seen, brief.research_goal, max_queries)

    for concept in brief.product_concept_assets[:2]:
        _append_unique_query(queries, seen, concept, max_queries)

    for claim in brief.claims[:3]:
        _append_unique_query(queries, seen, claim, max_queries)

    for value in list(brief.claims[3:]) + list(brief.product_concept_assets[2:]):
        _append_unique_query(queries, seen, value, max_queries)

    return queries


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


def _finding_type_from_evidence_type(evidence_type: str) -> str:
    normalized = evidence_type.strip().casefold()
    if normalized in {"claim_risk", "regulatory", "safety", "category_safety"}:
        return "risk_signal"
    if normalized in {"competitor", "competitor_signal"}:
        return "competitor_signal"
    if normalized in {"trend", "trend_signal", "social"}:
        return "trend_signal"
    return "category_context"


def build_source_evidence_findings(brief: ConsumerBusinessBrief) -> List[ResearchFinding]:
    """Convert curated source evidence spans into research findings."""
    findings: List[ResearchFinding] = []
    seen: set[str] = set()
    for span in getattr(brief, "source_evidence_spans", []) or []:
        if not isinstance(span, Mapping):
            continue
        snippet = str(span.get("snippet", "") or "").strip()
        if not snippet:
            continue
        title = str(span.get("title", "") or "").strip()
        url = str(span.get("url", "") or "").strip()
        key = f"{title}|{url}|{snippet}".casefold()
        if key in seen:
            continue
        seen.add(key)
        evidence_type = str(span.get("evidence_type", "") or "").strip()
        finding_type = _finding_type_from_evidence_type(evidence_type)
        try:
            confidence = float(span.get("confidence", 0.6))
        except (TypeError, ValueError):
            confidence = 0.6
        confidence = max(0.0, min(1.0, confidence))
        visibility = (
            GraphVisibility.Restricted
            if finding_type == "risk_signal"
            else GraphVisibility.Initial
        )
        findings.append(
            ResearchFinding(
                finding_id=_deterministic_finding_id(key, prefix="se"),
                finding_type=finding_type,  # type: ignore[arg-type]
                summary=snippet,
                evidence_snippets=[snippet],
                source_label="source_evidence",
                visibility=visibility,
                confidence=confidence,
                support_summary=title or url,
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

    # Derive findings from task-specific fields
    for asset in brief.packaging_assets:
        text = asset.strip()
        if not text:
            continue
        findings.append(
            ResearchFinding(
                finding_id=_deterministic_finding_id(text, prefix="ae_pkg"),
                finding_type="category_context",
                summary=f"Packaging asset: {text}",
                evidence_snippets=[text],
                source_label="auto_enrich",
                visibility=GraphVisibility.Initial,
                confidence=0.7,
            )
        )

    for variant in brief.test_variants:
        text = variant.label.strip()
        if not text:
            continue
        findings.append(
            ResearchFinding(
                finding_id=_deterministic_finding_id(text, prefix="ae_var"),
                finding_type="category_context",
                summary=f"Variant: {text}",
                evidence_snippets=[text],
                source_label="auto_enrich",
                visibility=GraphVisibility.Initial,
                confidence=0.7,
            )
        )

    for price in brief.price_points:
        text = price.strip()
        if not text:
            continue
        findings.append(
            ResearchFinding(
                finding_id=_deterministic_finding_id(text, prefix="ae_price"),
                finding_type="category_context",
                summary=f"Price point: {text}",
                evidence_snippets=[text],
                source_label="auto_enrich",
                visibility=GraphVisibility.Initial,
                confidence=0.7,
            )
        )

    return findings


def llm_auto_research_provider(brief: ConsumerBusinessBrief) -> List[ResearchFinding]:
    """LLM-powered auto-research provider that generates real findings.

    Uses the project's configured LLM to synthesize category context,
    risk signals, competitor signals, and trend signals based on the
    brief content. Returns structured ResearchFinding objects.

    Falls back to default_auto_research_provider if LLM is unavailable
    or the call fails.
    """
    try:
        from ...utils.llm_client import LLMClient

        client = LLMClient()
    except Exception as exc:
        logger.warning("LLM not available for auto-research, falling back: %s", exc)
        return default_auto_research_provider(brief)

    # Build a rich research prompt from the brief
    context_parts: List[str] = []
    if brief.research_goal:
        context_parts.append(f"Research Goal: {brief.research_goal}")
    if brief.product_concept_assets:
        context_parts.append(f"Product Concepts: {' | '.join(brief.product_concept_assets)}")
    if brief.copy_material:
        context_parts.append(f"Copy Material: {' | '.join(brief.copy_material)}")
    if brief.claims:
        context_parts.append(f"Claims: {' | '.join(brief.claims)}")
    if brief.target_audience:
        context_parts.append(f"Target Audience: {' | '.join(brief.target_audience)}")
    if brief.usage_scene:
        context_parts.append(f"Usage Scene: {' | '.join(brief.usage_scene)}")
    if brief.packaging_assets:
        context_parts.append(f"Packaging Assets: {' | '.join(brief.packaging_assets)}")
    if brief.test_variants:
        context_parts.append(f"Test Variants: {' | '.join(v.label for v in brief.test_variants)}")
    if brief.price_points:
        context_parts.append(f"Price Points: {' | '.join(brief.price_points)}")
    if brief.price_context:
        context_parts.append(f"Price Context: {brief.price_context}")

    context = "\n".join(context_parts)
    if not context:
        return default_auto_research_provider(brief)

    system_prompt = (
        "You are a market research analyst. Based on the consumer brief provided, "
        "generate structured pre-research findings that would help a consumer "
        "propagation simulation. Identify category context, potential risk signals, "
        "competitor signals, and trend signals."
    )

    user_prompt = (
        f"{context}\n\n"
        "Respond with a single JSON object containing a 'findings' array. "
        "Each finding must have:\n"
        '- "type": one of [category_context, risk_signal, competitor_signal, trend_signal]\n'
        '- "summary": a concise sentence (max 200 chars)\n'
        '- "visibility": one of [Initial, Propagation_Only, Restricted]\n'
        '- "confidence": a float between 0.0 and 1.0\n'
        "Generate at most 8 findings. Be specific and insightful."
    )

    try:
        data = client.chat_json(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.5,
            max_tokens=2048,
            fallback_on_failure=False,
            timeout=LLM_AUTO_RESEARCH_TIMEOUT_SECONDS,
        )
    except Exception as exc:
        logger.warning("LLM auto-research call failed, falling back: %s", exc)
        return default_auto_research_provider(brief)

    raw_findings = data.get("findings") if isinstance(data, Mapping) else None
    if not isinstance(raw_findings, list):
        logger.warning("LLM auto-research returned invalid findings format, falling back")
        return default_auto_research_provider(brief)

    findings: List[ResearchFinding] = []
    seen: set[str] = set()

    visibility_map: Dict[str, GraphVisibility] = {
        "Initial": GraphVisibility.Initial,
        "Propagation_Only": GraphVisibility.Propagation_Only,
        "Restricted": GraphVisibility.Restricted,
    }
    type_map: Dict[str, str] = {
        "category_context": "category_context",
        "risk_signal": "risk_signal",
        "competitor_signal": "competitor_signal",
        "trend_signal": "trend_signal",
    }

    for idx, item in enumerate(raw_findings):
        if not isinstance(item, Mapping):
            continue
        summary = str(item.get("summary", "")).strip()
        if not summary:
            continue
        key = summary.casefold()
        if key in seen:
            continue
        seen.add(key)

        finding_type = type_map.get(str(item.get("type", "")).strip().lower(), "category_context")
        visibility = visibility_map.get(
            str(item.get("visibility", "")).strip(), GraphVisibility.Propagation_Only
        )
        try:
            confidence = float(item.get("confidence", 0.6))
        except (TypeError, ValueError):
            confidence = 0.6
        confidence = max(0.0, min(1.0, confidence))

        findings.append(
            ResearchFinding(
                finding_id=_deterministic_finding_id(summary, prefix=f"ae_llm_{idx}"),
                finding_type=finding_type,  # type: ignore[arg-type]
                summary=summary,
                evidence_snippets=[summary],
                source_label="auto_enrich",
                visibility=visibility,
                confidence=confidence,
            )
        )

    if not findings:
        return default_auto_research_provider(brief)

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

    queries = _build_lane_b_queries(brief)

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

    source_evidence = build_source_evidence_findings(brief)
    for finding in source_evidence:
        if finding.finding_id not in seen_ids:
            result.append(finding)
            seen_ids.add(finding.finding_id)

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

    # Phase 4A: apply source quality scoring when project context exists
    if project_id is not None:
        registry = SourceRegistry(project_id, upload_root=upload_root)
        sources = registry.list_sources()
        if sources:
            scored_sources = evaluate_sources(sources)
            for s in scored_sources:
                registry.update_source(s)
            result = apply_source_quality_to_findings(result, scored_sources)

    return result


def build_research_snapshot(
    project_id: str,
    brief: Optional[ConsumerBusinessBrief] = None,
    upload_root: Optional[str] = None,
    provider: Optional[Callable[[ConsumerBusinessBrief], List[ResearchFinding]]] = None,
    enable_lane_b: bool = False,
    lane_b_provider: Optional[PublicWebSearchProvider] = None,
    precomputed_findings: Optional[List[ResearchFinding]] = None,
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
    if precomputed_findings is not None:
        findings = list(precomputed_findings)
    elif brief is not None:
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

    # Phase 4A: score source quality and annotate findings
    scored_sources = evaluate_sources(sources)
    if scored_sources:
        for s in scored_sources:
            registry.update_source(s)
    # resolve_research_findings() already annotates findings when project_id
    # is provided; skip re-application to avoid double-boosting / double-capping.
    if not findings or not findings[0].confidence_label:
        findings = apply_source_quality_to_findings(findings, scored_sources)
    quality_summary = build_source_quality_summary(scored_sources)
    persist_source_quality(project_id, quality_summary, upload_root=upload_root)

    return ResearchSnapshot(
        snapshot_id=f"rsnap_{project_id}",
        project_id=project_id,
        created_at=datetime.now(timezone.utc).isoformat(),
        sources=scored_sources,
        documents=documents,
        chunks=chunks,
        findings=findings,
        retrieval_traces=retrieval_traces,
        summary=build_research_summary(findings),
    )
