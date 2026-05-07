import pytest
from flask import Flask


def create_test_app():
    app = Flask(__name__)
    app.config['TESTING'] = True

    @app.after_request
    def add_security_headers(response):
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
        return response

    @app.route('/health')
    def health():
        return {'status': 'ok'}

    return app


@pytest.fixture
def app():
    app = create_test_app()
    yield app


@pytest.fixture
def client(app):
    return app.test_client()
