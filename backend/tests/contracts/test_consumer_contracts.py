"""Tests for consumer contract models."""

from pathlib import Path
import sys

BACKEND_ROOT = Path(__file__).resolve().parents[2]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

import pytest

from app.contracts.consumer_contracts import (
    BenchmarkReplayResult,
    ComparisonConfidence,
    ComparisonSide,
    ComparisonSnapshot,
    ConfidenceSummary,
    FindingConfidenceSummary,
    SourceQualitySummary,
)


class TestSourceQualitySummary:
    def test_defaults(self):
        s = SourceQualitySummary()
        assert s.source_count == 0
        assert s.average_source_confidence == 0.0

    def test_populated(self):
        s = SourceQualitySummary(
            source_count=5,
            lane_a_count=3,
            lane_b_count=2,
            average_source_confidence=0.85,
            average_freshness_score=72.5,
            trust_tier_distribution={"1": 3, "2": 2},
            coverage_tag_distribution={"user_provided": 3, "public_web": 2},
        )
        assert s.lane_a_count == 3
        assert s.coverage_tag_distribution["user_provided"] == 3


class TestConfidenceSummary:
    def test_defaults(self):
        c = ConfidenceSummary()
        assert c.confidence_label == "unknown"
        assert c.replay_alignment == "not_replayed"

    def test_with_findings(self):
        c = ConfidenceSummary(
            confidence_label="medium",
            confidence_score=0.65,
            confidence_reasons=["average_finding_confidence:0.65"],
            support_summary="Supported by 3 findings",
            replay_alignment="partial",
            finding_confidence_summary=[
                FindingConfidenceSummary(
                    finding_id="f1", confidence_label="high", confidence_score=0.8
                )
            ],
        )
        assert c.finding_confidence_summary[0].finding_id == "f1"


class TestComparisonSnapshot:
    def test_from_dict_normalizes_confidence(self):
        data = {
            "comparison_id": "cmp_123",
            "mode": "run_vs_run",
            "left": {"label": "L", "kind": "run", "id": "sim_l"},
            "right": {"label": "R", "kind": "run", "id": "sim_r"},
            "left_confidence": {"confidence_label": "high", "confidence_score": 0.8},
        }
        snap = ComparisonSnapshot.from_dict(data)
        assert snap.left_confidence.confidence_label == "high"
        assert snap.right_confidence.confidence_label == "unknown"  # default backfill

    def test_from_dict_preserves_existing_comparison_confidence(self):
        data = {
            "comparison_id": "cmp_456",
            "mode": "branch_vs_base",
            "left": {"label": "base", "kind": "run", "id": "sim_1"},
            "right": {"label": "branch", "kind": "branch", "id": "b1"},
            "comparison_confidence": {"comparison_label": "strongly_supported"},
        }
        snap = ComparisonSnapshot.from_dict(data)
        assert snap.comparison_confidence["comparison_label"] == "strongly_supported"


class TestBenchmarkReplayResult:
    def test_from_dict_backfills_optional_fields(self):
        data = {
            "replay_id": "replay_123",
            "benchmark_id": "bench_1",
            "alignment_status": "aligned",
            "overall_score": 0.92,
        }
        r = BenchmarkReplayResult.from_dict(data)
        assert r.expected_signals == {}
        assert r.actual_signals == {}
        assert r.metric_deltas == {}
        assert r.drift_signals == []

    def test_from_dict_preserves_gatekeeping(self):
        data = {
            "replay_id": "replay_456",
            "benchmark_id": "bench_2",
            "alignment_status": "drift",
            "overall_score": 0.3,
            "evidence_gatekeeping_summary": {"blocked_count": 2, "downgraded_count": 1},
        }
        r = BenchmarkReplayResult.from_dict(data)
        assert r.evidence_gatekeeping_summary["blocked_count"] == 2
