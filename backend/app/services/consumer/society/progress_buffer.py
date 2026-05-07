"""Buffered progress writer for the consumer society runtime."""

from __future__ import annotations

import time
from datetime import datetime
from typing import Any, Dict, Mapping


class ProgressBuffer:
    """Buffer progress updates and flush on step count, time interval, or final state."""

    def __init__(
        self,
        store: Any,
        simulation_id: str,
        progress_base: Mapping[str, Any],
        *,
        flush_interval_steps: int = 8,
        flush_interval_seconds: float = 2.0,
    ):
        self._store = store
        self._simulation_id = simulation_id
        self._progress: Dict[str, Any] = dict(progress_base)
        self._flush_interval_steps = flush_interval_steps
        self._flush_interval_seconds = flush_interval_seconds
        self._completed_since_flush = 0
        self._last_flush_time = time.monotonic()
        self._pending = False

    def step_completed(self, **kwargs: Any) -> None:
        """Record a completed agent step; flush if thresholds crossed."""
        self._progress.update(kwargs)
        self._completed_since_flush += 1
        self._pending = True
        if self._completed_since_flush >= self._flush_interval_steps:
            self.flush()

    def round_completed(self, round_index: int) -> None:
        """Record round completion and flush."""
        self._progress.update(
            {
                "current_round": round_index + 1,
                "status": "round_completed",
                "phase": "round_completed",
            }
        )
        self.flush()

    def final(self, status: str, **kwargs: Any) -> None:
        """Record final status and force flush."""
        self._progress.update({"status": status, "phase": "completed", **kwargs})
        self._force_flush()

    def maybe_time_flush(self) -> None:
        """Flush if the time interval has elapsed since the last flush."""
        now = time.monotonic()
        if self._pending and (now - self._last_flush_time) >= self._flush_interval_seconds:
            self.flush()

    def flush(self) -> None:
        """Flush pending progress if there is any."""
        if self._pending:
            self._force_flush()

    def _force_flush(self) -> None:
        self._progress["updated_at"] = datetime.now().isoformat()
        self._store.write_progress(self._simulation_id, self._progress)
        self._completed_since_flush = 0
        self._last_flush_time = time.monotonic()
        self._pending = False

    @property
    def progress(self) -> Dict[str, Any]:
        return dict(self._progress)


__all__ = ["ProgressBuffer"]
