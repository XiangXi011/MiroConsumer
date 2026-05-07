"""Background worker entry point for durable queue backends."""

import json
import time
import signal
from typing import Any, Dict, Optional

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
        # RQ workers are started separately via `rq worker` command
        return {"backend": "rq", "recovered": False, "status": "use_rq_worker_cli"}

    raise ValueError(f"Unsupported QUEUE_BACKEND for worker: {backend}")


def run_worker(config: Any = None, once: bool = True, poll_interval: float = 5.0) -> Dict[str, Any]:
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


if __name__ == "__main__":
    import sys
    once = "--once" in sys.argv
    print(json.dumps(run_worker(once=once), ensure_ascii=False))
