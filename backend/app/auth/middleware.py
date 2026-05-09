"""认证中间件"""
from functools import wraps
from flask import request, jsonify, g, current_app, has_app_context
from .models import ROLE_PERMISSIONS, ENDPOINT_PERMISSIONS, extract_api_key_id, verify_api_key
from .repository import AuthRepository, MemoryAuthRepository
import jwt
import time

_auth_repository: AuthRepository = MemoryAuthRepository()
_jwt_secret = None


def init_auth(app, auth_repository=None):
    """初始化认证系统"""
    global _auth_repository, _jwt_secret
    _jwt_secret = app.config.get('SECRET_KEY', 'dev-secret')
    repository = auth_repository or MemoryAuthRepository()
    _auth_repository = repository
    app.extensions['auth_repository'] = repository

    # 注册 before_request
    @app.before_request
    def authenticate():
        # 公开端点
        public_paths = ('/health', '/api/version', '/api/openapi.json', '/api/docs',
                        '/api/auth/register', '/api/auth/login',
                        '/api/v1/auth/register', '/api/v1/auth/login')
        if request.path in public_paths:
            g.current_user = None
            g.current_tenant = None
            return

        # 非 API 端点放行
        if not request.path.startswith('/api/'):
            g.current_user = None
            g.current_tenant = None
            return

        # 认证：检查 API Key 或 JWT
        if _auth_bypass_enabled():
            g.current_user = None
            g.current_tenant = None
            return

        user = None
        repository = get_auth_repository()

        # 1. API Key 认证
        api_key = request.headers.get('X-API-Key')
        if api_key:
            key_id = extract_api_key_id(api_key)
            ak = repository.get_api_key_by_id(key_id) if key_id else None
            if (
                ak
                and verify_api_key(api_key, ak.key_hash)
                and ak.is_active
                and (ak.expires_at is None or ak.expires_at > time.time())
            ):
                user = repository.get_user(ak.user_id)

        # 2. JWT 认证
        if not user:
            auth_header = request.headers.get('Authorization', '')
            if auth_header.startswith('Bearer '):
                token = auth_header[7:]
                try:
                    payload = jwt.decode(token, _jwt_secret, algorithms=['HS256'])
                    user_id = payload.get('user_id')
                    user = repository.get_user(user_id) if user_id else None
                except jwt.InvalidTokenError:
                    pass

        # 3. 未认证
        if not user or not user.is_active:
            return jsonify({
                "success": False,
                "error": "AUTH_REQUIRED",
                "message": "Authentication required. Provide X-API-Key or Bearer token."
            }), 401

        g.current_user = user
        g.current_tenant = user.tenant_id


def _auth_bypass_enabled() -> bool:
    if not current_app.config.get("TESTING"):
        return False
    return current_app.config.get("AUTH_BYPASS_IN_TESTING", True)


def _permission_bypass_enabled() -> bool:
    return _auth_bypass_enabled()


def require_permission(permission):
    """权限检查装饰器"""
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if _permission_bypass_enabled():
                return f(*args, **kwargs)

            user = getattr(g, 'current_user', None)
            if not user:
                return jsonify({"success": False, "error": "AUTH_REQUIRED", "message": "Authentication required"}), 401

            user_permissions = ROLE_PERMISSIONS.get(user.role, set())
            if permission not in user_permissions:
                return jsonify({
                    "success": False,
                    "error": "FORBIDDEN",
                    "message": f"Permission '{permission}' required. Your role '{user.role}' does not have this permission."
                }), 403

            return f(*args, **kwargs)
        return decorated
    return decorator


def get_auth_repository():
    """获取当前应用的认证 repository。"""
    if has_app_context():
        repository = current_app.extensions.get('auth_repository')
        if repository is not None:
            return repository
    return _auth_repository


def register_user(user):
    """注册用户"""
    get_auth_repository().save_user(user)


def register_api_key(api_key):
    """注册 API Key"""
    get_auth_repository().save_api_key(api_key)


def create_jwt_token(user, expires_in: int = 3600) -> str:
    """创建 JWT Token"""
    payload = {
        "user_id": user.user_id,
        "username": user.username,
        "role": user.role,
        "tenant_id": user.tenant_id,
        "workspace_id": user.workspace_id,
        "exp": int(time.time()) + expires_in,
        "iat": int(time.time()),
    }
    return jwt.encode(payload, _jwt_secret, algorithm='HS256')


def get_jwt_secret():
    """获取 JWT secret（供测试使用）"""
    return _jwt_secret


def clear_auth_state():
    """清除认证状态（供测试使用）"""
    get_auth_repository().clear_all()
