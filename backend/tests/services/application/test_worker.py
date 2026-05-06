"""Tests for background worker entry points."""

import os
import tempfile
from datetime import datetime, timezone, timedelta

import pytest
from sqlalchemy import create_engine, insert, select
from sqlalchemy.orm import sessionmaker

from app.config import Config
from app.repositories.sqlalchemy import metadata, tasks, task_attempts
from app.services.application.task_executor import PENDING, RUNNING


class TestWorkerExports:
    def test_recover_stale_tasks_is_exposed(self):
        from app.worker import recover_stale_tasks

        assert callable(recover_stale_tasks)

    def test_run_worker_is_exposed(self):
        from app.worker import run_worker

        assert callable(run_worker)

    def test_recover_stale_tasks_signature(self):
        import inspect
        from app.worker import recover_stale_tasks

        sig = inspect.signature(recover_stale_tasks)
        params = list(sig.parameters.keys())
        assert "config" in params
        assert "now" in params

    def test_run_worker_signature(self):
        import inspect
        from app.worker import run_worker

        sig = inspect.signature(run_worker)
        params = list(sig.parameters.keys())
        assert "config" in params
        assert "once" in params


class TestRecoverStaleTasksThread:
    def test_returns_noop_summary_for_thread_backend(self, monkeypatch):
        from app.worker import recover_stale_tasks

        monkeypatch.setenv("QUEUE_BACKEND", "thread")
        monkeypatch.setattr(Config, "_queue_backend_cache", None)

        result = recover_stale_tasks(config=Config)
        assert isinstance(result, dict)
        assert result["backend"] == "thread"
        assert result["recovered"] is False


class TestRecoverStaleTasksInvalid:
    def test_raises_valueerror_for_invalid_backend(self, monkeypatch):
        from app.worker import recover_stale_tasks

        monkeypatch.setenv("QUEUE_BACKEND", "invalid")
        monkeypatch.setattr(Config, "_queue_backend_cache", None)

        with pytest.raises(ValueError) as exc_info:
            recover_stale_tasks(config=Config)
        assert "invalid" in str(exc_info.value).lower() or "unsupported" in str(exc_info.value).lower()


class TestRecoverStaleTasksSQLite:
    def test_resets_stale_running_to_pending_and_inserts_attempt(self, monkeypatch):
        from app.worker import recover_stale_tasks

        # Create a temporary SQLite DB file
        fd, db_path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        db_url = f"sqlite:///{db_path}"

        try:
            engine = create_engine(db_url)
            metadata.create_all(engine)
            session_factory = sessionmaker(bind=engine)

            now = datetime.now(timezone.utc)
            old_time = now - timedelta(seconds=100)

            with session_factory() as session:
                session.execute(
                    insert(tasks).values(
                        id="worker_stale_1",
                        simulation_id="",
                        run_id="base",
                        task_type="test",
                        status=RUNNING,
                        payload={"attempt_count": 0, "callable": "my_fn"},
                        updated_at=old_time,
                    )
                )
                session.commit()

            monkeypatch.setenv("QUEUE_BACKEND", "sqlite")
            monkeypatch.setenv("DB_URL", db_url)
            monkeypatch.setattr(Config, "_queue_backend_cache", None)
            monkeypatch.setattr(Config, "_db_url_cache", None)
            monkeypatch.setattr(Config, "_queue_visibility_timeout_cache", 30)
            monkeypatch.setattr(Config, "_queue_retry_limit_cache", 3)

            result = recover_stale_tasks(config=Config, now=now)

            assert isinstance(result, dict)
            assert result["backend"] == "sqlite"
            assert result["recovered"] is True
            assert "status" in result

            with session_factory() as session:
                row = (
                    session.execute(select(tasks).where(tasks.c.id == "worker_stale_1"))
                    .mappings()
                    .fetchone()
                )
                assert row["status"] == PENDING
                payload = row["payload"]
                assert payload["attempt_count"] == 1

                attempts = session.execute(
                    select(task_attempts).where(task_attempts.c.task_id == "worker_stale_1")
                ).fetchall()
                assert len(attempts) == 1
                assert attempts[0].attempt_number == 1

        finally:
            engine.dispose()
            os.unlink(db_path)

    def test_summary_includes_recovered_false_when_nothing_stale(self, monkeypatch):
        from app.worker import recover_stale_tasks

        fd, db_path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        db_url = f"sqlite:///{db_path}"

        try:
            engine = create_engine(db_url)
            metadata.create_all(engine)
            session_factory = sessionmaker(bind=engine)

            now = datetime.now(timezone.utc)
            recent_time = now - timedelta(seconds=10)

            with session_factory() as session:
                session.execute(
                    insert(tasks).values(
                        id="worker_fresh_1",
                        simulation_id="",
                        run_id="base",
                        task_type="test",
                        status=RUNNING,
                        payload={"attempt_count": 0, "callable": "my_fn"},
                        updated_at=recent_time,
                    )
                )
                session.commit()

            monkeypatch.setenv("QUEUE_BACKEND", "sqlite")
            monkeypatch.setenv("DB_URL", db_url)
            monkeypatch.setattr(Config, "_queue_backend_cache", None)
            monkeypatch.setattr(Config, "_db_url_cache", None)
            monkeypatch.setattr(Config, "_queue_visibility_timeout_cache", 30)
            monkeypatch.setattr(Config, "_queue_retry_limit_cache", 3)

            result = recover_stale_tasks(config=Config, now=now)

            assert isinstance(result, dict)
            assert result["backend"] == "sqlite"
            assert result["recovered"] is False
            assert "status" in result

        finally:
            engine.dispose()
            os.unlink(db_path)


