import json

from app.models.project import ProjectManager
from app.services.consumer.convergence_detector import ConvergenceDetector
from app.services.consumer.graph_builder import ConsumerGraphBuilder
from app.services.consumer.models import ConsumerBusinessBrief
from app.services.consumer.orchestrator import ConsumerSimulationOrchestrator
from app.services.consumer.persona_pack import load_default_persona_pack
from app.services.simulation_runner import RunnerStatus, SimulationRunner


def _snapshot(agent_id, attitude_label, propagation_events=None):
    return {
        "agent_id": agent_id,
        "attitude_label": attitude_label,
        "propagation_events": propagation_events or [],
    }


def test_should_stop_when_attitude_distribution_is_stable():
    detector = ConvergenceDetector(
        attitude_change_threshold=0.01,
        active_agent_ratio_threshold=0.0,
        min_rounds=1,
    )
    previous = [
        _snapshot("a1", "positive"),
        _snapshot("a2", "neutral"),
    ]
    current = [
        _snapshot("a1", "positive", [{"event_type": "discussion"}]),
        _snapshot("a2", "neutral"),
    ]

    result = detector.should_stop(
        round_index=1,
        current_state=current,
        previous_state=previous,
    )

    assert result["stop"] is True
    assert "attitude_change_rate" in result["reason"]
    assert result["metrics"]["attitude_change_rate"] == 0.0
    assert result["metrics"]["active_agent_ratio"] == 0.5


def test_should_stop_when_no_agents_have_propagation_events():
    detector = ConvergenceDetector(
        attitude_change_threshold=0.0,
        active_agent_ratio_threshold=0.01,
        min_rounds=1,
    )
    previous = [
        _snapshot("a1", "positive"),
        _snapshot("a2", "neutral"),
    ]
    current = [
        _snapshot("a1", "positive"),
        _snapshot("a2", "negative"),
    ]

    result = detector.should_stop(
        round_index=1,
        current_state=current,
        previous_state=previous,
    )

    assert result["stop"] is True
    assert "active_agent_ratio" in result["reason"]
    assert result["metrics"]["active_agent_ratio"] == 0.0


def test_should_not_stop_when_attitudes_shift_and_events_are_active():
    detector = ConvergenceDetector(
        attitude_change_threshold=0.01,
        active_agent_ratio_threshold=0.1,
        min_rounds=1,
    )
    previous = [
        _snapshot("a1", "positive"),
        _snapshot("a2", "positive"),
    ]
    current = [
        _snapshot("a1", "negative", [{"event_type": "risk_discovery"}]),
        _snapshot("a2", "neutral", [{"event_type": "question"}]),
    ]

    result = detector.should_stop(
        round_index=1,
        current_state=current,
        previous_state=previous,
    )

    assert result["stop"] is False
    assert result["reason"] == "not_converged"
    assert result["metrics"]["attitude_change_rate"] > 0.01
    assert result["metrics"]["active_agent_ratio"] == 1.0


def test_convergence_metrics_include_event_distribution_and_community_saturation():
    detector = ConvergenceDetector(
        attitude_change_threshold=0.0,
        active_agent_ratio_threshold=0.0,
        event_distribution_change_threshold=0.01,
        community_coverage_threshold=0.75,
        min_rounds=1,
    )
    previous = [
        {
            "agent_id": "a1",
            "attitude_label": "positive",
            "community": "core",
            "propagation_events": [{"consumer_event_type": "ASK_PROOF"}],
        },
        {
            "agent_id": "a2",
            "attitude_label": "positive",
            "community": "edge",
            "propagation_events": [{"consumer_event_type": "SHARE_TO_CHANNEL"}],
        },
    ]
    current = [
        {
            "agent_id": "a1",
            "attitude_label": "positive",
            "community": "core",
            "propagation_events": [{"consumer_event_type": "ASK_PROOF"}],
        },
        {
            "agent_id": "a2",
            "attitude_label": "positive",
            "community": "edge",
            "propagation_events": [{"consumer_event_type": "SHARE_TO_CHANNEL"}],
        },
    ]

    result = detector.should_stop(
        round_index=1,
        current_state=current,
        previous_state=previous,
    )

    assert result["stop"] is True
    assert "event_type_distribution_change_rate" in result["reason"]
    assert "community_coverage_ratio" in result["reason"]
    assert result["metrics"]["event_type_distribution_change_rate"] == 0.0
    assert result["metrics"]["community_coverage_ratio"] == 1.0
    assert result["metrics"]["current_event_type_distribution"] == {
        "ASK_PROOF": 0.5,
        "SHARE_TO_CHANNEL": 0.5,
    }
    assert result["metrics"]["active_community_count"] == 2
    assert result["metrics"]["total_community_count"] == 2


