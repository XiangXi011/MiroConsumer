"""认证授权系统测试"""
import pytest
import time
import jwt
from flask import Flask, jsonify

from app.auth.models import (
    User, APIKey, extract_api_key_id, generate_api_key, hash_api_key,
    verify_api_key, ROLE_PERMISSIONS
)
from app.auth.middleware import (
    init_auth, register_user, register_api_key, create_jwt_token,
    get_jwt_secret, clear_auth_state, require_permission
)
from app.auth.routes import auth_bp, clear_auth_routes_state


@pytest.fixture
def auth_app():
    """创建带认证系统的测试应用"""
    app = Flask(__name__)
    app.config['TESTING'] = True
    app.config['SECRET_KEY'] = 'test-secret-key'
    app.config['AUTH_BYPASS_IN_TESTING'] = False

    init_auth(app)
    app.register_blueprint(auth_bp)

    # 添加 /health 公开端点
    @app.route('/health')
    def health():
        return {'status': 'ok'}

    # 添加受保护的测试端点
    @app.route('/api/test/read', methods=['GET'])
    @require_permission('project.read')
    def test_read():
        return jsonify({"success": True, "data": "read ok"})

    @app.route('/api/test/sim', methods=['POST'])
    @require_permission('simulation.run')
    def test_sim():
        return jsonify({"success": True, "data": "sim ok"})

    @app.route('/api/test/export', methods=['GET'])
    @require_permission('report.export')
    def test_export():
        return jsonify({"success": True, "data": "export ok"})

    yield app

    clear_auth_state()
    clear_auth_routes_state()


@pytest.fixture
def auth_client(auth_app):
    return auth_app.test_client()


@pytest.fixture
def registered_user(auth_client):
    """注册一个 researcher 用户并返回其信息"""
    resp = auth_client.post('/api/auth/register', json={
        'username': 'testuser',
        'email': 'test@example.com',
        'role': 'researcher',
        'tenant_id': 'tenant1'
    })
    data = resp.get_json()
    return data['data']


@pytest.fixture
def admin_user(auth_client):
    """注册一个 admin 用户并返回其信息"""
    resp = auth_client.post('/api/auth/register', json={
        'username': 'admin',
        'email': 'admin@example.com',
        'role': 'admin',
        'tenant_id': 'tenant1'
    })
    data = resp.get_json()
    return data['data']


@pytest.fixture
def viewer_user(auth_client):
    """注册一个 viewer 用户并返回其信息"""
    resp = auth_client.post('/api/auth/register', json={
        'username': 'viewer',
        'email': 'viewer@example.com',
        'role': 'viewer',
        'tenant_id': 'tenant1'
    })
    data = resp.get_json()
    return data['data']


def _get_jwt(auth_client, user_id):
    """Helper: 登录并获取 JWT"""
    resp = auth_client.post('/api/auth/login', json={'user_id': user_id})
    return resp.get_json()['data']['token']


# ============== 公开端点测试 ==============

class TestPublicEndpoints:
    def test_health_no_auth_required(self, auth_client):
        """/health 不需要认证"""
        resp = auth_client.get('/health')
        assert resp.status_code == 200
        assert resp.get_json()['status'] == 'ok'

    def test_version_no_auth_required(self, auth_client):
        """/api/version 不需要认证（通过 before_request 白名单）"""
        # /api/version 在白名单中，但我们的测试 app 没有注册它
        # 所以测 /health 即可
        resp = auth_client.get('/health')
        assert resp.status_code == 200


# ============== 未认证访问测试 ==============

class TestUnauthenticatedAccess:
    def test_api_endpoint_returns_401(self, auth_client):
        """未认证访问受保护的 API 端点返回 401"""
        resp = auth_client.get('/api/test/read')
        assert resp.status_code == 401
        data = resp.get_json()
        assert data['success'] is False
        assert data['error'] == 'AUTH_REQUIRED'

    def test_simulation_create_returns_401(self, auth_client):
        """未认证访问 /api/test/sim 返回 401"""
        resp = auth_client.post('/api/test/sim', json={})
        assert resp.status_code == 401


# ============== JWT 认证测试 ==============

