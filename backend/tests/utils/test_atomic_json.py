import json
import threading

from app.utils.atomic_json import atomic_write_json, safe_read_json


def test_atomic_write_json_round_trips_and_removes_tmp(tmp_path):
    path = tmp_path / "state.json"

    atomic_write_json(path, {"status": "running", "count": 3})

    assert safe_read_json(path) == {"status": "running", "count": 3}
    assert not list(tmp_path.glob("state.json.*.tmp"))


def test_safe_read_json_returns_default_for_partial_json(tmp_path):
    path = tmp_path / "run_state.json"
    path.write_text("{", encoding="utf-8")

    assert safe_read_json(path, default={"status": "unknown"}, retries=1, retry_delay=0) == {
        "status": "unknown"
    }


def test_atomic_write_json_survives_concurrent_readers(tmp_path):
    path = tmp_path / "metrics.json"
    atomic_write_json(path, {"value": 0})
    errors = []

    def writer():
        for index in range(30):
            try:
                atomic_write_json(path, {"value": index})
            except OSError as exc:
                errors.append(exc)

    def reader():
        for _ in range(60):
            try:
                payload = safe_read_json(path, default={})
                if payload:
                    assert "value" in payload
            except json.JSONDecodeError as exc:
                errors.append(exc)

    threads = [threading.Thread(target=writer), threading.Thread(target=reader)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert errors == []
