"""置信度阈值校准器 — P1-7.8

支持：
- ConfidenceThresholds: 可配置阈值数据类
- ConfidenceCalibrator: 黄金案例校准 + 历史数据自适应
- 全局 get/set/calibrated_label_from_score
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field

from app.utils.logger import get_logger

logger = get_logger("miroconsumer.confidence_calibrator")


@dataclass
class ConfidenceThresholds:
    """置信度阈值配置"""
    high: float = 0.75
    medium: float = 0.50
    low: float = 0.25

    def label_for_score(self, score: float) -> str:
        if score >= self.high:
            return "high"
        elif score >= self.medium:
            return "medium"
        elif score >= self.low:
            return "low"
        return "unknown"

    def to_dict(self) -> dict:
        return {"high": self.high, "medium": self.medium, "low": self.low}

    @classmethod
    def from_dict(cls, data: dict) -> "ConfidenceThresholds":
        return cls(
            high=data.get("high", 0.75),
            medium=data.get("medium", 0.50),
            low=data.get("low", 0.25),
        )


class ConfidenceCalibrator:
    """置信度阈值校准器"""

    def __init__(self, thresholds: ConfidenceThresholds = None, history_path: str = None):
        self.thresholds = thresholds or ConfidenceThresholds()
        self._history: List[float] = []
        self._history_path = history_path
        if history_path and Path(history_path).exists():
            self._load_history()

    def label_for_score(self, score: float) -> str:
        return self.thresholds.label_for_score(score)

    def record_score(self, score: float):
        """记录一个置信度分数用于自适应校准。"""
        self._history.append(score)

    def calibrate_from_golden_cases(
        self, golden_cases: List[Tuple[float, str]]
    ) -> ConfidenceThresholds:
        """基于黄金案例校准阈值。

        Args:
            golden_cases: [(score, expected_label), ...] 列表
        """
        if not golden_cases:
            return self.thresholds

        label_scores: Dict[str, List[float]] = {}
        for score, label in golden_cases:
            label_scores.setdefault(label, []).append(score)

        new_high = self.thresholds.high
        new_medium = self.thresholds.medium
        new_low = self.thresholds.low

        if "high" in label_scores and "medium" in label_scores:
            high_min = min(label_scores["high"])
            medium_max = max(label_scores["medium"])
            new_high = round((high_min + medium_max) / 2, 3)

        if "medium" in label_scores and "low" in label_scores:
            med_min = min(label_scores["medium"])
            low_max = max(label_scores["low"])
            new_medium = round((med_min + low_max) / 2, 3)

        if "low" in label_scores:
            low_min = min(label_scores["low"])
            # "unknown" boundary: below low
            unknown_scores = label_scores.get("unknown", [0.0])
            unknown_max = max(unknown_scores) if unknown_scores else 0.0
            new_low = round((low_min + unknown_max) / 2, 3)

        self.thresholds = ConfidenceThresholds(high=new_high, medium=new_medium, low=new_low)
        return self.thresholds

    def calibrate_from_history(self) -> ConfidenceThresholds:
        """基于历史记录自适应校准。"""
        if len(self._history) < 3:
            return self.thresholds

        sorted_scores = sorted(self._history)
        n = len(sorted_scores)

        # Use quartile-based approach
        q1_idx = n // 4
        q2_idx = n // 2
        q3_idx = (3 * n) // 4

        self.thresholds = ConfidenceThresholds(
            high=round(sorted_scores[q3_idx], 3),
            medium=round(sorted_scores[q2_idx], 3),
            low=round(sorted_scores[q1_idx], 3),
        )
        return self.thresholds

    def save_thresholds(self, path: str):
        """保存阈值到文件。"""
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.thresholds.to_dict(), f, indent=2)

    def load_thresholds(self, path: str) -> ConfidenceThresholds:
        """从文件加载阈值。"""
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.thresholds = ConfidenceThresholds.from_dict(data)
        return self.thresholds

    def save_history(self):
        """保存历史记录。"""
        if self._history_path:
            Path(self._history_path).parent.mkdir(parents=True, exist_ok=True)
            with open(self._history_path, "w", encoding="utf-8") as f:
                json.dump(self._history, f)

    def _load_history(self):
        """加载历史记录。"""
        try:
            with open(self._history_path, "r", encoding="utf-8") as f:
                self._history = json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            self._history = []


# ── 全局单例 ──────────────────────────────────────────

_default_calibrator: Optional[ConfidenceCalibrator] = None


def get_thresholds() -> ConfidenceCalibrator:
    """获取全局校准器实例。"""
    global _default_calibrator
    if _default_calibrator is None:
        _default_calibrator = ConfidenceCalibrator()
    return _default_calibrator


def set_thresholds(thresholds):
    """更新全局阈值。接受 ConfidenceThresholds 或 dict。"""
    global _default_calibrator
    if isinstance(thresholds, dict):
        thresholds = ConfidenceThresholds.from_dict(thresholds)
    _default_calibrator = ConfidenceCalibrator(thresholds=thresholds)


def calibrated_label_from_score(score: float) -> str:
    """使用全局校准器返回标签。"""
    return get_thresholds().label_for_score(score)
