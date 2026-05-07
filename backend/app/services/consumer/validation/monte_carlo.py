"""蒙特卡洛验证框架 — 验证仿真结果的统计显著性"""

import random
import math
from typing import List, Dict, Optional
from dataclasses import dataclass


@dataclass
class ValidationResult:
    """验证结果"""
    metric_name: str
    observed_value: float
    null_mean: float
    null_std: float
    z_score: float
    p_value: float
    significant: bool  # p < 0.05
    confidence_interval: tuple
    n_simulations: int


class MonteCarloValidator:
    """蒙特卡洛验证器"""

    def __init__(self, seed=None):
        self.rng = random.Random(seed)

    def validate_metric(self,
                        observed: float,
                        null_distribution: List[float],
                        alpha: float = 0.05) -> ValidationResult:
        """验证单个指标是否显著偏离零假设分布"""
        n = len(null_distribution)
        if n == 0:
            raise ValueError("null_distribution cannot be empty")

        mean = sum(null_distribution) / n
        variance = sum((x - mean) ** 2 for x in null_distribution) / n
        std = math.sqrt(variance) if variance > 0 else 1e-10

        z_score = (observed - mean) / std

        p_value = self._approx_p_value(abs(z_score))

        margin = 1.96 * std / math.sqrt(n)
        ci = (mean - margin, mean + margin)

        return ValidationResult(
            metric_name="",
            observed_value=observed,
            null_mean=mean,
            null_std=std,
            z_score=z_score,
            p_value=p_value,
            significant=p_value < alpha,
            confidence_interval=ci,
            n_simulations=n
        )

    def generate_null_distribution(self,
                                    base_values: List[float],
                                    n_simulations: int = 1000) -> List[float]:
        """生成零假设分布（随机打乱）"""
        null_values = []
        for _ in range(n_simulations):
            shuffled = base_values.copy()
            self.rng.shuffle(shuffled)
            null_values.append(sum(shuffled) / len(shuffled))
        return null_values

    def validate_simulation_results(self,
                                     observed_metrics: Dict[str, float],
                                     baseline_metrics: Dict[str, float],
                                     n_simulations: int = 1000,
                                     alpha: float = 0.05) -> Dict[str, ValidationResult]:
        """批量验证仿真结果"""
        results = {}
        for metric_name, observed in observed_metrics.items():
            baseline = baseline_metrics.get(metric_name)
            if baseline is None:
                continue

            null_dist = self.generate_null_distribution(
                [baseline + self.rng.gauss(0, abs(baseline) * 0.1) for _ in range(n_simulations)],
                n_simulations
            )

            result = self.validate_metric(observed, null_dist, alpha)
            result.metric_name = metric_name
            results[metric_name] = result

        return results

    @staticmethod
    def _approx_p_value(z: float) -> float:
        """近似双尾 p 值（正态分布）"""
        t = 1.0 / (1.0 + 0.2316419 * z)
        d = 0.3989422804014327
        p = d * math.exp(-z * z / 2.0) * (
            t * (0.3193815 + t * (-0.3565638 + t * (1.781478 + t * (-1.821256 + t * 1.330274))))
        )
        return 2.0 * p
