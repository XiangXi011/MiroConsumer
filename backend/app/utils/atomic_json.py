"""Atomic JSON helpers for polled file-system state."""

from __future__ import annotations

import json
import os
import time
import uuid
from pathlib import Path
from typing import Any

from .logger import get_logger

logger = get_logger("miroconsumer.atomic_json")


def atomic_write_json(path: str | os.PathLike, data: Any, *, indent: int = 2) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    temp_path = target.with_name(f"{target.name}.{uuid.uuid4().hex}.tmp")
    try:
        with temp_path.open("w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=indent, sort_keys=True)
            f.flush()
            os.fsync(f.fileno())
        last_error: OSError | None = None
        for attempt in range(5):
            try:
                os.replace(temp_path, target)
                last_error = None
                break
            except OSError as exc:
                last_error = exc
                time.sleep(0.02 * (attempt + 1))
        if last_error is not None:
            raise last_error
    finally:
        if temp_path.exists():
            try:
                temp_path.unlink()
            except OSError:
                logger.warning("Failed to remove temp json file: %s", temp_path)


def safe_read_json(
    path: str | os.PathLike,
    default: Any = None,
    *,
    retries: int = 3,
    retry_delay: float = 0.05,
) -> Any:
    target = Path(path)
    if not target.exists():
        return default
    last_error: Exception | None = None
    for attempt in range(max(1, retries)):
        try:
            with target.open("r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError) as exc:
            last_error = exc
            if attempt < retries - 1:
                time.sleep(retry_delay)
    logger.warning("safe_read_json returning default for %s after error: %s", target, last_error)
    return default


__all__ = ["atomic_write_json", "safe_read_json"]
