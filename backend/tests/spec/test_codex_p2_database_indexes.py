"""SPEC-P2-014 tenant columns and high-frequency index contract."""

from __future__ import annotations

import importlib.util
from pathlib import Path

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from app.models.project import ProjectStatus
from app.repositories.sqlalchemy import (
    SQLAlchemyProjectRepository,
    SQLAlchemyReportRepository,
    SQLAlchemySimulationRepository,
    metadata,
    projects,
    reports,
    simulations,
)
from app.services.report_agent import Report, ReportStatus

ROOT = Path(__file__).resolve().parents[2]
MIGRATION_PATH = ROOT / "alembic" / "versions" / "20260512_0002_add_tenant_columns_and_indexes.py"


def _index_columns(table):
    return {index.name: [column.name for column in index.columns] for index in table.indexes}


def test_core_tables_have_first_class_tenant_columns_and_indexes():
    for table in (projects, simulations, reports):
        assert "tenant_id" in table.c
        assert table.c.tenant_id.type.length == 255

    project_indexes = _index_columns(projects)
    simulation_indexes = _index_columns(simulations)
    report_indexes = _index_columns(reports)

    assert project_indexes["ix_projects_tenant_id"] == ["tenant_id"]
    assert simulation_indexes["ix_simulations_tenant_id"] == ["tenant_id"]
    assert simulation_indexes["ix_simulations_created_at"] == ["created_at"]
    assert simulation_indexes["ix_simulations_status"] == ["status"]
    assert simulation_indexes["ix_simulations_tenant_status"] == ["tenant_id", "status"]
    assert report_indexes["ix_reports_tenant_id"] == ["tenant_id"]
    assert report_indexes["ix_reports_simulation_id"] == ["simulation_id"]


def test_tenant_index_migration_is_incremental_and_zero_downtime_ready():
    text = MIGRATION_PATH.read_text(encoding="utf-8")

    for phrase in (
        "tenant_id",
        "ix_projects_tenant_id",
        "ix_simulations_tenant_status",
        "ix_reports_simulation_id",
        "ix_audit_logs_created_at",
        "postgresql_concurrently=True",
    ):
        assert phrase in text

    spec = importlib.util.spec_from_file_location("tenant_index_migration", MIGRATION_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    assert module.down_revision == "20260512_0001_add_foreign_keys"


def test_sqlalchemy_repositories_write_tenant_id_to_explicit_columns():
    engine = create_engine("sqlite:///:memory:")
    metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, class_=Session)

    project_repo = SQLAlchemyProjectRepository(session_factory=session_factory)
    simulation_repo = SQLAlchemySimulationRepository(session_factory=session_factory)
    report_repo = SQLAlchemyReportRepository(session_factory=session_factory)

    project = project_repo.create_project("Tenant Project")
    project.tenant_id = "tenant_a"
    project.status = ProjectStatus.CREATED
    project_repo.save_project(project)

    simulation = simulation_repo.create_simulation(
        project_id=project.project_id,
        graph_id="graph_a",
        tenant_id="tenant_a",
    )

    report = Report(
        report_id="report_tenant_a",
        simulation_id=simulation.simulation_id,
        graph_id="graph_a",
        simulation_requirement="tenant column check",
        status=ReportStatus.PENDING,
        report_context={"tenant_id": "tenant_a"},
    )
    report_repo.save_report(report)

    with session_factory() as session:
        assert session.execute(select(projects.c.tenant_id).where(projects.c.id == project.project_id)).scalar_one() == "tenant_a"
        assert session.execute(select(simulations.c.tenant_id).where(simulations.c.id == simulation.simulation_id)).scalar_one() == "tenant_a"
        assert session.execute(select(reports.c.tenant_id).where(reports.c.id == report.report_id)).scalar_one() == "tenant_a"

    assert project_repo.get_project(project.project_id).tenant_id == "tenant_a"
    assert simulation_repo.get_simulation(simulation.simulation_id).tenant_id == "tenant_a"
