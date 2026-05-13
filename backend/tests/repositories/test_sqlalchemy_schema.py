"""Tests for SQLAlchemy schema and Alembic migration coverage.

These tests use SQLite in-memory (no PostgreSQL server required).
"""

import importlib
import inspect
import os
import sys
from pathlib import Path

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import inspect as sa_inspect, create_engine, MetaData, Table, Column, Integer, DateTime, String, JSON
from sqlalchemy.dialects import postgresql
from sqlalchemy.dialects.postgresql import JSONB

# Build absolute path to backend directory for alembic import
BACKEND_DIR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(BACKEND_DIR))


ALL_TABLES = [
    "projects",
    "consumer_briefs",
    "simulations",
    "simulation_runs",
    "society_agents",
    "persona_packs",
    "round_snapshots",
    "graph_snapshots",
    "consumer_events",
    "branches",
    "interventions",
    "reports",
    "report_sections",
    "research_assets",
    "benchmarks",
    "benchmark_replays",
    "memory_entries",
    "tasks",
    "task_attempts",
    "dead_letters",
    "locks",
]

SIMULATION_CHILD_TABLES = [
    "simulation_runs",
    "society_agents",
    "round_snapshots",
    "consumer_events",
    "branches",
    "interventions",
    "reports",
    "report_sections",
    "memory_entries",
    "tasks",
    "task_attempts",
    "dead_letters",
    "locks",
]

SHARED_COLUMNS = ["id", "created_at", "updated_at", "version"]

INITIAL_MIGRATION_TABLES = [table for table in ALL_TABLES if table != "graph_snapshots"]


class TestSqlalchemySchema:
    """Verify SQLAlchemy metadata defines all required tables and columns."""

    @pytest.fixture(scope="class")
    def metadata_tables(self):
        from app.repositories.sqlalchemy import metadata
        return {t.name: t for t in metadata.sorted_tables}

    def test_all_required_tables_present(self, metadata_tables):
        present = set(metadata_tables.keys())
        expected = set(ALL_TABLES)
        assert present == expected, f"Missing tables: {expected - present}, Extra tables: {present - expected}"

    @pytest.mark.parametrize("table_name", ALL_TABLES)
    def test_every_table_has_shared_columns(self, metadata_tables, table_name):
        table = metadata_tables[table_name]
        column_names = {c.name for c in table.columns}
        for col in SHARED_COLUMNS:
            assert col in column_names, f"Table {table_name} missing column {col}"

    @pytest.mark.parametrize("table_name", SIMULATION_CHILD_TABLES)
    def test_simulation_child_tables_have_run_id(self, metadata_tables, table_name):
        table = metadata_tables[table_name]
        column_names = {c.name for c in table.columns}
        assert "simulation_id" in column_names, f"Table {table_name} missing simulation_id"
        assert "run_id" in column_names, f"Table {table_name} missing run_id"


    def test_graph_snapshots_has_checkpoint_columns(self, metadata_tables):
        table = metadata_tables["graph_snapshots"]
        column_names = {c.name for c in table.columns}
        assert {"simulation_id", "round_index", "snapshot_data"}.issubset(column_names)
    def test_metadata_uses_json_type(self, metadata_tables):
        """At least some tables should use JSON column type for flexible data."""
        json_found = False
        for table in metadata_tables.values():
            for col in table.columns:
                if isinstance(col.type, JSON):
                    json_found = True
                    break
            if json_found:
                break
        assert json_found, "No JSON column type found in metadata"

    def test_json_payload_columns_use_jsonb_for_postgresql(self, metadata_tables):
        """JSON payload columns must compile to JSONB under PostgreSQL."""
        json_columns = [
            col
            for table in metadata_tables.values()
            for col in table.columns
            if isinstance(col.type, JSON)
        ]
        assert json_columns, "No JSON payload columns found"
        assert any(
            isinstance(col.type.dialect_impl(postgresql.dialect()), JSONB)
            for col in json_columns
        ), "No JSON column maps to PostgreSQL JSONB"

    def test_schema_can_create_all_tables_in_memory(self):
        """Create all tables in SQLite memory to verify DDL validity."""
        from app.repositories.sqlalchemy import metadata
        engine = create_engine("sqlite:///:memory:")
        metadata.create_all(engine)
        inspector = sa_inspect(engine)
        actual_tables = set(inspector.get_table_names())
        expected = set(ALL_TABLES)
        assert actual_tables == expected, f"Missing: {expected - actual_tables}, Extra: {actual_tables - expected}"


class TestAlembicMigration:
    """Verify initial migration creates the base tables with required columns."""

    @pytest.fixture(scope="class")
    def migration_module(self):
        migration_path = BACKEND_DIR / "alembic" / "versions"
        if not migration_path.exists():
            pytest.skip("No alembic versions directory found")
        py_files = sorted([f for f in migration_path.iterdir() if f.suffix == ".py" and not f.name.startswith("__")])
        if not py_files:
            pytest.skip("No migration files found")
        # Import the first (initial) migration
        spec = importlib.util.spec_from_file_location("initial_migration", py_files[0])
        mod = importlib.util.module_from_spec(spec)
        sys.modules["initial_migration"] = mod
        spec.loader.exec_module(mod)
        return mod

    @pytest.fixture(scope="class")
    def migration_source(self, migration_module):
        return inspect.getsource(migration_module)

    def test_migration_mentions_all_tables(self, migration_source):
        for table in INITIAL_MIGRATION_TABLES:
            assert table in migration_source, f"Migration missing table name: {table}"

    def test_migration_mentions_shared_columns(self, migration_source):
        for col in SHARED_COLUMNS:
            assert col in migration_source, f"Migration missing shared column: {col}"

    def test_migration_mentions_simulation_id_and_run_id(self, migration_source):
        assert "simulation_id" in migration_source
        assert "run_id" in migration_source

    def test_migration_upgrade_runs_against_sqlite(self, migration_module):
        """Run the migration upgrade against SQLite to verify it works."""
        engine = create_engine("sqlite:///:memory:")
        with engine.begin() as connection:
            context = MigrationContext.configure(connection)
            with Operations.context(context):
                migration_module.upgrade()

            inspector = sa_inspect(connection)
            actual = set(inspector.get_table_names())
        assert actual == set(INITIAL_MIGRATION_TABLES)

