"""Add performance indexes for high-frequency application queries.

Revision ID: 20260508_0003_add_performance_indexes
Revises: 20260508_0001_auth_persistence
Create Date: 2026-05-08 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260508_0003_add_performance_indexes"
down_revision: Union[str, None] = "20260508_0001_auth_persistence"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


INDEXES = [
    ("ix_projects_created_at", "projects", ["created_at"]),
    ("ix_projects_project_type", "projects", ["project_type"]),
    ("ix_simulations_project_status", "simulations", ["project_id", "status"]),
    ("ix_simulations_project_created_at", "simulations", ["project_id", "created_at"]),
    ("ix_simulation_runs_simulation_run", "simulation_runs", ["simulation_id", "run_id"]),
    ("ix_branches_simulation_status", "branches", ["simulation_id", "status"]),
    ("ix_branches_simulation_created_at", "branches", ["simulation_id", "created_at"]),
    ("ix_reports_simulation_status", "reports", ["simulation_id", "status"]),
    ("ix_reports_simulation_created_at", "reports", ["simulation_id", "created_at"]),
    ("ix_tasks_simulation_status", "tasks", ["simulation_id", "status"]),
    ("ix_tasks_status_updated_at", "tasks", ["status", "updated_at"]),
    ("ix_task_attempts_task_attempt", "task_attempts", ["task_id", "attempt_number"]),
]


def upgrade() -> None:
    for index_name, table_name, columns in INDEXES:
        op.create_index(index_name, table_name, columns)


def downgrade() -> None:
    for index_name, table_name, _columns in reversed(INDEXES):
        op.drop_index(index_name, table_name=table_name)
