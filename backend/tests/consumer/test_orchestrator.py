import json

from app.models.project import ProjectManager
from app.services.consumer.graph_builder import ConsumerGraphBuilder
from app.services.consumer.models import ConsumerBusinessBrief
from app.services.consumer.orchestrator import ConsumerSimulationOrchestrator
from app.services.simulation_runner import RunnerStatus, SimulationRunner


def test_round_zero_prompt_pins_brief_and_hides_deep_risk():
    prompt = ConsumerSimulationOrchestrator().build_round_prompt(
        round_num=0,
        agent_traits={"search_propensity": "low", "cognition_level": "medium"},
        brief_summary="Pinned BusinessBrief Summary: yogurt pouch for breakfast",
        visible_graph_nodes=[
            {"type": "ProductConcept", "visibility": "Initial", "text": "yogurt pouch"},
            {"type": "RiskPoint", "visibility": "Restricted", "text": "ingredient controversy"},
        ],
    )

    assert "Pinned BusinessBrief Summary" in prompt
    assert "yogurt pouch" in prompt
    assert "ingredient controversy" not in prompt


def test_propagation_round_allows_high_search_agents_to_see_deep_nodes():
    prompt = ConsumerSimulationOrchestrator().build_round_prompt(
        round_num=2,
        agent_traits={"search_propensity": "high", "cognition_level": "high"},
        brief_summary="Pinned BusinessBrief Summary: yogurt pouch for breakfast",
        visible_graph_nodes=[
            {"type": "RiskPoint", "visibility": "Propagation_Only", "text": "sweetener debate"},
            {"type": "RiskPoint", "visibility": "Restricted", "text": "manufacturing controversy"},
        ],
    )

    assert "sweetener debate" in prompt
    assert "manufacturing controversy" in prompt


def test_persist_round_snapshot_writes_jsonl(tmp_path):
    output_path = tmp_path / "consumer_rounds.jsonl"
    orchestrator = ConsumerSimulationOrchestrator(output_path=output_path)

    orchestrator.persist_round_snapshot(
        {
            "round_num": 0,
            "agent_id": "persona_a",
            "quote": "This feels like a practical breakfast fix.",
        }
    )

    lines = output_path.read_text(encoding="utf-8").splitlines()

    assert len(lines) == 1
    assert json.loads(lines[0])["quote"].startswith("This feels like")


def test_simulation_runner_consumer_branch_writes_round_snapshots(tmp_path, monkeypatch):
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
        product_concept_assets=["Yogurt pouch for breakfast commuters"],
        copy_material=["Low sugar and easy to carry."],
        claims=["Low sugar"],
        target_audience=["Busy young professionals"],
        usage_scene=["Morning commute"],
        research_goal="Understand if commuters will discuss the concept positively.",
    )
    project = ProjectManager.create_project(name="Runner Consumer Test")
    project.project_type = "consumer_test"
    project.graph_id = f"consumer_{project.project_id}"
    project.consumer_brief = brief.to_summary()
    ProjectManager.save_project(project)
    ProjectManager.save_consumer_graph_payload(
        project.project_id,
        ConsumerGraphBuilder().build(
            brief=brief,
            background_text="Some creator circles mention a sweetener debate.",
            graph_id=project.graph_id,
        ),
    )

    sim_dir = simulations_dir / "sim_test_runner"
    sim_dir.mkdir(parents=True, exist_ok=True)
    (sim_dir / "simulation_config.json").write_text(
        json.dumps(
            {
                "project_id": project.project_id,
                "project_type": "consumer_test",
                "consumer_mode": True,
                "pinned_brief_summary": "Pinned BusinessBrief Summary: yogurt pouch for breakfast",
                "time_config": {"total_simulation_hours": 1, "minutes_per_round": 30},
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    state = SimulationRunner.start_simulation("sim_test_runner", max_rounds=2)

    assert state.runner_status == RunnerStatus.COMPLETED
    snapshot_lines = (sim_dir / "consumer_rounds.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(snapshot_lines) > 0
    first_snapshot = json.loads(snapshot_lines[0])
    assert "Pinned BusinessBrief Summary" in first_snapshot["prompt"]
    assert first_snapshot["round_num"] == 0
