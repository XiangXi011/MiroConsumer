"""蒙特卡洛验证框架测试"""

import math
import sys
import pytest

# Mock missing external dependencies before importing app.services
from unittest.mock import MagicMock
for mod_name in [
    "zep_cloud", "zep_cloud.client", "zep_cloud.types",
    "zep_cloud.types.graph", "zep_cloud.types.node",
    "oasis", "oasis.oasis", "oasis.oasis.Oasis",
]:
    if mod_name not in sys.modules:
        sys.modules[mod_name] = MagicMock()

from app.services.consumer.validation.monte_carlo import (
    MonteCarloValidator,
    ValidationResult,
    SimulationHistory,
    ComparisonEngine,
)


class TestMonteCarloValidator:

    def test_significant_deviation_detected(self):
        """明显偏离的观测值应被检测为 significant"""
        validator = MonteCarloValidator(seed=42)
        null_dist = [100.0 + validator.rng.gauss(0, 1) for _ in range(1000)]
        result = validator.validate_metric(observed=150.0, null_distribution=null_dist)
        assert result.significant is True
        assert result.p_value < 0.05

    def test_non_significant_near_mean(self):
        """接近零假设均值的观测值不 significant"""
        validator = MonteCarloValidator(seed=42)
        null_dist = [100.0 + validator.rng.gauss(0, 10) for _ in range(5000)]
        result = validator.validate_metric(observed=100.1, null_distribution=null_dist)
        assert result.significant is False
        assert result.p_value >= 0.05

    def test_empty_distribution_raises(self):
        """空分布抛出 ValueError"""
        validator = MonteCarloValidator()
        with pytest.raises(ValueError, match="null_distribution cannot be empty"):
            validator.validate_metric(observed=1.0, null_distribution=[])

    def test_z_score_calculation(self):
        """z_score 计算正确"""
        validator = MonteCarloValidator()
        null_dist = [10.0] * 100  # 均值 10, 方差 0 → std = 1e-10
        result = validator.validate_metric(observed=10.0, null_distribution=null_dist)
        assert result.z_score == pytest.approx(0.0, abs=1e-6)

        # 均匀分布验证 z-score
        null_dist2 = [0.0, 2.0, 4.0, 6.0, 8.0, 10.0]  # mean=5, var=11.67
        result2 = validator.validate_metric(observed=11.0, null_distribution=null_dist2)
        expected_z = (11.0 - result2.null_mean) / result2.null_std
        assert result2.z_score == pytest.approx(expected_z, abs=1e-6)

    def test_p_value_in_range(self):
        """p_value 在 [0, 1] 范围内"""
        validator = MonteCarloValidator(seed=42)
        for z in [0.0, 0.5, 1.0, 1.96, 2.58, 5.0, 10.0]:
            p = MonteCarloValidator._approx_p_value(z)
            assert 0.0 <= p <= 1.0 + 1e-9, f"p_value {p} out of range for z={z}"

    def test_generate_null_distribution_length(self):
        """generate_null_distribution 返回正确长度"""
        validator = MonteCarloValidator(seed=42)
        base = [1.0, 2.0, 3.0, 4.0, 5.0]
        result = validator.generate_null_distribution(base, n_simulations=500)
        assert len(result) == 500

    def test_validate_simulation_results_batch(self):
        """批量验证多个指标"""
        validator = MonteCarloValidator(seed=42)
        observed = {"metric_a": 120.0, "metric_b": 50.0, "metric_c": 5.0}
        baseline = {"metric_a": 100.0, "metric_b": 50.0, "metric_c": 5.0}

        results = validator.validate_simulation_results(
            observed, baseline, n_simulations=500, alpha=0.05
        )
        assert set(results.keys()) == {"metric_a", "metric_b", "metric_c"}
        for name, r in results.items():
            assert isinstance(r, ValidationResult)
            assert r.metric_name == name
            assert r.n_simulations == 500

    def test_confidence_interval_contains_null_mean(self):
        """置信区间包含零假设均值"""
        validator = MonteCarloValidator(seed=42)
        null_dist = [50.0 + validator.rng.gauss(0, 5) for _ in range(2000)]
        result = validator.validate_metric(observed=55.0, null_distribution=null_dist)
        lo, hi = result.confidence_interval
        assert lo <= result.null_mean <= hi

    def test_validation_result_fields(self):
        """ValidationResult 字段完整性"""
        validator = MonteCarloValidator(seed=42)
        null_dist = [10.0 + validator.rng.gauss(0, 2) for _ in range(1000)]
        result = validator.validate_metric(observed=10.0, null_distribution=null_dist)
        assert isinstance(result, ValidationResult)
        assert result.observed_value == 10.0
        assert result.null_std > 0
        assert isinstance(result.significant, bool)
        assert len(result.confidence_interval) == 2

    def test_skip_metric_without_baseline(self):
        """observed 中有但 baseline 中没有的指标被跳过"""
        validator = MonteCarloValidator(seed=42)
        observed = {"a": 1.0, "b": 2.0}
        baseline = {"a": 1.0}  # b 没有 baseline
        results = validator.validate_simulation_results(observed, baseline, n_simulations=100)
        assert "a" in results
        assert "b" not in results