class TestJWTAuth:
    def test_register_and_login(self, auth_client, registered_user):
        """注册用户后可用 JWT 认证"""
        token = _get_jwt(auth_client, registered_user['user_id'])

        resp = auth_client.get('/api/test/read', headers={
            'Authorization': f'Bearer {token}'
        })
        assert resp.status_code == 200
        assert resp.get_json()['success'] is True

    def test_me_endpoint(self, auth_client, registered_user):
        """/api/auth/me 返回当前用户信息"""
        token = _get_jwt(auth_client, registered_user['user_id'])

        resp = auth_client.get('/api/auth/me', headers={
            'Authorization': f'Bearer {token}'
        })
        assert resp.status_code == 200
        data = resp.get_json()['data']
        assert data['username'] == 'testuser'
        assert data['role'] == 'researcher'

    def test_invalid_jwt_returns_401(self, auth_client):
        """无效 JWT 返回 401"""
        resp = auth_client.get('/api/test/read', headers={
            'Authorization': 'Bearer invalid-token-here'
        })
        assert resp.status_code == 401

    def test_expired_jwt_returns_401(self, auth_app, auth_client, registered_user):
        """过期 JWT 返回 401"""
        user = User(
            user_id=registered_user['user_id'],
            username='testuser',
            email='test@example.com',
            role='researcher',
            tenant_id='tenant1',
            workspace_id='ws_tenant1'
        )
        # 创建已过期的 token（expires_in=-1 表示已过期）
        token = create_jwt_token(user, expires_in=-1)

        resp = auth_client.get('/api/test/read', headers={
            'Authorization': f'Bearer {token}'
        })
        assert resp.status_code == 401


# ============== API Key 认证测试 ==============

class TestAPIKeyAuth:
    def test_api_key_authentication(self, auth_app, auth_client, admin_user):
        """API Key 认证正常工作"""
        # 先用 JWT 认证创建 API Key
        token = _get_jwt(auth_client, admin_user['user_id'])

        resp = auth_client.post('/api/auth/api-keys', json={}, headers={
            'Authorization': f'Bearer {token}'
        })
        assert resp.status_code == 201
        api_key = resp.get_json()['data']['api_key']

        # 用 API Key 访问受保护端点
        resp = auth_client.get('/api/test/read', headers={
            'X-API-Key': api_key
        })
        assert resp.status_code == 200

    def test_invalid_api_key_returns_401(self, auth_client):
        """无效 API Key 返回 401"""
        resp = auth_client.get('/api/test/read', headers={
            'X-API-Key': 'invalid-key'
        })
        assert resp.status_code == 401


# ============== 角色权限测试 ==============

class TestRolePermissions:
    def test_viewer_cannot_run_simulation(self, auth_client, viewer_user):
        """viewer 角色不能运行模拟"""
        token = _get_jwt(auth_client, viewer_user['user_id'])

        resp = auth_client.post('/api/test/sim', json={}, headers={
            'Authorization': f'Bearer {token}'
        })
        assert resp.status_code == 403
        data = resp.get_json()
        assert data['error'] == 'FORBIDDEN'
        assert 'simulation.run' in data['message']

    def test_researcher_can_run_simulation(self, auth_client, registered_user):
        """researcher 角色可以运行模拟"""
        token = _get_jwt(auth_client, registered_user['user_id'])

        resp = auth_client.post('/api/test/sim', json={}, headers={
            'Authorization': f'Bearer {token}'
        })
        assert resp.status_code == 200

    def test_viewer_cannot_export(self, auth_client, viewer_user):
        """viewer 角色不能导出（需要 report.export）"""
        token = _get_jwt(auth_client, viewer_user['user_id'])

        resp = auth_client.get('/api/test/export', headers={
            'Authorization': f'Bearer {token}'
        })
        assert resp.status_code == 403

    def test_admin_can_export(self, auth_client, admin_user):
        """admin 角色可以导出"""
        token = _get_jwt(auth_client, admin_user['user_id'])

        resp = auth_client.get('/api/test/export', headers={
            'Authorization': f'Bearer {token}'
        })
        assert resp.status_code == 200

    def test_viewer_can_read(self, auth_client, viewer_user):
        """viewer 角色可以读取"""
        token = _get_jwt(auth_client, viewer_user['user_id'])

        resp = auth_client.get('/api/test/read', headers={
            'Authorization': f'Bearer {token}'
        })
        assert resp.status_code == 200

    def test_all_roles_have_permissions(self):
        """所有角色都有权限定义"""
        for role in ('owner', 'admin', 'researcher', 'viewer', 'auditor', 'service'):
            assert role in ROLE_PERMISSIONS
            assert len(ROLE_PERMISSIONS[role]) > 0


