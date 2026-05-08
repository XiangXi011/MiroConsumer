"""Tests for the auth session performance index migration."""

import importlib.util
from pathlib import Path

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import Column, Float, MetaData, String, Table, create_engine, inspect as sa_inspect

BACKEND_DIR = Path(__file__).resolve().parents[1]
MIGRATION_PATH = BACKEND_DIR / "alembic" / "versions" / "20260508_0003_add_performance_indexes.py"


@pytest.fixture(scope="module")
def migration_module():
    spec = importlib.util.spec_from_file_location("migration_20260508_0003", MIGRATION_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def sqlite_connection():
    engine = create_engine("sqlite:///:memory:")
    with engine.begin() as connection:
        yield connection


def _create_auth_sessions_table(connection):
    metadata = MetaData()
    Table(
        "auth_sessions",
        metadata,
        Column("session_id", String(64), primary_key=True),
        Column("user_id", String(64), nullable=False),
        Column("expires_at", Float(), nullable=False),
    )
    metadata.create_all(connection)


def test_auth_session_indexes_upgrade_and_downgrade(sqlite_connection, migration_module):
    _create_auth_sessions_table(sqlite_connection)

    context = MigrationContext.configure(sqlite_connection)
    with Operations.context(context):
        migration_module.upgrade()

    inspector = sa_inspect(sqlite_connection)
    indexes_after_upgrade = {index["name"] for index in inspector.get_indexes("auth_sessions")}
    assert indexes_after_upgrade == {"ix_auth_sessions_user_id", "ix_auth_sessions_expires_at"}

    context = MigrationContext.configure(sqlite_connection)
    with Operations.context(context):
        migration_module.downgrade()

    inspector = sa_inspect(sqlite_connection)
    indexes_after_downgrade = {index["name"] for index in inspector.get_indexes("auth_sessions")}
    assert indexes_after_downgrade == set()
