# Consumer Simulation Phase 7 Productionization Master Plan

## 1. Goal

Operationalize MiroConsumer so it can survive process restarts, scale beyond a single instance, and run in environments where local filesystem durability and in-process daemon threads are not acceptable operational guarantees.

Phase 7 is strictly about infrastructure hardening. It does not expand the consumer simulation kernel, product surface, or reporting model. It converts the existing architectural boundaries into production-capable implementations.

## 2. Non-Goals

- No new simulation kernels, runner channels, or propagation dynamics.
- No new frontend product surfaces, persona pack types, or evidence policies.
- No changes to the consumer API route contract or response schema.
- No migration of legacy `project_type=default` artifacts to new storage.
- Phase 7 does not deliver multi-region or high-availability clustering; it delivers the preconditions for those.

## 3. Current Evidence / Constraints

These constraints are verified by reading the current codebase, not assumed.

| Boundary | Current State | Evidence |
|---|---|---|
| Repository layer | ABCs exist (`ProjectRepository`, `SimulationRepository`, `BranchRepository`, `ReportRepository`, `BenchmarkRepository`, `ConsumerStateRepository`, `ConsumerProjectResearchProvider`) but all concrete implementations are filesystem-backed (`app/repositories/filesystem.py`). `ProjectManager` and local file paths are still the runtime reality. | `app/repositories/__init__.py` defines ABCs; `app/repositories/filesystem.py` provides `FilesystemProjectRepository`, `FilesystemSimulationRepository`, etc. |
| Task execution | `TaskExecutor` ABC exists but the default runtime is `ThreadTaskExecutor`, which spawns `threading.Thread(daemon=True)`. Background work is lost on process restart with no recovery queue. | `app/services/application/task_executor.py` lines 34-62 |
| State persistence | All simulation, branch, report, and benchmark state is JSON/JSONL on local disk. No transaction boundaries, no optimistic locking, no instance-level fencing. | `app/repositories/filesystem.py` delegates to `app/services/storage/` modules |
| Consumer research context | `ConsumerProjectResearchProvider` is an ABC, but the sole implementation still calls `ProjectManager` and `load_persisted_snapshot` internally. | `app/services/application/consumer_app_service.py` + provider wiring in `app/repositories/filesystem.py` |

## 4. Readiness Definition

MiroConsumer is "productionized" when:

1. **Persistence**: A database-backed repository implementation is available and passes the same contract tests as the filesystem implementations. The filesystem implementations remain as a local-dev fallback.
2. **Durability**: A queue-backed `TaskExecutor` implementation is available and recovers in-flight tasks across process restarts. The `ThreadTaskExecutor` remains as a local-dev fallback.
3. **Multi-instance safety**: Concurrent simulation runs, branch forks, and report generations do not corrupt shared state when more than one process serves the application.
4. **Observability**: All background task failures, database connection errors, and retry events are logged with `trace_id` correlation and stable error categories.
5. **Rollback safety**: Any Phase 7 change can be reverted to filesystem + thread executor without data loss or schema breakage.

## 5. Phase 7A - Persistence / Database Plan

### 5.1 Contract Hardening

- Run the existing `tests/repositories/test_filesystem_repositories.py` suite against a new `InMemoryRepository` harness to prove the ABC contracts are testable independent of filesystem details.
- Add missing contract tests for round-trip edge cases:
  - `save_simulation` followed by `get_simulation` within the same transaction.
  - `create_branch` + `add_intervention` + `update_branch_status` atomicity expectations.
  - `delete_project` cascades to simulations, reports, and branches.

### 5.2 Database Schema Design

- Design a relational schema for projects, simulations, branches, interventions, reports, and benchmarks.
- Preserve the existing JSON/JSONL shape as `jsonb` columns where the application layer still expects schemaless payloads.
- Add `version`, `created_at`, `updated_at`, and `instance_id` columns for optimistic locking and audit.

### 5.3 SQLAlchemy Implementation

- Implement `SQLAlchemyProjectRepository`, `SQLAlchemySimulationRepository`, `SQLAlchemyBranchRepository`, `SQLAlchemyReportRepository`, `SQLAlchemyBenchmarkRepository`, `SQLAlchemyConsumerStateRepository`, and `SQLAlchemyConsumerProjectResearchProvider`.
- Keep the implementations thin: map ABC methods to SQLAlchemy session operations, delegate JSON serialization to the same modules the filesystem layer uses.
- Provide a session factory that the Flask app context can inject.

### 5.4 Migration Strategy

- Introduce Alembic for schema migrations.
- Provide a `DB_URL` environment variable. When absent, the app continues to use filesystem repositories (backward compatibility).
- Phase 7A does **not** migrate existing filesystem artifacts to the database. It makes database persistence available for new projects.

### 5.5 Acceptance Criteria

- [ ] All repository ABCs have a passing SQLAlchemy implementation.
- [ ] `DB_URL` absent -> app boots with filesystem repositories (no regression).
- [ ] `DB_URL` present -> app boots with SQLAlchemy repositories.
- [ ] Existing backend test suite passes with filesystem repositories.
- [ ] New `tests/repositories/test_sqlalchemy_repositories.py` passes with a temporary test database.

## 6. Phase 7B - Durable Worker / Queue Plan

### 6.1 Queue Executor Contract

