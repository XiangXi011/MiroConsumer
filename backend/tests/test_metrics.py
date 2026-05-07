"""Tests for Prometheus metrics endpoint and request_id tracking."""
import uuid

import pytest
from flask import Flask, g, request

from app.utils.metrics import (
    _metrics,
    metrics_bp,
    record_request,
    record_simulation_run,
    set_active_runs,
)


@pytest.fixture
def metrics_app():
    app = Flask(__name__)
    app.config['TESTING'] = True
    app.register_blueprint(metrics_bp)

    @app.before_request
    def assign_request_id():
        g.request_id = request.headers.get('X-Request-ID', str(uuid.uuid4())[:8])

    @app.after_request
    def add_request_id_header(response):
        response.headers['X-Request-ID'] = getattr(g, 'request_id', 'unknown')
        record_request(response.status_code)
        return response

    return app


@pytest.fixture
def metrics_client(metrics_app):
    return metrics_app.test_client()


def test_metrics_endpoint_returns_200(metrics_client):
    resp = metrics_client.get('/metrics')
    assert resp.status_code == 200


def test_metrics_contains_requests_total(metrics_client):
    resp = metrics_client.get('/metrics')
    body = resp.data.decode()
    assert 'miroconsumer_requests_total' in body


def test_request_id_in_response_header(metrics_client):
    resp = metrics_client.get('/metrics')
    assert 'X-Request-ID' in resp.headers
    assert resp.headers['X-Request-ID'] != 'unknown'


def test_request_id_passthrough(metrics_client):
    resp = metrics_client.get('/metrics', headers={'X-Request-ID': 'test-abc'})
    assert resp.headers['X-Request-ID'] == 'test-abc'


def test_record_request_increments_counter():
    before = _metrics["requests_total"]
    record_request(200)
    assert _metrics["requests_total"] == before + 1


def test_record_request_tracks_status():
    key = "404"
    before = _metrics["requests_by_status"].get(key, 0)
    record_request(404)
    assert _metrics["requests_by_status"][key] == before + 1
