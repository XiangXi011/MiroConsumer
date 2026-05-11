import jwt
import pytest
from flask import Flask

from app.auth.middleware import get_auth_repository, get_jwt_secret, init_auth
from app.auth.routes import auth_bp


@pytest.fixture
def auth_app():
    app = Flask(__name__)
    app.config["TESTING"] = True
    app.config["SECRET_KEY"] = "test-secret-key-that-is-long-enough-32"
    app.config["AUTH_BYPASS_IN_TESTING"] = False
    app.config["AUDIT_LOG_PATH"] = ""
    init_auth(app)
    app.register_blueprint(auth_bp)
    yield app
    get_auth_repository().clear_all()


@pytest.fixture
def client(auth_app):
    return auth_app.test_client()


def _register(client, **overrides):
    payload = {
        "username": "demo",
        "email": "demo@example.com",
        "password": "StrongPassword123!",
        "role": "researcher",
        "tenant_id": "tenant_a",
    }
    payload.update(overrides)
    return client.post("/api/auth/register", json=payload)


def test_register_requires_password(client):
    response = _register(client, password=None)

    assert response.status_code == 400
    assert response.get_json()["error"] == "VALIDATION_ERROR"


def test_register_hashes_password_and_never_returns_hash(client):
    response = _register(client)

    assert response.status_code == 201
    data = response.get_json()["data"]
    assert "password" not in data
    assert "password_hash" not in data

    user = get_auth_repository().get_user(data["user_id"])
    assert user.password_hash
    assert user.password_hash != "StrongPassword123!"


def test_username_and_password_login_returns_sanitized_jwt(client):
    user_id = _register(client).get_json()["data"]["user_id"]

    response = client.post(
        "/api/auth/login",
        json={"username": "demo", "password": "StrongPassword123!"},
    )

    assert response.status_code == 200
    token = response.get_json()["data"]["token"]
    payload = jwt.decode(token, get_jwt_secret(), algorithms=["HS256"])
    assert payload["sub"] == user_id
    assert payload["user_id"] == user_id
    assert payload["tenant_id"] == "tenant_a"
    assert "jti" in payload
    assert "password_hash" not in payload


def test_user_id_only_login_is_forbidden(client):
    user_id = _register(client).get_json()["data"]["user_id"]

    response = client.post("/api/auth/login", json={"user_id": user_id})

    assert response.status_code == 401
    assert response.get_json() == {
        "success": False,
        "error": "AUTH_FAILED",
        "message": "Invalid credentials",
    }


def test_user_id_with_wrong_password_fails(client):
    user_id = _register(client).get_json()["data"]["user_id"]

    response = client.post(
        "/api/auth/login",
        json={"user_id": user_id, "password": "WrongPassword123!"},
    )

    assert response.status_code == 401
    assert response.get_json()["error"] == "AUTH_FAILED"


def test_missing_user_and_wrong_password_share_error_shape(client):
    _register(client)

    missing = client.post(
        "/api/auth/login",
        json={"username": "missing", "password": "StrongPassword123!"},
    )
    wrong = client.post(
        "/api/auth/login",
        json={"username": "demo", "password": "WrongPassword123!"},
    )

    assert missing.status_code == wrong.status_code == 401
    assert missing.get_json() == wrong.get_json()


def test_disabled_user_cannot_login(client):
    user_id = _register(client).get_json()["data"]["user_id"]
    user = get_auth_repository().get_user(user_id)
    user.is_active = False
    get_auth_repository().save_user(user)

    response = client.post(
        "/api/auth/login",
        json={"username": "demo", "password": "StrongPassword123!"},
    )

    assert response.status_code == 401
    assert response.get_json()["error"] == "AUTH_FAILED"
