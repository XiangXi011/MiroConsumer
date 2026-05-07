"""Tests for P1-7.7: DriftDetector."""

from pathlib import Path
import sys

BACKEND_ROOT = Path(__file__).resolve().parents[3]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

import pytest

from app.services.consumer.drift_detector import DriftDetector, DriftSignal, DriftReport


class TestDriftDetectorCompareBaselineVsCurrent:
    """Tests for compare_baseline_vs_current."""

    def test_stable_metrics(self):
        detector = DriftDetector(threshold=0.1)
        baseline = {"reach_rate": 0.5, "cascade_depth": 3}
        current = {"reach_rate": 0.5, "cascade_depth": 3}
        signals = detector.compare_baseline_vs_current(baseline, current)
        assert len(signals) == 2
        assert all(s.direction == "stable" for s in signals)
        assert all(s.drift_magnitude == 0.0 for s in signals)

    def test_upward_drift(self):
        detector = DriftDetector(threshold=0.1)
        baseline = {"reach_rate": 0.3}
        current = {"reach_rate": 0.8}
        signals = detector.compare_baseline_vs_current(baseline, current)
        assert len(signals) == 1
        assert signals[0].direction == "up"
        assert abs(signals[0].drift_magnitude - 0.5) < 1e-6

    def test_downward_drift(self):
        detector = DriftDetector(threshold=0.1)
        baseline = {"trust_decay_rate": 0.7}
        current = {"trust_decay_rate": 0.2}
        signals = detector.compare_baseline_vs_current(baseline, current)
        assert len(signals) == 1
        assert signals[0].direction == "down"

    def test_ignores_keys_only_in_one_dict(self):
        detector = DriftDetector()
        baseline = {"a": 0.5, "b": 0.3}
        current = {"a": 0.5, "c": 0.9}
        signals = detector.compare_baseline_vs_current(baseline, current)
        names = [s.metric_name for s in signals]
        assert names == ["a"]  # only 'a' is common

    def test_ignores_non_numeric_values(self):
        detector = DriftDetector()
        baseline = {"mode": "quick", "count": 5}
        current = {"mode": "standard", "count": 10}
        signals = detector.compare_baseline_vs_current(baseline, current)
        assert len(signals) == 1
        assert signals[0].metric_name == "count"

    def test_handles_int_values(self):
        detector = DriftDetector(threshold=0.1)
        baseline = {"rounds": 3}
        current = {"rounds": 5}
        signals = detector.compare_baseline_vs_current(baseline, current)
        assert signals[0].drift_magnitude == 2.0
        assert signals[0].direction == "up"

    def test_empty_metrics(self):
        detector = DriftDetector()
        signals = detector.compare_baseline_vs_current({}, {})
        assert signals == []

    def test_signal_to_dict(self):
        signal = DriftSignal(
            metric_name="reach_rate",
            baseline_value=0.3,
            current_value=0.5,
            drift_magnitude=0.2,
            direction="up",
        )
        d = signal.to_dict()
        assert d["metric_name"] == "reach_rate"
        assert d["direction"] == "up"


class TestDriftDetectorGenerateReport:
    """Tests for generate_drift_report."""

    def test_no_drift_report(self):
        detector = DriftDetector(threshold=0.1)
        baseline = {"reach_rate": 0.5}
        current = {"reach_rate": 0.5}
        report = detector.generate_drift_report(baseline, current)
        assert report.overall_drift_score == 0.0
        assert "No significant drift" in report.recommendation

    def test_drift_report_with_critical_metrics(self):
        detector = DriftDetector(threshold=0.1, critical_threshold=0.25)
        baseline = {"trust_decay_rate": 0.1}
        current = {"trust_decay_rate": 0.6}
        report = detector.generate_drift_report(baseline, current)
        assert report.overall_drift_score > 0.25
        assert "CRITICAL" in report.recommendation

    def test_drift_report_with_moderate_drift(self):
        detector = DriftDetector(threshold=0.05, critical_threshold=0.3)
        baseline = {"a": 0.5, "b": 0.5}
        current = {"a": 0.6, "b": 0.55}
        report = detector.generate_drift_report(baseline, current)
        assert report.overall_drift_score > 0
        assert len(report.drift_signals) == 2
        assert "significant drift" in report.recommendation

    def test_report_to_dict(self):
        detector = DriftDetector()
        report = detector.generate_drift_report({"a": 0.5}, {"a": 0.7})
        d = report.to_dict()
        assert "overall_drift_score" in d
        assert "drift_signals" in d
        assert "recommendation" in d
        assert isinstance(d["drift_signals"], list)

    def test_empty_baseline_and_current(self):
        detector = DriftDetector()
        report = detector.generate_drift_report({}, {})
        assert report.overall_drift_score == 0.0
        assert len(report.drift_signals) == 0

    def test_custom_threshold(self):
        detector = DriftDetector(threshold=0.01)
        baseline = {"a": 0.5}
        current = {"a": 0.52}
        report = detector.generate_drift_report(baseline, current)
        assert "significant drift" in report.recommendation

    def test_mixed_metrics_report(self):
        """Realistic scenario: some metrics drift, some stay stable."""
        detector = DriftDetector(threshold=0.1)
        baseline = {
            "reach_rate": 0.8,
            "misread_rate": 0.05,
            "purchase_intent_delta": 0.6,
            "trust_decay_rate": 0.1,
        }
        current = {
            "reach_rate": 0.82,          # stable
            "misread_rate": 0.15,         # drift but below threshold
            "purchase_intent_delta": 0.3, # significant drift
            "trust_decay_rate": 0.1,      # stable
        }
        report = detector.generate_drift_report(baseline, current)
        drifted_names = [s.metric_name for s in report.drift_signals if s.drift_magnitude >= 0.1]
        assert "purchase_intent_delta" in drifted_names
        assert report.overall_drift_score > 0
