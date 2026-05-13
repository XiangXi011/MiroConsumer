"""SPEC-P2-027 export endpoint rate and concurrency limits."""

from __future__ import annotations

import threading
from dataclasses import dataclass

from flask import Flask, g, jsonify, request

from app.middleware.rate_limiter import configure_rate_limiter, export_rate_limit


@dataclass
class FakeUser:
    user_id: str
    tenant_id: str = "tenant-a"


def _build_export_app(release: threading.Event | None = None, entered: threading.Event | None = None) -> Flask:
    app = Flask(__name__)
    app.config.update(
        TESTING=True,
        RATE_LIMIT_ENABLED=True,
        RATE_LIMIT_BACKEND="memory",
        EXPORT_RATE_LIMIT="5/hour",
    )
    configure_rate_limiter(app)

    @app.before_request
    def bind_identity():
        g.current_user = FakeUser(user_id=request.headers.get("X-Test-User", "user-a"))
        g.current_tenant = "tenant-a"

    @app.get("/export")
    @export_rate_limit
    def export():
        if entered is not None:
            entered.set()
        if release is not None:
            release.wait(timeout=5)
        return jsonify({"exported": True})

    return app


def test_export_rate_limit_uses_five_per_hour_and_headers():
    client = _build_export_app().test_client()

    responses = [client.get("/export") for _ in range(5)]
    blocked = client.get("/export")

    assert [response.status_code for response in responses] == [200, 200, 200, 200, 200]
    assert responses[0].headers["X-RateLimit-Export-Remaining"] == "4"
    assert responses[-1].headers["X-RateLimit-Export-Remaining"] == "0"
    assert blocked.status_code == 429
    assert blocked.headers["Retry-After"]
    assert blocked.get_json()["limit_type"] == "export"


def test_export_limit_is_per_user_not_shared_by_same_ip():
    client = _build_export_app().test_client()

    for _ in range(5):
        assert client.get("/export", headers={"X-Test-User": "user-a"}).status_code == 200

    response = client.get("/export", headers={"X-Test-User": "user-b"})

    assert response.status_code == 200
    assert response.headers["X-RateLimit-Export-Remaining"] == "4"


def test_concurrent_export_for_same_user_is_rejected():
    release = threading.Event()
    entered = threading.Event()
    app = _build_export_app(release=release, entered=entered)
    first_result: dict[str, int] = {}

    def run_first_request():
        response = app.test_client().get("/export", headers={"X-Test-User": "user-a"})
        first_result["status_code"] = response.status_code

    thread = threading.Thread(target=run_first_request)
    thread.start()
    assert entered.wait(timeout=2)

    blocked = app.test_client().get("/export", headers={"X-Test-User": "user-a"})
    release.set()
    thread.join(timeout=5)

    assert blocked.status_code == 429
    assert blocked.get_json()["error_message"] == "Concurrent export limit exceeded"
    assert first_result["status_code"] == 200
