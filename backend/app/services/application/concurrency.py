"""Concurrency lock foundation for Phase 7C."""

import os
import uuid
import sys
import threading
import time
from contextlib import contextmanager
from hashlib import blake2b
from pathlib import Path

import redis

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


class RedisLockManager:
    """Redis SET NX lock manager for cross-process and cross-node exclusion."""

    _release_script = """
if redis.call("get", KEYS[1]) == ARGV[1] then
    return redis.call("del", KEYS[1])
end
return 0
"""

    def __init__(
        self,
        redis_url,
        redis_client=None,
        namespace="miroconsumer:locks",
        min_ttl_seconds=30,
    ):
        if not redis_url and redis_client is None:
            raise ValueError("REDIS_URL is required for RedisLockManager")
        self.redis_url = redis_url
        self.namespace = namespace.rstrip(":")
        self.min_ttl_seconds = int(min_ttl_seconds)
        self._redis = redis_client if redis_client is not None else redis.Redis.from_url(redis_url)

    def _key(self, lock_type, resource_id):
        return f"{self.namespace}:{lock_type}:{lock_key(lock_type, resource_id)}"

    @contextmanager
    def acquire(self, lock_type, resource_id, timeout_seconds=30):
        redis_key = self._key(lock_type, resource_id)
        token = uuid.uuid4().hex
        ttl = max(self.min_ttl_seconds, int(timeout_seconds) + self.min_ttl_seconds)
        acquired = False
        start = time.monotonic()

        while True:
            try:
                acquired = bool(self._redis.set(redis_key, token, nx=True, ex=ttl))
            except redis.exceptions.RedisError as exc:
                raise ConcurrencyConflictError(
                    resource=lock_type,
                    resource_id=resource_id,
                    reason="lock_unavailable",
                ) from exc

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
            try:
                self._redis.eval(self._release_script, 1, redis_key, token)
            except redis.exceptions.RedisError:
                pass


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


def _database_or_file_lock_manager(config):
    db_url = config.DB_URL
    if not db_url:
        return FileLockManager()
    if db_url.startswith("sqlite:///"):
        from sqlalchemy import create_engine

        return SQLiteTransactionLockManager(create_engine(db_url))
    if db_url.startswith("postgresql+psycopg://"):
        return PostgresAdvisoryLockManager(db_url)
    raise ValueError(f"Unsupported database URL: {db_url}")


def create_lock_manager(config=None):
    """Factory returning the configured lock manager with local fallbacks."""
    from app.config import Config

    if config is None:
        config = Config

    lock_backend = getattr(config, "LOCK_BACKEND", "auto")
    if lock_backend == "file":
        return FileLockManager()
    if lock_backend == "db":
        return _database_or_file_lock_manager(config)
    if lock_backend == "redis":
        redis_url = config.REDIS_URL
        if not redis_url:
            raise ValueError("REDIS_URL is required when LOCK_BACKEND=redis")
        return RedisLockManager(redis_url)
    if lock_backend == "auto":
        redis_url = config.REDIS_URL
        if redis_url:
            return RedisLockManager(redis_url)
        return _database_or_file_lock_manager(config)
    raise ValueError(f"Unsupported lock backend: {lock_backend}")
