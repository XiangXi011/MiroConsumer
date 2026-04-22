"""Deterministic source quality scoring for Lane A and Lane B research sources."""

from __future__ import annotations

from typing import Any, Dict, List

from .models import ResearchFinding, ResearchSource, ResearchSourceLane, ResearchSourceType


def _freshness_from_metadata(metadata: Dict[str, Any]) -> int:
    """Extract a freshness score from source metadata if available."""
    if "freshness_score" in metadata:
        try:
            return max(0, min(100, int(metadata["freshness_score"])))
        except (ValueError, TypeError):
            pass
    if "published_year" in metadata:
        try:
            year = int(metadata["published_year"])
            # Simple heuristic: newer is fresher, capped at 2026
            import datetime

            current_year = datetime.datetime.now(datetime.timezone.utc).year
            age = max(0, current_year - year)
            return max(10, 100 - age * 10)
        except (ValueError, TypeError):
            pass
    return 0


def _domain_boost_from_metadata(metadata: Dict[str, Any]) -> float:
    """Return a confidence boost for trusted domains."""
    domain_tier = metadata.get("domain_tier", "")
    if domain_tier == "trusted":
        return 0.1
    if domain_tier == "authoritative":
        return 0.15
    return 0.0


def evaluate_source(source: ResearchSource) -> ResearchSource:
    """Assign deterministic quality scores to a research source.

    Lane A (user-provided) sources outrank Lane B (public-web) sources.
    """
    lane = source.lane
    source_type = source.source_type
    metadata = source.metadata or {}

    freshness = _freshness_from_metadata(metadata)
    domain_boost = _domain_boost_from_metadata(metadata)

    if lane == ResearchSourceLane.LaneA:
        trust_tier = 1
        if source_type == ResearchSourceType.Upload:
            base_confidence = 0.9
            base_freshness = 70 if freshness == 0 else freshness
            coverage_tags = ["user_provided", "primary"]
            quality_reasons = ["lane_a_user_upload", "user_material_outranks_public_web"]
        elif source_type == ResearchSourceType.Url:
            base_confidence = 0.85
            base_freshness = 60 if freshness == 0 else freshness
            coverage_tags = ["user_provided", "url"]
            quality_reasons = ["lane_a_user_url", "user_material_outranks_public_web"]
        else:
            base_confidence = 0.85
            base_freshness = 60 if freshness == 0 else freshness
            coverage_tags = ["user_provided"]
            quality_reasons = ["lane_a_source"]
    else:
        trust_tier = 2
        if source_type == ResearchSourceType.PublicWeb:
            base_confidence = 0.55
            base_freshness = 40 if freshness == 0 else freshness
            coverage_tags = ["public_web", "supplemental"]
            quality_reasons = ["lane_b_public_web", "public_web_supplement"]
        else:
            base_confidence = 0.6
            base_freshness = 45 if freshness == 0 else freshness
            coverage_tags = ["lane_b", "supplemental"]
            quality_reasons = ["lane_b_source"]

    source_confidence = min(1.0, base_confidence + domain_boost)

    return ResearchSource(
        source_id=source.source_id,
        lane=lane,
        source_type=source_type,
        label=source.label,
        uri=source.uri,
        metadata=metadata,
        added_at=source.added_at,
        trust_tier=trust_tier,
        freshness_score=base_freshness,
        source_confidence=source_confidence,
        coverage_tags=coverage_tags,
        quality_reasons=quality_reasons,
    )


def evaluate_sources(sources: List[ResearchSource]) -> List[ResearchSource]:
    """Score a list of sources deterministically."""
    return [evaluate_source(s) for s in sources]


