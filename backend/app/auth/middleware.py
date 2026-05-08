"""认证中间件"""
from functools import wraps
from flask import request, jsonify, g, current_app
from .models import ROLE_PERMISSIONS, ENDPOINT_PERMISSIONS, extract_api_key_id, verify_api_key
import jwt
import time

# 临时内存存储（生产应换成数据库）
_api_keys = {}  # key_id -> APIKey
_users = {}  # user_id -> User
_jwt_secret = None


def init_auth(app):
    """初始化认证系统"""
    global _jwt_secret
    _jwt_secret = app.config.get('SECRET_KEY', 'dev-secret')

    # 注册 before_request
    @app.before_request
    def authenticate():
        # 公开端点
        public_paths = ('/health', '/api/version', '/api/openapi.json', '/api/docs',
                        '/api/auth/register', '/api/auth/login')
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
        user = None

        # 1. API Key 认证
        api_key = request.headers.get('X-API-Key')
        if api_key:
            key_id = extract_api_key_id(api_key)
            candidates = [_api_keys[key_id]] if key_id in _api_keys else _api_keys.values()
            for ak in candidates:
                if (
                    verify_api_key(api_key, ak.key_hash)
                    and ak.is_active
                    and (ak.expires_at is None or ak.expires_at > time.time())
                ):
                    user = _users.get(ak.user_id)
                    break

        # 2. JWT 认证
        if not user:
            auth_header = request.headers.get('Authorization', '')
            if auth_header.startswith('Bearer '):
                token = auth_header[7:]
                try:
                    payload = jwt.decode(token, _jwt_secret, algorithms=['HS256'])
                    user = _users.get(payload.get('user_id'))
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


def require_permission(permission):
    """权限检查装饰器"""
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
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


def register_user(user):
    """注册用户（内存存储）"""
    _users[user.user_id] = user


def register_api_key(api_key):
    """注册 API Key"""
    _api_keys[api_key.key_id] = api_key


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
    _api_keys.clear()
    _users.clear()
