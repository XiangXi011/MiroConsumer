"""Tests for repository factory DB_URL selection and Config DB_URL validation."""

import os
from unittest.mock import patch
from pathlib import Path

import pytest

from app.config import Config
from app.repositories.factory import create_repository_bundle, RepositoryBundle


class TestConfigDbUrl:
    """Config exposes DB_URL, DB_POOL_SIZE, DB_MAX_OVERFLOW, DB_STATEMENT_TIMEOUT_SECONDS."""

    def test_db_url_default_empty(self, monkeypatch):
        monkeypatch.delenv("DB_URL", raising=False)
        monkeypatch.setattr(Config, "_db_url_cache", None)
        assert Config.DB_URL == ""

    def test_db_url_reads_from_env(self, monkeypatch):
        monkeypatch.setenv("DB_URL", "sqlite:///test.db")
        monkeypatch.setattr(Config, "_db_url_cache", None)
        assert Config.DB_URL == "sqlite:///test.db"

    def test_db_pool_size_default(self):
        assert Config.DB_POOL_SIZE == 5

    def test_db_max_overflow_default(self):
        assert Config.DB_MAX_OVERFLOW == 10

    def test_db_statement_timeout_default(self):
        assert Config.DB_STATEMENT_TIMEOUT_SECONDS == 30

    def test_db_pool_size_reads_from_env(self, monkeypatch):
        monkeypatch.setenv("DB_POOL_SIZE", "20")
        monkeypatch.setattr(Config, "_db_pool_size_cache", None)
        assert Config.DB_POOL_SIZE == 20

    def test_db_max_overflow_reads_from_env(self, monkeypatch):
        monkeypatch.setenv("DB_MAX_OVERFLOW", "15")
        monkeypatch.setattr(Config, "_db_max_overflow_cache", None)
        assert Config.DB_MAX_OVERFLOW == 15

    def test_db_statement_timeout_reads_from_spec_env(self, monkeypatch):
        monkeypatch.setenv("DB_STATEMENT_TIMEOUT_SECONDS", "60")
        monkeypatch.setattr(Config, "_db_statement_timeout_cache", None)
        assert Config.DB_STATEMENT_TIMEOUT_SECONDS == 60


class TestConfigValidateDbUrl:
    """validate() accepts/rejects DB_URL schemes correctly."""

    def test_validate_empty_db_url_ok(self):
        errors = Config.validate()
        db_url_errors = [e for e in errors if "DB_URL" in e]
        assert len(db_url_errors) == 0

    def test_validate_sqlite_ok(self, monkeypatch):
        monkeypatch.setenv("DB_URL", "sqlite:///test.db")
        monkeypatch.setattr(Config, "_db_url_cache", None)
        errors = Config.validate()
        db_url_errors = [e for e in errors if "DB_URL" in e]
        assert len(db_url_errors) == 0

    def test_validate_postgresql_psycopg_ok(self, monkeypatch):
        monkeypatch.setenv("DB_URL", "postgresql+psycopg://user:pass@localhost/db")
        monkeypatch.setattr(Config, "_db_url_cache", None)
        errors = Config.validate()
        db_url_errors = [e for e in errors if "DB_URL" in e]
        assert len(db_url_errors) == 0

    def test_validate_unsupported_scheme_fails(self, monkeypatch):
        monkeypatch.setenv("DB_URL", "mysql://user:pass@localhost/db")
        monkeypatch.setattr(Config, "_db_url_cache", None)
        errors = Config.validate()
        db_url_errors = [e for e in errors if "DB_URL" in e]
        assert len(db_url_errors) == 1
        assert "unsupported" in db_url_errors[0].lower() or "invalid" in db_url_errors[0].lower()

    def test_validate_mssql_scheme_fails(self, monkeypatch):
        monkeypatch.setenv("DB_URL", "mssql+pyodbc://user:pass@localhost/db")
        monkeypatch.setattr(Config, "_db_url_cache", None)
        errors = Config.validate()
        db_url_errors = [e for e in errors if "DB_URL" in e]
        assert len(db_url_errors) == 1


