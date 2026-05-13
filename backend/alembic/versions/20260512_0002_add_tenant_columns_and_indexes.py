"""add tenant columns and high-frequency tenant indexes

Revision ID: 20260512_0002_add_tenant_columns_and_indexes
Revises: 20260512_0001_add_foreign_keys
Create Date: 2026-05-12
Revision rationale: add tenant columns and high-frequency tenant indexes used by the P2/P3 isolation gates.
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260512_0002_add_tenant_columns_and_indexes"
down_revision: Union[str, None] = "20260512_0001_add_foreign_keys"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TENANT_TABLES = ("projects", "simulations", "reports")
TENANT_INDEXES = [
    ("ix_projects_tenant_id", "projects", ["tenant_id"]),
    ("ix_simulations_tenant_id", "simulations", ["tenant_id"]),
    ("ix_simulations_created_at", "simulations", ["created_at"]),
    ("ix_simulations_status", "simulations", ["status"]),
    ("ix_simulations_tenant_status", "simulations", ["tenant_id", "status"]),
    ("ix_reports_tenant_id", "reports", ["tenant_id"]),
    ("ix_reports_simulation_id", "reports", ["simulation_id"]),
    ("ix_audit_logs_created_at", "audit_logs", ["created_at"]),
]


def _inspector() -> sa.Inspector:
    return sa.inspect(op.get_bind())


def _is_postgresql() -> bool:
    bind = op.get_bind()
    return bool(bind is not None and bind.dialect.name == "postgresql")


def _table_exists(table_name: str) -> bool:
    return table_name in set(_inspector().get_table_names())


def _column_exists(table_name: str, column_name: str) -> bool:
    if not _table_exists(table_name):
        return False
    return column_name in {column["name"] for column in _inspector().get_columns(table_name)}


def _index_exists(table_name: str, index_name: str) -> bool:
    if not _table_exists(table_name):
        return False
    return index_name in {index["name"] for index in _inspector().get_indexes(table_name)}


def _quoted_identifier(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


def _backfill_tenant_id(table_name: str) -> None:
    table = _quoted_identifier(table_name)
    if _is_postgresql():
        if table_name == "reports":
            expression = "COALESCE(NULLIF(data->>'tenant_id', ''), NULLIF(data #>> '{report_context,tenant_id}', ''), '')"
        else:
            expression = "COALESCE(NULLIF(data->>'tenant_id', ''), '')"
        op.execute(sa.text(f"UPDATE {table} SET tenant_id = {expression} WHERE tenant_id IS NULL OR tenant_id = ''"))
        return

    if table_name == "reports":
        expression = "COALESCE(NULLIF(json_extract(data, '$.tenant_id'), ''), NULLIF(json_extract(data, '$.report_context.tenant_id'), ''), '')"
    else:
        expression = "COALESCE(NULLIF(json_extract(data, '$.tenant_id'), ''), '')"
    op.execute(sa.text(f"UPDATE {table} SET tenant_id = {expression} WHERE tenant_id IS NULL OR tenant_id = ''"))


def _add_tenant_column(table_name: str) -> None:
    if not _table_exists(table_name) or _column_exists(table_name, "tenant_id"):
        return
    op.add_column(
        table_name,
        sa.Column("tenant_id", sa.String(length=255), nullable=False, server_default=""),
    )
    _backfill_tenant_id(table_name)
    if _is_postgresql():
        op.alter_column(
            table_name,
            "tenant_id",
            existing_type=sa.String(length=255),
            existing_nullable=False,
            server_default=None,
        )


def _create_index(index_name: str, table_name: str, columns: list[str]) -> None:
    if not _table_exists(table_name) or _index_exists(table_name, index_name):
        return
    if _is_postgresql():
        with op.get_context().autocommit_block():
            op.create_index(
                index_name,
                table_name,
                columns,
                postgresql_concurrently=True,
            )
        return
    op.create_index(index_name, table_name, columns)


def _drop_index(index_name: str, table_name: str) -> None:
    if not _table_exists(table_name) or not _index_exists(table_name, index_name):
        return
    if _is_postgresql():
        with op.get_context().autocommit_block():
            op.drop_index(index_name, table_name=table_name, postgresql_concurrently=True)
        return
    op.drop_index(index_name, table_name=table_name)


def upgrade() -> None:
    for table_name in TENANT_TABLES:
        _add_tenant_column(table_name)
    for index_name, table_name, columns in TENANT_INDEXES:
        _create_index(index_name, table_name, columns)


def downgrade() -> None:
    for index_name, table_name, _columns in reversed(TENANT_INDEXES):
        _drop_index(index_name, table_name)
    for table_name in reversed(TENANT_TABLES):
        if _column_exists(table_name, "tenant_id"):
            op.drop_column(table_name, "tenant_id")
