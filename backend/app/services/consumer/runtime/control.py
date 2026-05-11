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
    # B6: partial retry
    enable_partial_retry: bool = True
    max_retry_rounds: int = 2
    # B7: risk threshold
    risk_threshold: int = 0  # 新风险点低于此值
    # B8: network activation threshold
    activation_threshold: float = 0.1


class RuntimeControlLayer:
    """运行时控制"""

    def __init__(self, early_stop_config: EarlyStopConfig = None):
        self.checkpoints: List[RoundCheckpoint] = []
        self.early_stop_config = early_stop_config or EarlyStopConfig()
        self._stagnant_rounds = 0
        self._retry_rounds = 0

    def save_checkpoint(self, round_id: int, state: Dict, metrics: Dict):
        """保存 checkpoint"""
        state_str = json.dumps(state, sort_keys=True, default=str)
        state_hash = hashlib.sha256(state_str.encode()).hexdigest()
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

        # B7: 有新风险点时不收敛
        new_risks = current_metrics.get("new_risks", 0)
        if new_risks >= config.risk_threshold and config.risk_threshold > 0:
            self._stagnant_rounds = 0
            return False, ""

        # B8: 网络激活度高时不收敛
        activation = current_metrics.get("network_activation", 0)
        if activation > config.activation_threshold and config.activation_threshold > 0:
            self._stagnant_rounds = 0
            return False, ""

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

    # B6: partial retry
    def should_partial_retry(self, round_metrics: dict) -> bool:
        """判断是否应进行部分重试"""
        if not self.early_stop_config.enable_partial_retry:
            return False
        new_events = round_metrics.get("new_events", 0)
        return 0 < new_events < self.early_stop_config.event_threshold

    # B9: branch diff
    def diff_branches(self, branch_a_checkpoints: List[RoundCheckpoint], branch_b_checkpoints: List[RoundCheckpoint]) -> dict:
        """对比两个分支的 checkpoint 差异"""
        if not branch_a_checkpoints or not branch_b_checkpoints:
            return {"diff": "empty branch"}
        last_a = branch_a_checkpoints[-1].metrics
        last_b = branch_b_checkpoints[-1].metrics
        diff = {}
        for key in set(last_a) | set(last_b):
            a_val = last_a.get(key, 0)
            b_val = last_b.get(key, 0)
            if a_val != b_val:
                delta = None
                if isinstance(a_val, (int, float)) and isinstance(b_val, (int, float)):
                    delta = b_val - a_val
                diff[key] = {"a": a_val, "b": b_val, "delta": delta}
        return diff

    # B10: intervention replay
    def replay_intervention(self, checkpoints: List[RoundCheckpoint], intervention_round: int, modified_state: dict) -> list:
        """从指定轮次重放干预"""
        replay_checkpoints = [cp for cp in checkpoints if cp.round_id < intervention_round]
        replay_checkpoints.append(RoundCheckpoint(
            round_id=intervention_round,
            state_hash="intervention",
            metrics=modified_state,
            timestamp=time.time(),
        ))
        return replay_checkpoints

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


class ConvergenceDetector:
    """收敛检测器"""

    def __init__(self, window_size: int = 3, threshold: float = 0.01):
        self.window_size = window_size
        self.threshold = threshold
        self.history: List[Dict] = []

    def update(self, metrics: Dict):
        self.history.append(metrics)

    def is_converged(self) -> tuple:
        if len(self.history) < self.window_size:
            return False, ""
        recent = self.history[-self.window_size:]
        attitudes = [m.get("avg_attitude", 0) for m in recent]
        mean_att = sum(attitudes) / len(attitudes)
        variance = sum((a - mean_att) ** 2 for a in attitudes) / len(attitudes)
        if variance < self.threshold:
            return True, f"Attitude variance {variance:.4f} < threshold {self.threshold}"
        return False, ""
