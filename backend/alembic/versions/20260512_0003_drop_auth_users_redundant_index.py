"""Drop redundant auth_users user_id index.

Revision ID: 20260512_0003_drop_auth_idx
Revises: 20260512_0002_tenant_indexes
Create Date: 2026-05-12
Revision rationale: remove the auth_users.user_id secondary index because the primary key already covers it.
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260512_0003_drop_auth_idx"
down_revision: Union[str, None] = "20260512_0002_tenant_indexes"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _index_exists(table_name: str, index_name: str) -> bool:
    inspector = sa.inspect(op.get_bind())
    if table_name not in set(inspector.get_table_names()):
        return False
    return index_name in {index["name"] for index in inspector.get_indexes(table_name)}


def upgrade() -> None:
    if _index_exists("auth_users", "ix_auth_users_user_id"):
        op.drop_index("ix_auth_users_user_id", table_name="auth_users")


def downgrade() -> None:
    if not _index_exists("auth_users", "ix_auth_users_user_id"):
        op.create_index("ix_auth_users_user_id", "auth_users", ["user_id"], if_not_exists=True)
