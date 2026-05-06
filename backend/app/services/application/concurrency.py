"""Concurrency lock foundation for Phase 7C."""

import os
import sys
import threading
import time
from contextlib import contextmanager
from hashlib import blake2b
from pathlib import Path

from app.contracts.errors import ConcurrencyConflictError

simulation_run_lock = "simulation_run_lock"
branch_fork_lock = "branch_fork_lock"
report_generation_lock = "report_generation_lock"

if sys.platform == "win32":
    import msvcrt
else:
    import fcntl


def lock_key(lock_type: str, resource_id: str) -> int:
    """Return a stable deterministic positive int hash."""
    payload = f"{lock_type}:{resource_id}".encode("utf-8")
    digest = blake2b(payload, digest_size=8).digest()
    return int.from_bytes(digest, "big") & 0x7FFFFFFFFFFFFFFF


class FileLockManager:
    """OS-level file locking with in-process deduplication."""

    def __init__(self, lock_dir=None):
        if lock_dir is None:
            backend_dir = Path(__file__).resolve().parents[3]
            self.lock_dir = str(backend_dir / "data" / "locks")
        else:
            self.lock_dir = lock_dir
        self._held = set()
        self._mutex = threading.Lock()

    @contextmanager
    def acquire(self, lock_type, resource_id, timeout_seconds=30):
        key = (lock_type, resource_id)
        with self._mutex:
            if key in self._held:
                raise ConcurrencyConflictError(
                    resource=lock_type,
                    resource_id=resource_id,
                    reason="lock_timeout",
                )
            self._held.add(key)

        lock_file = os.path.join(self.lock_dir, f"{lock_type}_{lock_key(lock_type, resource_id)}.lock")
        os.makedirs(os.path.dirname(lock_file), exist_ok=True)
        fd = os.open(lock_file, os.O_CREAT | os.O_RDWR)

        acquired = False
        start = time.monotonic()
        while True:
            try:
                if sys.platform == "win32":
                    msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
                else:
                    fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                acquired = True
                break
            except (OSError, BlockingIOError, IOError):
                if time.monotonic() - start >= timeout_seconds:
                    break
                time.sleep(0.05)

        if not acquired:
            with self._mutex:
                self._held.discard(key)
            os.close(fd)
            raise ConcurrencyConflictError(
                resource=lock_type,
                resource_id=resource_id,
                reason="lock_timeout",
            )

        try:
            yield
        finally:
            with self._mutex:
                self._held.discard(key)
            try:
                if sys.platform == "win32":
                    msvcrt.locking(fd, msvcrt.LK_UNLCK, 1)
                else:
                    fcntl.flock(fd, fcntl.LOCK_UN)
            except (OSError, BlockingIOError, IOError):
                pass
            os.close(fd)


class SQLiteTransactionLockManager:
    """SQLite BEGIN IMMEDIATE transaction-level locking."""

    def __init__(self, engine):
        self.engine = engine

    @contextmanager
    def acquire(self, lock_type, resource_id, timeout_seconds=30):
        raw_conn = self.engine.raw_connection()
        began = False
        try:
            raw_conn.execute(f"PRAGMA busy_timeout={int(timeout_seconds * 1000)}")
            raw_conn.execute("BEGIN IMMEDIATE")
            began = True
            yield
            raw_conn.execute("COMMIT")
        except Exception as exc:
            if began:
                try:
                    raw_conn.execute("ROLLBACK")
                except Exception:
                    pass
                raise
            raise ConcurrencyConflictError(
                resource=lock_type,
                resource_id=resource_id,
                reason="lock_timeout",
            ) from exc
        finally:
            raw_conn.close()


class PostgresAdvisoryLockManager:
    """Postgres advisory locking via pg_try_advisory_lock."""

    def __init__(self, db_url, engine=None):
        self.db_url = db_url
        self.engine = engine

    @contextmanager
    def acquire(self, lock_type, resource_id, timeout_seconds=30):
        from sqlalchemy import create_engine, text

        if self.engine is None:
            self.engine = create_engine(self.db_url)

        key = lock_key(lock_type, resource_id)
        with self.engine.connect() as conn:
            start = time.monotonic()
            while True:
                acquired = conn.execute(
                    text("SELECT pg_try_advisory_lock(:key)"),
                    {"key": key},
                ).scalar()
                if acquired:
                    break
                if time.monotonic() - start >= timeout_seconds:
                    raise ConcurrencyConflictError(
                        resource=lock_type,
                        resource_id=resource_id,
                        reason="lock_timeout",
                    )
                time.sleep(0.05)
            try:
                yield
            finally:
                conn.execute(text("SELECT pg_advisory_unlock(:key)"), {"key": key})


def create_lock_manager(config=None):
    """Factory returning the right lock manager for the configured DB."""
    from app.config import Config

    if config is None:
        config = Config
    db_url = config.DB_URL
    if not db_url:
        return FileLockManager()
    if db_url.startswith("sqlite:///"):
        from sqlalchemy import create_engine

        return SQLiteTransactionLockManager(create_engine(db_url))
    if db_url.startswith("postgresql+psycopg://"):
        return PostgresAdvisoryLockManager(db_url)
    raise ValueError(f"Unsupported database URL: {db_url}")
