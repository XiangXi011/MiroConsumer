"""Authentication API routes."""

from __future__ import annotations

import secrets

from flask import Blueprint, g, jsonify, request

from ..middleware.rate_limiter import auth_rate_limit
from ..security.audit_log import audit_event
from ..utils.request_validator import safe_get_json
from .middleware import (
    clear_auth_state,
    create_jwt_token,
    get_auth_repository,
    register_api_key,
    register_user,
    require_permission,
)
from .models import (
    APIKey,
    ROLE_PERMISSIONS,
    User,
    generate_api_key,
    hash_password,
    validate_password_strength,
    verify_password,
)


auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")


def _validation_error(message: str, status: int = 400):
    return jsonify({"success": False, "error": "VALIDATION_ERROR", "message": message}), status


def _auth_failed():
    return jsonify({"success": False, "error": "AUTH_FAILED", "message": "Invalid credentials"}), 401


def _audit_auth(event_type: str, *, user=None, success: bool, reason: str, identifier: str = "") -> None:
    audit_event(
        event_type=event_type,
        actor_user_id=getattr(user, "user_id", None) if user else None,
        actor_tenant_id=getattr(user, "tenant_id", None) if user else None,
        target_type="auth",
        target_id=identifier or getattr(user, "user_id", None),
        ip=request.remote_addr,
        user_agent=request.headers.get("User-Agent"),
        success=success,
        reason=reason,
        details={"identifier": identifier},
    )


@auth_bp.route("/register", methods=["POST"])
def register():
    data = safe_get_json()
    if isinstance(data, tuple):
        return data

    username = (data.get("username") or "").strip()
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""
    role = data.get("role", "researcher")
    tenant_id = data.get("tenant_id", "default")

    if not username or not email:
        return _validation_error("username and email required")

    password_error = validate_password_strength(password)
    if password_error:
        return _validation_error(password_error)

    if role not in ROLE_PERMISSIONS:
        return _validation_error(f"Invalid role. Must be one of: {list(ROLE_PERMISSIONS.keys())}")

    repository = get_auth_repository()
    if repository.get_user_by_username(username) or repository.get_user_by_email(email):
        return jsonify({"success": False, "error": "CONFLICT", "message": "User already exists"}), 409

    user_id = f"user_{secrets.token_hex(8)}"
    user = User(
        user_id=user_id,
        username=username,
        email=email,
        role=role,
        tenant_id=tenant_id,
        workspace_id=f"ws_{tenant_id}",
        password_hash=hash_password(password),
    )
    register_user(user)
    _audit_auth("auth.registered", user=user, success=True, reason="registered", identifier=username)

    return jsonify({"success": True, "data": {
        "user_id": user_id,
        "username": username,
        "email": email,
        "role": role,
        "tenant_id": tenant_id,
    }}), 201


@auth_bp.route("/login", methods=["POST"])
@auth_rate_limit
def login():
    data = safe_get_json()
    if isinstance(data, tuple):
        return data

    password = data.get("password") or ""
    username = (data.get("username") or "").strip()
    email = (data.get("email") or "").strip().lower()
    user_id = (data.get("user_id") or "").strip()
    identifier = username or email or user_id

    if not password or not identifier:
        _audit_auth("auth.login_failed", success=False, reason="missing_credentials", identifier=identifier)
        return _auth_failed()

    repository = get_auth_repository()
    user = None
    if username:
        user = repository.get_user_by_username(username)
    elif email:
        user = repository.get_user_by_email(email)
    elif user_id:
        user = repository.get_user(user_id)

    if not user or not user.is_active or not verify_password(password, user.password_hash):
        if user:
            user.failed_login_count += 1
            repository.save_user(user)
        _audit_auth("auth.login_failed", user=user, success=False, reason="invalid_credentials", identifier=identifier)
        return _auth_failed()

    if user.failed_login_count:
        user.failed_login_count = 0
        repository.save_user(user)

    token = create_jwt_token(user)
    _audit_auth("auth.login_success", user=user, success=True, reason="authenticated", identifier=identifier)
    return jsonify({"success": True, "data": {
        "token": token,
        "user_id": user.user_id,
        "username": user.username,
        "role": user.role,
        "tenant_id": user.tenant_id,
    }})


@auth_bp.route("/api-keys", methods=["POST"])
@require_permission("admin.manage_users")
def create_api_key():
    data = safe_get_json()
    if isinstance(data, tuple):
        return data
    user_id = data.get("user_id", g.current_user.user_id)
    repository = get_auth_repository()
    target_user = repository.get_user(user_id)
    if not target_user:
        return jsonify({"success": False, "error": "NOT_FOUND", "message": "User not found"}), 404
    requested_scopes = data.get("scopes")
    scopes = set(requested_scopes) if requested_scopes is not None else set(ROLE_PERMISSIONS.get(target_user.role, set()))

    raw_key, key_id, key_hash = generate_api_key()
    api_key = APIKey(
        key_id=key_id,
        key_hash=key_hash,
        user_id=user_id,
        tenant_id=g.current_user.tenant_id,
        scopes=scopes,
    )
    register_api_key(api_key)
    audit_event(
        event_type="auth.api_key_created",
        actor_user_id=g.current_user.user_id,
        actor_tenant_id=g.current_user.tenant_id,
        target_type="api_key",
        target_id=key_id,
        ip=request.remote_addr,
        user_agent=request.headers.get("User-Agent"),
        success=True,
        reason="created",
        details={"scopes": sorted(scopes), "api_key": raw_key},
    )

    return jsonify({"success": True, "data": {
        "key_id": key_id,
        "api_key": raw_key,
        "message": "Save this key, it won't be shown again.",
    }}), 201


@auth_bp.route("/me", methods=["GET"])
def me():
    user = g.current_user
    if not user:
        return jsonify({"success": False, "error": "AUTH_REQUIRED"}), 401
    return jsonify({"success": True, "data": {
        "user_id": user.user_id,
        "username": user.username,
        "role": user.role,
        "tenant_id": user.tenant_id,
    }})


@auth_bp.route("/admin/llm-cost", methods=["GET"])
@require_permission("admin.manage_users")
def llm_cost_dashboard():
    from ..utils.llm_governor import governor

    tenant_id = request.args.get("tenant_id", g.current_user.tenant_id)
    stats = governor.get_stats(tenant_id)
    return jsonify({"success": True, "data": stats})


def clear_auth_routes_state():
    clear_auth_state()