def build_source_quality_summary(sources: List[ResearchSource]) -> Dict[str, Any]:
    """Build a machine-readable summary of source quality across a snapshot."""
    if not sources:
        return {
            "source_count": 0,
            "lane_a_count": 0,
            "lane_b_count": 0,
            "average_source_confidence": 0.0,
            "average_freshness_score": 0,
            "trust_tier_distribution": {},
            "coverage_tag_distribution": {},
        }

    lane_a_count = sum(1 for s in sources if s.lane == ResearchSourceLane.LaneA)
    lane_b_count = sum(1 for s in sources if s.lane == ResearchSourceLane.LaneB)
    avg_confidence = sum(s.source_confidence for s in sources) / len(sources)
    avg_freshness = sum(s.freshness_score for s in sources) / len(sources)

    trust_tier_distribution: Dict[str, int] = {}
    for s in sources:
        tier_key = str(s.trust_tier)
        trust_tier_distribution[tier_key] = trust_tier_distribution.get(tier_key, 0) + 1

    coverage_tag_distribution: Dict[str, int] = {}
    for s in sources:
        for tag in s.coverage_tags:
            coverage_tag_distribution[tag] = coverage_tag_distribution.get(tag, 0) + 1

    return {
        "source_count": len(sources),
        "lane_a_count": lane_a_count,
        "lane_b_count": lane_b_count,
        "average_source_confidence": round(avg_confidence, 4),
        "average_freshness_score": round(avg_freshness, 2),
        "trust_tier_distribution": trust_tier_distribution,
        "coverage_tag_distribution": coverage_tag_distribution,
    }


def apply_source_quality_to_findings(
    findings: List[ResearchFinding],
    sources: List[ResearchSource],
) -> List[ResearchFinding]:
    """Annotate findings with confidence labels and reasons based on source quality.

    Keeps the original ResearchFinding.confidence as the numeric base field and
    adds companion metadata.
    """
    source_by_id = {s.source_id: s for s in sources}
    updated: List[ResearchFinding] = []

    for finding in findings:
        source = source_by_id.get(finding.source_id)
        if source is None:
            # No matching source: backfill with unknown
            updated.append(
                ResearchFinding(
                    finding_id=finding.finding_id,
                    finding_type=finding.finding_type,  # type: ignore[arg-type]
                    summary=finding.summary,
                    evidence_snippets=list(finding.evidence_snippets),
                    source_label=finding.source_label,
                    visibility=finding.visibility,
                    confidence=finding.confidence,
                    source_id=finding.source_id,
                    snippet_id=finding.snippet_id,
                    retrieval_trace_id=finding.retrieval_trace_id,
                    confidence_label="unknown",
                    confidence_reasons=["source_quality_unknown_no_matching_source"],
                    support_summary="Source quality could not be determined",
                )
            )
            continue

        # Adjust confidence based on source lane and quality
        if source.lane == ResearchSourceLane.LaneA:
            adjusted_confidence = max(0.75, finding.confidence + 0.1)
            if adjusted_confidence >= 0.8:
                label = "high"
            else:
                label = "medium"
        else:
            adjusted_confidence = min(0.6, finding.confidence)
            if adjusted_confidence < 0.5:
                label = "low"
            else:
                label = "medium"

        confidence_reasons = list(source.quality_reasons)
        if source.lane == ResearchSourceLane.LaneA:
            confidence_reasons.append("lane_a_boost_applied")
        else:
            confidence_reasons.append("lane_b_cap_applied")

        support_summary = (
            f"Supported by {source.lane.value} {source.source_type.value} "
            f"with {label} confidence"
        )

        updated.append(
            ResearchFinding(
                finding_id=finding.finding_id,
                finding_type=finding.finding_type,  # type: ignore[arg-type]
                summary=finding.summary,
                evidence_snippets=list(finding.evidence_snippets),
                source_label=finding.source_label,
                visibility=finding.visibility,
                confidence=round(adjusted_confidence, 4),
                source_id=finding.source_id,
                snippet_id=finding.snippet_id,
                retrieval_trace_id=finding.retrieval_trace_id,
                confidence_label=label,
                confidence_reasons=confidence_reasons,
                support_summary=support_summary,
            )
        )

    return updated
