"""Build structured evidence digests for society reasoning prompts."""

from __future__ import annotations

from typing import Any, Dict, List


_ALLOWED_SOURCE_QUALITY = {"lane_a", "lane_b", "simulation", "unknown"}
_ALLOWED_CONFIDENCE = {"high", "medium", "low", "unknown"}


def build_evidence_digest(findings: List[Any]) -> List[Dict[str, Any]]:
    """Normalize research findings into prompt-safe evidence digest records."""
    digest: List[Dict[str, Any]] = []
    for finding in findings:
        if isinstance(finding, dict):
            fid = finding.get("finding_id", "")
            claim = finding.get("claim", "")
            summary = finding.get("summary")
            display_claim = summary if summary is not None else claim
            evidence_snippets = finding.get("evidence_snippets")
            supporting = (
                list(evidence_snippets) if evidence_snippets else []
                if evidence_snippets is not None
                else finding.get("supporting_evidence", [])
            )
            contradicting = finding.get("contradicting_evidence", [])
            raw_source_quality = _derive_source_quality(finding)
            raw_confidence = finding.get("confidence", "")
        else:
            fid = getattr(finding, "finding_id", "")
            claim = getattr(finding, "claim", "")
            summary = getattr(finding, "summary", None)
            display_claim = summary if summary is not None else claim
            evidence_snippets = getattr(finding, "evidence_snippets", None)
            supporting = (
                list(evidence_snippets) if evidence_snippets else []
                if evidence_snippets is not None
                else getattr(finding, "supporting_evidence", [])
            )
            contradicting = getattr(finding, "contradicting_evidence", [])
            raw_source_quality = _derive_source_quality_from_obj(finding)
            raw_confidence = getattr(finding, "confidence", "")

        digest.append(
            {
                "finding_id": fid,
                "claim": display_claim,
                "supporting_evidence": list(supporting) if supporting else [],
                "contradicting_evidence": list(contradicting) if contradicting else [],
                "source_quality": constrain_source_quality(raw_source_quality),
                "confidence": constrain_confidence(raw_confidence),
            }
        )
    return digest


def _derive_source_quality(finding: Dict[str, Any]) -> Any:
    for key in ("source_quality", "source_label", "source_id", "lane", "source_lane"):
        value = finding.get(key, "")
        if value:
            return value
    source = finding.get("source")
    if isinstance(source, dict):
        lane = source.get("lane", "")
        if lane:
            return lane
    return ""


def _derive_source_quality_from_obj(finding: Any) -> Any:
    for key in ("source_quality", "source_label", "source_id", "lane", "source_lane"):
        value = getattr(finding, key, "")
        if value:
            return value
    source = getattr(finding, "source", None)
    if source is not None:
        lane = getattr(source, "lane", "")
        if lane:
            return lane
    return ""


def constrain_source_quality(value: Any) -> str:
    value_text = str(value).strip().lower() if value else ""
    if value_text in _ALLOWED_SOURCE_QUALITY:
        return value_text
    if "public_web" in value_text or "lane_b" in value_text:
        return "lane_b"
    if "ingested_document" in value_text or "brief_background" in value_text or "lane_a" in value_text:
        return "lane_a"
    if "auto_enrich" in value_text or "simulation" in value_text:
        return "simulation"
    return "unknown"


def constrain_confidence(value: Any) -> str:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        value_text = str(value).strip().lower() if value else ""
        return value_text if value_text in _ALLOWED_CONFIDENCE else "unknown"

    if numeric >= 0.75:
        return "high"
    if numeric >= 0.45:
        return "medium"
    if numeric > 0:
        return "low"
    return "unknown"


__all__ = ["build_evidence_digest", "constrain_confidence", "constrain_source_quality"]