class TestSimulationHistory:

    def test_record_and_get_history(self):
        h = SimulationHistory()
        h.record_run("run-1", {"accuracy": 0.85, "latency": 120.0}, seed=42, timestamp=1000.0)
        h.record_run("run-2", {"accuracy": 0.90, "latency": 110.0}, seed=43, timestamp=2000.0)

        assert len(h.get_history()) == 2
        assert h.get_history()[0]["run_id"] == "run-1"

    def test_get_history_by_metric(self):
        h = SimulationHistory()
        h.record_run("run-1", {"accuracy": 0.85}, seed=42)
        h.record_run("run-2", {"latency": 110.0}, seed=43)
        h.record_run("run-3", {"accuracy": 0.90, "latency": 100.0}, seed=44)

        acc_runs = h.get_history("accuracy")
        assert len(acc_runs) == 2
        assert all("accuracy" in r["metrics"] for r in acc_runs)

        lat_runs = h.get_history("latency")
        assert len(lat_runs) == 2

    def test_get_history_missing_metric(self):
        h = SimulationHistory()
        h.record_run("run-1", {"accuracy": 0.85}, seed=42)

        assert h.get_history("nonexistent") == []

    def test_empty_history(self):
        h = SimulationHistory()
        assert h.get_history() == []


class TestComparisonEngine:

    def test_compare_basic(self):
        engine = ComparisonEngine()
        a = {"accuracy": 0.80, "latency": 100.0}
        b = {"accuracy": 0.90, "latency": 80.0}

        result = engine.compare(a, b)

        assert result["accuracy"]["a"] == 0.80
        assert result["accuracy"]["b"] == 0.90
        assert result["accuracy"]["diff"] == pytest.approx(0.10)
        assert result["accuracy"]["pct_change"] == pytest.approx(12.5)

        assert result["latency"]["diff"] == pytest.approx(-20.0)
        assert result["latency"]["pct_change"] == pytest.approx(-20.0)

    def test_compare_only_common_metrics(self):
        engine = ComparisonEngine()
        a = {"accuracy": 0.80, "extra_a": 1.0}
        b = {"accuracy": 0.90, "extra_b": 2.0}

        result = engine.compare(a, b)

        assert set(result.keys()) == {"accuracy"}

    def test_compare_zero_baseline(self):
        engine = ComparisonEngine()
        a = {"metric": 0.0}
        b = {"metric": 5.0}

        result = engine.compare(a, b)

        assert result["metric"]["diff"] == 5.0
        assert result["metric"]["pct_change"] == 0.0  # division by zero guard

    def test_compare_identical(self):
        engine = ComparisonEngine()
        m = {"x": 42.0, "y": 7.0}

        result = engine.compare(m, m)

        for metric in result:
            assert result[metric]["diff"] == 0.0
            assert result[metric]["pct_change"] == 0.0