def test_orchestrator_convergence_check_surfaces_stop_reason():
    detector = ConvergenceDetector(
        attitude_change_threshold=0.01,
        active_agent_ratio_threshold=0.0,
        min_rounds=1,
    )
    orchestrator = ConsumerSimulationOrchestrator(convergence_detector=detector)

    result = orchestrator.check_convergence(
        round_index=2,
        current_state=[_snapshot("a1", "positive")],
        previous_state=[_snapshot("a1", "positive")],
    )

    assert result["stop"] is True
    assert result["reason"]
    assert "attitude_change_rate" in result["metrics"]


def test_simulation_runner_records_convergence_stop_reason(tmp_path, monkeypatch):
    projects_dir = tmp_path / "uploads" / "projects"
    simulations_dir = tmp_path / "uploads" / "simulations"
    monkeypatch.setattr(ProjectManager, "PROJECTS_DIR", str(projects_dir))
    monkeypatch.setattr(SimulationRunner, "RUN_STATE_DIR", str(simulations_dir))
    SimulationRunner._run_states.clear()
    SimulationRunner._monitor_threads.clear()

    class ImmediateThread:
        def __init__(self, target=None, args=None, daemon=None):
            self._target = target
            self._args = args or ()
            self.daemon = daemon

        def start(self):
            self._target(*self._args)

    monkeypatch.setattr("app.services.simulation_runner.threading.Thread", ImmediateThread)

    brief = ConsumerBusinessBrief(
        task_type="concept_test",
        product_concept_assets=["Yogurt pouch"],
        copy_material=["Low sugar."],
        claims=["Low sugar"],
        target_audience=["Busy commuters"],
        usage_scene=["Morning commute"],
        research_goal="Test convergence stop.",
    )
    project = ProjectManager.create_project(name="Convergence Stop Test")
    project.project_type = "consumer_test"
    project.graph_id = f"consumer_{project.project_id}"
    project.consumer_brief = brief.to_summary()
    ProjectManager.save_project(project)
    ProjectManager.save_consumer_graph_payload(
        project.project_id,
        ConsumerGraphBuilder().build(
            brief=brief,
            background_text="Background.",
            graph_id=project.graph_id,
        ),
    )

    sim_dir = simulations_dir / "sim_convergence"
    sim_dir.mkdir(parents=True, exist_ok=True)
    (sim_dir / "simulation_config.json").write_text(
        json.dumps(
            {
                "project_id": project.project_id,
                "project_type": "consumer_test",
                "consumer_mode": True,
                "pinned_brief_summary": "Pinned BusinessBrief Summary: yogurt pouch",
                "time_config": {"total_simulation_hours": 5, "minutes_per_round": 60},
                "convergence_config": {
                    "min_rounds": 1,
                    "active_agent_ratio_threshold": 1.0,
                    "attitude_change_threshold": 0.0,
                },
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    (sim_dir / "consumer_config.json").write_text(
        json.dumps({"research_findings": []}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    state = SimulationRunner.start_simulation("sim_convergence", max_rounds=5)

    assert state.runner_status == RunnerStatus.COMPLETED
    assert state.current_round == 1
    convergence = state.society_metrics["convergence"]
    assert convergence["stopped"] is True
    assert "active_agent_ratio" in convergence["reason"]
    assert convergence["metrics"]["active_agent_ratio"] == 0.0

    snapshot_lines = (sim_dir / "consumer_rounds.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(snapshot_lines) == len(load_default_persona_pack())
