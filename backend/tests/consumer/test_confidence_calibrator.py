"""Tests for P1-7.8: ConfidenceCalibrator and calibrated thresholds."""

import json
from pathlib import Path
import sys

BACKEND_ROOT = Path(__file__).resolve().parents[3]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

import pytest

from app.services.consumer.confidence_calibrator import (
    ConfidenceThresholds,
    ConfidenceCalibrator,
    get_thresholds,
    set_thresholds,
    calibrated_label_from_score,
)


class TestConfidenceThresholds:
    """Unit tests for ConfidenceThresholds data class."""

    def test_default_values(self):
        t = ConfidenceThresholds()
        assert t.high == 0.75
        assert t.medium == 0.50
        assert t.low == 0.25

    def test_label_for_score_defaults(self):
        t = ConfidenceThresholds()
        assert t.label_for_score(0.9) == "high"
        assert t.label_for_score(0.75) == "high"
        assert t.label_for_score(0.6) == "medium"
        assert t.label_for_score(0.5) == "medium"
        assert t.label_for_score(0.3) == "low"
        assert t.label_for_score(0.25) == "low"
        assert t.label_for_score(0.1) == "unknown"

    def test_label_for_score_custom(self):
        t = ConfidenceThresholds(high=0.8, medium=0.6, low=0.4)
        assert t.label_for_score(0.9) == "high"
        assert t.label_for_score(0.7) == "medium"
        assert t.label_for_score(0.5) == "low"
        assert t.label_for_score(0.3) == "unknown"

    def test_to_dict_and_from_dict_roundtrip(self):
        t = ConfidenceThresholds(high=0.85, medium=0.55, low=0.3)
        d = t.to_dict()
        t2 = ConfidenceThresholds.from_dict(d)
        assert t2.high == 0.85
        assert t2.medium == 0.55
        assert t2.low == 0.3

    def test_from_dict_uses_defaults_for_missing_keys(self):
        t = ConfidenceThresholds.from_dict({"high": 0.9})
        assert t.high == 0.9
        assert t.medium == 0.50
        assert t.low == 0.25


class TestCalibratedLabelFromScore:
    """Test the global calibrated_label_from_score function."""

    def test_uses_default_thresholds(self):
        # Reset to defaults
        set_thresholds(ConfidenceThresholds())
        assert calibrated_label_from_score(0.8) == "high"
        assert calibrated_label_from_score(0.6) == "medium"
        assert calibrated_label_from_score(0.3) == "low"
        assert calibrated_label_from_score(0.1) == "unknown"

    def test_respects_changed_thresholds(self):
        original = get_thresholds()
        try:
            set_thresholds(ConfidenceThresholds(high=0.9, medium=0.7, low=0.5))
            assert calibrated_label_from_score(0.85) == "medium"
            assert calibrated_label_from_score(0.95) == "high"
            assert calibrated_label_from_score(0.6) == "low"
            assert calibrated_label_from_score(0.4) == "unknown"
        finally:
            set_thresholds(original)


class TestConfidenceScoringIntegration:
    """Test that confidence_scoring._label_from_score uses calibrated thresholds."""

    def test_label_from_score_respects_calibration(self):
        from app.services.consumer.confidence_scoring import _label_from_score

        original = get_thresholds()
        try:
            # With defaults
            set_thresholds(ConfidenceThresholds())
            assert _label_from_score(0.8) == "high"
            assert _label_from_score(0.6) == "medium"

            # Change thresholds
            set_thresholds(ConfidenceThresholds(high=0.9, medium=0.7, low=0.4))
            assert _label_from_score(0.8) == "medium"
            assert _label_from_score(0.95) == "high"
        finally:
            set_thresholds(original)


class TestConfidenceCalibratorGoldenCases:
    """Test golden-case based calibration."""

    def test_calibrate_from_golden_cases(self):
        calibrator = ConfidenceCalibrator()
        golden = [
            (0.9, "high"),
            (0.85, "high"),
            (0.8, "high"),
            (0.65, "medium"),
            (0.6, "medium"),
            (0.55, "medium"),
            (0.35, "low"),
            (0.3, "low"),
            (0.15, "unknown"),
        ]
        thresholds = calibrator.calibrate_from_golden_cases(golden)
        # high threshold should be between min-high (0.8) and max-medium (0.65)
        assert 0.65 <= thresholds.high <= 0.8
        # medium threshold should be between min-medium (0.55) and max-low (0.35)
        assert 0.35 <= thresholds.medium <= 0.55
        # Monotonicity
        assert thresholds.high > thresholds.medium > thresholds.low

    def test_calibrate_from_empty_golden_cases(self):
        calibrator = ConfidenceCalibrator()
        original_high = calibrator.thresholds.high
        thresholds = calibrator.calibrate_from_golden_cases([])
        assert thresholds.high == original_high  # unchanged

    def test_calibrate_from_single_label_group(self):
        calibrator = ConfidenceCalibrator()
        golden = [(0.9, "high"), (0.85, "high")]
        thresholds = calibrator.calibrate_from_golden_cases(golden)
        assert thresholds.high <= 0.9


class TestConfidenceCalibratorAdaptive:
    """Test adaptive (history-based) calibration."""

    def test_calibrate_from_history(self):
        calibrator = ConfidenceCalibrator()
        # Simulate a distribution of scores
        scores = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
        for s in scores:
            calibrator.record_score(s)

        thresholds = calibrator.calibrate_from_history()
        # With even distribution, thresholds should be near quartiles
        assert 0.2 <= thresholds.low <= 0.5
        assert 0.4 <= thresholds.medium <= 0.7
        assert 0.6 <= thresholds.high <= 0.9
        assert thresholds.high > thresholds.medium > thresholds.low

    def test_calibrate_from_history_insufficient_data(self):
        calibrator = ConfidenceCalibrator()
        calibrator.record_score(0.5)
        thresholds = calibrator.calibrate_from_history()
        # Should return default thresholds unchanged
        assert thresholds.high == 0.75

    def test_record_score(self):
        calibrator = ConfidenceCalibrator()
        calibrator.record_score(0.5)
        calibrator.record_score(0.7)
        assert len(calibrator._history) == 2


class TestConfidenceCalibratorPersistence:
    """Test save/load of thresholds."""

    def test_save_and_load_thresholds(self, tmp_path):
        path = str(tmp_path / "thresholds.json")
        calibrator = ConfidenceCalibrator()
        calibrator.thresholds = ConfidenceThresholds(high=0.85, medium=0.6, low=0.35)
        calibrator.save_thresholds(path)

        calibrator2 = ConfidenceCalibrator()
        loaded = calibrator2.load_thresholds(path)
        assert loaded.high == 0.85
        assert loaded.medium == 0.6
        assert loaded.low == 0.35

    def test_save_and_load_history(self, tmp_path):
        path = str(tmp_path / "history.json")
        calibrator = ConfidenceCalibrator(history_path=path)
        calibrator.record_score(0.5)
        calibrator.record_score(0.7)
        calibrator.save_history()

        calibrator2 = ConfidenceCalibrator(history_path=path)
        assert len(calibrator2._history) == 2
