"""SQLite-backed durable task queue.

Persists tasks into the tasks table, supports idempotency via
(task_type, idempotency_key), and provides recovery + dead-letter handling.
"""

import uuid
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

from sqlalchemy import select, insert, update
from sqlalchemy.orm import sessionmaker

from ...utils.logger import get_logger
from .task_executor import PENDING, RUNNING, SUCCEEDED, FAILED, CANCELLED, DEAD_LETTER
from ...repositories.sqlalchemy import tasks, task_attempts, dead_letters

logger = get_logger("miroconsumer.sqlite_queue")


def _json_safe(value: Any) -> Any:
    """Recursively convert a value to a JSON-safe representation.

    - datetime  -> ISO 8601 string
    - objects   -> stable repr string
    - dict/list -> recursively converted
    """
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, dict):
        return {k: _json_safe(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_json_safe(v) for v in value]
    try:
        # Fast path: let json.dumps decide; if it works, keep the value as-is
        __import__("json").dumps(value)
        return value
    except (TypeError, ValueError):
        return repr(value)


class SQLiteQueueBackend:
    """Durable queue using SQLite for task persistence."""

    def __init__(self, session_factory: Optional[sessionmaker] = None) -> None:
        self.session_factory = session_factory

    def _session(self):
        return self.session_factory()

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
    ):
        """Persist a task and return (trace_id, created).

        If an idempotency_key is provided and a task with the same
        (task_type, idempotency_key) already exists, return the existing
        task id with created=False.

        Returns a tuple (trace_id, created) where created is True for a new
        task and False for a duplicate.
        """
        if self.session_factory is None:
            logger.warning("SQLiteQueueBackend has no session_factory", extra={"trace_id": trace_id})
            return (trace_id, True)

        # Build payload with JSON-safe representations
        payload = {
            "callable": getattr(fn, "__name__", repr(fn)),
            "args": [_json_safe(a) for a in args],
            "kwargs": {k: _json_safe(v) for k, v in kwargs.items()},
        }
        if idempotency_key is not None:
            payload["idempotency_key"] = idempotency_key

        with self._session() as session:
            # Idempotency: check for existing task with same (task_type, idempotency_key)
            if idempotency_key is not None and task_type is not None:
                existing = session.execute(
                    select(tasks)
                    .where(tasks.c.task_type == task_type)
                    .where(tasks.c.payload["idempotency_key"].as_string() == idempotency_key)
                ).mappings().fetchone()
                if existing is not None:
                    return (existing["id"], False)

            # Check for duplicate by trace_id
            existing_by_id = session.execute(
                select(tasks.c.id).where(tasks.c.id == trace_id)
            ).fetchone()
            if existing_by_id is not None:
                return (trace_id, False)

            session.execute(
                insert(tasks).values(
                    id=trace_id,
                    simulation_id=simulation_id or "",
                    run_id=run_id or "base",
                    task_type=task_type,
                    status=PENDING,
                    payload=payload,
                )
            )
            session.commit()
        return (trace_id, True)

    def get_status(self, trace_id: str) -> Dict[str, Any]:
        """Return task status from persistent store."""
        if self.session_factory is None:
            return {
                "trace_id": trace_id,
                "status": FAILED,
                "error_category": "task:not_found",
                "backend": "sqlite",
            }

        with self._session() as session:
            row = (
                session.execute(select(tasks).where(tasks.c.id == trace_id))
                .mappings()
                .fetchone()
            )
            if row is None:
                return {
                    "trace_id": trace_id,
                    "status": FAILED,
                    "error_category": "task:not_found",
                    "backend": "sqlite",
                }
            result = {
                "trace_id": trace_id,
                "status": row["status"],
                "backend": "sqlite",
            }
            if row.get("task_type") is not None:
                result["task_type"] = row["task_type"]
            payload = dict(row.get("payload", {}) or {})
            if payload.get("error_category"):
                result["error_category"] = payload["error_category"]
            return result

    def cancel(self, trace_id: str) -> Dict[str, Any]:
        """Mark a task as cancelled in persistent store."""
        if self.session_factory is None:
            return {
                "trace_id": trace_id,
                "status": FAILED,
                "cancelled": False,
                "error_category": "task:not_found",
                "backend": "sqlite",
            }

        with self._session() as session:
            result = session.execute(
                update(tasks)
                .where(tasks.c.id == trace_id)
                .values(status=CANCELLED)
            )
            session.commit()
            if result.rowcount == 0:
                return {
                    "trace_id": trace_id,
                    "status": FAILED,
                    "cancelled": False,
                    "error_category": "task:not_found",
                    "backend": "sqlite",
                }
            return {
                "trace_id": trace_id,
                "status": CANCELLED,
                "cancelled": True,
                "backend": "sqlite",
            }

    def mark_running(self, trace_id: str) -> bool:
        """Mark a task as RUNNING. Returns True if the task was found."""
        if self.session_factory is None:
            return False
        with self._session() as session:
            result = session.execute(
                update(tasks)
                .where(tasks.c.id == trace_id)
                .values(status=RUNNING)
            )
            session.commit()
            return result.rowcount > 0

    def mark_succeeded(self, trace_id: str, result: Any = None) -> bool:
        """Mark a task as SUCCEEDED and store optional result in payload.

        Returns True if the task was found and updated.
        Returns False if the task was not found or is already CANCELLED.
        """
        if self.session_factory is None:
            return False
        with self._session() as session:
            row = (
                session.execute(select(tasks).where(tasks.c.id == trace_id))
                .mappings()
                .fetchone()
            )
            if row is None:
                return False
            if row["status"] == CANCELLED:
                return False
            payload = dict(row.get("payload", {}) or {})
            if result is not None:
                payload["result"] = _json_safe(result)
            session.execute(
                update(tasks)
                .where(tasks.c.id == trace_id)
                .values(status=SUCCEEDED, payload=payload)
            )
            session.commit()
            return True

    def mark_failed(self, trace_id: str, error_category: str, error: str) -> bool:
        """Mark a task as FAILED and store error info in payload.

        Returns True if the task was found and updated.
        Returns False if the task was not found or is already CANCELLED.
        """
        if self.session_factory is None:
            return False
        with self._session() as session:
            row = (
                session.execute(select(tasks).where(tasks.c.id == trace_id))
                .mappings()
                .fetchone()
            )
            if row is None:
                return False
            if row["status"] == CANCELLED:
                return False
            payload = dict(row.get("payload", {}) or {})
            payload["error_category"] = error_category
            payload["error"] = error
            session.execute(
                update(tasks)
                .where(tasks.c.id == trace_id)
                .values(status=FAILED, payload=payload)
            )
            session.commit()
            return True

    def recover_stale_running(
        self,
        now: datetime,
        visibility_timeout_seconds: int,
        retry_limit: int,
    ) -> int:
        """Find stale RUNNING tasks and either retry or dead-letter them.

        Returns the number of stale tasks processed.
        """
        if self.session_factory is None:
            return 0

        threshold = now - __import__("datetime").timedelta(seconds=visibility_timeout_seconds)

        with self._session() as session:
            stale_rows = session.execute(
                select(tasks)
                .where(tasks.c.status == RUNNING)
                .where(tasks.c.updated_at < threshold)
            ).mappings().fetchall()

            for row in stale_rows:
                task_id = row["id"]
                payload = dict(row.get("payload", {}) or {})
                sim_id = row["simulation_id"] or ""
                run_id = row["run_id"] or "base"
                task_type = row.get("task_type")
                attempt_count = payload.get("attempt_count", 0) or 0

                if attempt_count >= retry_limit:
                    # Dead letter: limit reached
                    original_payload = dict(payload)
                    dl_payload = {
                        **original_payload,
                        "original_payload": original_payload,
                        "failure_reason": "max_retries_exceeded",
                        "final_attempt_count": attempt_count,
                        "written_at": datetime.now(timezone.utc).isoformat(),
                    }
                    session.execute(
                        update(tasks)
                        .where(tasks.c.id == task_id)
                        .values(status=DEAD_LETTER)
                    )
                    session.execute(
                        insert(dead_letters).values(
                            id=f"dl_{uuid.uuid4().hex[:12]}",
                            simulation_id=sim_id,
                            run_id=run_id,
                            task_id=task_id,
                            reason="max_retries_exceeded",
                            payload=dl_payload,
                        )
                    )
                else:
                    # Retry: record attempt, increment count, reset to PENDING
                    new_attempt = attempt_count + 1
                    session.execute(
                        insert(task_attempts).values(
                            id=f"att_{uuid.uuid4().hex[:12]}",
                            simulation_id=sim_id,
                            run_id=run_id,
                            task_id=task_id,
                            attempt_number=new_attempt,
                        )
                    )
                    payload["attempt_count"] = new_attempt
                    session.execute(
                        update(tasks)
                        .where(tasks.c.id == task_id)
                        .values(status=PENDING, payload=payload)
                    )

            session.commit()
            return len(stale_rows)

    def list_dead_letters(self) -> List[Dict[str, Any]]:
        """Return all persisted dead-letter records."""
        if self.session_factory is None:
            return []

        with self._session() as session:
            rows = session.execute(
                select(dead_letters).order_by(dead_letters.c.created_at.desc())
            ).mappings().fetchall()
            return [
                {
                    "id": row["id"],
                    "task_id": row["task_id"],
                    "reason": row["reason"],
                    "payload": dict(row.get("payload", {}) or {}),
                    "simulation_id": row.get("simulation_id"),
                    "run_id": row.get("run_id"),
                    "created_at": row.get("created_at"),
                }
                for row in rows
            ]
