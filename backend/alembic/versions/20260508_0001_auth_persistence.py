"""Add persistent auth users and API keys.

Revision ID: 20260508_0001_auth_persistence
Revises: 7a1_initial_20_tables
Create Date: 2026-05-08 00:00:00.000000
Revision rationale: add durable users and API keys for permission and tenant isolation tests.

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "20260508_0001_auth_persistence"
down_revision: Union[str, None] = "7a1_initial_20_tables"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _json_type():
    return sa.JSON().with_variant(postgresql.JSONB, "postgresql")


def upgrade() -> None:
    op.create_table(
        "auth_users",
        sa.Column("user_id", sa.String(64), primary_key=True),
        sa.Column("username", sa.String(255), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("role", sa.String(50), nullable=False),
        sa.Column("tenant_id", sa.String(255), nullable=False),
        sa.Column("workspace_id", sa.String(255), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.Float(), nullable=False),
    )
    op.create_index("ix_auth_users_user_id", "auth_users", ["user_id"])
    op.create_index("ix_auth_users_tenant_id", "auth_users", ["tenant_id"])

    op.create_table(
        "auth_api_keys",
        sa.Column("key_id", sa.String(64), primary_key=True),
        sa.Column("key_hash", sa.String(255), nullable=False),
        sa.Column(
            "user_id",
            sa.String(64),
            sa.ForeignKey("auth_users.user_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("tenant_id", sa.String(255), nullable=False),
        sa.Column("scopes", _json_type(), nullable=False, server_default="[]"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.Float(), nullable=False),
        sa.Column("expires_at", sa.Float()),
    )
    op.create_index("ix_auth_api_keys_user_id", "auth_api_keys", ["user_id"])
    op.create_index("ix_auth_api_keys_tenant_id", "auth_api_keys", ["tenant_id"])
    op.create_index("ix_auth_api_keys_key_hash", "auth_api_keys", ["key_hash"])


def downgrade() -> None:
    op.drop_index("ix_auth_api_keys_key_hash", table_name="auth_api_keys")
    op.drop_index("ix_auth_api_keys_tenant_id", table_name="auth_api_keys")
    op.drop_index("ix_auth_api_keys_user_id", table_name="auth_api_keys")
    op.drop_table("auth_api_keys")

    op.drop_index("ix_auth_users_tenant_id", table_name="auth_users")
    op.drop_index("ix_auth_users_user_id", table_name="auth_users")
    op.drop_table("auth_users")
