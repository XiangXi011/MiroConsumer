# MiroConsumer Phase 7 生产化执行规格

## 1. 文档状态

| 字段 | 内容 |
|---|---|
| 日期 | 2026-04-28 |
| 阶段 | Phase 7 |
| 阶段名称 | 生产化 |
| 目标工作区 | `D:\project\MiroFish\.worktrees\phase5a-identity` |
| 目标分支 | `codex/phase5-closure` |
| 文档状态 | 审核基线 |

## 2. 阶段目标

Phase 7 必须把 MiroConsumer 从本地文件系统与进程内线程模型升级为生产部署架构。

本阶段完成后，系统必须支持：

- 数据库持久化。
- 文件系统回退。
- 耐久任务队列。
- Worker 恢复。
- 多实例写入安全。
- 成本控制。
- 运行追踪。
- 生产 Docker 部署。
- 全链路冒烟验收。

## 3. 阶段边界

### 3.1 必须交付

1. SQLAlchemy repository。
2. Alembic migration。
3. `DB_URL` 切换。
4. Repository contract tests。
5. QueueTaskExecutor。
6. SQLite queue 本地模式。
7. Redis RQ 生产模式。
8. Worker recovery。
9. Task retry。
10. Dead-letter queue。
11. Simulation lock。
12. Branch fork lock。
13. Report generation lock。
14. Optimistic version。
15. Advisory lock。
16. File lock 回退。
17. LLM budget manager。
18. Run cost estimate。
19. Trace logging。
20. Production Docker。
21. Docker image 一致性修复。
22. 环境变量治理。
23. Whole-phase smoke test。
24. Golden case regression。

### 3.2 禁止纳入

本阶段禁止纳入以下工作：

- 新增消费者模拟内核。
- 新增消费者渠道规则。
- 新增前端产品面。
- 修改 consumer API response schema。
- 迁移 legacy `project_type=default` 文件系统产物到数据库。
- 删除文件系统回退。
- 删除 ThreadTaskExecutor 回退。
- 删除 legacy shim。

## 4. 数据库化

### 4.1 依赖

必须修改：

```text
backend/pyproject.toml
```

必须新增依赖：

```text
sqlalchemy
alembic
psycopg[binary]
```

SQLite 使用 Python 标准库。

### 4.2 配置

必须修改：

```text
backend/app/config.py
.env.example
```

必须新增环境变量：

```env
DB_URL=
DB_POOL_SIZE=5
DB_MAX_OVERFLOW=10
DB_STATEMENT_TIMEOUT_SECONDS=30
```

切换规则固定为：

- `DB_URL` 为空：使用文件系统 repositories。
- `DB_URL` 以 `sqlite:///` 开头：使用 SQLAlchemy SQLite repositories。
- `DB_URL` 以 `postgresql+psycopg://` 开头：使用 SQLAlchemy PostgreSQL repositories。
- 其他 scheme：启动失败。

### 4.3 Schema

必须新增 Alembic 迁移。

必须创建表：

```text
projects
consumer_briefs
simulations
simulation_runs
society_agents
persona_packs
round_snapshots
consumer_events
branches
interventions
reports
report_sections
research_assets
benchmarks
benchmark_replays
memory_entries
tasks
task_attempts
dead_letters
locks
```

所有业务表必须包含：

```text
id
created_at
updated_at
version
```

所有 simulation 子表必须包含：

```text
simulation_id
run_id
```

JSON payload 必须存入 `JSON` 类型。PostgreSQL 必须使用 `JSONB`。

### 4.4 Repository 实现

必须新增：

```text
backend/app/repositories/sqlalchemy.py
backend/app/repositories/session.py
backend/app/repositories/factory.py
```

必须实现：

- `SQLAlchemyProjectRepository`
- `SQLAlchemySimulationRepository`
- `SQLAlchemyBranchRepository`
- `SQLAlchemyReportRepository`
- `SQLAlchemyBenchmarkRepository`
- `SQLAlchemyConsumerStateRepository`
- `SQLAlchemyConsumerProjectResearchProvider`

Factory 规则固定为：

```python
if Config.DB_URL:
    return SQLAlchemy repositories
return Filesystem repositories
```

应用服务禁止直接实例化 filesystem repository。应用服务必须从 repository factory 获取实例。

### 4.5 Repository Contract Tests

必须新增：

```text
backend/tests/repositories/test_repository_contracts.py
backend/tests/repositories/test_sqlalchemy_repositories.py
backend/tests/repositories/test_repository_factory.py
```

同一 contract 必须跑两套实现：

- filesystem
- sqlalchemy sqlite

