"""Add persisted graph snapshots.

Revision ID: 20260512_0004_add_graph_snapshots
Revises: 20260512_0003_drop_auth_users_redundant_index
Create Date: 2026-05-13
Revision rationale: persist branch graph snapshots so simulations can resume from the latest checkpoint.
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260512_0004_add_graph_snapshots"
down_revision: Union[str, None] = "20260512_0003_drop_auth_users_redundant_index"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _table_exists(table_name: str) -> bool:
    return table_name in set(sa.inspect(op.get_bind()).get_table_names())


def _index_exists(table_name: str, index_name: str) -> bool:
    if not _table_exists(table_name):
        return False
    return index_name in {index["name"] for index in sa.inspect(op.get_bind()).get_indexes(table_name)}


def upgrade() -> None:
    if not _table_exists("graph_snapshots"):
        op.create_table(
            "graph_snapshots",
            sa.Column("id", sa.String(length=36), primary_key=True),
            sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
            sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("simulation_id", sa.String(length=36), nullable=False),
            sa.Column("round_index", sa.Integer(), nullable=False),
            sa.Column("snapshot_data", sa.JSON(), nullable=True),
        )
    if not _index_exists("graph_snapshots", "ix_graph_snapshots_sim_round"):
        op.create_index(
            "ix_graph_snapshots_sim_round",
            "graph_snapshots",
            ["simulation_id", "round_index"],
            unique=False,
        )


def downgrade() -> None:
    if _index_exists("graph_snapshots", "ix_graph_snapshots_sim_round"):
        op.drop_index("ix_graph_snapshots_sim_round", table_name="graph_snapshots")
    if _table_exists("graph_snapshots"):
        op.drop_table("graph_snapshots")
