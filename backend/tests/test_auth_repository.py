"""Tests for authentication repository backends."""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.auth.models import APIKey, User
from app.auth.repository import (
    MemoryAuthRepository,
    SqlAlchemyAuthRepository,
    auth_metadata,
    create_auth_repository_from_config,
)


@pytest.fixture
def user():
    return User(
        user_id="user_test",
        username="testuser",
        email="test@example.com",
        role="researcher",
        tenant_id="tenant1",
        workspace_id="ws_tenant1",
        created_at=1000.0,
    )


@pytest.fixture
def api_key(user):
    return APIKey(
        key_id="key_test",
        key_hash="$2b$12$abcdefghijklmnopqrstuuZK0DQYfBNx5gSWsFoN8ub0WiwPY7pXe",
        user_id=user.user_id,
        tenant_id=user.tenant_id,
        scopes={"project.read", "report.read"},
        created_at=1001.0,
        expires_at=2000.0,
    )


@pytest.fixture
def sqlite_session_factory():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    auth_metadata.create_all(engine)
    try:
        yield sessionmaker(bind=engine, class_=Session)
    finally:
        auth_metadata.drop_all(engine)
        engine.dispose()


def assert_user_matches(actual, expected):
    assert actual == expected
    assert actual is not expected


def assert_api_key_matches(actual, expected):
    assert actual == expected
    assert actual is not expected
    assert actual.scopes == expected.scopes
    assert actual.scopes is not expected.scopes


class TestMemoryAuthRepository:
    def test_user_and_api_key_crud(self, user, api_key):
        repo = MemoryAuthRepository()

        repo.save_user(user)
        assert_user_matches(repo.get_user(user.user_id), user)
        assert repo.get_user("missing") is None

        repo.save_api_key(api_key)
        assert_api_key_matches(repo.get_api_key_by_id(api_key.key_id), api_key)
        assert repo.get_api_key_by_id("missing") is None
        assert repo.get_api_keys_by_user(user.user_id) == [api_key]
        assert repo.get_api_keys_by_user("missing") == []

        assert repo.delete_api_key(api_key.key_id) is True
        assert repo.get_api_key_by_id(api_key.key_id) is None
        assert repo.delete_api_key(api_key.key_id) is False

        repo.save_api_key(api_key)
        repo.clear_all()
        assert repo.get_user(user.user_id) is None
        assert repo.get_api_key_by_id(api_key.key_id) is None

    def test_saved_objects_are_isolated_from_later_mutation(self, user, api_key):
        repo = MemoryAuthRepository()
        repo.save_user(user)
        repo.save_api_key(api_key)

        user.username = "mutated"
        api_key.scopes.add("admin.manage_users")

        assert repo.get_user(user.user_id).username == "testuser"
        assert repo.get_api_key_by_id(api_key.key_id).scopes == {
            "project.read",
            "report.read",
        }


class TestSqlAlchemyAuthRepository:
    def test_user_and_api_key_crud(self, sqlite_session_factory, user, api_key):
        repo = SqlAlchemyAuthRepository(sqlite_session_factory)

        repo.save_user(user)
        assert repo.get_user(user.user_id) == user
        assert repo.get_user("missing") is None

        updated_user = User(
            **{
                **user.__dict__,
                "username": "updated",
                "is_active": False,
            }
        )
        repo.save_user(updated_user)
        assert repo.get_user(user.user_id) == updated_user

        repo.save_api_key(api_key)
        assert repo.get_api_key_by_id(api_key.key_id) == api_key
        assert repo.get_api_key_by_id("missing") is None
        assert repo.get_api_keys_by_user(user.user_id) == [api_key]
        assert repo.get_api_keys_by_user("missing") == []

        updated_api_key = APIKey(
            **{
                **api_key.__dict__,
                "scopes": {"project.read"},
                "is_active": False,
                "expires_at": None,
            }
        )
        repo.save_api_key(updated_api_key)
        assert repo.get_api_key_by_id(api_key.key_id) == updated_api_key

        assert repo.delete_api_key(api_key.key_id) is True
        assert repo.get_api_key_by_id(api_key.key_id) is None
        assert repo.delete_api_key(api_key.key_id) is False

        repo.clear_all()
        assert repo.get_user(user.user_id) is None

    def test_repository_instance_restart_keeps_auth_state(
        self, sqlite_session_factory, user, api_key
    ):
        first_repo = SqlAlchemyAuthRepository(sqlite_session_factory)
        first_repo.save_user(user)
        first_repo.save_api_key(api_key)

        restarted_repo = SqlAlchemyAuthRepository(sqlite_session_factory)

        assert restarted_repo.get_user(user.user_id) == user
        assert restarted_repo.get_api_key_by_id(api_key.key_id) == api_key
        assert restarted_repo.get_api_keys_by_user(user.user_id) == [api_key]


class TestConfiguredAuthRepository:
    def test_empty_db_url_uses_memory_repository(self):
        class TestConfig:
            DB_URL = ""

        repo, engine = create_auth_repository_from_config(TestConfig)

        assert isinstance(repo, MemoryAuthRepository)
        assert engine is None

    def test_db_url_uses_persistent_sqlalchemy_repository(self, tmp_path, user, api_key):
        db_path = tmp_path / "auth.db"

        class TestConfig:
            DB_URL = f"sqlite:///{db_path}"

        repo, engine = create_auth_repository_from_config(TestConfig)
        try:
            assert isinstance(repo, SqlAlchemyAuthRepository)
            repo.save_user(user)
            repo.save_api_key(api_key)
        finally:
            engine.dispose()

        restarted_repo, restarted_engine = create_auth_repository_from_config(TestConfig)
        try:
            assert restarted_repo.get_user(user.user_id) == user
            assert restarted_repo.get_api_key_by_id(api_key.key_id) == api_key
        finally:
            restarted_engine.dispose()


class TestCachedAuthRepository:
    def test_get_user_uses_auth_user_cache_with_600_second_ttl(self, user):
        from app.auth.repository import CachedAuthRepository

        base = MemoryAuthRepository()
        cache = type("FakeCache", (), {})()
        cache.get = lambda key: None
        cache.set_calls = []
        cache.set = lambda key, value, ttl=300: cache.set_calls.append((key, value, ttl)) or True
        cache.delete = lambda key: True

        repo = CachedAuthRepository(base, cache)
        repo.save_user(user)
        loaded = repo.get_user(user.user_id)

        assert loaded == user
        assert ("auth:user:user_test", user.__dict__, 600) in cache.set_calls

    def test_get_user_returns_cached_user_without_delegating(self, user):
        from app.auth.repository import CachedAuthRepository

        base = MemoryAuthRepository()
        cache = type("FakeCache", (), {})()
        cache.get = lambda key: user.__dict__ if key == "auth:user:user_test" else None
        cache.set = lambda *args, **kwargs: True
        cache.delete = lambda key: True

        repo = CachedAuthRepository(base, cache)

        assert repo.get_user(user.user_id) == user
        assert base.get_user(user.user_id) is None
