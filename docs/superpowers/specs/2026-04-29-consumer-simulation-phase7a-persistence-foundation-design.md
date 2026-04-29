# MiroConsumer Phase 7A 持久化基础规格

## 1. 文档状态

| 字段 | 内容 |
|---|---|
| 日期 | 2026-04-29 |
| 子阶段 | 7A |
| 子阶段名称 | 持久化基础 |
| 上游依赖 | Phase 6J readiness gate；Phase 6F 至 Phase 6I 稳定 schema |
| 下游依赖 | Phase 7B、7C、7D、7E、7F |
| 文档状态 | 审核基线 |

## 2. 依赖声明

### 2.1 输入依赖

- Phase 6F consumer research action response schema（只读引用，禁止修改）。
- Phase 6F consumer event ontology（只读引用，禁止修改）。
- Phase 6G unified role enum（只读引用，禁止修改）。
- Phase 6G society snapshot schema（只读引用，禁止修改）。
- Phase 6H channel event schema（只读引用，禁止修改）。
- Phase 6I interview history schema（只读引用，禁止修改）。
- Phase 6J readiness gate（前置门禁，必须通过）。

### 2.2 输出依赖

Phase 7B 依赖 7A 交付的 repository factory 与 database session 基础设施。
Phase 7C 依赖 7A 交付的表结构（locks 表）用于锁持久化。
Phase 7D 依赖 7A 交付的表结构用于 trace 与 audit 数据存储。

## 3. 交付物

### 3.1 依赖包

必须修改 `backend/pyproject.toml`，新增以下依赖：

```text
sqlalchemy
alembic
psycopg[binary]
```

SQLite 使用 Python 标准库，不列入外部依赖。

### 3.2 环境变量

必须修改以下文件：

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

### 3.3 Alembic 迁移

必须新增 Alembic 迁移目录与初始迁移脚本，创建以下表：

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

JSON payload 存入 `JSON` 类型。PostgreSQL 必须使用 `JSONB`。

### 3.4 Repository 实现

必须新增以下文件：

```text
backend/app/repositories/sqlalchemy.py
backend/app/repositories/session.py
backend/app/repositories/factory.py
```

必须实现以下 repository 类：

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

### 3.5 Repository Contract Tests

必须新增以下测试文件：

```text
backend/tests/repositories/test_repository_contracts.py
backend/tests/repositories/test_sqlalchemy_repositories.py
backend/tests/repositories/test_repository_factory.py
```

同一 contract 必须跑两套实现：

- filesystem
- sqlalchemy sqlite

PostgreSQL contract 必须在 CI service container 中运行。

## 4. 禁止范围

本子阶段禁止纳入以下工作：

- 新增消费者模拟内核。
- 新增消费者渠道规则。
- 新增前端产品面。
- 修改 consumer API response schema。
- 迁移 legacy `project_type=default` 文件系统产物到数据库。
- 删除文件系统回退。
- 删除 ThreadTaskExecutor 回退。
- 删除 legacy shim。
- 实现队列逻辑（归属 Phase 7B）。
- 实现锁逻辑（归属 Phase 7C）。
- 实现成本估算逻辑（归属 Phase 7D）。
- 实现部署配置（归属 Phase 7E）。
- 实现冒烟测试（归属 Phase 7F）。

## 5. 退出条件

Phase 7A 退出必须同时满足：

1. `backend/pyproject.toml` 包含 sqlalchemy、alembic、psycopg[binary]。
2. `backend/app/config.py` 新增 `DB_URL` 等变量与校验逻辑。
3. `.env.example` 包含 `DB_URL` 等全部数据库变量。
4. Alembic 初始迁移存在且能创建全部 20 张表。
5. `SQLAlchemyProjectRepository` 通过全部 contract tests。
6. `SQLAlchemySimulationRepository` 通过全部 contract tests。
7. `SQLAlchemyBranchRepository` 通过全部 contract tests。
8. `SQLAlchemyReportRepository` 通过全部 contract tests。
9. `SQLAlchemyBenchmarkRepository` 通过全部 contract tests。
10. `SQLAlchemyConsumerStateRepository` 通过全部 contract tests。
11. `SQLAlchemyConsumerProjectResearchProvider` 通过全部 contract tests。
12. Repository factory 在 `DB_URL` 为空时返回 filesystem repositories。
13. Repository factory 在 `DB_URL=sqlite:///...` 时返回 SQLAlchemy SQLite repositories。
14. Repository factory 在 `DB_URL=postgresql+psycopg://...` 时返回 SQLAlchemy PostgreSQL repositories。
15. PostgreSQL contract tests 在 CI service container 中通过。
16. 应用服务中不存在直接实例化 filesystem repository 的代码。
