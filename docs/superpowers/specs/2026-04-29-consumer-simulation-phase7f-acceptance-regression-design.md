# MiroConsumer Phase 7F 验收回归规格

## 1. 文档状态

| 字段 | 内容 |
|---|---|
| 日期 | 2026-04-29 |
| 子阶段 | 7F |
| 子阶段名称 | 验收回归 |
| 上游依赖 | Phase 7A 至 7E 全部交付物 |
| 下游依赖 | 无（Phase 7 最终子阶段） |
| 文档状态 | 审核基线 |

## 2. 依赖声明

### 2.1 输入依赖

- Phase 7A 交付的 repository factory、全部 SQLAlchemy repositories、contract tests。
- Phase 7B 交付的 QueueTaskExecutor、worker recovery、dead-letter queue、idempotency。
- Phase 7C 交付的 simulation lock、branch fork lock、report generation lock、optimistic version、409 mapping。
- Phase 7D 交付的 LLM budget manager、run estimate、trace logging、audit chain API。
- Phase 7E 交付的 production Dockerfiles、docker-compose.prod.yml、gunicorn、nginx、env var governance。
- Phase 6F 至 Phase 6I 稳定 schema（只读引用，禁止修改）。

### 2.2 输出依赖

Phase 7F 为 Phase 7 最终子阶段，无下游依赖。

## 3. 交付物

### 3.1 Whole-Phase Smoke Test

必须新增以下文件：

```text
backend/tests/smoke/test_whole_phase_consumer_flow.py
scripts/smoke_consumer_flow.py
```

Smoke 流程固定为以下 14 步：

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

每一步必须断言 HTTP status 与 response schema。

### 3.2 Golden Case Regression

必须新增目录：

```text
backend/tests/golden_cases/
```

必须包含五个案例文件：

```text
high_price_new_product.json
low_sugar_health_food.json
packaging_redesign.json
ab_copy_test.json
negative_review_repair.json
```

每个案例文件必须包含以下结构：

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

Regression 必须验证以下规则：

- 正确 claim 出现。
- 正确 risk 出现。
- 正确 skeptic segment 出现。
- 修复证据被识别。
- forbidden strong claims 未出现。
- weak evidence 被降级。

### 3.3 Rollback Gates

必须定义以下 rollback 规则：

- Smoke test 失败时禁止合并到主分支。
- Golden case regression 失败时禁止合并到主分支。
- Contract test 失败时禁止合并到主分支。
- `docker-compose.prod.yml` 配置校验失败时禁止合并到主分支。
- `git diff --check` 输出非空时禁止合并到主分支。

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
python -m pytest tests/smoke/test_whole_phase_consumer_flow.py -q
python -m pytest tests/smoke/test_phase7_rollback_modes.py -q
python -m pytest tests/golden_cases/ -q
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

- 修改 repository 表结构（归属 Phase 7A）。
- 实现队列逻辑（归属 Phase 7B）。
- 实现并发锁逻辑（归属 Phase 7C）。
- 实现成本预算控制（归属 Phase 7D）。
- 修改部署配置（归属 Phase 7E）。
- 修改 consumer API response schema。
- 新增消费者模拟内核或渠道规则。
- 新增前端产品面。

## 5. 退出条件

Phase 7F 退出必须同时满足：

1. `test_whole_phase_consumer_flow.py` 存在且覆盖 14 步 smoke 流程。
2. Smoke 流程每一步断言 HTTP status 与 response schema。
3. `scripts/smoke_consumer_flow.py` 存在且作为独立脚本可运行。
4. `backend/tests/golden_cases/` 目录存在。
5. 五个 golden case 文件（high_price_new_product、low_sugar_health_food、packaging_redesign、ab_copy_test、negative_review_repair）全部存在。
6. 每个 golden case 包含 `input_materials`、`expected_propagating_claims`、`expected_risks`、`expected_skeptic_segments`、`expected_repair_evidence`、`forbidden_strong_claims`。
7. Golden case regression 验证正确 claim 出现。
8. Golden case regression 验证正确 risk 出现。
9. Golden case regression 验证正确 skeptic segment 出现。
10. Golden case regression 验证修复证据被识别。
11. Golden case regression 验证 forbidden strong claims 未出现。
12. Golden case regression 验证 weak evidence 被降级。
13. Repository contract tests 在 CI 中通过。
14. Smoke test 在 CI 中通过。
15. Golden case regression 在 CI 中通过。
16. 全量后端测试在 CI 中通过。
17. 前端 node 测试在 CI 中通过。
18. 前端 build 在 CI 中通过。
19. `docker compose -f docker-compose.prod.yml config` 在 CI 中通过。
20. `git diff --check` 在 CI 中无输出。
21. 以上任一 CI gate 失败时阻止代码合并。
