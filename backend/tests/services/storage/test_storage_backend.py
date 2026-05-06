"""Phase 7E/7F storage backend tests."""

from app.config import Config


def test_local_storage_backend_returns_fixed_local_paths(monkeypatch):
    from app.services.storage import get_storage_backend

    monkeypatch.setattr(Config, "_storage_backend_cache", "local")

    backend = get_storage_backend(Config)

    assert backend.backend == "local"
    assert backend.local_paths["uploads"].endswith("backend\\uploads") or backend.local_paths["uploads"].endswith("backend/uploads")
    assert backend.local_paths["data"].endswith("backend\\data") or backend.local_paths["data"].endswith("backend/data")


def test_s3_storage_backend_requires_credentials(monkeypatch):
    import pytest

    from app.services.storage import get_storage_backend

    monkeypatch.setattr(Config, "_storage_backend_cache", "s3")
    monkeypatch.setattr(Config, "_s3_endpoint_cache", "")
    monkeypatch.setattr(Config, "_s3_bucket_cache", "")
    monkeypatch.setattr(Config, "_s3_access_key_cache", "")
    monkeypatch.setattr(Config, "_s3_secret_key_cache", "")

    with pytest.raises(ValueError, match="S3_ENDPOINT"):
        get_storage_backend(Config)
