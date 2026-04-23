"""Task executor abstraction for background work.

Application services submit long-running tasks through this boundary
instead of constructing raw threads inline.
"""

import threading
import uuid
from abc import ABC, abstractmethod
from typing import Any, Callable, Optional

from ...utils.logger import get_logger

logger = get_logger("miroconsumer.task_executor")


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


class ThreadTaskExecutor(TaskExecutor):
    """In-process executor backed by daemon threads."""

    def submit(
        self,
        fn: Callable,
        *args: Any,
        trace_id: Optional[str] = None,
        **kwargs: Any,
    ) -> str:
        tid = trace_id or f"trace_{uuid.uuid4().hex[:12]}"

        def _run() -> None:
            try:
                fn(*args, **kwargs)
            except Exception as exc:
                error_category = _categorize_error(exc)
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
