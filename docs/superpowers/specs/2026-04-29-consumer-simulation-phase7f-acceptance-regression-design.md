# MiroConsumer Phase 7F 生产化验收规格

## 1. 文档状态

| 字段 | 内容 |
|---|---|
| 日期 | 2026-04-29 |
| 子阶段 | 7F |
| 子阶段名称 | 生产化验收 |
| 上游依赖 | Phase 6J readiness gate；Phase 7A 至 7E 全部交付物 |
| 下游依赖 | 无（Phase 7 最终子阶段） |
| 文档状态 | 审核基线 |

## 2. 依赖声明

### 2.1 输入依赖

- Phase 6J 交付的 consumer golden cases 与 calibration report 作为只读前置门禁。
- Phase 7A 交付的 repository factory、全部 SQLAlchemy repositories、contract tests。
- Phase 7B 交付的 QueueTaskExecutor、worker recovery、dead-letter queue、idempotency。
- Phase 7C 交付的 simulation lock、branch fork lock、report generation lock、optimistic version、409 mapping。
- Phase 7D 交付的 LLM budget manager、run estimate、trace logging、audit chain API。
- Phase 7E 交付的 production Dockerfiles、docker-compose.prod.yml、gunicorn、nginx、env var governance。
- Phase 6F 至 Phase 6I 稳定 schema（只读引用，禁止修改）。

### 2.2 输出依赖

Phase 7F 为 Phase 7 最终子阶段，无下游依赖。

## 3. 交付物

### 3.1 Production Smoke Test

必须新增以下文件：

```text
backend/tests/smoke/test_phase7_production_flow.py
scripts/smoke_consumer_flow.py
```

Production smoke 流程固定为：

1. 文件系统 repository 模式启动。
2. SQLite repository 模式启动。
3. QueueTaskExecutor thread mode 启动。
4. QueueTaskExecutor sqlite mode 启动。
5. lock service 启动。
6. run estimate API 返回固定结构。
7. audit chain API 返回固定结构。
8. local storage backend 启动。
9. production compose 配置解析通过。

每一步必须断言：

```text
HTTP status
response schema
trace_id
repository backend
task status
```

### 3.2 Phase 6J 前置门禁

Phase 7F 禁止重新定义 consumer golden cases。

Phase 7F 必须读取 Phase 6J calibration report，并验证：

- `Phase 7 entry decision` 为 `PASS`。
- End-to-end golden flow 已通过。
- Evidence gatekeeping hard rules 已通过。
- Explainability panel acceptance 已通过。

### 3.3 Rollback Gates

必须新增 rollback gate 测试文件：

```text
backend/tests/smoke/test_phase7_rollback_modes.py
```

该文件必须覆盖以下 rollback 场景验证：

- `DB_URL` 为空时回退到 filesystem repositories。
- `QUEUE_BACKEND=thread` 时回退到 ThreadTaskExecutor。
- `STORAGE_BACKEND=local` 时回退到 local storage。
- `QUEUE_BACKEND` 不为 `rq` 时 Redis 不启用。
- `DB_URL` 为空时 PostgreSQL 不启用。
- `STORAGE_BACKEND` 不为 `s3` 时 S3 不启用。

Rollback 规则固定为：

- Production smoke test 失败时禁止合并到主分支。
- Phase 6J readiness gate 失败时禁止合并到主分支。
- Contract test 失败时禁止合并到主分支。
- `docker-compose.prod.yml` 配置校验失败时禁止合并到主分支。
- `git diff --check` 输出非空时禁止合并到主分支。

### 3.4 CI Gates

后端 CI 必须执行以下命令序列：

```bash
cd backend
python -m pytest tests/repositories/ -q
python -m pytest tests/services/application/test_task_executor_contract.py -q
python -m pytest tests/services/application/test_queue_task_executor.py -q
python -m pytest tests/concurrency/ -q
python -m pytest tests/services/application/test_llm_budget_manager.py -q
python -m pytest tests/services/application/test_audit_chain_service.py -q
python -m pytest tests/services/storage/ -q
python -m pytest tests/smoke/test_phase7_production_flow.py -q
python -m pytest tests/smoke/test_phase7_rollback_modes.py -q
python -m pytest tests/ --tb=short -q
```

前端 CI 必须执行以下命令序列：

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

## 4. 禁止范围

本子阶段禁止纳入以下工作：

- repository schema 新增。
- queue backend 新增。
- lock 行为新增。
- budget 行为新增。
- audit chain 行为新增。
- storage backend 新增。
- Dockerfile 行为新增。
- consumer golden case 行为新增。
- 既有 API response schema 修改。

## 5. 退出条件

Phase 7F 退出必须同时满足：

1. Phase 6J calibration report 的 `Phase 7 entry decision` 为 `PASS`。
2. Production smoke test 通过。
3. Rollback gates 通过。
4. Repository tests 通过。
5. Queue tests 通过。
6. Concurrency tests 通过。
7. Budget tests 通过。
8. Audit chain tests 通过。
9. Storage tests 通过。
10. 全量后端测试通过。
11. 前端 node 测试通过。
12. 前端 build 通过。
13. `docker compose -f docker-compose.prod.yml config` 通过。
14. `git diff --check` 无输出。
15. Phase 7 总规格的总退出条件全部通过。
