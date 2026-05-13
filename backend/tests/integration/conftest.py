"""Shared fixtures for SPEC-P2-018 integration tests."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.config import Config
from app.models.project import Project, ProjectManager, ProjectStatus
from app.repositories.sqlalchemy import (
    SQLAlchemyBranchRepository,
    SQLAlchemyProjectRepository,
    SQLAlchemyReportRepository,
    SQLAlchemySimulationRepository,
    metadata,
)
from app.services.report_agent import Report, ReportStatus
from app.services.simulation_manager import SimulationManager


@dataclass
class IntegrationBundle:
    engine: object
    session_factory: object
    project_repo: SQLAlchemyProjectRepository
    simulation_repo: SQLAlchemySimulationRepository
    branch_repo: SQLAlchemyBranchRepository
    report_repo: SQLAlchemyReportRepository


class CapturingExecutor:
    """Task executor fake that records submissions without running background work."""

    def __init__(self) -> None:
        self.submissions: list[dict] = []

    def submit(self, func, *args, **kwargs):
        trace_id = kwargs.get("trace_id") or f"integration-trace-{len(self.submissions) + 1}"
        self.submissions.append(
            {
                "func": func,
                "args": args,
                "kwargs": dict(kwargs),
                "trace_id": trace_id,
            }
        )
        return trace_id


@pytest.fixture()
def integration_bundle(tmp_path):
    db_path = tmp_path / "integration.db"
    engine = create_engine(f"sqlite:///{db_path.as_posix()}")
    metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)
    bundle = IntegrationBundle(
        engine=engine,
        session_factory=session_factory,
        project_repo=SQLAlchemyProjectRepository(session_factory=session_factory),
        simulation_repo=SQLAlchemySimulationRepository(session_factory=session_factory),
        branch_repo=SQLAlchemyBranchRepository(session_factory=session_factory),
        report_repo=SQLAlchemyReportRepository(session_factory=session_factory),
    )
    try:
        yield bundle
    finally:
        metadata.drop_all(engine)
        engine.dispose()


@pytest.fixture()
def isolated_uploads(tmp_path, monkeypatch) -> Path:
    uploads = tmp_path / "uploads"
    simulations = uploads / "simulations"
    projects = uploads / "projects"
    reports = uploads / "reports"
    for path in (simulations, projects, reports):
        path.mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr(Config, "UPLOAD_FOLDER", str(uploads))
    monkeypatch.setattr(Config, "OASIS_SIMULATION_DATA_DIR", str(simulations))
    monkeypatch.setattr(ProjectManager, "PROJECTS_DIR", str(projects))
    monkeypatch.setattr(SimulationManager, "SIMULATION_DATA_DIR", str(simulations))
    return uploads


@pytest.fixture()
def app_services(integration_bundle, isolated_uploads, monkeypatch):
    from app.services.application.report_app_service import ReportAppService
    from app.services.application.simulation_app_service import SimulationAppService
    from app.services.consumer import phase6j_calibration

    executor = CapturingExecutor()

    monkeypatch.setattr(SimulationAppService, "_project_repo", integration_bundle.project_repo)
    monkeypatch.setattr(SimulationAppService, "_simulation_repo", integration_bundle.simulation_repo)
    monkeypatch.setattr(ReportAppService, "_project_repo", integration_bundle.project_repo)
    monkeypatch.setattr(ReportAppService, "_simulation_repo", integration_bundle.simulation_repo)
    monkeypatch.setattr(ReportAppService, "_report_repo", integration_bundle.report_repo)
    monkeypatch.setattr(ReportAppService, "_executor", executor)
    monkeypatch.setattr(
        phase6j_calibration,
        "check_phase6j_gate",
        lambda simulation_dir: {"blocked": False, "reason": "", "details": {}},
    )

    return SimpleNamespace(bundle=integration_bundle, executor=executor, uploads=isolated_uploads)


@pytest.fixture()
def seed_project(integration_bundle):
    def _seed(
        *,
        project_id: str = "proj_integration",
        tenant_id: str = "tenant-a",
        project_type: str = "consumer_test",
        brief: dict | None = None,
    ) -> Project:
        now = datetime.now(timezone.utc).isoformat()
        project = Project(
            project_id=project_id,
            name=f"Integration {project_id}",
            status=ProjectStatus.GRAPH_COMPLETED,
            created_at=now,
            updated_at=now,
            project_type=project_type,
            tenant_id=tenant_id,
            graph_id=f"graph_{project_id}",
            simulation_requirement="brief: validate new packaging concept",
            consumer_brief=brief
            or {
                "brief_id": f"brief_{project_id}",
                "product": "sparkling tea",
                "audience": "urban commuters",
                "objective": "measure purchase intent",
            },
        )
        integration_bundle.project_repo.save_project(project)
        return project

    return _seed


@pytest.fixture()
def seed_simulation(integration_bundle, seed_project):
    def _seed(
        *,
        project: Project | None = None,
        tenant_id: str = "tenant-a",
        status=None,
    ):
        from app.services.simulation_manager import SimulationStatus

        project = project or seed_project(tenant_id=tenant_id)
        state = integration_bundle.simulation_repo.create_simulation(
            project_id=project.project_id,
            graph_id=project.graph_id or f"graph_{project.project_id}",
            project_type=project.project_type,
            tenant_id=tenant_id,
        )
        if status is not None:
            state.status = status
            integration_bundle.simulation_repo.save_simulation(state)
        else:
            state.status = SimulationStatus.READY
            state.config_generated = True
            integration_bundle.simulation_repo.save_simulation(state)
        return state

    return _seed


@pytest.fixture()
def seed_report(integration_bundle):
    def _seed(*, simulation_id: str, tenant_id: str = "tenant-a", report_id: str = "report_integration"):
        report = Report(
            report_id=report_id,
            simulation_id=simulation_id,
            graph_id="graph_integration",
            simulation_requirement="brief: validate new packaging concept",
            status=ReportStatus.COMPLETED,
            project_type="consumer_test",
            markdown_content="# Integration report\n\nEvidence-backed result.",
            report_context={"tenant_id": tenant_id},
            created_at=datetime.now(timezone.utc).isoformat(),
            completed_at=datetime.now(timezone.utc).isoformat(),
        )
        setattr(report, "tenant_id", tenant_id)
        integration_bundle.report_repo.save_report(report)
        return report

    return _seed
