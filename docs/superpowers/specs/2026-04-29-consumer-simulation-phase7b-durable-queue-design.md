# MiroConsumer Phase 7B 耐久队列规格

## 1. 文档状态

| 字段 | 内容 |
|---|---|
| 日期 | 2026-04-29 |
| 子阶段 | 7B |
| 子阶段名称 | 耐久队列 |
| 上游依赖 | Phase 7A 交付的 repository factory、database session、tasks 表 |
| 下游依赖 | Phase 7C、7D、7E、7F |
| 文档状态 | 审核基线 |

## 2. 依赖声明

### 2.1 输入依赖

- Phase 7A 交付的 `tasks` 表（用于 SQLite queue 持久化）。
- Phase 7A 交付的 `task_attempts` 表（用于重试计数）。
- Phase 7A 交付的 `dead_letters` 表（用于死信存储）。
- Phase 6F 至 Phase 6I 稳定 schema（只读引用，禁止修改）。

### 2.2 输出依赖

Phase 7C 依赖 7B 交付的 QueueTaskExecutor 状态查询接口用于并发诊断。
Phase 7D 依赖 7B 交付的 trace_id 生成与任务状态追踪用于 audit chain。
Phase 7E 依赖 7B 交付的 worker 容器启动逻辑用于 docker-compose.prod.yml 配置。

## 3. 交付物

### 3.1 TaskExecutor Contract

必须修改：

```text
backend/app/services/application/task_executor.py
```

`TaskExecutor` 必须新增以下接口：

```python
get_status(trace_id: str) -> dict
cancel(trace_id: str) -> dict
```

`submit` 返回值仍为 `trace_id`。

Task status 取值固定为：

```text
PENDING
RUNNING
SUCCEEDED
FAILED
CANCELLED
DEAD_LETTER
```

### 3.2 QueueTaskExecutor 实现

必须新增以下文件：

```text
backend/app/services/application/queue_task_executor.py
backend/app/services/application/sqlite_queue.py
backend/app/services/application/rq_queue.py
backend/app/worker.py
```

队列后端环境变量固定为：

```env
QUEUE_BACKEND=thread
REDIS_URL=
QUEUE_RETRY_LIMIT=3
QUEUE_VISIBILITY_TIMEOUT_SECONDS=900
```

切换规则固定为：

- `QUEUE_BACKEND=thread`：使用 `ThreadTaskExecutor`。
- `QUEUE_BACKEND=sqlite`：使用 SQLite queue。
- `QUEUE_BACKEND=rq`：使用 Redis RQ。
- 其他值：启动失败。

`QUEUE_BACKEND=sqlite` 必须使用数据库中的 `tasks` 表。
`QUEUE_BACKEND=rq` 必须使用 `REDIS_URL`。

### 3.3 Worker Recovery

Worker 启动时必须执行以下步骤：

1. 查找状态为 `RUNNING` 且 `updated_at` 超过 timeout 的任务。
2. 将任务状态改为 `PENDING`。
3. 增加 attempt 计数。
4. 超过 retry limit 的任务写入 dead letters。
5. 记录 trace log。

### 3.4 Retry 机制

任务失败时必须按以下规则重试：

- 重试次数上限由 `QUEUE_RETRY_LIMIT` 控制。
- 每次重试必须更新 `task_attempts` 表。
- 达到上限后任务状态变为 `DEAD_LETTER`。

### 3.5 Dead-Letter Queue

必须实现以下死信规则：

- 超过重试上限的任务写入 `dead_letters` 表。
- dead letter 记录必须包含原始 task payload、失败原因、最终 attempt 次数、写入时间。
- 提供 API 查询死信列表。

### 3.6 Idempotency

以下任务必须具备幂等规则：

| 任务 | 幂等键 |
|---|---|
| prepare simulation | `simulation_id:prepare` |
| run simulation | `simulation_id:run:<run_id>` |
| generate report | `simulation_id:report:<report_id>` |
| resume branch | `simulation_id:branch:<branch_id>:resume` |
| research action | `simulation_id:research_action:<action_hash>` |

重复提交必须返回既有 `trace_id`。

## 4. 禁止范围

本子阶段禁止纳入以下工作：

- 修改 repository 表结构（归属 Phase 7A）。
- 实现并发锁（归属 Phase 7C）。
- 实现成本预算控制（归属 Phase 7D）。
- 实现生产部署配置（归属 Phase 7E）。
- 实现冒烟测试（归属 Phase 7F）。
- 新增消费者模拟内核或渠道规则。
- 删除 ThreadTaskExecutor 回退。

## 5. 退出条件

Phase 7B 退出必须同时满足：

1. `TaskExecutor.get_status` 接口存在且返回固定 status 枚举值。
2. `TaskExecutor.cancel` 接口存在且将任务状态置为 `CANCELLED`。
3. `QueueTaskExecutor` 支持 `QUEUE_BACKEND=sqlite` 模式。
4. `QueueTaskExecutor` 支持 `QUEUE_BACKEND=rq` 模式。
5. `QUEUE_BACKEND=thread` 仍使用既有 `ThreadTaskExecutor`。
6. Worker 启动时自动执行 recovery：将超时 `RUNNING` 任务重置为 `PENDING`。
7. Worker recovery 正确增加 attempt 计数。
8. 超过 `QUEUE_RETRY_LIMIT` 的任务写入 `dead_letters` 表。
9. Dead-letter 记录包含完整 payload 与失败原因。
10. 五个任务类型（prepare、run、generate report、resume branch、research action）全部具备幂等规则。
11. 重复提交返回既有 `trace_id`，不创建新任务。
12. SQLite queue 任务在数据库 `tasks` 表中持久化。
13. Redis RQ 队列连接使用 `REDIS_URL`。
14. 无效 `QUEUE_BACKEND` 值触发启动失败。
