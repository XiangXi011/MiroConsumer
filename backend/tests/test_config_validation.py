import pytest
import os


def test_weak_secret_key_rejected():
    """生产模式下弱 SECRET_KEY 应导致启动失败"""
    os.environ.pop('FLASK_DEBUG', None)
    from app.config import Config
    class TestConfig(Config):
        SECRET_KEY = 'dev-only-change-me'
        DEBUG = False
    errors = TestConfig.validate()
    assert any('SECRET_KEY' in e and 'weak' in e.lower() or 'default' in e.lower() for e in errors)


def test_short_secret_key_rejected():
    """长度 < 32 的 SECRET_KEY 应被拒绝"""
    from app.config import Config
    class TestConfig(Config):
        SECRET_KEY = 'short'
        DEBUG = False
    errors = TestConfig.validate()
    assert any('32' in e for e in errors)


def test_valid_secret_key_passes():
    """有效的 SECRET_KEY 应通过校验"""
    from app.config import Config
    class TestConfig(Config):
        SECRET_KEY = 'a' * 32
        DEBUG = False
    errors = TestConfig.validate()
    assert not any('SECRET_KEY' in e for e in errors)
