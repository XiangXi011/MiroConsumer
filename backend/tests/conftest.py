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


@pytest.fixture
def mock_llm_client():
    """模拟 LLM 客户端（返回固定文本）"""

    class _MockLLMClient:
        def chat(self, prompt, **kwargs):
            return "这是模拟的 LLM 回复文本。"

    return _MockLLMClient()


@pytest.fixture
def sample_simulation_data():
    """示例仿真请求数据"""
    return {
        "persona_count": 10,
        "topic": "新品发布",
        "rounds": 3,
        "strategy": "balanced",
    }


@pytest.fixture
def sample_persona():
    """示例消费者画像"""
    return {
        "name": "张三",
        "age": 28,
        "gender": "male",
        "income_level": "middle",
        "personality": ["open", "conscientious"],
        "purchase_history": ["手机", "笔记本电脑"],
        "interests": ["科技", "旅行"],
    }
