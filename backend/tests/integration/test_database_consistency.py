"""Database transaction and tenant-isolation integration tests for SPEC-P2-018."""

from __future__ import annotations

from types import SimpleNamespace

import pytest
from sqlalchemy import insert, select

from app.auth.tenant_guard import TenantAccessDenied, TenantGuard
from app.repositories.sqlalchemy import projects, reports, simulations
from app.services.simulation_manager import SimulationStatus


def test_transaction_rollback_removes_simulation_when_creation_fails(integration_bundle):
    session = integration_bundle.session_factory()

    with pytest.raises(RuntimeError, match="boom after simulation insert"):
        with session.begin():
            session.execute(
                insert(projects).values(
                    id="proj_tx_rollback",
                    name="Rollback project",
                    project_type="consumer_test",
                    tenant_id="tenant-a",
                    status="created",
                    version=1,
                    data={"graph_id": "graph_tx_rollback"},
                )
            )
            session.execute(
                insert(simulations).values(
                    id="sim_tx_rollback",
                    project_id="proj_tx_rollback",
                    graph_id="graph_tx_rollback",
                    project_type="consumer_test",
                    tenant_id="tenant-a",
                    consumer_mode=1,
                    status="created",
                    version=1,
                    data={"current_round": 0},
                )
            )
            raise RuntimeError("boom after simulation insert")

    with integration_bundle.session_factory() as verify:
        rows = verify.execute(select(simulations).where(simulations.c.id == "sim_tx_rollback")).fetchall()
    assert rows == []


def test_transaction_commit_persists_project_simulation_and_report_together(integration_bundle):
    with integration_bundle.session_factory() as session:
        with session.begin():
            session.execute(
                insert(projects).values(
                    id="proj_tx_commit",
                    name="Commit project",
                    project_type="consumer_test",
                    tenant_id="tenant-a",
                    status="created",
                    version=1,
                    data={"graph_id": "graph_tx_commit"},
                )
            )
            session.execute(
                insert(simulations).values(
                    id="sim_tx_commit",
                    project_id="proj_tx_commit",
                    graph_id="graph_tx_commit",
                    project_type="consumer_test",
                    tenant_id="tenant-a",
                    consumer_mode=1,
                    status="completed",
                    version=1,
                    data={"current_round": 3},
                )
            )
            session.execute(
                insert(reports).values(
                    id="report_tx_commit",
                    simulation_id="sim_tx_commit",
                    run_id="base",
                    tenant_id="tenant-a",
                    report_type="consumer",
                    status="completed",
                    progress=100,
                    version=1,
                    data={"markdown_content": "ready"},
                )
            )

    assert integration_bundle.project_repo.get_project("proj_tx_commit").tenant_id == "tenant-a"
    assert integration_bundle.simulation_repo.get_simulation("sim_tx_commit").current_round == 3
    assert integration_bundle.report_repo.get_report("report_tx_commit").status.value == "completed"


def test_tenant_isolation_query_returns_only_current_tenant_simulations(integration_bundle, seed_project):
    tenant_a = seed_project(project_id="proj_tenant_a", tenant_id="tenant-a")
    tenant_b = seed_project(project_id="proj_tenant_b", tenant_id="tenant-b")
    integration_bundle.simulation_repo.create_simulation(
        tenant_a.project_id,
        tenant_a.graph_id,
        project_type="consumer_test",
        tenant_id="tenant-a",
    )
    integration_bundle.simulation_repo.create_simulation(
        tenant_b.project_id,
        tenant_b.graph_id,
        project_type="consumer_test",
        tenant_id="tenant-b",
    )

    with integration_bundle.session_factory() as session:
        tenant_a_rows = session.execute(
            select(simulations.c.tenant_id).where(simulations.c.tenant_id == "tenant-a")
        ).fetchall()

    assert [row[0] for row in tenant_a_rows] == ["tenant-a"]


def test_tenant_guard_rejects_cross_tenant_simulation(seed_simulation):
    state = seed_simulation(tenant_id="tenant-b")
    user = SimpleNamespace(user_id="user-a", tenant_id="tenant-a", role="analyst")

    with pytest.raises(TenantAccessDenied):
        TenantGuard.assert_simulation_access(state, user=user)


def test_tenant_guard_allows_same_tenant_simulation(seed_simulation):
    state = seed_simulation(tenant_id="tenant-a")
    user = SimpleNamespace(user_id="user-a", tenant_id="tenant-a", role="analyst")

    TenantGuard.assert_simulation_access(state, user=user)


def test_delete_project_cascades_simulations_and_reports(
    integration_bundle,
    seed_project,
    seed_simulation,
    seed_report,
):
    project = seed_project(project_id="proj_delete", tenant_id="tenant-a")
    state = seed_simulation(project=project, tenant_id="tenant-a", status=SimulationStatus.COMPLETED)
    seed_report(simulation_id=state.simulation_id, report_id="report_delete", tenant_id="tenant-a")

    assert integration_bundle.project_repo.delete_project(project.project_id) is True

    assert integration_bundle.project_repo.get_project(project.project_id) is None
    assert integration_bundle.simulation_repo.get_simulation(state.simulation_id) is None
    assert integration_bundle.report_repo.get_report("report_delete") is None


def test_report_tenant_column_supports_isolation_query(integration_bundle, seed_simulation, seed_report):
    tenant_a_state = seed_simulation(tenant_id="tenant-a")
    tenant_b_state = seed_simulation(tenant_id="tenant-b")
    seed_report(simulation_id=tenant_a_state.simulation_id, tenant_id="tenant-a", report_id="report_tenant_a")
    seed_report(simulation_id=tenant_b_state.simulation_id, tenant_id="tenant-b", report_id="report_tenant_b")

    with integration_bundle.session_factory() as session:
        report_ids = session.execute(
            select(reports.c.id).where(reports.c.tenant_id == "tenant-b")
        ).fetchall()

    assert [row[0] for row in report_ids] == ["report_tenant_b"]
