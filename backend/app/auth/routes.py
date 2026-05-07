"""认证 API 路由"""
from flask import Blueprint, request, jsonify, g
from ..utils.request_validator import safe_get_json
from .models import User, APIKey, generate_api_key, ROLE_PERMISSIONS
from .middleware import register_user, register_api_key, create_jwt_token, require_permission
import secrets

auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')

# 内存存储
_users_db = {}
_api_keys_db = {}


@auth_bp.route('/register', methods=['POST'])
def register():
    data = safe_get_json()
    if isinstance(data, tuple): return data
    username = data.get('username')
    email = data.get('email')
    role = data.get('role', 'researcher')
    tenant_id = data.get('tenant_id', 'default')

    if not username or not email:
        return jsonify({"success": False, "error": "VALIDATION_ERROR", "message": "username and email required"}), 400

    if role not in ROLE_PERMISSIONS:
        return jsonify({"success": False, "error": "VALIDATION_ERROR",
                        "message": f"Invalid role. Must be one of: {list(ROLE_PERMISSIONS.keys())}"}), 400

    user_id = f"user_{secrets.token_hex(8)}"
    user = User(
        user_id=user_id, username=username, email=email,
        role=role, tenant_id=tenant_id, workspace_id=f"ws_{tenant_id}"
    )
    _users_db[user_id] = user
    register_user(user)

    return jsonify({"success": True, "data": {"user_id": user_id, "username": username, "role": role}}), 201


@auth_bp.route('/login', methods=['POST'])
def login():
    data = safe_get_json()
    if isinstance(data, tuple): return data
    user_id = data.get('user_id')
    user = _users_db.get(user_id)

    if not user or not user.is_active:
        return jsonify({"success": False, "error": "AUTH_FAILED", "message": "Invalid credentials"}), 401

    token = create_jwt_token(user)
    return jsonify({"success": True, "data": {"token": token, "user_id": user.user_id, "role": user.role}})


@auth_bp.route('/api-keys', methods=['POST'])
@require_permission('admin.manage_users')
def create_api_key():
    data = safe_get_json()
    if isinstance(data, tuple): return data
    user_id = data.get('user_id', g.current_user.user_id)
    scopes = set(data.get('scopes', []))

    raw_key, key_id, key_hash = generate_api_key()
    api_key = APIKey(key_id=key_id, key_hash=key_hash, user_id=user_id,
                     tenant_id=g.current_user.tenant_id, scopes=scopes)
    _api_keys_db[key_id] = api_key
    register_api_key(api_key)

    return jsonify({"success": True, "data": {"key_id": key_id, "api_key": raw_key,
                    "message": "Save this key, it won't be shown again."}}), 201


@auth_bp.route('/me', methods=['GET'])
def me():
    user = g.current_user
    if not user:
        return jsonify({"success": False, "error": "AUTH_REQUIRED"}), 401
    return jsonify({"success": True, "data": {
        "user_id": user.user_id, "username": user.username,
        "role": user.role, "tenant_id": user.tenant_id
    }})


@auth_bp.route('/admin/llm-cost', methods=['GET'])
@require_permission('admin.manage_users')
def llm_cost_dashboard():
    """管理员 LLM 成本看板"""
    from ..utils.llm_governor import governor

    tenant_id = request.args.get('tenant_id', g.current_user.tenant_id)
    stats = governor.get_stats(tenant_id)

    return jsonify({"success": True, "data": stats})


def clear_auth_routes_state():
    """清除路由状态（供测试使用）"""
    _users_db.clear()
    _api_keys_db.clear()
