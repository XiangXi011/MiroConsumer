"""Task executor abstraction for background work.

Application services submit long-running tasks through this boundary
instead of constructing raw threads inline.
"""

import threading
import uuid
from abc import ABC, abstractmethod
from typing import Any, Callable, Dict, Optional

from ...utils.logger import get_logger

# Delayed import to avoid circular dependency
_config_cls = None

logger = get_logger("miroconsumer.task_executor")

# Fixed task statuses
PENDING = "PENDING"
RUNNING = "RUNNING"
SUCCEEDED = "SUCCEEDED"
FAILED = "FAILED"
CANCELLED = "CANCELLED"
DEAD_LETTER = "DEAD_LETTER"


class TaskExecutor(ABC):
    """Abstract boundary for launching background work."""

    @abstractmethod
    def submit(
        self,
        fn: Callable,
        *args: Any,
        trace_id: Optional[str] = None,
        **kwargs: Any,
    ) -> str:
        """Queue fn(*args, **kwargs) for background execution.

        Returns a trace_id that can be used to correlate logs.
        """

    @abstractmethod
    def get_status(self, trace_id: str) -> Dict[str, Any]:
        """Return the current status of a task by trace_id as a dict."""

    @abstractmethod
    def cancel(self, trace_id: str) -> Dict[str, Any]:
        """Cancel a task by trace_id. Returns a status dict."""


class ThreadTaskExecutor(TaskExecutor):
    """In-process executor backed by daemon threads."""

    def __init__(self) -> None:
        self._statuses: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()

    def submit(
        self,
        fn: Callable,
        *args: Any,
        trace_id: Optional[str] = None,
        **kwargs: Any,
    ) -> str:
        # Pop queue metadata kwargs so they are not passed to fn
        _kwargs = dict(kwargs)
        _kwargs.pop("task_type", None)
        _kwargs.pop("idempotency_key", None)
        _kwargs.pop("simulation_id", None)
        _kwargs.pop("run_id", None)

        tid = trace_id or f"trace_{uuid.uuid4().hex[:12]}"

        with self._lock:
            self._statuses[tid] = {"status": PENDING}

        def _run() -> None:
            with self._lock:
                if self._statuses.get(tid, {}).get("status") == CANCELLED:
                    return
                self._statuses[tid]["status"] = RUNNING
            try:
                fn(*args, **_kwargs)
                with self._lock:
                    if self._statuses.get(tid, {}).get("status") != CANCELLED:
                        self._statuses[tid]["status"] = SUCCEEDED
            except Exception as exc:
                error_category = _categorize_error(exc)
                with self._lock:
                    if self._statuses.get(tid, {}).get("status") != CANCELLED:
                        self._statuses[tid]["status"] = FAILED
                        self._statuses[tid]["error_category"] = error_category
                logger.error(
                    "Background task failed",
                    extra={
                        "trace_id": tid,
                        "error_category": error_category,
                        "error_type": type(exc).__name__,
                        "error": str(exc),
                    },
                )

        thread = threading.Thread(target=_run, daemon=True)
        thread.start()
        return tid

    def get_status(self, trace_id: str) -> Dict[str, Any]:
        with self._lock:
            info = self._statuses.get(trace_id)
        if info is None:
            return {
                "trace_id": trace_id,
                "status": FAILED,
                "error_category": "task:not_found",
                "backend": "thread",
            }
        result = {
            "trace_id": trace_id,
            "status": info["status"],
            "backend": "thread",
        }
        if "error_category" in info:
            result["error_category"] = info["error_category"]
        return result

    def cancel(self, trace_id: str) -> Dict[str, Any]:
        with self._lock:
            if trace_id in self._statuses:
                self._statuses[trace_id]["status"] = CANCELLED
                return {
                    "trace_id": trace_id,
                    "status": CANCELLED,
                    "cancelled": True,
                    "backend": "thread",
                }
        return {
            "trace_id": trace_id,
            "status": FAILED,
            "cancelled": False,
            "error_category": "task:not_found",
            "backend": "thread",
        }


def _categorize_error(exc: Exception) -> str:
    """Map an exception to a stable failure-reason category for observability."""
    from ...contracts.errors import CanonicalError

    if isinstance(exc, CanonicalError):
        return f"canonical:{exc.code}"
    name = type(exc).__name__
    if name in {"ConnectionError", "TimeoutError", "HTTPError"}:
        return "infra:external"
    if "Validation" in name or name == "ValueError":
        return "biz:validation"
    if "NotFound" in name:
        return "biz:not_found"
    if "Auth" in name or "Permission" in name:
        return "security:auth"
    return f"uncategorized:{name}"


def create_task_executor(config: Any = None) -> TaskExecutor:
    """Factory: create the appropriate TaskExecutor from Config."""
    if config is None:
        from app.config import Config as _Config
        config = _Config
    backend = config.QUEUE_BACKEND
    if backend == "thread":
        return ThreadTaskExecutor()
    if backend == "sqlite":
        from .queue_task_executor import QueueTaskExecutor
        from .sqlite_queue import SQLiteQueueBackend
        from ...repositories.session import create_engine_from_config, create_session_factory

        db_url = config.DB_URL
        if not db_url:
            raise ValueError("DB_URL is required when QUEUE_BACKEND=sqlite")
        engine = create_engine_from_config(config)
        session_factory = create_session_factory(engine)
        return QueueTaskExecutor(
            backend_name="sqlite",
            backend=SQLiteQueueBackend(session_factory=session_factory),
        )
    if backend == "rq":
        from .queue_task_executor import QueueTaskExecutor
        from .rq_queue import RQQueueBackend

        return QueueTaskExecutor(
            backend_name="rq",
            backend=RQQueueBackend(
                redis_url=config.REDIS_URL,
                queue_name=getattr(config, "RQ_QUEUE_NAME", "default"),
            ),
        )
    raise ValueError(f"Unsupported QUEUE_BACKEND: {backend}")
