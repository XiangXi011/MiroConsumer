"""Tests for dead-letter query API.

Uses temporary SQLite DB files so the API reads real persisted data.
"""

import os

from flask import Flask
from sqlalchemy import create_engine, insert
from sqlalchemy.orm import sessionmaker

from app.api import consumer_bp, graph_bp, report_bp, simulation_bp
from app.config import Config
from app.repositories.sqlalchemy import metadata, dead_letters


def _create_test_app():
    app = Flask(__name__)
    app.config["TESTING"] = True
    if hasattr(app, "json") and hasattr(app.json, "ensure_ascii"):
        app.json.ensure_ascii = False
    app.register_blueprint(graph_bp, url_prefix="/api/graph")
    app.register_blueprint(simulation_bp, url_prefix="/api/simulation")
    app.register_blueprint(report_bp, url_prefix="/api/report")
    app.register_blueprint(consumer_bp, url_prefix="/api/consumer")
    return app


def test_sqlite_backend_returns_dead_letters(tmp_path, monkeypatch):
    db_path = tmp_path / "test_dl.db"
    db_url = f"sqlite:///{db_path}"
    engine = create_engine(db_url)
    metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)

    with session_factory() as session:
        session.execute(
            insert(dead_letters).values(
                id="dl_test_1",
                simulation_id="sim_1",
                run_id="base",
                task_id="task_1",
                reason="max_retries_exceeded",
                payload={"attempt_count": 3, "error": "timeout"},
            )
        )
        session.commit()

    monkeypatch.setattr(Config, "_queue_backend_cache", "sqlite")
    monkeypatch.setattr(Config, "_db_url_cache", db_url)

    app = _create_test_app()
    client = app.test_client()

    response = client.get("/api/consumer/task-queue/dead-letters")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["success"] is True
    assert payload["data"]["backend"] == "sqlite"
    assert len(payload["data"]["dead_letters"]) == 1
    assert payload["data"]["dead_letters"][0]["id"] == "dl_test_1"
    assert payload["data"]["dead_letters"][0]["task_id"] == "task_1"
    assert payload["data"]["dead_letters"][0]["reason"] == "max_retries_exceeded"


def test_repeated_sqlite_calls_do_not_leak_file_handles(tmp_path, monkeypatch):
    """Repeated API calls against a temp SQLite DB must not fail on Windows file cleanup."""
    db_path = tmp_path / "test_dl_repeated.db"
    db_url = f"sqlite:///{db_path}"
    engine = create_engine(db_url)
    metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)

    with session_factory() as session:
        session.execute(
            insert(dead_letters).values(
                id="dl_test_r1",
                simulation_id="sim_r1",
                run_id="base",
                task_id="task_r1",
                reason="max_retries_exceeded",
                payload={"attempt_count": 3, "error": "timeout"},
            )
        )
        session.commit()

    engine.dispose()

    monkeypatch.setattr(Config, "_queue_backend_cache", "sqlite")
    monkeypatch.setattr(Config, "_db_url_cache", db_url)

    app = _create_test_app()
    client = app.test_client()

    # Make repeated calls; without engine.dispose() each call leaks a file handle
    for _ in range(3):
        response = client.get("/api/consumer/task-queue/dead-letters")
        assert response.status_code == 200
        payload = response.get_json()
        assert payload["success"] is True
        assert len(payload["data"]["dead_letters"]) == 1

    # On Windows, undisposed engines hold file locks; verify cleanup is possible
    assert os.path.exists(str(db_path))
    os.remove(str(db_path))


def test_thread_backend_returns_empty_dead_letters(monkeypatch):
    monkeypatch.setattr(Config, "_queue_backend_cache", "thread")

    app = _create_test_app()
    client = app.test_client()

    response = client.get("/api/consumer/task-queue/dead-letters")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["success"] is True
    assert payload["data"]["backend"] == "thread"
    assert payload["data"]["dead_letters"] == []


def test_invalid_backend_returns_400(monkeypatch):
    monkeypatch.setattr(Config, "_queue_backend_cache", "unknown")

    app = _create_test_app()
    client = app.test_client()

    response = client.get("/api/consumer/task-queue/dead-letters")

    assert response.status_code == 400
    payload = response.get_json()
    assert payload["success"] is False
    assert "backend" in payload["error"].lower() or "unsupported" in payload["error"].lower()