- Extend the `TaskExecutor` ABC with a `get_status(trace_id: str)` method so callers can poll durable task state.
- Add a `QueueTaskExecutor` implementation backed by a message broker or lightweight job queue (e.g., Celery, RQ, or a custom SQLite queue for small deployments).

### 6.2 Worker Recovery

- On worker startup, requeue or resume tasks that were `PENDING` or `RUNNING` at the time of the previous shutdown.
- Define idempotency rules for `prepare`, `run`, and `report` phases so duplicate execution is safe.

### 6.3 Integration with Repository Layer

- The queue executor must use the same repository instances as the web process so task state updates are visible to both.
- If the database repository is active, the queue executor uses database transactions for state transitions.

### 6.4 Acceptance Criteria

- [ ] `QueueTaskExecutor` passes the same observability tests as `ThreadTaskExecutor`.
- [ ] A task submitted before process restart is recoverable and eventually completes after restart.
- [ ] `ThreadTaskExecutor` remains the default when no queue broker is configured.
- [ ] Task failure categories and `trace_id` correlation are preserved across queue boundaries.

## 7. Phase 7C - Multi-Instance Safety Plan

### 7.1 State-Level Fencing

- Add `instance_id` or `lock_version` to simulation, branch, and report records.
- Prevent concurrent `run` or `report` operations on the same simulation/branch from different instances.
- Use database-level advisory locks or optimistic versioning depending on the active repository implementation.

### 7.2 Branch Fork Isolation

- Ensure that forking a branch at `fork_round > 0` copies pre-fork state atomically and that the copy cannot be modified by the parent branch's ongoing run.

### 7.3 Report Generation Isolation

- A report generation task must hold a lock on its `simulation_id` for the duration of assembly so that concurrent report requests do not produce interleaved sections.

### 7.4 Filesystem Fallback Fencing

- When running in filesystem mode, use file-based locking (e.g., `fcntl` / `msvcrt` lock) on the simulation state file to provide at least basic multi-process safety on the same host.

### 7.5 Acceptance Criteria

- [ ] Concurrent `POST /api/consumer/simulations/{id}/run` from two instances safely rejects or serializes the second request.
- [ ] Branch fork during an active parent run does not observe partially written parent state.
- [ ] Report assembly does not interleave sections when two requests arrive simultaneously.
- [ ] File-based locking passes on Windows (`msvcrt`) and POSIX (`fcntl`).

## 8. Acceptance Gates (Cross-Phase)

Every Phase 7 subproject must include:

| Gate | Verification |
|---|---|
| Contract tests | Repository ABC tests pass against both filesystem and SQLAlchemy backends. |
| Task executor tests | `ThreadTaskExecutor` and `QueueTaskExecutor` both pass observability and recovery tests. |
| Backend regression | `python -m pytest tests/ --tb=short -q` passes with filesystem fallback. |
| Frontend regression | `npm run build` and `node --test` pass (no frontend changes expected, but verify). |
| Multi-instance stress | A script that fires concurrent run/report requests from two processes and asserts no corrupted state. |
| Rollback check | Unset `DB_URL` and queue broker config; app boots and passes full suite on filesystem + threads. |

## 9. Risks

| Risk | Mitigation |
|---|---|
| Schema migration drift | Alembic from day one; every schema change is a migration script. |
| Performance regression from ORM overhead | Benchmark the filesystem vs SQLAlchemy path on the same dataset before Phase 7 closes. |
| Queue broker as a new operational dependency | Support SQLite-queue as a zero-dependency fallback; broker is opt-in. |
| Locking deadlocks in multi-instance mode | Use short-lived locks with timeouts; never hold a lock across an external API call. |
| Phase 7 scope creep into kernel/surface work | Reject any PR that changes `HybridSimulationKernel`, `PropagationState`, Vue components, or API schemas under the Phase 7 label. |

## 10. Recommended Sequencing

1. **Phase 7A.1** - Contract hardening + in-memory harness (no new infrastructure).
2. **Phase 7A.2** - Database schema + Alembic + SQLAlchemy repository implementations.
3. **Phase 7A.3** - Repository dual-mode wiring (`DB_URL` toggle) + regression pass.
4. **Phase 7B.1** - `TaskExecutor` status extension + queue executor skeleton.
5. **Phase 7B.2** - Worker recovery + idempotency rules for prepare/run/report.
6. **Phase 7B.3** - Queue/web shared repository integration + regression pass.
7. **Phase 7C.1** - Optimistic versioning / advisory locks for database mode.
8. **Phase 7C.2** - File-based locking for filesystem fallback mode.
9. **Phase 7C.3** - Multi-instance stress test + rollback verification.

## 11. Exit Criteria

Phase 7 is complete when:

- Database-backed repositories are available and toggled by `DB_URL`.
- Queue-backed task executor is available and recovers across restarts.
- Multi-instance safety is verified for both database and filesystem fallback modes.
- The full backend and frontend regression suites pass in both configurations.
- No new architecture debt is introduced in the consumer kernel, product surface, or API contracts.

## 12. Follow-On After Phase 7

After productionization is complete, the next capability waves can safely proceed with:

- Horizontal scaling and load-balancing configuration.
- Monitoring, alerting, and SLO definition.
- Backup and disaster-recovery automation.
- Larger-scale runtime parameter tuning (these now have durable state and queue recovery as a safety net).
