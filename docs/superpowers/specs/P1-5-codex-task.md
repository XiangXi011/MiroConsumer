# P1-5: 增加传播演化收敛检测

## 目标
仿真不只依赖固定 `max_rounds`，能在态度变化率或事件分布稳定时提前停止。

## 当前状态
`backend/app/services/consumer/orchestrator.py` 中轮次执行使用固定 `max_rounds`，无自动停止条件。

## 要求

### 必须做
1. 在 `backend/app/services/consumer/` 下新增 `convergence_detector.py`
2. 定义收敛指标：
   - 态度变化率（attitude_change_rate）：连续两轮态度分布的差异
   - 活跃 agent 比例（active_agent_ratio）：有传播事件的 agent 占比
3. 提供 `should_stop(round_index, current_state, previous_state) -> dict` 方法
   - 返回 `{"stop": bool, "reason": str, "metrics": dict}`
4. 收敛阈值可配置（通过参数传入，有合理默认值）
5. 在 `orchestrator.py` 中集成：每轮结束后检查收敛条件
6. 未收敛时仍受 `max_rounds` 限制

### 不要做什么
- 不删除 `max_rounds` 参数
- 不改变默认工作流输出结构
- 不修改认知引擎逻辑

## 验收标准
1. `convergence_detector.py` 存在且可导入
2. 单元测试覆盖收敛/未收敛两种场景
3. 现有测试不受影响
4. 收敛时报告或运行摘要可显示停止原因

## 环境
- Python: `/Users/xiangdong/.hermes/hermes-agent/venv/bin/python`
- 工作目录: `/Users/xiangdong/MiroConsumer-phase5`
- 参考: `backend/app/services/consumer/orchestrator.py`, `backend/app/services/consumer/propagation_state.py`
