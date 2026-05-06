"""Background worker entry point for durable queue backends.

Phase 7B.2 will implement the worker loop for sqlite and rq backends.
"""

import json
from typing import Any, Dict, Optional

from app.utils.logger import get_logger

logger = get_logger("miroconsumer.worker")


def recover_stale_tasks(config: Any = None, now: Any = None) -> Dict[str, Any]:
    """Find stale RUNNING tasks and reset them to PENDING or dead-letter.

    Returns a dict summary with backend, recovered flag, and status.
    """
    if config is None:
        from app.config import Config as _Config
        config = _Config

    backend = config.QUEUE_BACKEND

    if backend == "thread":
        return {
            "backend": "thread",
            "recovered": False,
            "status": "no-op",
        }

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
            return {
                "backend": "sqlite",
                "recovered": count > 0,
                "status": "ok",
            }
        finally:
            if engine is not None:
                engine.dispose()

    raise ValueError(f"Unsupported QUEUE_BACKEND for worker: {backend}")


def run_worker(config: Any = None, once: bool = True) -> Dict[str, Any]:
    """Start the background worker process.

    When once=True, performs startup recovery (stale-task reset) and returns
    the recovery summary.  Continuous loop is left unimplemented.
    """
    if config is None:
        from app.config import Config as _Config
        config = _Config

    if not once:
        raise NotImplementedError("Continuous worker loop not yet implemented")

    return recover_stale_tasks(config=config)


if __name__ == "__main__":
    print(json.dumps(run_worker(), ensure_ascii=False))
