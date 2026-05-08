"""Background worker entry point for durable queue backends."""

import json
import os
import time
import signal
from typing import Any, Dict, Optional

import redis
import rq

from app.utils.logger import get_logger

logger = get_logger("miroconsumer.worker")

_shutdown_requested = False


def _handle_signal(signum, frame):
    global _shutdown_requested
    _shutdown_requested = True
    logger.info("Worker shutdown signal received (sig=%s)", signum)


def recover_stale_tasks(config: Any = None, now: Any = None) -> Dict[str, Any]:
    """Find stale RUNNING tasks and reset them to PENDING or dead-letter."""
    if config is None:
        from app.config import Config as _Config
        config = _Config

    backend = config.QUEUE_BACKEND

    if backend == "thread":
        return {"backend": "thread", "recovered": False, "status": "no-op"}

    if backend == "sqlite":
        from app.services.application.sqlite_queue import SQLiteQueueBackend
        from app.repositories.session import create_engine_from_config, create_session_factory

        engine = create_engine_from_config(config)
        try:
            session_factory = create_session_factory(engine)
            queue_backend = SQLiteQueueBackend(session_factory=session_factory)

            if now is None:
                from datetime import datetime, timezone
                now = datetime.now(timezone.utc)

            count = queue_backend.recover_stale_running(
                now,
                visibility_timeout_seconds=config.QUEUE_VISIBILITY_TIMEOUT_SECONDS,
                retry_limit=config.QUEUE_RETRY_LIMIT,
            )
            return {"backend": "sqlite", "recovered": count > 0, "status": "ok"}
        finally:
            if engine is not None:
                engine.dispose()

    if backend == "rq":
        conn = _create_rq_connection(config)
        conn.ping()
        return {
            "backend": "rq",
            "recovered": False,
            "status": "ready",
            "queue": _rq_queue_name(config),
        }

    raise ValueError(f"Unsupported QUEUE_BACKEND for worker: {backend}")


def run_worker(
    config: Any = None,
    once: bool = True,
    poll_interval: float = 5.0,
    burst: bool = False,
) -> Dict[str, Any]:
    """Start the background worker process.

    When once=True, performs startup recovery and returns.
    When once=False, enters a continuous polling loop (SIGTERM/SIGINT graceful shutdown).
    """
    global _shutdown_requested

    if config is None:
        from app.config import Config as _Config
        config = _Config

    if once:
        return recover_stale_tasks(config=config)

    if config.QUEUE_BACKEND == "rq":
        return run_rq_worker(config=config, burst=burst)

    # Continuous mode
    signal.signal(signal.SIGTERM, _handle_signal)
    signal.signal(signal.SIGINT, _handle_signal)

    logger.info("Worker started (backend=%s, poll_interval=%.1fs)", config.QUEUE_BACKEND, poll_interval)

    # Initial recovery
    recover_stale_tasks(config=config)

    while not _shutdown_requested:
        try:
            recover_stale_tasks(config=config)
        except Exception as e:
            logger.error("Worker recovery cycle error: %s", e)

        # Sleep in small increments for responsive shutdown
        elapsed = 0.0
        while elapsed < poll_interval and not _shutdown_requested:
            time.sleep(min(1.0, poll_interval - elapsed))
            elapsed += 1.0

    logger.info("Worker stopped gracefully")
    return {"status": "stopped"}


def run_rq_worker(config: Any = None, burst: bool = False) -> Dict[str, Any]:
    """Run an RQ worker that consumes jobs from Redis."""
    if config is None:
        from app.config import Config as _Config
        config = _Config

    queue_name = _rq_queue_name(config)
    conn = _create_rq_connection(config)
    conn.ping()

    logger.info("RQ worker started (queue=%s, burst=%s)", queue_name, burst)
    worker = rq.Worker([queue_name], connection=conn)
    worker.work(burst=burst)
    logger.info("RQ worker stopped (queue=%s)", queue_name)
    return {"backend": "rq", "status": "stopped", "queue": queue_name}


def _rq_queue_name(config: Any) -> str:
    return str(getattr(config, "RQ_QUEUE_NAME", None) or os.environ.get("RQ_QUEUE_NAME", "default"))


def _create_rq_connection(config: Any) -> redis.Redis:
    redis_url = getattr(config, "REDIS_URL", "") or ""
    if not redis_url:
        raise ValueError("REDIS_URL is required when QUEUE_BACKEND=rq")
    try:
        return redis.Redis.from_url(redis_url)
    except ValueError as exc:
        raise ConnectionError(f"Invalid Redis URL for RQ worker: {redis_url}") from exc


if __name__ == "__main__":
    import sys
    once = "--once" in sys.argv
    burst = "--burst" in sys.argv
    print(json.dumps(run_worker(once=once, burst=burst), ensure_ascii=False))
