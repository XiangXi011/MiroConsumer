"""Tests for the Redis/RQ queue backend."""

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest
import redis

from app.services.application.task_executor import (
    CANCELLED,
    FAILED,
    PENDING,
    RUNNING,
    SUCCEEDED,
)


def _work(*args, **kwargs):
    return None


def _mock_backend():
    redis_conn = MagicMock()
    queue = MagicMock()
    patches = [
        patch("app.services.application.rq_queue.redis.Redis.from_url", return_value=redis_conn),
        patch("app.services.application.rq_queue.rq.Queue", return_value=queue),
    ]
    return redis_conn, queue, patches


def test_enqueue_uses_rq_queue_enqueue():
    from app.services.application.rq_queue import RQQueueBackend

    redis_conn, queue, patches = _mock_backend()
    with patches[0] as from_url, patches[1] as queue_cls:
        backend = RQQueueBackend(redis_url="redis://localhost:6379/0")
        result = backend.enqueue(
            "trace_1",
            _work,
            1,
            task_type="simulation",
            idempotency_key="idem_1",
            simulation_id="sim_1",
            run_id="base",
            payload=True,
        )

    assert result == "trace_1"
    from_url.assert_called_once_with("redis://localhost:6379/0")
    redis_conn.ping.assert_called_once()
    queue_cls.assert_called_once_with("default", connection=redis_conn)
    queue.enqueue.assert_called_once()

    args, kwargs = queue.enqueue.call_args
    assert args == (_work, 1)
    assert kwargs["payload"] is True
    assert kwargs["job_id"] == "trace_1"
    assert kwargs["meta"] == {
        "trace_id": "trace_1",
        "task_type": "simulation",
        "idempotency_key": "idem_1",
        "simulation_id": "sim_1",
        "run_id": "base",
    }


@pytest.mark.parametrize(
    ("rq_status", "expected"),
    [
        ("queued", PENDING),
        ("started", RUNNING),
        ("finished", SUCCEEDED),
        ("failed", FAILED),
        ("canceled", CANCELLED),
    ],
)
def test_get_status_fetches_rq_job_and_maps_status(rq_status, expected):
    from app.services.application.rq_queue import RQQueueBackend

    redis_conn, _queue, patches = _mock_backend()
    job = MagicMock()
    job.get_status.return_value = rq_status

    with patches[0], patches[1], patch(
        "app.services.application.rq_queue.Job.fetch",
        return_value=job,
    ) as fetch:
        backend = RQQueueBackend(redis_url="redis://localhost:6379/0")
        status = backend.get_status("trace_status")

    fetch.assert_called_once_with("trace_status", connection=redis_conn)
    job.get_status.assert_called_once_with(refresh=True)
    assert status == {
        "trace_id": "trace_status",
        "status": expected,
        "backend": "rq",
    }


def test_cancel_fetches_rq_job_and_calls_cancel():
    from app.services.application.rq_queue import RQQueueBackend

    redis_conn, _queue, patches = _mock_backend()
    job = MagicMock()

    with patches[0], patches[1], patch(
        "app.services.application.rq_queue.Job.fetch",
        return_value=job,
    ) as fetch:
        backend = RQQueueBackend(redis_url="redis://localhost:6379/0")
        result = backend.cancel("trace_cancel")

    fetch.assert_called_once_with("trace_cancel", connection=redis_conn)
    job.cancel.assert_called_once()
    assert result == {
        "trace_id": "trace_cancel",
        "status": CANCELLED,
        "cancelled": True,
        "backend": "rq",
    }


def test_invalid_redis_url_raises_connection_error():
    from app.services.application.rq_queue import RQQueueBackend

    with pytest.raises(ConnectionError, match="Invalid Redis URL"):
        RQQueueBackend(redis_url="not-a-redis-url")


def test_redis_ping_failure_raises_connection_error_by_default():
    from app.services.application.rq_queue import RQQueueBackend

    redis_conn, _queue, patches = _mock_backend()
    redis_conn.ping.side_effect = redis.exceptions.ConnectionError("redis down")

    with patches[0], patches[1], pytest.raises(ConnectionError, match="Unable to connect"):
        RQQueueBackend(redis_url="redis://localhost:6379/0")


def test_redis_unavailable_can_fallback_to_memory_mode():
    from app.services.application.rq_queue import RQQueueBackend

    redis_conn, queue, patches = _mock_backend()
    redis_conn.ping.side_effect = redis.exceptions.ConnectionError("redis down")

    with patches[0], patches[1] as queue_cls:
        backend = RQQueueBackend(
            redis_url="redis://localhost:6379/0",
            allow_memory_fallback=True,
        )
        trace_id = backend.enqueue("trace_fallback", _work)
        status = backend.get_status("trace_fallback")
        cancel = backend.cancel("trace_fallback")

    queue_cls.assert_not_called()
    queue.enqueue.assert_not_called()
    assert trace_id == "trace_fallback"
    assert status == {
        "trace_id": "trace_fallback",
        "status": PENDING,
        "backend": "rq",
    }
    assert cancel == {
        "trace_id": "trace_fallback",
        "status": CANCELLED,
        "cancelled": True,
        "backend": "rq",
    }


def test_list_dead_letters_reads_failed_job_registry():
    from app.services.application.rq_queue import RQQueueBackend

    _redis_conn, _queue, patches = _mock_backend()
    registry = MagicMock()
    registry.get_job_ids.return_value = ["trace_failed"]
    job = MagicMock()
    job.meta = {"simulation_id": "sim_1", "run_id": "base"}
    job.exc_info = "boom"
    job.created_at = datetime(2026, 5, 8, tzinfo=timezone.utc)

    with patches[0], patches[1], patch(
        "app.services.application.rq_queue.FailedJobRegistry",
        return_value=registry,
    ) as registry_cls, patch(
        "app.services.application.rq_queue.Job.fetch",
        return_value=job,
    ):
        backend = RQQueueBackend(redis_url="redis://localhost:6379/0")
        result = backend.list_dead_letters()

    registry_cls.assert_called_once()
    assert result == [
        {
            "id": "trace_failed",
            "task_id": "trace_failed",
            "reason": "rq_failed_job",
            "payload": {
                "status": FAILED,
                "meta": {"simulation_id": "sim_1", "run_id": "base"},
                "exc_info": "boom",
            },
            "simulation_id": "sim_1",
            "run_id": "base",
            "created_at": "2026-05-08T00:00:00+00:00",
        }
    ]


def test_queue_task_executor_does_not_spawn_local_worker_for_rq_backend():
    from app.services.application.queue_task_executor import QueueTaskExecutor

    backend = MagicMock()
    backend.runs_externally = True
    backend.enqueue.return_value = "trace_external"
    executor = QueueTaskExecutor(backend_name="rq", backend=backend)
    executor._spawn_worker = MagicMock()

    result = executor.submit(_work, trace_id="trace_external")

    assert result == "trace_external"
    backend.enqueue.assert_called_once()
    executor._spawn_worker.assert_not_called()


def test_queue_task_executor_reraises_enqueue_failure_for_rq_backend():
    from app.services.application.queue_task_executor import QueueTaskExecutor

    backend = MagicMock()
    backend.runs_externally = True
    backend.enqueue.side_effect = ConnectionError("redis down")
    executor = QueueTaskExecutor(backend_name="rq", backend=backend)

    with pytest.raises(ConnectionError, match="redis down"):
        executor.submit(_work, trace_id="trace_failure")
