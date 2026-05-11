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
        monkeypatch.setattr(Config, "_redis_url_cache", "")
        monkeypatch.setattr(Config, "_lock_backend_cache", "auto", raising=False)
        mgr = create_lock_manager()
        assert isinstance(mgr, FileLockManager)

    def test_sqlite_url_returns_sqlite_transaction_lock_manager(self, monkeypatch):
        from app.services.application.concurrency import (
            SQLiteTransactionLockManager,
            create_lock_manager,
        )

        monkeypatch.setattr(Config, "_db_url_cache", "sqlite:///test.db")
        monkeypatch.setattr(Config, "_redis_url_cache", "")
        monkeypatch.setattr(Config, "_lock_backend_cache", "auto", raising=False)
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
        monkeypatch.setattr(Config, "_redis_url_cache", "")
        monkeypatch.setattr(Config, "_lock_backend_cache", "auto", raising=False)
        mgr = create_lock_manager()
        assert isinstance(mgr, PostgresAdvisoryLockManager)

    def test_auto_backend_prefers_redis_when_redis_url_is_configured(self, monkeypatch):
        from app.services.application.concurrency import RedisLockManager, create_lock_manager

        class FakeRedis:
            def ping(self):
                return True

        monkeypatch.setattr(Config, "_db_url_cache", "")
        monkeypatch.setattr(Config, "_redis_url_cache", "redis://localhost:6379/0")
        monkeypatch.setattr(Config, "_lock_backend_cache", "auto", raising=False)
        monkeypatch.setattr(
            "app.services.application.concurrency.redis.Redis.from_url",
            lambda url: FakeRedis(),
        )

        mgr = create_lock_manager()

        assert isinstance(mgr, RedisLockManager)

    def test_explicit_file_backend_uses_file_lock_even_with_redis_url(self, monkeypatch):
        from app.services.application.concurrency import FileLockManager, create_lock_manager

        monkeypatch.setattr(Config, "_db_url_cache", "postgresql+psycopg://user:pass@host/db")
        monkeypatch.setattr(Config, "_redis_url_cache", "redis://localhost:6379/0")
        monkeypatch.setattr(Config, "_lock_backend_cache", "file", raising=False)

        mgr = create_lock_manager()

        assert isinstance(mgr, FileLockManager)

    def test_explicit_redis_backend_requires_redis_url(self, monkeypatch):
        from app.services.application.concurrency import create_lock_manager

        monkeypatch.setattr(Config, "_db_url_cache", "")
        monkeypatch.setattr(Config, "_redis_url_cache", "")
        monkeypatch.setattr(Config, "_lock_backend_cache", "redis", raising=False)

        with pytest.raises(ValueError, match="REDIS_URL"):
            create_lock_manager()

    def test_invalid_db_url_raises_value_error(self, monkeypatch):
        from app.services.application.concurrency import create_lock_manager

        monkeypatch.setattr(Config, "_db_url_cache", "mysql://bad")
        monkeypatch.setattr(Config, "_redis_url_cache", "")
        monkeypatch.setattr(Config, "_lock_backend_cache", "auto", raising=False)
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


class TestRedisLockManager:
    def test_acquire_sets_namespaced_lock_with_token_and_ttl_then_releases(self):
        from app.services.application.concurrency import RedisLockManager, simulation_run_lock

        class FakeRedis:
            def __init__(self):
                self.set_calls = []
                self.eval_calls = []

            def ping(self):
                return True

            def set(self, key, token, nx=False, ex=None):
                self.set_calls.append({"key": key, "token": token, "nx": nx, "ex": ex})
                return True

            def eval(self, script, numkeys, key, token):
                self.eval_calls.append(
                    {"script": script, "numkeys": numkeys, "key": key, "token": token}
                )
                return 1

        redis_client = FakeRedis()
        mgr = RedisLockManager(
            redis_url="redis://localhost:6379/0",
            redis_client=redis_client,
            namespace="testlocks",
        )

        with mgr.acquire(simulation_run_lock, "sim_1", timeout_seconds=0):
            pass

        assert len(redis_client.set_calls) == 1
        set_call = redis_client.set_calls[0]
        assert set_call["key"].startswith("testlocks:simulation_run_lock:")
        assert set_call["nx"] is True
        assert set_call["ex"] >= 30
        assert len(redis_client.eval_calls) == 1
        assert redis_client.eval_calls[0]["key"] == set_call["key"]
        assert redis_client.eval_calls[0]["token"] == set_call["token"]

    def test_second_manager_conflicts_on_same_redis_lock(self):
        from app.services.application.concurrency import RedisLockManager, branch_fork_lock

        class SharedRedis:
            def __init__(self):
                self.held = {}

            def ping(self):
                return True

            def set(self, key, token, nx=False, ex=None):
                if nx and key in self.held:
                    return False
                self.held[key] = token
                return True

            def eval(self, script, numkeys, key, token):
                if self.held.get(key) == token:
                    del self.held[key]
                    return 1
                return 0

        redis_client = SharedRedis()
        mgr_a = RedisLockManager("redis://localhost:6379/0", redis_client=redis_client)
        mgr_b = RedisLockManager("redis://localhost:6379/0", redis_client=redis_client)

        with mgr_a.acquire(branch_fork_lock, "branch_1", timeout_seconds=0):
            with pytest.raises(ConcurrencyConflictError) as exc_info:
                with mgr_b.acquire(branch_fork_lock, "branch_1", timeout_seconds=0):
                    pass

        assert exc_info.value.to_response()["reason"] == "lock_timeout"
