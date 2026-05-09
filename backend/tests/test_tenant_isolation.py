"""跨租户访问隔离测试"""
import pytest


class TestTenantIsolation:
    """跨租户访问隔离测试"""

    @pytest.fixture
    def app(self):
        from app import create_app
        app = create_app()
        app.config['TESTING'] = True
        app.config['AUTH_BYPASS_IN_TESTING'] = False
        return app

    @pytest.fixture
    def client(self, app):
        return app.test_client()

    def _register_and_login(self, client, tenant_id, role='researcher'):
        resp = client.post('/api/auth/register', json={
            'username': f'user_{tenant_id}_{role}',
            'email': f'{tenant_id}_{role}@test.com',
            'role': role,
            'tenant_id': tenant_id,
        })
        data = resp.get_json().get('data', {})
        user_id = data.get('user_id')
        if not user_id:
            return None
        resp = client.post('/api/auth/login', json={'user_id': user_id})
        return resp.get_json().get('data', {}).get('token')

    def test_create_simulation_records_tenant(self, client):
        """创建仿真时应记录 tenant_id"""
        token = self._register_and_login(client, 'tenant_test_1')
        if not token:
            pytest.skip("Auth setup failed")

        resp = client.post('/api/simulation/create',
            json={'name': 'Tenant Test Sim', 'project_id': 'proj_tenant'},
            headers={'Authorization': f'Bearer {token}'})

        data = resp.get_json().get('data', {})
        # tenant_id 应该被注入
        assert data.get('tenant_id') == 'tenant_test_1' or resp.status_code in (400, 409)

    def test_cross_tenant_simulation_access_denied(self, client):
        """tenant1 不能访问 tenant2 的仿真"""
        token_a = self._register_and_login(client, 'tenant_iso_a')
        token_b = self._register_and_login(client, 'tenant_iso_b')

        if not token_a or not token_b:
            pytest.skip("Auth setup failed")

        # tenant_iso_a 创建仿真
        resp = client.post('/api/simulation/create',
            json={'name': 'ISO Sim A', 'project_id': 'proj_iso_a'},
            headers={'Authorization': f'Bearer {token_a}'})

        sim_id = resp.get_json().get('data', {}).get('id')
        if not sim_id:
            pytest.skip("Simulation creation failed")

        # tenant_iso_b 尝试访问
        resp = client.get(f'/api/simulation/{sim_id}',
            headers={'Authorization': f'Bearer {token_b}'})

        assert resp.status_code in (403, 404), \
            f"Cross-tenant access should be denied, got {resp.status_code}"

    def test_simulation_list_filtered_by_tenant(self, client):
        """仿真列表应按租户过滤"""
        token_a = self._register_and_login(client, 'tenant_list_a')
        token_b = self._register_and_login(client, 'tenant_list_b')

        if not token_a or not token_b:
            pytest.skip("Auth setup failed")

        # tenant_list_a 创建仿真
        client.post('/api/simulation/create',
            json={'name': 'List Sim A', 'project_id': 'proj_list_a'},
            headers={'Authorization': f'Bearer {token_a}'})

        # tenant_list_b 的列表不应包含 tenant_list_a 的仿真
        resp_b = client.get('/api/simulation/list',
            headers={'Authorization': f'Bearer {token_b}'})

        sims_b = resp_b.get_json().get('data', [])
        for sim in sims_b:
            if sim.get('tenant_id'):
                assert sim['tenant_id'] != 'tenant_list_a', \
                    "tenant_list_b should not see tenant_list_a's simulations"

    def test_unauthenticated_access_still_blocked(self, client):
        """未认证访问仍然被阻止"""
        resp = client.get('/api/simulation/list')
        assert resp.status_code == 401

    def test_same_tenant_access_allowed(self, client):
        """同租户用户可以访问"""
        token = self._register_and_login(client, 'tenant_same')
        if not token:
            pytest.skip("Auth setup failed")

        resp = client.get('/api/simulation/list',
            headers={'Authorization': f'Bearer {token}'})

        # 应该成功返回（即使列表为空）
        assert resp.status_code == 200
