"""Queue-backed task executor for durable background work.

Implements the TaskExecutor contract using configurable queue backends.
"""

import threading
import uuid
from typing import Any, Callable, Dict, Optional

from .task_executor import TaskExecutor, PENDING, RUNNING, SUCCEEDED, FAILED, CANCELLED
from ...utils.logger import get_logger

logger = get_logger("miroconsumer.queue_task_executor")


class QueueTaskExecutor(TaskExecutor):
    """Task executor backed by a durable queue (sqlite or rq)."""

    def __init__(self, backend_name: str = "sqlite", backend: Any = None) -> None:
        self.backend_name = backend_name
        self.backend = backend
        self._submitted: Dict[str, Dict[str, Any]] = {}
        self._cancelled: set = set()
        self._lock = threading.Lock()

    def submit(
        self,
        fn: Callable,
        *args: Any,
        trace_id: Optional[str] = None,
        **kwargs: Any,
    ) -> str:
        # Extract metadata kwargs that should be passed to the backend
        metadata = {
            "task_type": kwargs.pop("task_type", None),
            "idempotency_key": kwargs.pop("idempotency_key", None),
            "simulation_id": kwargs.pop("simulation_id", ""),
            "run_id": kwargs.pop("run_id", "base"),
        }

        tid = trace_id or f"trace_{uuid.uuid4().hex[:12]}"
        created = True

        if self.backend is not None:
            try:
                result = self.backend.enqueue(tid, fn, *args, **metadata, **kwargs)
                # Backward compat: handle both tuple (sqlite) and plain str (rq)
                if isinstance(result, tuple):
                    tid, created = result
                else:
                    tid = result
                    created = True
            except Exception as exc:
                logger.error(
                    "Queue enqueue failed",
                    extra={
                        "trace_id": tid,
                        "backend": self.backend_name,
                        "error": str(exc),
                    },
                )
                if getattr(self.backend, "runs_externally", False):
                    raise
        else:
            logger.info(
                "Queue submit (no-op skeleton)",
                extra={"trace_id": tid, "backend": self.backend_name},
            )

        with self._lock:
            self._submitted[tid] = {"status": PENDING, "task_type": metadata.get("task_type")}

        # Only execute locally for backends whose workers live in this process.
        if created and self.backend is not None and not getattr(self.backend, "runs_externally", False):
            self._spawn_worker(tid, fn, args, kwargs)

        return tid

    def _spawn_worker(
        self,
        tid: str,
        fn: Callable,
        args: tuple,
        kwargs: Dict[str, Any],
    ) -> None:
        """Spawn a daemon thread to execute fn and update backend lifecycle."""

        def _run() -> None:
            # Check if already cancelled before doing anything
            if self.backend is not None and hasattr(self.backend, "get_status"):
                try:
                    status_info = self.backend.get_status(tid)
                    if status_info.get("status") == CANCELLED:
                        return
                except Exception:
                    pass

            # Mark running in backend if available
            if self.backend is not None and hasattr(self.backend, "mark_running"):
                try:
                    self.backend.mark_running(tid)
                except Exception as exc:
                    logger.error(
                        "mark_running failed",
                        extra={"trace_id": tid, "error": str(exc)},
                    )

            try:
                fn(*args, **kwargs)
                if self.backend is not None and hasattr(self.backend, "mark_succeeded"):
                    try:
                        self.backend.mark_succeeded(tid)
                    except Exception as exc:
                        logger.error(
                            "mark_succeeded failed",
                            extra={"trace_id": tid, "error": str(exc)},
                        )
                with self._lock:
                    if tid in self._submitted:
                        self._submitted[tid]["status"] = SUCCEEDED
            except Exception as exc:
                from .task_executor import _categorize_error
                error_category = _categorize_error(exc)
                if self.backend is not None and hasattr(self.backend, "mark_failed"):
                    try:
                        self.backend.mark_failed(tid, error_category, str(exc))
                    except Exception as mark_exc:
                        logger.error(
                            "mark_failed failed",
                            extra={"trace_id": tid, "error": str(mark_exc)},
                        )
                with self._lock:
                    if tid in self._submitted:
                        self._submitted[tid]["status"] = FAILED
                        self._submitted[tid]["error_category"] = error_category
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

    def get_status(self, trace_id: str) -> Dict[str, Any]:
        # Delegate to backend first if available
        if self.backend is not None:
            try:
                return self.backend.get_status(trace_id)
            except Exception as exc:
                logger.error(
                    "Queue get_status failed",
                    extra={
                        "trace_id": trace_id,
                        "backend": self.backend_name,
                        "error": str(exc),
                    },
                )

        with self._lock:
            if trace_id in self._cancelled:
                return {
                    "trace_id": trace_id,
                    "status": CANCELLED,
                    "backend": self.backend_name,
                }
            info = self._submitted.get(trace_id)
        if info is not None:
            result = {
                "trace_id": trace_id,
                "status": info.get("status", PENDING),
                "backend": self.backend_name,
            }
            if "error_category" in info:
                result["error_category"] = info["error_category"]
            return result
        return {
            "trace_id": trace_id,
            "status": FAILED,
            "error_category": "task:not_found",
            "backend": self.backend_name,
        }

    def cancel(self, trace_id: str) -> Dict[str, Any]:
        # Delegate to backend first if available
        if self.backend is not None:
            try:
                return self.backend.cancel(trace_id)
            except Exception as exc:
                logger.error(
                    "Queue cancel failed",
                    extra={
                        "trace_id": trace_id,
                        "backend": self.backend_name,
                        "error": str(exc),
                    },
                )

        with self._lock:
            known = trace_id in self._submitted
        if known:
            with self._lock:
                self._cancelled.add(trace_id)
                self._submitted[trace_id]["status"] = CANCELLED
            return {
                "trace_id": trace_id,
                "status": CANCELLED,
                "cancelled": True,
                "backend": self.backend_name,
            }
        return {
            "trace_id": trace_id,
            "status": FAILED,
            "cancelled": False,
            "error_category": "task:not_found",
            "backend": self.backend_name,
        }
