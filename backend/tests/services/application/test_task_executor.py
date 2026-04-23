"""Tests for task executor abstraction."""

import threading
import time

from app.services.application.task_executor import ThreadTaskExecutor


class TestThreadTaskExecutor:
    def test_submit_runs_function_in_background(self):
        executor = ThreadTaskExecutor()
        results = []

        def capture():
            results.append(threading.current_thread().name)

        executor.submit(capture)
        time.sleep(0.2)

        assert len(results) == 1
        assert "Thread" in results[0]

    def test_submit_passes_args_and_kwargs(self):
        executor = ThreadTaskExecutor()
        results = []

        def capture(a, b, c=None):
            results.append((a, b, c))

        executor.submit(capture, 1, 2, c=3)
        time.sleep(0.2)

        assert results == [(1, 2, 3)]
