"""Queue application service for dead-letter inspection."""

from typing import Any, Dict, List

from app.config import Config


def list_dead_letters() -> Dict[str, Any]:
    """Return dead letters for the current queue backend.

    Returns a dict with ``backend`` name and ``dead_letters`` list.
    Raises ``ValueError`` for unsupported backends.
    """
    backend = Config.QUEUE_BACKEND

    if backend == "sqlite":
        db_url = Config.DB_URL
        if not db_url:
            raise ValueError("DB_URL is required when QUEUE_BACKEND=sqlite")
        from app.repositories.session import create_engine_from_config, create_session_factory
        from app.services.application.sqlite_queue import SQLiteQueueBackend

        engine = create_engine_from_config(Config)
        try:
            session_factory = create_session_factory(engine)
            queue_backend = SQLiteQueueBackend(session_factory=session_factory)
            return {"backend": "sqlite", "dead_letters": queue_backend.list_dead_letters()}
        finally:
            engine.dispose()

    if backend == "thread":
        return {"backend": "thread", "dead_letters": []}

    if backend == "rq":
        redis_url = Config.REDIS_URL
        if not redis_url:
            raise ValueError("REDIS_URL is required when QUEUE_BACKEND=rq")
        from app.services.application.rq_queue import RQQueueBackend

        queue_backend = RQQueueBackend(
            redis_url=redis_url,
            queue_name=getattr(Config, "RQ_QUEUE_NAME", "default"),
        )
        return {"backend": "rq", "dead_letters": queue_backend.list_dead_letters()}

    raise ValueError(f"Unsupported QUEUE_BACKEND: {backend}")
