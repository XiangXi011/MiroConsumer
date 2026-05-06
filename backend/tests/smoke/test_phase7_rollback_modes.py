"""Phase 7 rollback mode gates."""

from app.config import Config


def test_db_url_empty_uses_filesystem_repositories(monkeypatch):
    from app.repositories.factory import create_repository_bundle

    monkeypatch.setattr(Config, "_db_url_cache", "")

    assert create_repository_bundle(Config).backend == "filesystem"


def test_thread_queue_uses_thread_executor(monkeypatch):
    from app.services.application.task_executor import ThreadTaskExecutor, create_task_executor

    monkeypatch.setattr(Config, "_queue_backend_cache", "thread")

    assert isinstance(create_task_executor(Config), ThreadTaskExecutor)


def test_local_storage_uses_local_backend(monkeypatch):
    from app.services.storage import get_storage_backend

    monkeypatch.setattr(Config, "_storage_backend_cache", "local")

    assert get_storage_backend(Config).backend == "local"


def test_redis_not_required_when_queue_backend_is_not_rq(monkeypatch):
    monkeypatch.setattr(Config, "_queue_backend_cache", "thread")
    monkeypatch.setattr(Config, "_redis_url_cache", "")

    errors = Config.validate()

    assert not any("REDIS_URL is required" in error for error in errors)


def test_postgres_not_required_when_db_url_empty(monkeypatch):
    from app.repositories.session import create_engine_from_config

    monkeypatch.setattr(Config, "_db_url_cache", "")

    assert create_engine_from_config(Config) is None


def test_s3_not_required_when_storage_backend_is_local(monkeypatch):
    monkeypatch.setattr(Config, "_storage_backend_cache", "local")
    monkeypatch.setattr(Config, "_s3_endpoint_cache", "")
    monkeypatch.setattr(Config, "_s3_bucket_cache", "")
    monkeypatch.setattr(Config, "_s3_access_key_cache", "")
    monkeypatch.setattr(Config, "_s3_secret_key_cache", "")

    errors = Config.validate()

    assert not any("STORAGE_BACKEND=s3" in error for error in errors)
