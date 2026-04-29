# MiroConsumer Phase 7 生产化总规格

## 1. 文档状态

| 字段 | 内容 |
|---|---|
| 日期 | 2026-04-29 |
| 阶段 | Phase 7 |
| 阶段名称 | 生产化 |
| 目标工作区 | `D:\project\MiroFish\.worktrees\phase5a-identity` |
| 目标分支 | `codex/phase5-closure` |
| 文档状态 | 审核基线 |

## 2. 阶段依赖图

```text
Phase 6F 消费者语义激活
  -> Phase 6G 大规模消费者社会桥接
  -> Phase 6H 多渠道消费者传播
  -> Phase 6I 虚拟焦点小组
  -> Phase 6J 校准与可信度验收
  -> Phase 7A 持久化基础
  -> Phase 7B 耐久队列
  -> Phase 7C 并发安全
  -> Phase 7D 成本可观测
  -> Phase 7E 生产部署
  -> Phase 7F 生产化验收
```

## 3. 全局冻结边界

Phase 7 全量子阶段必须遵守以下冻结规则：

- 禁止修改 Phase 6F consumer research action response schema。
- 禁止修改 Phase 6F consumer event ontology。
- 禁止修改 Phase 6G unified role enum。
- 禁止修改 Phase 6G society snapshot schema。
- 禁止修改 Phase 6H channel event schema。
- 禁止修改 Phase 6I interview history schema。
- Phase 7A 启动前必须通过 Phase 6J readiness gate。
- 仅允许为稳定 schema 增加 repository、queue、lock、deployment 实现。

## 4. 子阶段索引

| 子阶段 | 文件 | 职责 |
|---|---|---|
| 7A | [phase7a-persistence-foundation-design.md](2026-04-29-consumer-simulation-phase7a-persistence-foundation-design.md) | SQLAlchemy repositories、Alembic、DB_URL 切换、repository contract tests |
| 7B | [phase7b-durable-queue-design.md](2026-04-29-consumer-simulation-phase7b-durable-queue-design.md) | TaskExecutor contract、QueueTaskExecutor、SQLite queue、Redis RQ、worker recovery、retry、dead letters、idempotency |
| 7C | [phase7c-concurrency-safety-design.md](2026-04-29-consumer-simulation-phase7c-concurrency-safety-design.md) | simulation lock、branch fork lock、report generation lock、optimistic version、advisory lock、SQLite transaction lock、file lock、409 mapping |
| 7D | [phase7d-cost-observability-design.md](2026-04-29-consumer-simulation-phase7d-cost-observability-design.md) | LLM budget manager、run estimate、trace logging、audit chain API |
| 7E | [phase7e-production-deployment-design.md](2026-04-29-consumer-simulation-phase7e-production-deployment-design.md) | storage backend、Docker image 一致性、production Dockerfiles、compose、gunicorn、nginx、env var governance |
| 7F | [phase7f-acceptance-regression-design.md](2026-04-29-consumer-simulation-phase7f-acceptance-regression-design.md) | production smoke、rollback gates、Phase 6J readiness check、CI gates |

## 5. 阶段总退出条件

Phase 7 退出必须同时满足：

1. 子阶段 7A 至 7F 各自退出条件全部达成。
2. Phase 6J readiness gate 已通过。
3. 全量后端测试通过。
4. 前端 node 测试通过。
5. 前端 build 通过。
6. `docker compose -f docker-compose.prod.yml config` 通过。
7. `git diff --check` 无输出。
