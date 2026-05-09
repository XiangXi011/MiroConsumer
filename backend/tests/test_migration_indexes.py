"""Tests for the application performance index migration."""

import importlib.util
from pathlib import Path

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import Column, DateTime, Integer, MetaData, String, Table, create_engine, inspect as sa_inspect

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


def _create_indexed_tables(connection):
    metadata = MetaData()
    table_columns = {
        "projects": [
            Column("id", String(36), primary_key=True),
            Column("created_at", DateTime()),
            Column("project_type", String(50)),
        ],
        "simulations": [
            Column("id", String(36), primary_key=True),
            Column("project_id", String(36)),
            Column("status", String(50)),
            Column("created_at", DateTime()),
        ],
        "simulation_runs": [
            Column("id", String(36), primary_key=True),
            Column("simulation_id", String(36)),
            Column("run_id", String(36)),
        ],
        "branches": [
            Column("id", String(36), primary_key=True),
            Column("simulation_id", String(36)),
            Column("status", String(50)),
            Column("created_at", DateTime()),
        ],
        "reports": [
            Column("id", String(36), primary_key=True),
            Column("simulation_id", String(36)),
            Column("status", String(50)),
            Column("created_at", DateTime()),
        ],
        "tasks": [
            Column("id", String(36), primary_key=True),
            Column("simulation_id", String(36)),
            Column("status", String(50)),
            Column("updated_at", DateTime()),
        ],
        "task_attempts": [
            Column("id", String(36), primary_key=True),
            Column("task_id", String(36)),
            Column("attempt_number", Integer()),
        ],
    }
    for table_name, columns in table_columns.items():
        Table(table_name, metadata, *columns)
    metadata.create_all(connection)


def test_performance_indexes_upgrade_and_downgrade(sqlite_connection, migration_module):
    _create_indexed_tables(sqlite_connection)

    context = MigrationContext.configure(sqlite_connection)
    with Operations.context(context):
        migration_module.upgrade()

    inspector = sa_inspect(sqlite_connection)
    expected_by_table = {}
    for index_name, table_name, _columns in migration_module.INDEXES:
        expected_by_table.setdefault(table_name, set()).add(index_name)

    for table_name, expected_indexes in expected_by_table.items():
        indexes_after_upgrade = {index["name"] for index in inspector.get_indexes(table_name)}
        assert indexes_after_upgrade == expected_indexes

    assert "auth_sessions" not in inspector.get_table_names()

    context = MigrationContext.configure(sqlite_connection)
    with Operations.context(context):
        migration_module.downgrade()

    inspector = sa_inspect(sqlite_connection)
    for table_name in expected_by_table:
        indexes_after_downgrade = {index["name"] for index in inspector.get_indexes(table_name)}
        assert indexes_after_downgrade == set()


def test_performance_migration_declares_postgres_jsonb_gin_indexes(migration_module):
    expected = {
        ("ix_projects_data_gin", "projects", "data"),
        ("ix_simulations_data_gin", "simulations", "data"),
        ("ix_reports_data_gin", "reports", "data"),
        ("ix_consumer_events_payload_gin", "consumer_events", "payload"),
        ("ix_research_assets_payload_gin", "research_assets", "payload"),
        ("ix_tasks_payload_gin", "tasks", "payload"),
    }

    assert set(migration_module.POSTGRES_GIN_INDEXES) >= expected
