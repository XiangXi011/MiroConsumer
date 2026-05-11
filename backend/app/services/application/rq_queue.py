"""RQ (Redis Queue) backed task queue."""

from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

import redis
import rq
from rq.exceptions import NoSuchJobError
from rq.job import Job
from rq.registry import FailedJobRegistry

from ...utils.logger import get_logger
from .task_executor import PENDING, RUNNING, SUCCEEDED, FAILED, CANCELLED

logger = get_logger("miroconsumer.rq_queue")


class RQQueueBackend:
    """Queue backend using Redis and RQ for distributed task processing."""

    runs_externally = True

    def __init__(
        self,
        redis_url: str = "",
        queue_name: str = "default",
        allow_memory_fallback: bool = False,
    ) -> None:
        self.redis_url = redis_url
        self.queue_name = queue_name
        self.allow_memory_fallback = allow_memory_fallback
        self._submitted: Dict[str, Dict[str, Any]] = {}
        self._redis: Optional[redis.Redis] = None
        self._queue: Optional[rq.Queue] = None
        self._memory_mode = False
        self._fallback_reason: Optional[str] = None

        try:
            self._redis = redis.Redis.from_url(redis_url)
        except ValueError as exc:
            raise ConnectionError(f"Invalid Redis URL for RQ backend: {redis_url}") from exc

        try:
            self._redis.ping()
        except redis.exceptions.RedisError as exc:
            if allow_memory_fallback:
                self._enable_memory_fallback(f"Redis ping failed: {exc}")
                return
            raise ConnectionError(f"Unable to connect to Redis for RQ backend: {redis_url}") from exc

        self._queue = rq.Queue(queue_name, connection=self._redis)

    def enqueue(
        self,
        trace_id: str,
        fn: Callable,
        *args: Any,
        task_type: Optional[str] = None,
        idempotency_key: Optional[str] = None,
        simulation_id: str = "",
        run_id: str = "base",
        **kwargs: Any,
    ) -> str:
        """Enqueue a task via RQ and return trace_id."""
        if self._memory_mode:
            return self._enqueue_memory(trace_id)

        if self._queue is None:
            if self.allow_memory_fallback:
                self._enable_memory_fallback("RQ queue is unavailable")
                return self._enqueue_memory(trace_id)
            raise ConnectionError("RQ queue is unavailable")

        meta = {
            "trace_id": trace_id,
            "task_type": task_type,
            "idempotency_key": idempotency_key,
            "simulation_id": simulation_id or "",
            "run_id": run_id or "base",
        }
        meta = {key: value for key, value in meta.items() if value is not None}

        try:
            self._queue.enqueue(fn, *args, **kwargs, job_id=trace_id, meta=meta)
        except redis.exceptions.RedisError as exc:
            if self.allow_memory_fallback:
                self._enable_memory_fallback(f"Redis enqueue failed: {exc}")
                return self._enqueue_memory(trace_id)
            raise ConnectionError(f"Unable to enqueue RQ job {trace_id}") from exc

        self._submitted[trace_id] = {"status": PENDING}
        return trace_id

    def get_status(self, trace_id: str) -> Dict[str, Any]:
        """Return task status from RQ."""
        if self._memory_mode:
            return self._get_memory_status(trace_id)

        if self._redis is None:
            if self.allow_memory_fallback:
                self._enable_memory_fallback("Redis connection is unavailable")
                return self._get_memory_status(trace_id)
            raise ConnectionError("Redis connection is unavailable")

        try:
            job = Job.fetch(trace_id, connection=self._redis)
            status = _map_rq_status(job.get_status(refresh=True))
        except NoSuchJobError:
            return self._not_found(trace_id)
        except redis.exceptions.RedisError as exc:
            if self.allow_memory_fallback:
                self._enable_memory_fallback(f"Redis status lookup failed: {exc}")
                return self._get_memory_status(trace_id)
            raise ConnectionError(f"Unable to fetch RQ job {trace_id}") from exc

        self._submitted[trace_id] = {"status": status}
        return {
            "trace_id": trace_id,
            "status": status,
            "backend": "rq",
        }

    def cancel(self, trace_id: str) -> Dict[str, Any]:
        """Cancel an RQ job by trace_id."""
        if self._memory_mode:
            return self._cancel_memory(trace_id)

        if self._redis is None:
            if self.allow_memory_fallback:
                self._enable_memory_fallback("Redis connection is unavailable")
                return self._cancel_memory(trace_id)
            raise ConnectionError("Redis connection is unavailable")

        try:
            job = Job.fetch(trace_id, connection=self._redis)
            job.cancel()
        except NoSuchJobError:
            return {
                "trace_id": trace_id,
                "status": FAILED,
                "cancelled": False,
                "error_category": "task:not_found",
                "backend": "rq",
            }
        except redis.exceptions.RedisError as exc:
            if self.allow_memory_fallback:
                self._enable_memory_fallback(f"Redis cancel failed: {exc}")
                return self._cancel_memory(trace_id)
            raise ConnectionError(f"Unable to cancel RQ job {trace_id}") from exc

        self._submitted[trace_id] = {"status": CANCELLED}
        return {
            "trace_id": trace_id,
            "status": CANCELLED,
            "cancelled": True,
            "backend": "rq",
        }

    def list_dead_letters(self) -> List[Dict[str, Any]]:
        """Return jobs from RQ's failed-job registry."""
        if self._memory_mode:
            return []

        if self._redis is None or self._queue is None:
            raise ConnectionError("Redis connection is unavailable")

        try:
            registry = FailedJobRegistry(queue=self._queue)
            job_ids = registry.get_job_ids()
        except redis.exceptions.RedisError as exc:
            raise ConnectionError("Unable to list RQ failed jobs") from exc

        dead_letters: List[Dict[str, Any]] = []
        for job_id in job_ids:
            item: Dict[str, Any] = {
                "id": job_id,
                "task_id": job_id,
                "reason": "rq_failed_job",
                "payload": {},
                "simulation_id": None,
                "run_id": None,
                "created_at": None,
            }
            try:
                job = Job.fetch(job_id, connection=self._redis)
            except (NoSuchJobError, redis.exceptions.RedisError):
                dead_letters.append(item)
                continue

            meta = dict(getattr(job, "meta", {}) or {})
            created_at = getattr(job, "created_at", None)
            item["payload"] = {
                "status": FAILED,
                "meta": meta,
                "exc_info": getattr(job, "exc_info", None),
            }
            item["simulation_id"] = meta.get("simulation_id")
            item["run_id"] = meta.get("run_id")
            item["created_at"] = _serialize_datetime(created_at)
            dead_letters.append(item)

        return dead_letters

    def _enable_memory_fallback(self, reason: str) -> None:
        self._memory_mode = True
        self._fallback_reason = reason
        self._queue = None
        logger.warning("RQQueueBackend using memory fallback", extra={"reason": reason})

    def _enqueue_memory(self, trace_id: str) -> str:
        self._submitted[trace_id] = {"status": PENDING}
        return trace_id

    def _get_memory_status(self, trace_id: str) -> Dict[str, Any]:
        if trace_id in self._submitted:
            return {
                "trace_id": trace_id,
                "status": self._submitted[trace_id]["status"],
                "backend": "rq",
            }
        return self._not_found(trace_id)

    def _cancel_memory(self, trace_id: str) -> Dict[str, Any]:
        if trace_id in self._submitted:
            self._submitted[trace_id]["status"] = CANCELLED
            return {
                "trace_id": trace_id,
                "status": CANCELLED,
                "cancelled": True,
                "backend": "rq",
            }
        return {
            "trace_id": trace_id,
            "status": FAILED,
            "cancelled": False,
            "error_category": "task:not_found",
            "backend": "rq",
        }

    def _not_found(self, trace_id: str) -> Dict[str, Any]:
        return {
            "trace_id": trace_id,
            "status": FAILED,
            "error_category": "task:not_found",
            "backend": "rq",
        }


def _map_rq_status(status: Any) -> str:
    value = getattr(status, "value", status)
    value = str(value).lower()
    if value in {"created", "queued", "deferred", "scheduled"}:
        return PENDING
    if value == "started":
        return RUNNING
    if value == "finished":
        return SUCCEEDED
    if value == "failed":
        return FAILED
    if value in {"stopped", "canceled", "cancelled"}:
        return CANCELLED
    return PENDING


def _serialize_datetime(value: Any) -> Optional[str]:
    if isinstance(value, datetime):
        return value.isoformat()
    return value
