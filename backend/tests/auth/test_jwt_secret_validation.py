import time

import jwt
import pytest
from flask import Flask, jsonify

from app.auth.middleware import create_jwt_token, init_auth, register_user, require_permission
from app.auth.models import User


def _app_with_secret(secret=None):
    app = Flask(__name__)
    app.config["TESTING"] = True
    app.config["AUTH_BYPASS_IN_TESTING"] = False
    if secret is not None:
        app.config["SECRET_KEY"] = secret
    return app


def test_init_auth_requires_secret():
    with pytest.raises(RuntimeError, match="JWT secret is required"):
        init_auth(_app_with_secret(""))


def test_init_auth_rejects_dev_secret():
    with pytest.raises(RuntimeError, match="weak/default"):
        init_auth(_app_with_secret("dev-secret"))


def test_init_auth_rejects_short_secret():
    with pytest.raises(RuntimeError, match=">= 32"):
        init_auth(_app_with_secret("short-secret"))


def test_init_auth_accepts_valid_secret():
    app = _app_with_secret("valid-secret-key-that-is-long-enough-32")

    init_auth(app)

    assert app.extensions["auth_repository"]


@pytest.fixture
def protected_app():
    app = _app_with_secret("valid-secret-key-that-is-long-enough-32")
    init_auth(app)

    @app.route("/api/protected")
    @require_permission("project.read")
    def protected():
        return jsonify({"success": True})

    user = User(
        user_id="user_jwt",
        username="jwt",
        email="jwt@example.com",
        role="researcher",
        tenant_id="tenant_a",
        workspace_id="ws_tenant_a",
    )
    register_user(user)
    return app


def test_expired_token_is_rejected(protected_app):
    user = protected_app.extensions["auth_repository"].get_user("user_jwt")
    token = create_jwt_token(user, expires_in=-1)

    response = protected_app.test_client().get(
        "/api/protected",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 401


def test_forged_token_is_rejected(protected_app):
    token = jwt.encode(
        {
            "sub": "user_jwt",
            "user_id": "user_jwt",
            "role": "researcher",
            "tenant_id": "tenant_a",
            "workspace_id": "ws_tenant_a",
            "iat": int(time.time()),
            "exp": int(time.time()) + 3600,
            "jti": "jwt_forged",
        },
        "different-secret-that-is-long-enough-32",
        algorithm="HS256",
    )

    response = protected_app.test_client().get(
        "/api/protected",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 401


def test_alg_none_token_is_rejected(protected_app):
    token = jwt.encode(
        {
            "sub": "user_jwt",
            "user_id": "user_jwt",
            "role": "researcher",
            "tenant_id": "tenant_a",
            "workspace_id": "ws_tenant_a",
            "iat": int(time.time()),
            "exp": int(time.time()) + 3600,
            "jti": "jwt_none",
        },
        key="",
        algorithm="none",
    )

    response = protected_app.test_client().get(
        "/api/protected",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 401
