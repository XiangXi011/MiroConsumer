"""蒙特卡洛验证框架 — 验证仿真结果的统计显著性.

Null-model tuning parameters are documented in
``docs/research/monte-carlo-tuning.md``. The key knobs are
``random_walk_std`` for Gaussian random-walk shock size,
``baseline_floor`` for the minimum variance scale, and
``baseline_relative_noise`` for history-based baseline jitter.
"""

import random
import math
import time
from typing import List, Dict, Optional
from dataclasses import dataclass, field


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
    sample_n: int = 0  # 样本量
    run_n: int = 0  # 重复运行次数


class MonteCarloValidator:
    """蒙特卡洛验证器.

    See ``docs/research/monte-carlo-tuning.md`` before changing the null
    model defaults; those values are part of the statistical acceptance
    contract for P3-004.
    """

    def __init__(
        self,
        seed=None,
        random_walk_std: float = 1.0,
        baseline_floor: float = 1.0,
        baseline_relative_noise: float = 0.1,
    ):
        self.rng = random.Random(seed)
        self.random_walk_std = float(random_walk_std)
        self.baseline_floor = float(baseline_floor)
        self.baseline_relative_noise = float(baseline_relative_noise)

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
            n_simulations=n,
            sample_n=n,
            run_n=1,
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

    def null_under_random_walk(
        self,
        baseline_value: float,
        n_simulations: int = 1000,
    ) -> List[float]:
        """Generate a random-walk null distribution around one baseline value."""
        scale = math.sqrt(max(abs(float(baseline_value)), self.baseline_floor))
        return [
            float(baseline_value) + self.rng.gauss(0, self.random_walk_std) * scale
            for _ in range(n_simulations)
        ]

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
                [
                    baseline
                    + self.rng.gauss(
                        0,
                        max(abs(baseline), self.baseline_floor)
                        * self.baseline_relative_noise,
                    )
                    for _ in range(n_simulations)
                ],
                n_simulations,
            )

            result = self.validate_metric(observed, null_dist, alpha)
            result.metric_name = metric_name
            result.sample_n = n_simulations
            result.run_n = 1
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


class SimulationHistory:
    """运行历史管理"""

    def __init__(self):
        self.runs: List[Dict] = []

    def record_run(self, run_id: str, metrics: Dict[str, float], seed: int | None = None, timestamp: float | None = None):
        self.runs.append({
            "run_id": run_id,
            "metrics": metrics,
            "seed": seed,
            "timestamp": timestamp if timestamp is not None else time.time(),
        })

    def get_history(self, metric_name: str | None = None) -> List[Dict]:
        if metric_name:
            return [r for r in self.runs if metric_name in r["metrics"]]
        return self.runs


class ComparisonEngine:
    """A/B 对比引擎"""

    def compare(self, run_a_metrics: Dict[str, float], run_b_metrics: Dict[str, float],
                run_a_std: Optional[Dict[str, float]] = None,
                run_b_std: Optional[Dict[str, float]] = None) -> Dict[str, Dict]:
        results = {}
        for metric in set(run_a_metrics) & set(run_b_metrics):
            a_val = run_a_metrics[metric]
            b_val = run_b_metrics[metric]
            diff = b_val - a_val
            pct = (diff / a_val * 100) if a_val != 0 else 0.0
            # Cohen's d
            pooled_std = 1.0
            if run_a_std and run_b_std and metric in run_a_std and metric in run_b_std:
                pooled_std = ((run_a_std[metric] ** 2 + run_b_std[metric] ** 2) / 2) ** 0.5
            effect_size = diff / pooled_std if pooled_std > 0 else 0
            results[metric] = {
                "a": a_val,
                "b": b_val,
                "diff": diff,
                "pct_change": pct,
                "effect_size": round(effect_size, 3),
                "effect_magnitude": "small" if abs(effect_size) < 0.2 else
                                   "medium" if abs(effect_size) < 0.8 else "large",
            }
        return results
