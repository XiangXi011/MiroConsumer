"""Tests for the Phase 7C concurrency lock foundation."""

import pytest

from app.config import Config
from app.contracts.errors import ConflictError, ConcurrencyConflictError


class TestConcurrencyConflictError:
    def test_subclasses_conflict_error(self):
        exc = ConcurrencyConflictError(
            resource="simulation",
            resource_id="sim_1",
            reason="lock_timeout",
        )
        assert isinstance(exc, ConflictError)

    def test_to_response_shape_matches_api_409_contract(self):
        exc = ConcurrencyConflictError(
            resource="simulation",
            resource_id="sim_1",
            reason="lock_timeout",
        )

        assert exc.to_response() == {
            "error": "conflict",
            "resource": "simulation",
            "resource_id": "sim_1",
            "reason": "lock_timeout",
        }


class TestLockConstants:
    def test_constants_are_distinct_strings(self):
        from app.services.application.concurrency import (
            branch_fork_lock,
            report_generation_lock,
            simulation_run_lock,
        )

        locks = {simulation_run_lock, branch_fork_lock, report_generation_lock}
        assert len(locks) == 3
        for lock in locks:
            assert isinstance(lock, str) and lock


class TestLockKey:
    def test_returns_stable_deterministic_int(self):
        from app.services.application.concurrency import lock_key, simulation_run_lock

        k1 = lock_key(simulation_run_lock, "sim_42")
        k2 = lock_key(simulation_run_lock, "sim_42")
        assert isinstance(k1, int)
        assert k1 == k2

    def test_distinguishes_type_and_resource(self):
        from app.services.application.concurrency import (
            branch_fork_lock,
            lock_key,
            simulation_run_lock,
        )

        assert lock_key(simulation_run_lock, "sim_42") != lock_key(
            branch_fork_lock, "sim_42"
        )
        assert lock_key(simulation_run_lock, "sim_42") != lock_key(
            simulation_run_lock, "sim_99"
        )


class TestCreateLockManager:
    def test_empty_db_url_returns_file_lock_manager(self, monkeypatch):
        from app.services.application.concurrency import FileLockManager, create_lock_manager

        monkeypatch.setattr(Config, "_db_url_cache", "")
        mgr = create_lock_manager()
        assert isinstance(mgr, FileLockManager)

    def test_sqlite_url_returns_sqlite_transaction_lock_manager(self, monkeypatch):
        from app.services.application.concurrency import (
            SQLiteTransactionLockManager,
            create_lock_manager,
        )

        monkeypatch.setattr(Config, "_db_url_cache", "sqlite:///test.db")
        mgr = create_lock_manager()
        assert isinstance(mgr, SQLiteTransactionLockManager)

    def test_postgresql_url_returns_postgres_advisory_lock_manager(self, monkeypatch):
        from app.services.application.concurrency import (
            PostgresAdvisoryLockManager,
            create_lock_manager,
        )

        monkeypatch.setattr(
            Config,
            "_db_url_cache",
            "postgresql+psycopg://user:pass@localhost/db",
        )
        mgr = create_lock_manager()
        assert isinstance(mgr, PostgresAdvisoryLockManager)

    def test_invalid_db_url_raises_value_error(self, monkeypatch):
        from app.services.application.concurrency import create_lock_manager

        monkeypatch.setattr(Config, "_db_url_cache", "mysql://bad")
        with pytest.raises(ValueError):
            create_lock_manager()


class TestFileLockManagerAcquire:
    def test_default_lock_dir_is_backend_data_locks(self):
        from app.services.application.concurrency import FileLockManager

        mgr = FileLockManager()

        normalized = mgr.lock_dir.replace("\\", "/")
        assert normalized.endswith("/backend/data/locks")

    def test_second_simultaneous_acquire_rejects_with_lock_timeout(self, tmp_path):
        from app.services.application.concurrency import FileLockManager, simulation_run_lock

        lock_dir = tmp_path / "locks"
        mgr = FileLockManager(lock_dir=str(lock_dir))

        with mgr.acquire(simulation_run_lock, "sim_1", timeout_seconds=0):
            with pytest.raises(ConcurrencyConflictError) as exc_info:
                with mgr.acquire(simulation_run_lock, "sim_1", timeout_seconds=0):
                    pass

            assert exc_info.value.to_response() == {
                "error": "conflict",
                "resource": simulation_run_lock,
                "resource_id": "sim_1",
                "reason": "lock_timeout",
            }


class TestPostgresAdvisoryLockManager:
    def test_acquire_uses_try_advisory_lock_and_unlock(self):
        from app.services.application.concurrency import (
            PostgresAdvisoryLockManager,
            report_generation_lock,
        )

        class FakeResult:
            def scalar(self):
                return True

        class FakeConnection:
            def __init__(self):
                self.statements = []

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def execute(self, statement, params=None):
                self.statements.append((str(statement), params or {}))
                return FakeResult()

        class FakeEngine:
            def __init__(self):
                self.connection = FakeConnection()

            def connect(self):
                return self.connection

        engine = FakeEngine()
        mgr = PostgresAdvisoryLockManager(
            db_url="postgresql+psycopg://user:pass@localhost/db",
            engine=engine,
        )

        with mgr.acquire(report_generation_lock, "report_1", timeout_seconds=0):
            pass

        statements = [item[0] for item in engine.connection.statements]
        assert any("pg_try_advisory_lock" in statement for statement in statements)
        assert any("pg_advisory_unlock" in statement for statement in statements)
