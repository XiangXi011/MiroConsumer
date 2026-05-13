"""Core SPEC-P2-018 business-flow integration tests."""

from __future__ import annotations

from app.services.application.report_app_service import ReportAppService
from app.services.application.simulation_app_service import SimulationAppService
from app.services.consumer.society.population_models import ConsumerSocietySnapshot
from app.services.consumer.society.state_store import SocietyStateStore
from app.services.report_agent import ReportStatus
from app.services.simulation_manager import SimulationStatus


def test_brief_to_simulation_to_round_to_report_queue_flow(app_services, seed_project):
    brief = {
        "brief_id": "brief_full_flow",
        "product": "sparkling tea",
        "audience": "urban commuters",
        "objective": "measure purchase intent",
    }
    project = seed_project(project_id="proj_full_flow", brief=brief)

    simulation = SimulationAppService.create_simulation(
        {
            "project_id": project.project_id,
            "graph_id": project.graph_id,
            "tenant_id": project.tenant_id,
        }
    )
    state = app_services.bundle.simulation_repo.get_simulation(simulation["simulation_id"])
    state.status = SimulationStatus.RUNNING
    state.current_round = 1
    state.config_generated = True
    app_services.bundle.simulation_repo.save_simulation(state)

    store = SocietyStateStore(base_dir=app_services.uploads / "simulations")
    store.ensure_started(state.simulation_id)
    store.write_rounds(
        state.simulation_id,
        [
            ConsumerSocietySnapshot(
                simulation_id=state.simulation_id,
                run_id="base",
                round_index=1,
                agents_count=8,
                events=[{"type": "reaction", "sentiment": "curious"}],
                metrics={"awareness": 0.44},
            )
        ],
    )

    queued_report = ReportAppService.generate_report(state.simulation_id)

    assert simulation["project_id"] == project.project_id
    assert state.consumer_mode is True
    assert state.tenant_id == "tenant-a"
    assert store.read_rounds(state.simulation_id)[0]["round_index"] == 1
    assert queued_report["status"] == "generating"
    assert queued_report["report_id"].startswith("report_")
    assert app_services.executor.submissions[0]["kwargs"]["task_type"] == "generate_report"


def test_brief_payload_survives_project_repository_reload(integration_bundle, seed_project):
    project = seed_project(
        project_id="proj_brief_reload",
        brief={"brief_id": "brief_reload", "product": "coffee", "objective": "test packaging"},
    )

    reloaded = integration_bundle.project_repo.get_project(project.project_id)

    assert reloaded.consumer_brief["brief_id"] == "brief_reload"
    assert reloaded.consumer_brief["objective"] == "test packaging"
    assert reloaded.tenant_id == "tenant-a"


def test_simulation_start_persists_running_status(integration_bundle, seed_simulation):
    state = seed_simulation()

    state.status = SimulationStatus.RUNNING
    state.current_round = 0
    integration_bundle.simulation_repo.save_simulation(state)
    reloaded = integration_bundle.simulation_repo.get_simulation(state.simulation_id)

    assert reloaded.status == SimulationStatus.RUNNING
    assert reloaded.current_round == 0
    assert reloaded.project_type == "consumer_test"


def test_round_advance_persists_current_round_and_society_progress(app_services, seed_simulation):
    state = seed_simulation()
    store = SocietyStateStore(base_dir=app_services.uploads / "simulations")
    store.ensure_started(state.simulation_id)

    state.current_round = 2
    state.status = SimulationStatus.RUNNING
    app_services.bundle.simulation_repo.save_simulation(state)
    store.write_progress(
        state.simulation_id,
        {"current_round": 2, "status": "running", "degradation": False},
    )

    reloaded = app_services.bundle.simulation_repo.get_simulation(state.simulation_id)
    progress = store.read_progress(state.simulation_id)

    assert reloaded.current_round == 2
    assert progress["current_round"] == 2
    assert progress["status"] == "running"


def test_report_generation_deduplicates_completed_report(app_services, seed_simulation, seed_report):
    state = seed_simulation()
    completed = seed_report(simulation_id=state.simulation_id, report_id="report_existing")

    result = ReportAppService.generate_report(state.simulation_id, force_regenerate=False)

    assert result["already_generated"] is True
    assert result["report_id"] == completed.report_id
    assert result["status"] == ReportStatus.COMPLETED.value
    assert app_services.executor.submissions == []


def test_force_report_generation_queues_even_when_report_exists(app_services, seed_simulation, seed_report):
    state = seed_simulation()
    seed_report(simulation_id=state.simulation_id, report_id="report_force_existing")

    result = ReportAppService.generate_report(state.simulation_id, force_regenerate=True)

    assert result["already_generated"] is False
    assert result["status"] == "generating"
    assert len(app_services.executor.submissions) == 1


def test_branch_intervention_flow_attaches_intervention_to_round(integration_bundle, seed_simulation):
    state = seed_simulation()
    branch = integration_bundle.branch_repo.create_branch(
        simulation_id=state.simulation_id,
        name="Price test branch",
        fork_round=1,
        description="intervention branch for branch diff",
    )

    intervention = integration_bundle.branch_repo.add_intervention(
        state.simulation_id,
        branch.branch_id,
        "evidence_reveal",
        {"message": "discount shown"},
        target_round=2,
    )
    interventions = integration_bundle.branch_repo.list_interventions(state.simulation_id, branch.branch_id)

    assert intervention.target_round == 2
    assert interventions[0].payload["message"] == "discount shown"
    assert interventions[0].branch_id == branch.branch_id


def test_comparison_context_includes_branch_diff_inputs(integration_bundle, seed_simulation):
    state = seed_simulation()
    base = integration_bundle.branch_repo.create_branch(state.simulation_id, "Base", 0)
    variant = integration_bundle.branch_repo.create_branch(
        state.simulation_id,
        "Variant",
        1,
        parent_branch_id=base.branch_id,
    )
    integration_bundle.branch_repo.add_intervention(
        state.simulation_id,
        variant.branch_id,
        "revised_claim_injection",
        {"claim": "zero sugar"},
        target_round=1,
    )

    context = integration_bundle.branch_repo.build_comparison_context(state.simulation_id, variant.branch_id)

    assert context["branch_id"] == variant.branch_id
    assert context["base_branch_id"] == base.branch_id
    assert context["fork_round"] == 1
    assert context["interventions"][0]["payload"]["claim"] == "zero sugar"
