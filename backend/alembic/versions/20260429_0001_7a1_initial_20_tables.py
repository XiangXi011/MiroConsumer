"""Initial migration: create all 20 tables.

Every table has id, created_at, updated_at, version.
Simulation child tables additionally have simulation_id and run_id.

Tables created: projects, consumer_briefs, simulations, simulation_runs,
society_agents, persona_packs, round_snapshots, consumer_events, branches,
interventions, reports, report_sections, research_assets, benchmarks,
benchmark_replays, memory_entries, tasks, task_attempts, dead_letters, locks.

Revision ID: 7a1_initial_20_tables
Revises:
Create Date: 2026-04-29 00:00:00.000000
Revision rationale: establish the first durable schema for projects, simulations, reports, queues, and locks.

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "7a1_initial_20_tables"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _json_type():
    return sa.JSON().with_variant(postgresql.JSONB, "postgresql")


def upgrade() -> None:
    # ── projects ──────────────────────────────────────────────
    op.create_table(
        "projects",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.Column("version", sa.Integer, nullable=False, default=1),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("project_type", sa.String(50), default="default"),
        sa.Column("status", sa.String(50), default="created"),
        sa.Column("data", _json_type(), default=dict),
    )

    # ── consumer_briefs ───────────────────────────────────────
    op.create_table(
        "consumer_briefs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.Column("version", sa.Integer, nullable=False, default=1),
        sa.Column("project_id", sa.String(36), nullable=False),
        sa.Column("payload", _json_type(), default=dict),
    )

    # ── simulations ───────────────────────────────────────────
    op.create_table(
        "simulations",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.Column("version", sa.Integer, nullable=False, default=1),
        sa.Column("project_id", sa.String(36), nullable=False),
        sa.Column("graph_id", sa.String(36)),
        sa.Column("project_type", sa.String(50), default="default"),
        sa.Column("consumer_mode", sa.Integer, default=0),
        sa.Column("status", sa.String(50), default="created"),
        sa.Column("data", _json_type(), default=dict),
    )

    # ── simulation_runs (child) ───────────────────────────────
    op.create_table(
        "simulation_runs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.Column("version", sa.Integer, nullable=False, default=1),
        sa.Column("simulation_id", sa.String(36), nullable=False),
        sa.Column("run_id", sa.String(36), nullable=False),
        sa.Column("status", sa.String(50), default="created"),
        sa.Column("data", _json_type(), default=dict),
    )

    # ── society_agents (child) ────────────────────────────────
    op.create_table(
        "society_agents",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.Column("version", sa.Integer, nullable=False, default=1),
        sa.Column("simulation_id", sa.String(36), nullable=False),
        sa.Column("run_id", sa.String(36), nullable=False),
        sa.Column("platform", sa.String(50)),
        sa.Column("persona_data", _json_type(), default=dict),
    )

    # ── persona_packs ─────────────────────────────────────────
    op.create_table(
        "persona_packs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.Column("version", sa.Integer, nullable=False, default=1),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("lineage", sa.String(255)),
        sa.Column("config", _json_type(), default=dict),
    )

    # ── round_snapshots (child) ───────────────────────────────
    op.create_table(
        "round_snapshots",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.Column("version", sa.Integer, nullable=False, default=1),
        sa.Column("simulation_id", sa.String(36), nullable=False),
        sa.Column("run_id", sa.String(36), nullable=False),
        sa.Column("round_number", sa.Integer, nullable=False),
        sa.Column("snapshot_data", _json_type(), default=dict),
    )

    # ── consumer_events (child) ───────────────────────────────
    op.create_table(
        "consumer_events",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.Column("version", sa.Integer, nullable=False, default=1),
        sa.Column("simulation_id", sa.String(36), nullable=False),
        sa.Column("run_id", sa.String(36), nullable=False),
        sa.Column("event_type", sa.String(100)),
        sa.Column("payload", _json_type(), default=dict),
    )

    # ── branches (child) ──────────────────────────────────────
    op.create_table(
        "branches",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.Column("version", sa.Integer, nullable=False, default=1),
        sa.Column("simulation_id", sa.String(36), nullable=False),
        sa.Column("run_id", sa.String(36), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("fork_round", sa.Integer, nullable=False),
        sa.Column("description", sa.String(1000)),
        sa.Column("parent_branch_id", sa.String(36)),
        sa.Column("status", sa.String(50), default="active"),
        sa.Column("data", _json_type(), default=dict),
    )

    # ── interventions (child) ─────────────────────────────────
    op.create_table(
        "interventions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.Column("version", sa.Integer, nullable=False, default=1),
        sa.Column("simulation_id", sa.String(36), nullable=False),
        sa.Column("run_id", sa.String(36), nullable=False),
        sa.Column("branch_id", sa.String(36), nullable=False),
        sa.Column("intervention_type", sa.String(100)),
        sa.Column("payload", _json_type(), default=dict),
        sa.Column("target_round", sa.Integer),
    )

    # ── reports (child) ───────────────────────────────────────
    op.create_table(
        "reports",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.Column("version", sa.Integer, nullable=False, default=1),
        sa.Column("simulation_id", sa.String(36), nullable=False),
        sa.Column("run_id", sa.String(36), nullable=False),
        sa.Column("report_type", sa.String(50)),
        sa.Column("status", sa.String(50), default="pending"),
        sa.Column("progress", sa.Integer, default=0),
        sa.Column("data", _json_type(), default=dict),
    )

    # ── report_sections (child) ───────────────────────────────
    op.create_table(
        "report_sections",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.Column("version", sa.Integer, nullable=False, default=1),
        sa.Column("simulation_id", sa.String(36), nullable=False),
        sa.Column("run_id", sa.String(36), nullable=False),
        sa.Column("report_id", sa.String(36), nullable=False),
        sa.Column("section_index", sa.Integer, nullable=False),
        sa.Column("title", sa.String(500)),
        sa.Column("content", _json_type(), default=dict),
    )

    # ── research_assets ───────────────────────────────────────
    op.create_table(
        "research_assets",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.Column("version", sa.Integer, nullable=False, default=1),
        sa.Column("project_id", sa.String(36), nullable=False),
        sa.Column("asset_type", sa.String(100)),
        sa.Column("payload", _json_type(), default=dict),
    )

    # ── benchmarks ────────────────────────────────────────────
    op.create_table(
        "benchmarks",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.Column("version", sa.Integer, nullable=False, default=1),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("source_pack_lineage", sa.String(255)),
        sa.Column("expected_signals", _json_type(), default=dict),
        sa.Column("simulation_context", _json_type(), default=dict),
    )

    # ── benchmark_replays ─────────────────────────────────────
    op.create_table(
        "benchmark_replays",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.Column("version", sa.Integer, nullable=False, default=1),
        sa.Column("benchmark_id", sa.String(36), nullable=False),
        sa.Column("replay_result", _json_type(), default=dict),
    )

    # ── memory_entries (child) ────────────────────────────────
    op.create_table(
        "memory_entries",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.Column("version", sa.Integer, nullable=False, default=1),
        sa.Column("simulation_id", sa.String(36), nullable=False),
        sa.Column("run_id", sa.String(36), nullable=False),
        sa.Column("agent_id", sa.String(36)),
        sa.Column("memory_type", sa.String(100)),
        sa.Column("content", _json_type(), default=dict),
    )

    # ── tasks (child) ─────────────────────────────────────────
    op.create_table(
        "tasks",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.Column("version", sa.Integer, nullable=False, default=1),
        sa.Column("simulation_id", sa.String(36), nullable=False),
        sa.Column("run_id", sa.String(36), nullable=False),
        sa.Column("task_type", sa.String(100)),
        sa.Column("status", sa.String(50), default="PENDING"),
        sa.Column("payload", _json_type(), default=dict),
    )

    # ── task_attempts (child) ─────────────────────────────────
    op.create_table(
        "task_attempts",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.Column("version", sa.Integer, nullable=False, default=1),
        sa.Column("simulation_id", sa.String(36), nullable=False),
        sa.Column("run_id", sa.String(36), nullable=False),
        sa.Column("task_id", sa.String(36), nullable=False),
        sa.Column("attempt_number", sa.Integer, nullable=False, default=1),
        sa.Column("result", _json_type(), default=dict),
        sa.Column("error", _json_type()),
    )

    # ── dead_letters (child) ──────────────────────────────────
    op.create_table(
        "dead_letters",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.Column("version", sa.Integer, nullable=False, default=1),
        sa.Column("simulation_id", sa.String(36), nullable=False),
        sa.Column("run_id", sa.String(36), nullable=False),
        sa.Column("task_id", sa.String(36)),
        sa.Column("reason", sa.String(500)),
        sa.Column("payload", _json_type(), default=dict),
    )

    # ── locks (child) ─────────────────────────────────────────
    op.create_table(
        "locks",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.Column("version", sa.Integer, nullable=False, default=1),
        sa.Column("simulation_id", sa.String(36), nullable=False),
        sa.Column("run_id", sa.String(36), nullable=False),
        sa.Column("resource_id", sa.String(255), nullable=False),
        sa.Column("lock_type", sa.String(100)),
        sa.Column("owner", sa.String(255)),
        sa.Column("expires_at", sa.DateTime),
    )


def downgrade() -> None:
    op.drop_table("locks")
    op.drop_table("dead_letters")
    op.drop_table("task_attempts")
    op.drop_table("tasks")
    op.drop_table("memory_entries")
    op.drop_table("benchmark_replays")
    op.drop_table("benchmarks")
    op.drop_table("research_assets")
    op.drop_table("report_sections")
    op.drop_table("reports")
    op.drop_table("interventions")
    op.drop_table("branches")
    op.drop_table("consumer_events")
    op.drop_table("round_snapshots")
    op.drop_table("persona_packs")
    op.drop_table("society_agents")
    op.drop_table("simulation_runs")
    op.drop_table("simulations")
    op.drop_table("consumer_briefs")
    op.drop_table("projects")