class TestRunWorkerSQLite:
    def test_once_true_triggers_recovery_and_returns_summary(self, monkeypatch):
        from app.worker import run_worker

        fd, db_path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        db_url = f"sqlite:///{db_path}"

        try:
            engine = create_engine(db_url)
            metadata.create_all(engine)
            session_factory = sessionmaker(bind=engine)

            now = datetime.now(timezone.utc)
            old_time = now - timedelta(seconds=100)

            with session_factory() as session:
                session.execute(
                    insert(tasks).values(
                        id="run_worker_stale_1",
                        simulation_id="",
                        run_id="base",
                        task_type="test",
                        status=RUNNING,
                        payload={"attempt_count": 0, "callable": "my_fn"},
                        updated_at=old_time,
                    )
                )
                session.commit()

            monkeypatch.setenv("QUEUE_BACKEND", "sqlite")
            monkeypatch.setenv("DB_URL", db_url)
            monkeypatch.setattr(Config, "_queue_backend_cache", None)
            monkeypatch.setattr(Config, "_db_url_cache", None)
            monkeypatch.setattr(Config, "_queue_visibility_timeout_cache", 30)
            monkeypatch.setattr(Config, "_queue_retry_limit_cache", 3)

            result = run_worker(config=Config, once=True)

            assert isinstance(result, dict)
            assert result["backend"] == "sqlite"
            assert result["recovered"] is True
            assert "status" in result

            with session_factory() as session:
                row = (
                    session.execute(select(tasks).where(tasks.c.id == "run_worker_stale_1"))
                    .mappings()
                    .fetchone()
                )
                assert row["status"] == PENDING
                payload = row["payload"]
                assert payload["attempt_count"] == 1

        finally:
            engine.dispose()
            os.unlink(db_path)


class TestRunWorkerThread:
    def test_once_true_returns_noop_summary_for_thread_backend(self, monkeypatch):
        from app.worker import run_worker

        monkeypatch.setenv("QUEUE_BACKEND", "thread")
        monkeypatch.setattr(Config, "_queue_backend_cache", None)

        result = run_worker(config=Config, once=True)

        assert isinstance(result, dict)
        assert result["backend"] == "thread"
        assert result["recovered"] is False
        assert result["status"] == "no-op"


class TestRunWorkerContinuous:
    def test_once_false_raises_not_implemented(self, monkeypatch):
        from app.worker import run_worker

        monkeypatch.setenv("QUEUE_BACKEND", "thread")
        monkeypatch.setattr(Config, "_queue_backend_cache", None)

        with pytest.raises(NotImplementedError) as exc_info:
            run_worker(config=Config, once=False)
        assert "continuous" in str(exc_info.value).lower() or "not implemented" in str(exc_info.value).lower()