class TestRepositoryFactory:
    """factory.py returns correct repository implementations based on DB_URL."""

    def test_empty_db_url_returns_filesystem_repos(self, monkeypatch):
        monkeypatch.setenv("DB_URL", "")
        monkeypatch.setattr(Config, "_db_url_cache", None)
        bundle = create_repository_bundle()
        assert isinstance(bundle, RepositoryBundle)
        assert bundle.backend == "filesystem"
        assert bundle.project_repo is not None
        assert bundle.simulation_repo is not None
        assert bundle.branch_repo is not None
        assert bundle.report_repo is not None
        assert bundle.benchmark_repo is not None
        assert bundle.consumer_state_repo is not None
        assert bundle.consumer_research_provider is not None

    def test_sqlite_url_returns_sqlalchemy_repos(self, monkeypatch):
        monkeypatch.setenv("DB_URL", "sqlite:///:memory:")
        monkeypatch.setattr(Config, "_db_url_cache", None)
        bundle = create_repository_bundle()
        assert isinstance(bundle, RepositoryBundle)
        assert bundle.backend == "sqlalchemy"
        assert bundle.project_repo is not None
        assert bundle.simulation_repo is not None
        assert bundle.branch_repo is not None
        assert bundle.report_repo is not None
        assert bundle.benchmark_repo is not None
        assert bundle.consumer_state_repo is not None
        assert bundle.consumer_research_provider is not None

    def test_postgresql_url_returns_sqlalchemy_repos(self, monkeypatch):
        monkeypatch.setenv("DB_URL", "postgresql+psycopg://user:pass@localhost/db")
        monkeypatch.setattr(Config, "_db_url_cache", None)
        bundle = create_repository_bundle()
        assert isinstance(bundle, RepositoryBundle)
        assert bundle.backend == "sqlalchemy"

    def test_unsupported_scheme_raises_value_error(self, monkeypatch):
        monkeypatch.setenv("DB_URL", "mysql://user:pass@localhost/db")
        monkeypatch.setattr(Config, "_db_url_cache", None)
        with pytest.raises(ValueError):
            create_repository_bundle()

    def test_sqlalchemy_repo_classes_instantiable(self, monkeypatch):
        """SQLAlchemy repository classes must be instantiable even if methods raise NotImplementedError."""
        monkeypatch.setenv("DB_URL", "sqlite:///:memory:")
        monkeypatch.setattr(Config, "_db_url_cache", None)
        bundle = create_repository_bundle()

        # All repos should be instantiable objects
        assert bundle.project_repo is not None
        assert bundle.simulation_repo is not None
        assert bundle.branch_repo is not None
        assert bundle.report_repo is not None
        assert bundle.benchmark_repo is not None
        assert bundle.consumer_state_repo is not None
        assert bundle.consumer_research_provider is not None


def test_application_services_do_not_directly_instantiate_filesystem_repositories():
    """Phase 7A requires application services to obtain repositories from the factory."""
    app_dir = Path(__file__).resolve().parents[2] / "app" / "services" / "application"
    offenders = []
    for path in app_dir.glob("*.py"):
        source = path.read_text(encoding="utf-8")
        if "repositories.filesystem" in source or "Filesystem" in source:
            offenders.append(path.name)
    assert offenders == []


def test_application_services_do_not_directly_instantiate_thread_task_executor():
    """Phase 7B requires application services to use create_task_executor() factory."""
    app_dir = Path(__file__).resolve().parents[2] / "app" / "services" / "application"
    offenders = []
    for path in app_dir.glob("*_app_service.py"):
        source = path.read_text(encoding="utf-8")
        if "ThreadTaskExecutor()" in source:
            offenders.append(path.name)
    assert offenders == []
