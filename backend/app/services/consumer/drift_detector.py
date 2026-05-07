"""漂移检测器 — P1-7.7 对比基线与当前仿真结果"""

from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field, asdict


@dataclass
class DriftSignal:
    """单个漂移信号"""
    metric_name: str
    baseline_value: float
    current_value: float
    drift_magnitude: float
    direction: str  # "up", "down", "stable"
    significant: bool = False

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class DriftReport:
    """漂移报告"""
    overall_drift_score: float = 0.0
    drift_signals: List[DriftSignal] = field(default_factory=list)
    recommendation: str = ""
    baseline_run_id: Optional[str] = None
    current_run_id: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "overall_drift_score": self.overall_drift_score,
            "drift_signals": [s.to_dict() for s in self.drift_signals],
            "recommendation": self.recommendation,
            "baseline_run_id": self.baseline_run_id,
            "current_run_id": self.current_run_id,
        }


class DriftDetector:
    """检测仿真结果相对于基线的漂移"""

    def __init__(self, threshold: float = 0.1, critical_threshold: float = None):
        self.threshold = threshold
        self.critical_threshold = critical_threshold

    def compare_baseline_vs_current(
        self,
        baseline_metrics: Dict[str, Any],
        current_metrics: Dict[str, Any],
    ) -> List[DriftSignal]:
        """对比基线与当前指标，返回漂移信号列表。"""
        signals = []
        common_keys = set(baseline_metrics.keys()) & set(current_metrics.keys())

        for key in sorted(common_keys):
            base_val = baseline_metrics[key]
            curr_val = current_metrics[key]

            if not isinstance(base_val, (int, float)) or not isinstance(curr_val, (int, float)):
                continue

            magnitude = curr_val - base_val  # absolute difference
            abs_mag = abs(magnitude)

            if abs_mag < 1e-9:
                direction = "stable"
            elif magnitude > 0:
                direction = "up"
            else:
                direction = "down"

            signals.append(DriftSignal(
                metric_name=key,
                baseline_value=float(base_val),
                current_value=float(curr_val),
                drift_magnitude=round(abs_mag, 6),
                direction=direction,
                significant=abs_mag >= self.threshold,
            ))

        return signals

    def generate_drift_report(
        self,
        baseline_metrics: Dict[str, Any],
        current_metrics: Dict[str, Any],
    ) -> DriftReport:
        """生成完整漂移报告。"""
        signals = self.compare_baseline_vs_current(baseline_metrics, current_metrics)

        if not signals:
            return DriftReport(
                overall_drift_score=0.0,
                drift_signals=[],
                recommendation="No significant drift",
            )

        significant_count = sum(1 for s in signals if s.significant)
        total = len(signals)
        overall_score = round(significant_count / total, 3) if total else 0.0

        # Determine recommendation
        if self.critical_threshold and overall_score > self.critical_threshold:
            recommendation = "CRITICAL: significant drift detected — review simulation parameters"
        elif overall_score > 0:
            recommendation = "significant drift detected — monitor next runs"
        else:
            recommendation = "No significant drift"

        return DriftReport(
            overall_drift_score=overall_score,
            drift_signals=signals,
            recommendation=recommendation,
        )