PostgreSQL contract 必须在 CI service container 中运行。

## 5. 队列化

### 5.1 TaskExecutor Contract

必须修改：

```text
backend/app/services/application/task_executor.py
```

`TaskExecutor` 必须新增：

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

### 5.2 QueueTaskExecutor

必须新增：

```text
backend/app/services/application/queue_task_executor.py
backend/app/services/application/sqlite_queue.py
backend/app/services/application/rq_queue.py
backend/app/worker.py
```

队列后端规则固定为：

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

### 5.3 Worker Recovery

Worker 启动时必须执行：

1. 查找 `RUNNING` 且 `updated_at` 超过 timeout 的任务。
2. 把任务状态改为 `PENDING`。
3. 增加 attempt。
4. 超过 retry limit 的任务写入 dead letters。
5. 记录 trace log。

### 5.4 Idempotency

以下任务必须具备幂等规则：

| 任务 | 幂等键 |
|---|---|
| prepare simulation | `simulation_id:prepare` |
| run simulation | `simulation_id:run:<run_id>` |
| generate report | `simulation_id:report:<report_id>` |
| resume branch | `simulation_id:branch:<branch_id>:resume` |
| research action | `simulation_id:research_action:<action_hash>` |

重复提交必须返回既有 `trace_id`。

## 6. 多实例安全

### 6.1 锁类型

必须实现三类锁：

```text
simulation_run_lock
branch_fork_lock
report_generation_lock
```

### 6.2 数据库锁

PostgreSQL 模式必须使用 advisory lock。

SQLite 模式必须使用事务锁。

文件系统模式必须使用文件锁：

- Windows：`msvcrt`
- POSIX：`fcntl`

### 6.3 写入规则

硬性规则：

- 同一个 simulation 禁止两个 run 同时写 rounds。
- 同一个 branch 禁止重复 resume。
- branch fork 必须原子复制 pre-fork state。
- report generation 必须持有 report lock。
- report sections 禁止交叉写入。
- lock timeout 必须返回 409。

### 6.4 Optimistic Version

所有 repository update 必须检查 `version`。

版本冲突必须抛出 `ConcurrencyConflictError`。

API 必须把版本冲突映射为 409。

## 7. 成本控制

### 7.1 Budget Manager

必须新增：

```text
backend/app/services/application/llm_budget_manager.py
```

必须控制：

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

### 7.2 Run Estimate

启动 simulation 前必须返回估算：

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

当估算超过 `LLM_BUDGET_LIMIT` 时必须返回 `blocked` 并拒绝启动。

## 8. 运行追踪

### 8.1 Trace Fields

所有日志必须包含：

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

缺失字段必须填空字符串。

### 8.2 Report Audit Chain

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

## 9. 存储后端

必须新增环境变量：

```env
STORAGE_BACKEND=local
S3_ENDPOINT=
S3_BUCKET=
S3_ACCESS_KEY=
S3_SECRET_KEY=
S3_REGION=us-east-1
```

切换规则固定为：

- `STORAGE_BACKEND=local`：使用本地 volume。
- `STORAGE_BACKEND=s3`：使用 S3 兼容存储。
- 其他值：启动失败。

本地存储路径固定为：

```text
backend/uploads
backend/data
```

## 10. Docker 与部署

### 10.1 镜像一致性

必须修改：

```text
docker-compose.yml
.github/workflows/*
```

规则固定为：

- `docker-compose.yml` 禁止写死 `ghcr.io/666ghj/miroconsumer`。
- 镜像名必须来自环境变量 `MIROCONSUMER_IMAGE`。
- `.env.example` 必须包含：

```env
MIROCONSUMER_IMAGE=ghcr.io/xiangxi011/miroconsumer:latest
```

### 10.2 Production Dockerfile

必须新增：

```text
Dockerfile.backend
Dockerfile.frontend
Dockerfile.worker
nginx.conf
docker-compose.prod.yml
```

容器职责固定为：

| container | 职责 |
|---|---|
| frontend | 运行 nginx，服务 Vite build 静态产物 |
| backend | 运行 gunicorn Flask API |
| worker | 运行 `backend/app/worker.py` |
| postgres | PostgreSQL |
| redis | Redis RQ |
| minio | S3 兼容对象存储 |

开发 `Dockerfile` 保留。生产部署必须使用 `docker-compose.prod.yml`。

### 10.3 Backend Server

生产 backend 必须使用 gunicorn。

启动命令固定为：

```bash
gunicorn "app:create_app()" --bind 0.0.0.0:5001 --workers 2 --threads 4 --timeout 300
```

