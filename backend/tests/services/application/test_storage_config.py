"""Phase 7E storage backend configuration tests."""

from app.config import Config


def test_invalid_storage_backend_fails_validation(monkeypatch):
    monkeypatch.setattr(Config, "_storage_backend_cache", "bad")

    errors = Config.validate()

    assert any("STORAGE_BACKEND" in error for error in errors)


def test_s3_storage_requires_s3_variables(monkeypatch):
    monkeypatch.setattr(Config, "_storage_backend_cache", "s3")
    monkeypatch.setattr(Config, "_s3_endpoint_cache", "")
    monkeypatch.setattr(Config, "_s3_bucket_cache", "")
    monkeypatch.setattr(Config, "_s3_access_key_cache", "")
    monkeypatch.setattr(Config, "_s3_secret_key_cache", "")

    errors = Config.validate()

    assert any("S3_ENDPOINT" in error for error in errors)
    assert any("S3_BUCKET" in error for error in errors)


def test_local_storage_does_not_require_s3_variables(monkeypatch):
    monkeypatch.setattr(Config, "_storage_backend_cache", "local")
    monkeypatch.setattr(Config, "_s3_endpoint_cache", "")
    monkeypatch.setattr(Config, "_s3_bucket_cache", "")
    monkeypatch.setattr(Config, "_s3_access_key_cache", "")
    monkeypatch.setattr(Config, "_s3_secret_key_cache", "")

    errors = Config.validate()

    assert not any("S3_ENDPOINT" in error for error in errors)
