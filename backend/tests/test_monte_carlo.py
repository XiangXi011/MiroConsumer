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
