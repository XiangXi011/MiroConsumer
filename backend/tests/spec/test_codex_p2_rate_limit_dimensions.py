"""SPEC-P2-023 multi-dimensional rate limit contract."""

from __future__ import annotations

from dataclasses import dataclass

from flask import Flask, g, jsonify, request

from app.middleware.rate_limiter import configure_rate_limiter, rate_limit


@dataclass
class FakeUser:
    user_id: str
    tenant_id: str


def _build_app() -> Flask:
    app = Flask(__name__)
    app.config.update(
        TESTING=True,
        RATE_LIMIT_ENABLED=True,
        RATE_LIMIT_BACKEND="memory",
        RATE_LIMIT_IP="100/minute",
        RATE_LIMIT_USER="10/minute",
        RATE_LIMIT_TENANT="2/minute",
    )
    configure_rate_limiter(app)

    @app.before_request
    def bind_identity():
        tenant_id = request.headers.get("X-Test-Tenant", "tenant-a")
        user_id = request.headers.get("X-Test-User", "user-a")
        g.current_user = FakeUser(user_id=user_id, tenant_id=tenant_id)
        g.current_tenant = tenant_id

    @app.get("/limited")
    @rate_limit
    def limited():
        return jsonify({"ok": True})

    return app


def test_same_tenant_users_share_tenant_quota_before_user_or_ip_quota():
    app = _build_app()
    client = app.test_client()

    first = client.get("/limited", headers={"X-Test-Tenant": "tenant-a", "X-Test-User": "user-a"})
    second = client.get("/limited", headers={"X-Test-Tenant": "tenant-a", "X-Test-User": "user-b"})
    blocked = client.get("/limited", headers={"X-Test-Tenant": "tenant-a", "X-Test-User": "user-c"})

    assert first.status_code == 200
    assert second.status_code == 200
    assert blocked.status_code == 429
    payload = blocked.get_json()
    assert payload["error_code"] == "RATE_LIMITED"
    assert payload["limit_type"] == "tenant"


def test_same_ip_different_tenants_have_independent_tenant_counters():
    app = _build_app()
    client = app.test_client()

    assert client.get("/limited", headers={"X-Test-Tenant": "tenant-a", "X-Test-User": "user-a"}).status_code == 200
    assert client.get("/limited", headers={"X-Test-Tenant": "tenant-a", "X-Test-User": "user-b"}).status_code == 200

    response = client.get("/limited", headers={"X-Test-Tenant": "tenant-b", "X-Test-User": "user-c"})

    assert response.status_code == 200


def test_response_headers_expose_ip_user_and_tenant_remaining_counts():
    app = _build_app()
    response = app.test_client().get(
        "/limited",
        headers={"X-Test-Tenant": "tenant-a", "X-Test-User": "user-a"},
    )

    assert response.status_code == 200
    assert response.headers["X-RateLimit-Remaining-IP"] == "99"
    assert response.headers["X-RateLimit-Remaining-User"] == "9"
    assert response.headers["X-RateLimit-Remaining-Tenant"] == "1"
