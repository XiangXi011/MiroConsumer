"""Explicit contracts for high-value consumer API boundaries.

These Pydantic models replace ad hoc dict handling at the app-service
boundary for comparison, replay, source-quality, and confidence payloads.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class SourceQualitySummary(BaseModel):
    """Machine-readable summary of source quality across a research snapshot."""

    source_count: int = 0
    lane_a_count: int = 0
    lane_b_count: int = 0
    average_source_confidence: float = 0.0
    average_freshness_score: float = 0.0
    trust_tier_distribution: Dict[str, int] = Field(default_factory=dict)
    coverage_tag_distribution: Dict[str, int] = Field(default_factory=dict)


class FindingConfidenceSummary(BaseModel):
    """Flattened confidence summary for a single finding."""

    finding_id: str
    confidence_label: str
    confidence_score: float


class ConfidenceSummary(BaseModel):
    """Report-level confidence summary returned by consumer APIs."""

    confidence_label: str = "unknown"
    confidence_score: float = 0.0
    confidence_reasons: List[str] = Field(default_factory=list)
    support_summary: str = ""
    replay_alignment: str = "not_replayed"
    finding_confidence_summary: List[FindingConfidenceSummary] = Field(default_factory=list)
    low_confidence_findings: List[Dict[str, Any]] = Field(default_factory=list)


class ComparisonSide(BaseModel):
    """One side of a comparison snapshot."""

    label: str
    kind: str = "run"  # run | branch | project
    id: str
    acceptance_positive: float = 0.0
    resonance_points: List[str] = Field(default_factory=list)
    risk_points: List[str] = Field(default_factory=list)


class ComparisonConfidence(BaseModel):
    """Confidence block for a single side of a comparison."""

    confidence_label: str = "unknown"
    confidence_score: float = 0.0
    confidence_reasons: List[str] = Field(default_factory=list)
    support_summary: str = ""
    evidence_gatekeeping_summary: Optional[Dict[str, Any]] = None


class ComparisonSnapshot(BaseModel):
    """Persisted comparison snapshot between two simulations, branches, or projects."""

    comparison_id: str
    mode: str  # run_vs_run | branch_vs_base | project_vs_project
    created_at: str = ""
    project_ids: List[str] = Field(default_factory=list)
    left: ComparisonSide
    right: ComparisonSide
    resonance_overlap: List[str] = Field(default_factory=list)
    recurring_risk_signals: List[str] = Field(default_factory=list)
    evidence_backed_divergences: List[Dict[str, Any]] = Field(default_factory=list)
    acceptance_delta_pp: float = 0.0
    source_overlap_count: int = 0
    left_confidence: ComparisonConfidence = Field(default_factory=ComparisonConfidence)
    right_confidence: ComparisonConfidence = Field(default_factory=ComparisonConfidence)
    comparison_confidence: Dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> ComparisonSnapshot:
        """Create from a plain dict, normalizing nested confidence blocks."""
        raw = dict(data)
        raw.setdefault("mode", "unknown")
        raw.setdefault("left", {"label": "", "id": ""})
        raw.setdefault("right", {"label": "", "id": ""})
        if isinstance(raw.get("left_confidence"), dict):
            raw["left_confidence"] = ComparisonConfidence(**raw["left_confidence"])
        else:
            raw["left_confidence"] = ComparisonConfidence()
        if isinstance(raw.get("right_confidence"), dict):
            raw["right_confidence"] = ComparisonConfidence(**raw["right_confidence"])
        else:
            raw["right_confidence"] = ComparisonConfidence()
        return cls(**raw)


class BenchmarkReplayResult(BaseModel):
    """Result of replaying a benchmark against a current report context."""

    replay_id: str
    benchmark_id: str
    project_id: Optional[str] = None
    simulation_id: Optional[str] = None
    replayed_at: str = ""
    expected_signals: Dict[str, Any] = Field(default_factory=dict)
    actual_signals: Dict[str, Any] = Field(default_factory=dict)
    alignment_status: str = "drift"  # aligned | partial | drift
    metric_deltas: Dict[str, float] = Field(default_factory=dict)
    drift_signals: List[str] = Field(default_factory=list)
    overall_score: float = 0.0
    replay_summary: str = ""
    evidence_gatekeeping_summary: Optional[Dict[str, Any]] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> BenchmarkReplayResult:
        """Create from a plain dict with optional gatekeeping backfill."""
        raw = dict(data)
        # Ensure required keys exist for backward compatibility with old snapshots
        raw.setdefault("expected_signals", {})
        raw.setdefault("actual_signals", {})
        raw.setdefault("metric_deltas", {})
        raw.setdefault("drift_signals", [])
        return cls(**raw)
