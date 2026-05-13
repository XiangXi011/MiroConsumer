"""Authentication middleware and permission enforcement."""

from __future__ import annotations

import secrets
import time
from functools import wraps

import jwt
from flask import current_app, g, has_app_context, jsonify, request

from ..config import WEAK_SECRET_KEYS
from ..core.errors import MCErrCode, build_error_payload
from ..security.audit_log import audit_event
from .models import ROLE_PERMISSIONS, extract_api_key_id, verify_api_key
from .repository import AuthRepository, MemoryAuthRepository

_auth_repository: AuthRepository = MemoryAuthRepository()
_jwt_secret: str | None = None


def _resolve_jwt_secret(app) -> str:
    secret = app.config.get("JWT_SECRET_KEY") or app.config.get("SECRET_KEY") or ""
    if not secret:
        raise RuntimeError("JWT secret is required")
    if secret in WEAK_SECRET_KEYS:
        raise RuntimeError("JWT secret must not use a weak/default value")
    if len(secret) < 32:
        raise RuntimeError(f"JWT secret must be >= 32 bytes, got {len(secret)}")
    return secret


def init_auth(app, auth_repository=None):
    """Initialize authentication state and before-request auth."""
    global _auth_repository, _jwt_secret
    _jwt_secret = _resolve_jwt_secret(app)
    repository = auth_repository or MemoryAuthRepository()
    _auth_repository = repository
    app.extensions["auth_repository"] = repository

    @app.before_request
    def authenticate():
        public_paths = (
            "/health",
            "/ready",
            "/api/version",
            "/api/openapi.json",
            "/api/docs",
            "/api/auth/register",
            "/api/auth/login",
            "/api/v1/auth/register",
            "/api/v1/auth/login",
        )
        if request.path in public_paths:
            g.current_user = None
            g.current_tenant = None
            g.current_api_key = None
            return None

        if not request.path.startswith("/api/"):
            g.current_user = None
            g.current_tenant = None
            g.current_api_key = None
            return None

        if _auth_bypass_enabled():
            g.current_user = None
            g.current_tenant = None
            g.current_api_key = None
            return None

        repository = get_auth_repository()
        g.current_api_key = None
        user = _authenticate_api_key(repository) or _authenticate_jwt(repository)

        if not user or not user.is_active:
            return jsonify(build_error_payload(
                MCErrCode.AUTH_REQUIRED,
                message="Authentication required. Provide X-API-Key or Bearer token.",
                request_id=getattr(g, "request_id", None),
                legacy_error="AUTH_REQUIRED",
            )), 401

        g.current_user = user
        g.current_tenant = user.tenant_id
        return None


def _authenticate_api_key(repository: AuthRepository):
    api_key = request.headers.get("X-API-Key")
    if not api_key:
        return None
    key_id = extract_api_key_id(api_key)
    api_key_record = repository.get_api_key_by_id(key_id) if key_id else None
    if not api_key_record:
        return None
    if not api_key_record.is_active:
        return None
    if api_key_record.expires_at is not None and api_key_record.expires_at <= time.time():
        return None
    if not verify_api_key(api_key, api_key_record.key_hash):
        return None
    user = repository.get_user(api_key_record.user_id)
    if user:
        g.current_api_key = api_key_record
    return user


def _authenticate_jwt(repository: AuthRepository):
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return None
    token = auth_header[7:]
    try:
        payload = jwt.decode(
            token,
            _jwt_secret,
            algorithms=["HS256"],
            options={"require": ["exp", "iat", "sub", "jti"]},
        )
        user_id = payload.get("user_id") or payload.get("sub")
        if not user_id or payload.get("sub") != user_id:
            return None
        return repository.get_user(user_id)
    except jwt.InvalidTokenError as exc:
        audit_event(
            event_type="auth.token_rejected",
            target_type="auth",
            target_id="jwt",
            ip=request.remote_addr,
            user_agent=request.headers.get("User-Agent"),
            success=False,
            reason=exc.__class__.__name__,
            details={"token": token},
        )
        return None


def _auth_bypass_enabled() -> bool:
    if not current_app.config.get("TESTING"):
        return False
    return current_app.config.get("AUTH_BYPASS_IN_TESTING", True)


def _permission_bypass_enabled() -> bool:
    return _auth_bypass_enabled()


def require_permission(permission):
    """Decorator enforcing role permissions."""

    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if _permission_bypass_enabled():
                return f(*args, **kwargs)

            user = getattr(g, "current_user", None)
            if not user:
                return jsonify(build_error_payload(
                    MCErrCode.AUTH_REQUIRED,
                    request_id=getattr(g, "request_id", None),
                    legacy_error="AUTH_REQUIRED",
                )), 401

            user_permissions = ROLE_PERMISSIONS.get(user.role, set())
            if permission not in user_permissions:
                audit_event(
                    event_type="auth.permission_denied",
                    actor_user_id=user.user_id,
                    actor_tenant_id=user.tenant_id,
                    target_type="endpoint",
                    target_id=f"{request.method} {request.path}",
                    ip=request.remote_addr,
                    user_agent=request.headers.get("User-Agent"),
                    success=False,
                    reason="missing_permission",
                    details={"permission": permission, "role": user.role},
                )
                return jsonify(build_error_payload(
                    MCErrCode.PERMISSION_DENIED,
                    message=f"Permission '{permission}' required. Your role '{user.role}' does not have this permission.",
                    request_id=getattr(g, "request_id", None),
                    legacy_error="FORBIDDEN",
                )), 403

            api_key_record = getattr(g, "current_api_key", None)
            if api_key_record is not None and permission not in set(api_key_record.scopes or set()):
                audit_event(
                    event_type="auth.permission_denied",
                    actor_user_id=user.user_id,
                    actor_tenant_id=user.tenant_id,
                    target_type="endpoint",
                    target_id=f"{request.method} {request.path}",
                    ip=request.remote_addr,
                    user_agent=request.headers.get("User-Agent"),
                    success=False,
                    reason="missing_api_key_scope",
                    details={
                        "permission": permission,
                        "key_id": getattr(api_key_record, "key_id", None),
                        "scopes": sorted(api_key_record.scopes or set()),
                    },
                )
                return jsonify(build_error_payload(
                    MCErrCode.PERMISSION_DENIED,
                    message=f"API key scope '{permission}' required.",
                    request_id=getattr(g, "request_id", None),
                    legacy_error="FORBIDDEN",
                )), 403

            return f(*args, **kwargs)
        return decorated
    return decorator


def get_auth_repository():
    if has_app_context():
        repository = current_app.extensions.get("auth_repository")
        if repository is not None:
            return repository
    return _auth_repository


def register_user(user):
    get_auth_repository().save_user(user)


def register_api_key(api_key):
    get_auth_repository().save_api_key(api_key)


def create_jwt_token(user, expires_in: int = 3600) -> str:
    now = int(time.time())
    payload = {
        "sub": user.user_id,
        "user_id": user.user_id,
        "username": user.username,
        "role": user.role,
        "tenant_id": user.tenant_id,
        "workspace_id": user.workspace_id,
        "jti": secrets.token_urlsafe(16),
        "exp": now + expires_in,
        "iat": now,
    }
    return jwt.encode(payload, _jwt_secret, algorithm="HS256")


def get_jwt_secret():
    return _jwt_secret


def clear_auth_state():
    get_auth_repository().clear_all()
