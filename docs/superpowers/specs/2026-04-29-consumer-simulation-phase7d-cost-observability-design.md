# MiroConsumer Phase 7D 成本可观测规格

## 1. 文档状态

| 字段 | 内容 |
|---|---|
| 日期 | 2026-04-29 |
| 子阶段 | 7D |
| 子阶段名称 | 成本可观测 |
| 上游依赖 | Phase 7A 交付的 repository、database session；Phase 7B 交付的 QueueTaskExecutor、trace_id；Phase 7C 交付的 lock/conflict 行为 |
| 下游依赖 | Phase 7E、7F |
| 文档状态 | 审核基线 |

## 2. 依赖声明

### 2.1 输入依赖

- Phase 7A 交付的 repository、table 用于读取 simulation、event、report、finding、source、agent、channel 数据以组装 audit chain。
- Phase 7B 交付的 `trace_id` 生成机制与任务状态追踪。
- Phase 7C 交付的 lock/conflict 行为（用于并发场景下 trace 与 audit 的完整性验证）。
- Phase 6F 至 Phase 6I 稳定 schema（只读引用，禁止修改）。

### 2.2 输出依赖

Phase 7E 依赖 7D 交付的 env var 治理规范用于 `.env.example` 与 `docker-compose.prod.yml` 环境变量注入。
Phase 7F 依赖 7D 交付的 audit chain API 用于冒烟测试中的追踪链验证。

## 3. 交付物

### 3.1 LLM Budget Manager

必须新增：

```text
backend/app/services/application/llm_budget_manager.py
```

必须控制以下维度：

- per-run token estimate。
- per-run max LLM calls。
- deep reasoning ratio。
- max agents。
- max rounds。
- sampling strategy。
- early stop。
- deterministic fallback。

环境变量固定为：

```env
LLM_BUDGET_LIMIT=500
LLM_DEEP_REASONING_RATIO=0.1
MAX_AGENTS=1000
MAX_ROUNDS=10
ENABLE_DETERMINISTIC_FALLBACK=true
```

当估算值超过 `LLM_BUDGET_LIMIT` 时，budget manager 必须拒绝 run 启动。

### 3.2 Run Estimate

启动 simulation 前必须返回估算结构：

```json
{
  "agents_count": 200,
  "rounds_count": 10,
  "estimated_llm_calls": 80,
  "cost_level": "medium",
  "estimated_duration_seconds": 600
}
```

`cost_level` 取值固定为：

```text
low
medium
high
blocked
```

当估算超过 `LLM_BUDGET_LIMIT` 时返回 `blocked` 并拒绝启动。

### 3.3 Trace Logging

所有日志必须包含以下字段：

```text
trace_id
run_id
simulation_id
branch_id
agent_id
channel_id
event_id
finding_id
source_id
task_id
```

缺失字段填空字符串，不允许省略字段。

Trace log 必须输出为结构化应用日志，包含上述固定 10 个 trace 字段。Phase 7D 禁止新增数据库表。

### 3.4 Audit Chain API

系统必须支持以下追踪链：

```text
report conclusion
  -> finding_id
  -> source_id
  -> round_snapshot_id
  -> event_id
  -> agent_id
  -> channel_id
  -> task_id
  -> trace_id
```

必须新增：

```text
backend/app/services/application/audit_chain_service.py
```

必须新增 API：

```http
GET /api/consumer/reports/<report_id>/audit-chain
```

Audit chain 响应必须包含从 report conclusion 到 trace_id 的完整链路，每一级包含资源 ID、类型、时间戳。

## 4. 禁止范围

本子阶段禁止纳入以下工作：

- 修改 repository 表结构（归属 Phase 7A）。
- 实现队列逻辑（归属 Phase 7B）。
- 实现并发锁逻辑（归属 Phase 7C）。
- 实现生产部署配置（归属 Phase 7E）。
- 实现冒烟测试（归属 Phase 7F）。
- 修改 consumer API response schema。
- 新增消费者模拟内核或渠道规则。
- 修改 LLM 调用 SDK 本身（仅做预算控制与日志包装）。

## 5. 退出条件

Phase 7D 退出必须同时满足：

1. `llm_budget_manager.py` 存在且实现全部 8 个控制维度。
2. 当 run 估算超过 `LLM_BUDGET_LIMIT` 时，budget manager 拒绝启动并返回 `blocked`。
3. Run estimate API 返回固定 JSON 结构，包含 `agents_count`、`rounds_count`、`estimated_llm_calls`、`cost_level`、`estimated_duration_seconds`。
4. `cost_level` 取值严格限定为 `low`、`medium`、`high`、`blocked`。
5. 所有日志包含固定 10 个 trace 字段，缺失字段为空字符串。
6. Trace log 支持按 `trace_id`、`run_id`、`simulation_id` 字段过滤结构化应用日志。
7. Audit chain service 能从 report conclusion 回溯到 `trace_id`。
8. `GET /api/consumer/reports/<report_id>/audit-chain` 返回完整链路数据。
9. Audit chain 每一级包含资源 ID、类型、时间戳。
10. 全部 budget manager 单元测试通过。
11. 全部 audit chain 单元测试通过。
