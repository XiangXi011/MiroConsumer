"""Clean orphan rows before enabling database foreign keys."""

from __future__ import annotations

import os
from typing import Iterable

from sqlalchemy import create_engine, text

CLEANUP_QUERIES = [
    "DELETE FROM consumer_briefs WHERE NOT EXISTS (SELECT 1 FROM projects WHERE projects.id = consumer_briefs.project_id)",
    "DELETE FROM simulations WHERE NOT EXISTS (SELECT 1 FROM projects WHERE projects.id = simulations.project_id)",
    "DELETE FROM simulation_runs WHERE NOT EXISTS (SELECT 1 FROM simulations WHERE simulations.id = simulation_runs.simulation_id)",
    "DELETE FROM society_agents WHERE NOT EXISTS (SELECT 1 FROM simulations WHERE simulations.id = society_agents.simulation_id)",
    "DELETE FROM round_snapshots WHERE NOT EXISTS (SELECT 1 FROM simulation_runs WHERE simulation_runs.id = round_snapshots.run_id)",
    "DELETE FROM consumer_events WHERE NOT EXISTS (SELECT 1 FROM simulation_runs WHERE simulation_runs.id = consumer_events.run_id)",
    "DELETE FROM branches WHERE NOT EXISTS (SELECT 1 FROM simulations WHERE simulations.id = branches.simulation_id)",
    "DELETE FROM interventions WHERE NOT EXISTS (SELECT 1 FROM simulations WHERE simulations.id = interventions.simulation_id)",
    "DELETE FROM interventions WHERE NOT EXISTS (SELECT 1 FROM branches WHERE branches.id = interventions.branch_id)",
    "DELETE FROM reports WHERE NOT EXISTS (SELECT 1 FROM simulations WHERE simulations.id = reports.simulation_id)",
    "DELETE FROM report_sections WHERE NOT EXISTS (SELECT 1 FROM reports WHERE reports.id = report_sections.report_id)",
    "DELETE FROM memory_entries WHERE NOT EXISTS (SELECT 1 FROM simulation_runs WHERE simulation_runs.id = memory_entries.run_id)",
    "DELETE FROM tasks WHERE NOT EXISTS (SELECT 1 FROM simulations WHERE simulations.id = tasks.simulation_id)",
    "DELETE FROM task_attempts WHERE NOT EXISTS (SELECT 1 FROM tasks WHERE tasks.id = task_attempts.task_id)",
    "DELETE FROM dead_letters WHERE NOT EXISTS (SELECT 1 FROM simulations WHERE simulations.id = dead_letters.simulation_id)",
    "DELETE FROM locks WHERE NOT EXISTS (SELECT 1 FROM simulations WHERE simulations.id = locks.simulation_id)",
    "DELETE FROM research_assets WHERE NOT EXISTS (SELECT 1 FROM projects WHERE projects.id = research_assets.project_id)",
    "DELETE FROM benchmark_replays WHERE NOT EXISTS (SELECT 1 FROM benchmarks WHERE benchmarks.id = benchmark_replays.benchmark_id)",
]


def clean_orphans(database_url: str | None = None, queries: Iterable[str] = CLEANUP_QUERIES) -> int:
    url = database_url or os.environ.get("DB_URL") or os.environ.get("DATABASE_URL")
    if not url:
        raise RuntimeError("DB_URL or DATABASE_URL is required to clean orphan records")
    engine = create_engine(url)
    total_deleted = 0
    with engine.begin() as connection:
        for query in queries:
            result = connection.execute(text(query))
            total_deleted += int(result.rowcount or 0)
    return total_deleted


if __name__ == "__main__":
    print(f"Cleaned {clean_orphans()} orphan records")