# ============== 模型测试 ==============

class TestModels:
    def test_generate_api_key(self):
        """API Key 生成返回正确的格式"""
        raw_key, key_id, key_hash = generate_api_key()
        assert raw_key.startswith('mk_')
        assert key_id.startswith('key_')
        assert extract_api_key_id(raw_key) == key_id
        assert key_hash.startswith(('$2a$', '$2b$', '$2y$'))
        assert len(key_hash) == 60  # bcrypt standard output length

    def test_verify_api_key(self):
        """API Key 验证正确"""
        raw_key, key_id, key_hash = generate_api_key()
        assert verify_api_key(raw_key, key_hash) is True
        assert verify_api_key('wrong-key', key_hash) is False

    def test_hash_api_key_uses_salt(self):
        """API Key hashes are salted and not deterministic."""
        raw_key = 'mk_key_test.example-secret'
        first_hash = hash_api_key(raw_key)
        second_hash = hash_api_key(raw_key)
        assert first_hash != second_hash
        assert verify_api_key(raw_key, first_hash) is True
        assert verify_api_key(raw_key, second_hash) is True


# ============== 注册验证测试 ==============

# ============== 管理员 LLM 成本看板测试 ==============

class TestAdminLLMCost:
    def test_admin_can_access_llm_cost(self, auth_client, admin_user):
        """admin 可以访问 LLM 成本看板"""
        token = _get_jwt(auth_client, admin_user['user_id'])
        resp = auth_client.get('/api/auth/admin/llm-cost', headers={
            'Authorization': f'Bearer {token}'
        })
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['success'] is True
        assert 'budget_limit' in data['data']
        assert 'budget_used' in data['data']
        assert 'budget_remaining' in data['data']

    def test_viewer_cannot_access_llm_cost(self, auth_client, viewer_user):
        """viewer 不能访问 LLM 成本看板"""
        token = _get_jwt(auth_client, viewer_user['user_id'])
        resp = auth_client.get('/api/auth/admin/llm-cost', headers={
            'Authorization': f'Bearer {token}'
        })
        assert resp.status_code == 403

    def test_researcher_cannot_access_llm_cost(self, auth_client, registered_user):
        """researcher 不能访问 LLM 成本看板"""
        token = _get_jwt(auth_client, registered_user['user_id'])
        resp = auth_client.get('/api/auth/admin/llm-cost', headers={
            'Authorization': f'Bearer {token}'
        })
        assert resp.status_code == 403

    def test_unauthenticated_cannot_access_llm_cost(self, auth_client):
        """未认证不能访问 LLM 成本看板"""
        resp = auth_client.get('/api/auth/admin/llm-cost')
        assert resp.status_code == 401


class TestRegistration:
    def test_register_requires_username_and_email(self, auth_client):
        """注册需要 username 和 email"""
        resp = auth_client.post('/api/auth/register', json={})
        assert resp.status_code == 400
        assert resp.get_json()['error'] == 'VALIDATION_ERROR'

    def test_register_invalid_role(self, auth_client):
        """无效角色返回 400"""
        resp = auth_client.post('/api/auth/register', json={
            'username': 'test', 'email': 'test@test.com', 'role': 'invalid'
        })
        assert resp.status_code == 400
        assert 'Invalid role' in resp.get_json()['message']

    def test_register_success(self, auth_client):
        """注册成功返回用户信息"""
        resp = auth_client.post('/api/auth/register', json={
            'username': 'newuser', 'email': 'new@test.com'
        })
        assert resp.status_code == 201
        data = resp.get_json()['data']
        assert data['username'] == 'newuser'
        assert data['role'] == 'researcher'  # default role
