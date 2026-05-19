"""add_foreign_keys_core_tables

Revision ID: 20260512_0001_add_foreign_keys
Revises: 20260508_0003_perf_indexes
Create Date: 2026-05-12
Revision rationale: enforce durable parent-child integrity across project, simulation, report, queue, and asset tables.
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op

revision: str = "20260512_0001_add_foreign_keys"
down_revision: Union[str, None] = "20260508_0003_perf_indexes"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

FOREIGN_KEYS = [
    ("fk_consumer_briefs_project_id", "consumer_briefs", "projects", ["project_id"], ["id"], "CASCADE"),
    ("fk_simulations_project_id", "simulations", "projects", ["project_id"], ["id"], "CASCADE"),
    ("fk_simulation_runs_simulation_id", "simulation_runs", "simulations", ["simulation_id"], ["id"], "CASCADE"),
    ("fk_society_agents_simulation_id", "society_agents", "simulations", ["simulation_id"], ["id"], "CASCADE"),
    ("fk_round_snapshots_run_id", "round_snapshots", "simulation_runs", ["run_id"], ["id"], "CASCADE"),
    ("fk_consumer_events_run_id", "consumer_events", "simulation_runs", ["run_id"], ["id"], "CASCADE"),
    ("fk_branches_simulation_id", "branches", "simulations", ["simulation_id"], ["id"], "CASCADE"),
    ("fk_interventions_simulation_id", "interventions", "simulations", ["simulation_id"], ["id"], "CASCADE"),
    ("fk_interventions_branch_id", "interventions", "branches", ["branch_id"], ["id"], "CASCADE"),
    ("fk_reports_simulation_id", "reports", "simulations", ["simulation_id"], ["id"], "CASCADE"),
    ("fk_report_sections_report_id", "report_sections", "reports", ["report_id"], ["id"], "CASCADE"),
    ("fk_memory_entries_run_id", "memory_entries", "simulation_runs", ["run_id"], ["id"], "CASCADE"),
    ("fk_tasks_simulation_id", "tasks", "simulations", ["simulation_id"], ["id"], "SET NULL"),
    ("fk_task_attempts_task_id", "task_attempts", "tasks", ["task_id"], ["id"], "CASCADE"),
    ("fk_dead_letters_simulation_id", "dead_letters", "simulations", ["simulation_id"], ["id"], "SET NULL"),
    ("fk_locks_simulation_id", "locks", "simulations", ["simulation_id"], ["id"], "CASCADE"),
    ("fk_research_assets_project_id", "research_assets", "projects", ["project_id"], ["id"], "CASCADE"),
    ("fk_benchmark_replays_benchmark_id", "benchmark_replays", "benchmarks", ["benchmark_id"], ["id"], "CASCADE"),
]


def upgrade() -> None:
    if op.get_context().dialect.name == "sqlite":
        return
    for name, source, target, local_cols, remote_cols, ondelete in FOREIGN_KEYS:
        op.create_foreign_key(
            constraint_name=name,
            source_table=source,
            referent_table=target,
            local_cols=local_cols,
            remote_cols=remote_cols,
            ondelete=ondelete,
        )


def downgrade() -> None:
    if op.get_context().dialect.name == "sqlite":
        return
    for name, source, *_ in reversed(FOREIGN_KEYS):
        op.drop_constraint(name, source, type_="foreignkey")
