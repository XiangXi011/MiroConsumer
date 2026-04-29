# MiroConsumer Phase 7C 并发安全规格

## 1. 文档状态

| 字段 | 内容 |
|---|---|
| 日期 | 2026-04-29 |
| 子阶段 | 7C |
| 子阶段名称 | 并发安全 |
| 上游依赖 | Phase 7A 交付的 repository、database session、locks 表；Phase 7B 交付的 QueueTaskExecutor |
| 下游依赖 | Phase 7D、7E、7F |
| 文档状态 | 审核基线 |

## 2. 依赖声明

### 2.1 输入依赖

- Phase 7A 交付的 `locks` 表（用于锁持久化）。
- Phase 7A 交付的 repository 的 `version` 字段（用于乐观锁）。
- Phase 7B 交付的 QueueTaskExecutor 状态查询接口。
- Phase 6F 至 Phase 6I 稳定 schema（只读引用，禁止修改）。

### 2.2 输出依赖

Phase 7D 依赖 7C 交付的并发冲突信息用于 trace logging 中的冲突事件记录。
Phase 7E 依赖 7C 交付的锁超时行为用于生产环境多 worker 配置验证。

## 3. 交付物

### 3.1 锁类型

必须实现三类锁：

```text
simulation_run_lock
branch_fork_lock
report_generation_lock
```

### 3.2 Advisory Lock（PostgreSQL 模式）

PostgreSQL 模式必须使用数据库 advisory lock。

- `simulation_run_lock` 使用 `pg_advisory_lock` 与 `pg_advisory_unlock`。
- `branch_fork_lock` 使用 `pg_advisory_lock` 与 `pg_advisory_unlock`。
- `report_generation_lock` 使用 `pg_advisory_lock` 与 `pg_advisory_unlock`。
- 锁 key 由锁类型字符串与资源 ID 组合哈希生成。
- 锁获取超时必须返回 `ConcurrencyConflictError`。

### 3.3 SQLite Transaction Lock（SQLite 模式）

SQLite 模式必须使用事务锁。

- 利用 `BEGIN IMMEDIATE` 事务获取排他锁。
- 锁超时由 `DB_STATEMENT_TIMEOUT_SECONDS` 控制。
- 锁获取超时必须返回 `ConcurrencyConflictError`。

### 3.4 File Lock（文件系统回退模式）

文件系统模式必须使用文件锁：

- Windows 平台使用 `msvcrt` 模块的锁原语。
- POSIX 平台使用 `fcntl` 模块的锁原语。
- 锁文件存放在 `backend/data/locks/` 目录下。
- 锁获取超时必须返回 `ConcurrencyConflictError`。

### 3.5 写入规则

硬性规则固定为：

- 同一个 simulation 禁止两个 run 同时写入 rounds。
- 同一个 branch 禁止重复 resume。
- branch fork 必须原子复制 pre-fork state。
- report generation 必须持有 report lock。
- report sections 禁止交叉写入。
- lock timeout 必须返回 HTTP 409。

### 3.6 Optimistic Version

所有 repository update 必须检查 `version` 字段。

- 读取记录时获取当前 `version`。
- 更新时 WHERE 子句必须包含 `version = 读取值`。
- 版本冲突必须抛出 `ConcurrencyConflictError`。
- API 层必须把 `ConcurrencyConflictError` 映射为 HTTP 409。

### 3.7 409 映射

API 层必须将以下并发冲突统一映射为 HTTP 409：

- 锁获取超时。
- 乐观版本冲突。
- 重复 branch resume。
- 重复 report generation。

409 响应体固定为：

```json
{
  "error": "conflict",
  "resource": "<resource_type>",
  "resource_id": "<resource_id>",
  "reason": "<lock_timeout|version_conflict|duplicate_operation>"
}
```

## 4. 禁止范围

本子阶段禁止纳入以下工作：

- 修改 repository 表结构（归属 Phase 7A）。
- 实现队列逻辑（归属 Phase 7B）。
- 实现成本预算控制（归属 Phase 7D）。
- 实现生产部署配置（归属 Phase 7E）。
- 实现冒烟测试（归属 Phase 7F）。
- 修改 consumer API response schema。
- 新增消费者模拟内核或渠道规则。

## 5. 退出条件

Phase 7C 退出必须同时满足：

1. `simulation_run_lock` 在 PostgreSQL 模式下使用 advisory lock。
2. `simulation_run_lock` 在 SQLite 模式下使用 transaction lock。
3. `simulation_run_lock` 在文件系统模式下使用 file lock。
4. `branch_fork_lock` 在三种模式下均正确实现。
5. `report_generation_lock` 在三种模式下均正确实现。
6. 同一个 simulation 的两个并发 run 写入 rounds 时被阻止。
7. 同一个 branch 的重复 resume 被阻止。
8. branch fork 原子复制 pre-fork state。
9. report generation 持有 report lock 时其他 report generation 被阻止。
10. 所有 repository update 检查 `version` 字段。
11. 乐观版本冲突抛出 `ConcurrencyConflictError`。
12. `ConcurrencyConflictError` 映射为 HTTP 409。
13. 锁获取超时返回 HTTP 409，响应体包含固定字段结构。
14. file lock 在 Windows 平台测试通过。
15. file lock 在 POSIX 平台测试通过。
