"""运行时控制层 — checkpoint/early stop/convergence"""
import hashlib
import json
import time
from typing import Dict, List, Optional
from dataclasses import dataclass, field


@dataclass
class RoundCheckpoint:
    round_id: int
    state_hash: str
    metrics: Dict
    timestamp: float
    agent_states: Dict = field(default_factory=dict)


@dataclass
class EarlyStopConfig:
    enabled: bool = True
    patience: int = 3  # 连续N轮无变化则停止
    min_rounds: int = 3  # 最少运行轮次
    event_threshold: int = 5  # 新事件数低于此值
    attitude_change_threshold: float = 0.01  # 态度变化低于此值


class RuntimeControlLayer:
    """运行时控制"""

    def __init__(self, early_stop_config: EarlyStopConfig = None):
        self.checkpoints: List[RoundCheckpoint] = []
        self.early_stop_config = early_stop_config or EarlyStopConfig()
        self._stagnant_rounds = 0

    def save_checkpoint(self, round_id: int, state: Dict, metrics: Dict):
        """保存 checkpoint"""
        state_str = json.dumps(state, sort_keys=True, default=str)
        state_hash = hashlib.md5(state_str.encode()).hexdigest()
        cp = RoundCheckpoint(
            round_id=round_id,
            state_hash=state_hash,
            metrics=metrics,
            timestamp=time.time(),
            agent_states=state,
        )
        self.checkpoints.append(cp)
        return cp

    def should_early_stop(self, round_id: int, current_metrics: Dict) -> tuple:
        """判断是否应该提前停止"""
        config = self.early_stop_config
        if not config.enabled:
            return False, ""
        if round_id < config.min_rounds:
            return False, ""

        if len(self.checkpoints) < 1:
            return False, ""

        prev = self.checkpoints[-1].metrics
        new_events = current_metrics.get("new_events", 0)
        attitude_change = abs(
            current_metrics.get("avg_attitude", 0) - prev.get("avg_attitude", 0)
        )

        if (
            new_events < config.event_threshold
            and attitude_change < config.attitude_change_threshold
        ):
            self._stagnant_rounds += 1
        else:
            self._stagnant_rounds = 0

        if self._stagnant_rounds >= config.patience:
            return (
                True,
                f"Converged: {self._stagnant_rounds} consecutive rounds with no significant change",
            )

        return False, ""

    def get_resume_point(self, round_id: int = -1) -> Optional[RoundCheckpoint]:
        """获取恢复点"""
        if not self.checkpoints:
            return None
        if round_id == -1:
            return self.checkpoints[-1]
        for cp in reversed(self.checkpoints):
            if cp.round_id <= round_id:
                return cp
        return None
