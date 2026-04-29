from app.services.consumer.interview.focus_group_service import FocusGroupService
from app.services.consumer.interview.interview_models import ConsumerInterviewRequest
from app.services.simulation_manager import SimulationStatus
from test_representative_sampler import _write_society_fixture


class _Repo:
    def get_simulation(self, simulation_id):
        return type(
            "State",
            (),
            {
                "status": SimulationStatus.READY,
                "project_id": "project-1",
                "graph_id": "graph-1",
                "project_type": "consumer_test",
                "consumer_mode": True,
            },
        )()


def test_focus_group_runs_fixed_four_turns_and_writes_history(tmp_path):
    _write_society_fixture(tmp_path, simulation_id="sim-focus")
    service = FocusGroupService(base_dir=tmp_path, simulation_repo=_Repo())
    request = ConsumerInterviewRequest(
        simulation_id="sim-focus",
        topic="packaging proof and price resistance",
        questions=[],
        agent_ids=[],
        roles=["skeptic", "advocate"],
        mode="snapshot",
        max_agents=8,
        target_context={"claim": "low sugar", "branch_id": "branch-1"},
    )

    session = service.run_focus_group(request, moderator_goal="Find trust repair path")

    assert len(session.turns) == 4
    assert [turn["turn"] for turn in session.turns] == [1, 2, 3, 4]
    assert len(session.participant_cards) <= 8
    assert session.consensus
    assert session.disagreements
    assert session.next_what_if_experiments
    assert session.evidence_map
    history = service.history_store.list_focus_groups("sim-focus")
    assert history[0]["focus_group_id"] == session.focus_group_id
