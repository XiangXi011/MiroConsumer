from flask import Flask, jsonify

from app.auth.middleware import init_auth, register_user, require_permission
from app.auth.models import User
from app.auth.routes import auth_bp
from app.middleware.rate_limiter import auth_rate_limit, configure_rate_limiter


SECRET = "error-contract-secret-key-1234567890"


def test_auth_required_response_contract():
    app = Flask(__name__)
    app.config.update(TESTING=True, SECRET_KEY=SECRET, AUTH_BYPASS_IN_TESTING=False)
    init_auth(app)

    @app.route("/api/protected")
    @require_permission("project.read")
    def protected():
        return jsonify({"success": True})

    response = app.test_client().get("/api/protected")
    payload = response.get_json()

    assert response.status_code == 401
    assert payload["success"] is False
    assert payload["error"] == "AUTH_REQUIRED"
    assert "message" in payload


def test_forbidden_response_contract():
    app = Flask(__name__)
    app.config.update(TESTING=True, SECRET_KEY=SECRET, AUTH_BYPASS_IN_TESTING=False)
    init_auth(app)

    @app.route("/api/admin")
    @require_permission("admin.manage_users")
    def admin():
        return jsonify({"success": True})

    user = User("u1", "viewer", "viewer@example.com", "viewer", "tenant_a", "ws_tenant_a")
    register_user(user)
    from app.auth.middleware import create_jwt_token
    token = create_jwt_token(user)

    response = app.test_client().get("/api/admin", headers={"Authorization": f"Bearer {token}"})
    payload = response.get_json()

    assert response.status_code == 403
    assert payload["success"] is False
    assert payload["error"] == "FORBIDDEN"
    assert "message" in payload


def test_rate_limited_response_contract():
    app = Flask(__name__)
    app.config.update(TESTING=True, RATE_LIMIT_ENABLED=True, RATE_LIMIT_BACKEND="memory", AUTH_RATE_LIMIT_PER_MINUTE=1)
    configure_rate_limiter(app)

    @app.route("/api/auth/login", methods=["POST"])
    @auth_rate_limit
    def login():
        return jsonify({"success": False, "error": "AUTH_FAILED", "message": "Invalid credentials"}), 401

    client = app.test_client()
    client.post("/api/auth/login", json={"username": "demo"})
    response = client.post("/api/auth/login", json={"username": "demo"})
    payload = response.get_json()

    assert response.status_code == 429
    assert payload["success"] is False
    assert payload["error"] == "RATE_LIMITED"
    assert "retry_after" in payload
