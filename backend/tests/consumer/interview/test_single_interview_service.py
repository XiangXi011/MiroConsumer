import pytest

from app.services.consumer.interview.interview_models import ConsumerInterviewRequest, LiveInterviewUnavailable
from app.services.consumer.interview.single_interview_service import SingleInterviewService
from app.services.simulation_manager import SimulationStatus
from test_representative_sampler import _write_society_fixture


class _Repo:
    def __init__(self, status=SimulationStatus.READY, project_type="consumer_test"):
        self.state = type(
            "State",
            (),
            {
                "status": status,
                "project_id": "project-1",
                "graph_id": "graph-1",
                "project_type": project_type,
                "consumer_mode": project_type == "consumer_test",
            },
        )()

    def get_simulation(self, simulation_id):
        return self.state


def test_snapshot_interview_builds_sanitized_answers_and_writes_history(tmp_path):
    _write_society_fixture(tmp_path, simulation_id="sim-interview")
    service = SingleInterviewService(base_dir=tmp_path, simulation_repo=_Repo())
    request = ConsumerInterviewRequest(
        simulation_id="sim-interview",
        topic="proof for low sugar",
        questions=["What proof would repair trust?"],
        agent_ids=["agent-skeptic"],
        roles=[],
        mode="snapshot",
        max_agents=1,
        target_context={"finding_id": "finding-1", "claim": "low sugar"},
    )

    result = service.run(request)

    assert result.mode == "snapshot"
    assert result.answers[0]["agent_id"] == "agent-skeptic"
    assert "What proof would repair trust?" in result.answers[0]["question"]
    prompt = result.answers[0]["prompt"]
    assert "persona segment" in prompt
    assert "role" in prompt
    assert "key quote" in prompt
    assert "attitude history" in prompt
    assert "consumer events" in prompt
    assert "evidence context" in prompt
    for forbidden in ["twitter", "reddit", "OASIS", "jsonl"]:
        assert forbidden.lower() not in prompt.lower()
    assert result.evidence_map["agent-skeptic"]["support_level"] in {
        "supported",
        "weak_support",
        "insufficient_support",
    }
    history = service.history_store.list_interviews("sim-interview")
    assert history[0]["interview_id"] == result.interview_id


def test_live_mode_without_running_environment_raises_conflict(tmp_path):
    _write_society_fixture(tmp_path, simulation_id="sim-live")
    service = SingleInterviewService(base_dir=tmp_path, simulation_repo=_Repo(status=SimulationStatus.READY))
    request = ConsumerInterviewRequest(
        simulation_id="sim-live",
        topic="live probe",
        questions=[],
        agent_ids=[],
        roles=["skeptic"],
        mode="live",
        max_agents=1,
        target_context={},
    )

    with pytest.raises(LiveInterviewUnavailable):
        service.run(request)


def test_auto_mode_falls_back_to_snapshot_when_environment_is_not_running(tmp_path):
    _write_society_fixture(tmp_path, simulation_id="sim-auto")
    service = SingleInterviewService(base_dir=tmp_path, simulation_repo=_Repo(status=SimulationStatus.READY))
    request = ConsumerInterviewRequest(
        simulation_id="sim-auto",
        topic="auto probe",
        questions=[],
        agent_ids=[],
        roles=["skeptic"],
        mode="auto",
        max_agents=1,
        target_context={},
    )

    result = service.run(request)

    assert result.mode == "snapshot"
    assert result.answers