## 11. 环境变量治理

`.env.example` 必须包含：

```env
LLM_API_KEY=
LLM_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
LLM_MODEL_NAME=qwen-plus
ZEP_API_KEY=
DB_URL=
QUEUE_BACKEND=thread
REDIS_URL=
STORAGE_BACKEND=local
S3_ENDPOINT=
S3_BUCKET=
S3_ACCESS_KEY=
S3_SECRET_KEY=
MAX_AGENTS=1000
MAX_ROUNDS=10
LLM_BUDGET_LIMIT=500
ENABLE_SOCIETY_MODE=false
ENABLE_GRAPH_MEMORY_WRITEBACK=false
MIROCONSUMER_IMAGE=ghcr.io/xiangxi011/miroconsumer:latest
```

`Config.validate()` 必须校验：

- LLM 变量。
- ZEP 变量。
- DB_URL scheme。
- QUEUE_BACKEND 取值。
- REDIS_URL 与 `QUEUE_BACKEND=rq` 的绑定。
- STORAGE_BACKEND 取值。
- S3 变量与 `STORAGE_BACKEND=s3` 的绑定。

## 12. Whole-Phase Smoke Test

必须新增：

```text
backend/tests/smoke/test_whole_phase_consumer_flow.py
scripts/smoke_consumer_flow.py
```

Smoke 流程固定为：

1. 创建 consumer brief。
2. 构建 graph。
3. prepare simulation。
4. run simulation。
5. 获取 consumer summary。
6. 生成 report。
7. 创建 branch。
8. 注入 evidence。
9. resume branch。
10. 创建 comparison。
11. 导出 research asset。
12. 获取 representative agents。
13. 执行 consumer interview。
14. 读取 audit chain。

每一步必须断言 HTTP status 和 response schema。

## 13. Golden Case Regression

必须新增目录：

```text
backend/tests/golden_cases/
```

必须包含五个案例：

```text
high_price_new_product.json
low_sugar_health_food.json
packaging_redesign.json
ab_copy_test.json
negative_review_repair.json
```

每个案例必须包含：

```json
{
  "input_materials": {},
  "expected_propagating_claims": [],
  "expected_risks": [],
  "expected_skeptic_segments": [],
  "expected_repair_evidence": [],
  "forbidden_strong_claims": []
}
```

Regression 必须验证：

- 正确 claim 出现。
- 正确 risk 出现。
- 正确 skeptic segment 出现。
- 修复证据被识别。
- forbidden strong claims 未出现。
- weak evidence 被降级。

## 14. CI Gates

CI 必须执行：

```bash
cd backend
python -m pytest tests/repositories/ -q
python -m pytest tests/services/application/test_task_executor_observability.py -q
python -m pytest tests/smoke/test_whole_phase_consumer_flow.py -q
python -m pytest tests/golden_cases/ -q
python -m pytest tests/ --tb=short -q
```

前端 CI 必须执行：

```bash
cd frontend
node --test tests/*.test.js tests/composables/*.test.js
npm run build
```

仓库 CI 必须执行：

```bash
git diff --check
```

Production compose CI 必须执行：

```bash
docker compose -f docker-compose.prod.yml config
```

## 15. 退出条件

Phase 7 退出必须同时满足：

1. `DB_URL` 为空时文件系统 repositories 启动。
2. `DB_URL=sqlite:///...` 时 SQLAlchemy SQLite repositories 启动。
3. PostgreSQL repositories 在 CI 通过 contract tests。
4. Alembic migration 完整。
5. Repository factory 替代应用服务中的直接 filesystem 实例化。
6. `TaskExecutor.get_status` 存在。
7. `QueueTaskExecutor` 支持 SQLite queue。
8. `QueueTaskExecutor` 支持 Redis RQ。
9. Worker recovery 生效。
10. Dead-letter queue 生效。
11. simulation run lock 生效。
12. branch fork lock 生效。
13. report generation lock 生效。
14. optimistic version 冲突返回 409。
15. file lock 在 Windows 与 POSIX 测试通过。
16. LLM budget manager 阻断超预算 run。
17. run estimate API 返回固定结构。
18. audit chain API 返回完整追踪链。
19. Docker image 不再写死旧 GHCR 地址。
20. Production Dockerfile 与 compose 存在。
21. `.env.example` 包含全部生产变量。
22. Whole-phase smoke test 通过。
23. Golden case regression 通过。
24. 全量后端测试通过。
25. 前端 node 测试通过。
26. 前端 build 通过。
27. `docker compose -f docker-compose.prod.yml config` 通过。
28. `git diff --check` 无输出。
