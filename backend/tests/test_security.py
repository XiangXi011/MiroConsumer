import pytest


def test_health_endpoint_no_info_leak(client):
    resp = client.get('/health')
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['status'] == 'ok'
    if 'rate_limiter' in data:
        assert data['rate_limiter'] in {'enabled', 'disabled'}
    assert 'version' not in data
    assert 'model' not in data
    assert 'service' not in data


def test_security_headers_present(client):
    resp = client.get('/health')
    assert resp.headers.get('X-Content-Type-Options') == 'nosniff'
    assert resp.headers.get('X-Frame-Options') == 'DENY'
    assert resp.headers.get('X-XSS-Protection') == '1; mode=block'
    assert 'Strict-Transport-Security' in resp.headers
