import json

from app.models.project import ProjectManager
from app.services.consumer.graph_builder import ConsumerGraphBuilder
from app.services.consumer.models import ConsumerBusinessBrief, GraphVisibility, ResearchFinding
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


def test_packaging_prompt_uses_task_aware_focus_line():
    prompt = ConsumerSimulationOrchestrator().build_round_prompt(
        round_num=0,
        agent_traits={"search_propensity": "low", "cognition_level": "medium"},
        brief_summary="Pinned BusinessBrief Summary: packaging test",
        visible_graph_nodes=[
            {"type": "PackagingCue", "visibility": "Initial", "text": "glass jar"},
        ],
        task_type="packaging_test",
    )

    assert "packaging design, shelf appeal, and trust cues" in prompt


def test_price_snapshot_carries_task_aware_prompt_focus():
    snapshot = ConsumerSimulationOrchestrator().build_round_snapshot(
        round_num=1,
        agent_traits={"search_propensity": "high", "cognition_level": "high"},
        brief_summary="Pinned BusinessBrief Summary: price test",
        visible_graph_nodes=[
            {"type": "PricePoint", "visibility": "Initial", "text": "$9.99"},
        ],
        agent_id="agent_1",
        agent_name="Agent 1",
        task_type="price_test",
    )

    assert "price perception, value trade-offs, and purchase intent" in snapshot["prompt"]


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
    (sim_dir / "consumer_config.json").write_text(
        json.dumps(
            {
                "research_findings": [
                    {
                        "finding_id": "r1",
                        "finding_type": "risk_signal",
                        "summary": "Sweetener concern",
                        "evidence_snippets": ["Sweetener concern"],
                        "source_label": "brief_background",
                        "visibility": "Restricted",
                        "confidence": 0.6,
                    }
                ],
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


def test_round_zero_prompt_hides_restricted_research_findings():
    prompt = ConsumerSimulationOrchestrator().build_round_prompt(
        round_num=0,
        agent_traits={"search_propensity": "high", "cognition_level": "high"},
        brief_summary="Pinned BusinessBrief Summary: yogurt pouch for breakfast",
        visible_graph_nodes=[
            {"type": "ProductConcept", "visibility": "Initial", "text": "yogurt pouch"},
        ],
        research_findings=[
            ResearchFinding(
                finding_id="r1",
                finding_type="risk_signal",
                summary="Sweetener concern",
                visibility=GraphVisibility.Restricted,
            ),
        ],
    )

    assert "Sweetener concern" not in prompt


def test_propagation_round_prompt_shows_restricted_findings_to_high_search_persona():
    prompt = ConsumerSimulationOrchestrator().build_round_prompt(
        round_num=2,
        agent_traits={"search_propensity": "high", "cognition_level": "high"},
        brief_summary="Pinned BusinessBrief Summary: yogurt pouch for breakfast",
        visible_graph_nodes=[
            {"type": "TalkingPoint", "visibility": "Propagation_Only", "text": "breakfast angle"},
        ],
        research_findings=[
            ResearchFinding(
                finding_id="r1",
                finding_type="risk_signal",
                summary="Sweetener concern",
                visibility=GraphVisibility.Restricted,
            ),
        ],
    )

    assert "Sweetener concern" in prompt


def test_propagation_round_prompt_hides_restricted_findings_from_low_search_persona():
    prompt = ConsumerSimulationOrchestrator().build_round_prompt(
        round_num=2,
        agent_traits={"search_propensity": "low", "cognition_level": "medium"},
        brief_summary="Pinned BusinessBrief Summary: yogurt pouch for breakfast",
        visible_graph_nodes=[
            {"type": "TalkingPoint", "visibility": "Propagation_Only", "text": "breakfast angle"},
        ],
        research_findings=[
            ResearchFinding(
                finding_id="r1",
                finding_type="risk_signal",
                summary="Sweetener concern",
                visibility=GraphVisibility.Restricted,
            ),
        ],
    )

    assert "Sweetener concern" not in prompt


def test_round_snapshot_tracks_visible_finding_ids():
    snapshot = ConsumerSimulationOrchestrator().build_round_snapshot(
        round_num=2,
        agent_traits={"search_propensity": "high", "cognition_level": "high"},
        brief_summary="Pinned BusinessBrief Summary: yogurt pouch for breakfast",
        visible_graph_nodes=[
            {"type": "TalkingPoint", "visibility": "Propagation_Only", "text": "breakfast angle"},
        ],
        agent_id="agent_1",
        agent_name="Test Agent",
        research_findings=[
            ResearchFinding(
                finding_id="r1",
                finding_type="risk_signal",
                summary="Sweetener concern",
                visibility=GraphVisibility.Restricted,
            ),
        ],
    )

    assert snapshot["visible_finding_ids"] == ["r1"]


def test_simulation_runner_round_zero_hides_restricted_findings_later_exposes_to_high_search(
    tmp_path, monkeypatch
):
    """Prove BLOCKER 2 fix: runner loads research findings and enforces visibility rules."""
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
    project = ProjectManager.create_project(name="Runner Research Findings Test")
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

    sim_dir = simulations_dir / "sim_test_research"
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
    # Write consumer_config with a mix of Initial and Restricted findings
    (sim_dir / "consumer_config.json").write_text(
        json.dumps(
            {
                "research_findings": [
                    {
                        "finding_id": "init_1",
                        "finding_type": "category_context",
                        "summary": "Initial finding visible to all",
                        "evidence_snippets": ["Initial"],
                        "source_label": "auto_enrich",
                        "visibility": "Initial",
                        "confidence": 0.7,
                    },
                    {
                        "finding_id": "rest_1",
                        "finding_type": "risk_signal",
                        "summary": "Restricted deep risk finding",
                        "evidence_snippets": ["Deep risk"],
                        "source_label": "brief_background",
                        "visibility": "Restricted",
                        "confidence": 0.6,
                    },
                ],
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    state = SimulationRunner.start_simulation("sim_test_research", max_rounds=2)
    assert state.runner_status == RunnerStatus.COMPLETED

    snapshot_lines = (sim_dir / "consumer_rounds.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(snapshot_lines) > 0

    # Parse all snapshots
    snapshots = [json.loads(line) for line in snapshot_lines]

    # Group by round
    round0 = [s for s in snapshots if s["round_num"] == 0]
    round1 = [s for s in snapshots if s["round_num"] == 1]

    # Round 0: no restricted findings visible to ANY persona
    for snap in round0:
        assert "Restricted deep risk" not in snap["prompt"]
        assert "rest_1" not in snap["visible_finding_ids"]

    # Round 0: Initial finding IS visible
    for snap in round0:
        assert "Initial finding visible to all" in snap["prompt"]
        assert "init_1" in snap["visible_finding_ids"]

    # Round 1: high-search/high-cognition personas see restricted findings
    # M01 = Care-driven urban mom (high search, high cognition)
    # M05 = Ingredient-first analyst (high search, high cognition)
    # M07 = Evidence-maximizing planner (high search, high cognition)
    high_search_snapshots = [
        s for s in round1
        if s["agent_id"] in ("M01", "M05", "M07")
    ]
    assert len(high_search_snapshots) > 0
    for snap in high_search_snapshots:
        assert "Restricted deep risk" in snap["prompt"]
        assert "rest_1" in snap["visible_finding_ids"]

    # Round 1: low-search personas do NOT see restricted findings
    # M03 = Traditional value caretaker (low search, medium cognition)
    # M08 = Budget-safe minimalist (low search, low cognition)
    low_search_snapshots = [
        s for s in round1
        if s["agent_id"] in ("M03", "M08")
    ]
    assert len(low_search_snapshots) > 0
    for snap in low_search_snapshots:
        assert "Restricted deep risk" not in snap["prompt"]
        assert "rest_1" not in snap["visible_finding_ids"]


def test_branch_run_writes_branch_rounds_artifact(tmp_path, monkeypatch):
    from app.config import Config
    from app.services.consumer.intervention_manager import ConsumerInterventionManager

    projects_dir = tmp_path / "uploads" / "projects"
    simulations_dir = tmp_path / "uploads" / "simulations"
    monkeypatch.setattr(ProjectManager, "PROJECTS_DIR", str(projects_dir))
    monkeypatch.setattr(SimulationRunner, "RUN_STATE_DIR", str(simulations_dir))
    monkeypatch.setattr(Config, "UPLOAD_FOLDER", str(tmp_path / "uploads"))
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
    project = ProjectManager.create_project(name="Branch Run Test")
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

    sim_dir = simulations_dir / "sim_branch_run"
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
    (sim_dir / "consumer_config.json").write_text(
        json.dumps({"research_findings": []}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    # Create a branch
    branches_dir = simulations_dir / "sim_branch_run" / "branches"
    int_mgr = ConsumerInterventionManager(branches_dir=str(branches_dir))
    branch = int_mgr.create_branch("sim_branch_run", name="Test Branch", fork_round=0)

    config = {
        "project_id": project.project_id,
        "consumer_mode": True,
        "pinned_brief_summary": "Pinned BusinessBrief Summary: yogurt pouch for breakfast",
        "time_config": {"total_simulation_hours": 1, "minutes_per_round": 30},
        "total_rounds": 2,
    }

    SimulationRunner.run_branch_simulation("sim_branch_run", branch.branch_id, config)

    branch_rounds_path = branches_dir / branch.branch_id / "rounds.jsonl"
    assert branch_rounds_path.exists()
    snapshot_lines = branch_rounds_path.read_text(encoding="utf-8").splitlines()
    assert len(snapshot_lines) > 0
    first_snapshot = json.loads(snapshot_lines[0])
    assert "Pinned BusinessBrief Summary" in first_snapshot["prompt"]
    assert first_snapshot["round_num"] == 0

    run_status = int_mgr.get_branch_run_status("sim_branch_run", branch.branch_id)
    assert run_status["status"] == "completed"


def test_branch_run_fork_round_seeds_from_base_simulation(tmp_path, monkeypatch):
    from app.config import Config
    from app.services.consumer.intervention_manager import ConsumerInterventionManager

    projects_dir = tmp_path / "uploads" / "projects"
    simulations_dir = tmp_path / "uploads" / "simulations"
    monkeypatch.setattr(ProjectManager, "PROJECTS_DIR", str(projects_dir))
    monkeypatch.setattr(SimulationRunner, "RUN_STATE_DIR", str(simulations_dir))
    monkeypatch.setattr(Config, "UPLOAD_FOLDER", str(tmp_path / "uploads"))
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
        research_goal="Test fork semantics.",
    )
    project = ProjectManager.create_project(name="Fork Test")
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

    sim_dir = simulations_dir / "sim_fork"
    sim_dir.mkdir(parents=True, exist_ok=True)
    (sim_dir / "simulation_config.json").write_text(
        json.dumps(
            {
                "project_id": project.project_id,
                "project_type": "consumer_test",
                "consumer_mode": True,
                "pinned_brief_summary": "Pinned BusinessBrief Summary: yogurt pouch",
                "time_config": {"total_simulation_hours": 1, "minutes_per_round": 30},
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

    # Write base simulation rounds (round 0 only)
    base_rounds_path = sim_dir / "consumer_rounds.jsonl"
    base_rounds_path.write_text(
        json.dumps(
            {"round_num": 0, "agent_id": "M01", "attitude_label": "neutral", "bucket": "question", "prompt": "base prompt"}
        )
        + "\n",
        encoding="utf-8",
    )

    # Create branch with fork_round=1 (no parent_branch_id)
    branches_dir = sim_dir / "branches"
    int_mgr = ConsumerInterventionManager(branches_dir=str(branches_dir))
    branch = int_mgr.create_branch("sim_fork", name="Fork Branch", fork_round=1)

    config = {
        "project_id": project.project_id,
        "consumer_mode": True,
        "pinned_brief_summary": "Pinned BusinessBrief Summary: yogurt pouch",
        "time_config": {"total_simulation_hours": 1, "minutes_per_round": 30},
        "total_rounds": 2,
    }

    SimulationRunner.run_branch_simulation("sim_fork", branch.branch_id, config)

    branch_rounds_path = branches_dir / branch.branch_id / "rounds.jsonl"
    assert branch_rounds_path.exists()
    snapshot_lines = branch_rounds_path.read_text(encoding="utf-8").splitlines()
    snapshots = [json.loads(line) for line in snapshot_lines]

    # Should include the seeded round 0 from base simulation
    round0 = [s for s in snapshots if s["round_num"] == 0]
    assert len(round0) == 1
    assert round0[0]["attitude_label"] == "neutral"

    # Should also include round 1 generated by the branch run (8 personas)
    round1 = [s for s in snapshots if s["round_num"] == 1]
    assert len(round1) == 8


def test_branch_run_interventions_appear_in_snapshot_prompt(tmp_path, monkeypatch):
    from app.config import Config
    from app.services.consumer.intervention_manager import (
        ConsumerInterventionManager,
        InterventionType,
    )

    projects_dir = tmp_path / "uploads" / "projects"
    simulations_dir = tmp_path / "uploads" / "simulations"
    monkeypatch.setattr(ProjectManager, "PROJECTS_DIR", str(projects_dir))
    monkeypatch.setattr(SimulationRunner, "RUN_STATE_DIR", str(simulations_dir))
    monkeypatch.setattr(Config, "UPLOAD_FOLDER", str(tmp_path / "uploads"))
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
        research_goal="Test interventions.",
    )
    project = ProjectManager.create_project(name="Intervention Test")
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

    sim_dir = simulations_dir / "sim_int"
    sim_dir.mkdir(parents=True, exist_ok=True)
    (sim_dir / "simulation_config.json").write_text(
        json.dumps(
            {
                "project_id": project.project_id,
                "project_type": "consumer_test",
                "consumer_mode": True,
                "pinned_brief_summary": "Pinned BusinessBrief Summary: yogurt pouch",
                "time_config": {"total_simulation_hours": 1, "minutes_per_round": 30},
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

    branches_dir = sim_dir / "branches"
    int_mgr = ConsumerInterventionManager(branches_dir=str(branches_dir))
    branch = int_mgr.create_branch("sim_int", name="Intervention Branch", fork_round=0)

    int_mgr.add_intervention(
        simulation_id="sim_int",
        branch_id=branch.branch_id,
        intervention_type=InterventionType.clarification_injection,
        payload={"message": "Clarify: less than 5g sugar"},
        target_round=0,
    )

    config = {
        "project_id": project.project_id,
        "consumer_mode": True,
        "pinned_brief_summary": "Pinned BusinessBrief Summary: yogurt pouch",
        "time_config": {"total_simulation_hours": 1, "minutes_per_round": 30},
        "total_rounds": 1,
    }

    SimulationRunner.run_branch_simulation("sim_int", branch.branch_id, config)

    branch_rounds_path = branches_dir / branch.branch_id / "rounds.jsonl"
    snapshot_lines = branch_rounds_path.read_text(encoding="utf-8").splitlines()
    snapshots = [json.loads(line) for line in snapshot_lines]

    # All round 0 snapshots should include the intervention
    for snap in snapshots:
        if snap["round_num"] == 0:
            assert "Clarify: less than 5g sugar" in snap["prompt"]


def test_branch_run_fork_from_parent_branch(tmp_path, monkeypatch):
    from app.config import Config
    from app.services.consumer.intervention_manager import ConsumerInterventionManager

    projects_dir = tmp_path / "uploads" / "projects"
    simulations_dir = tmp_path / "uploads" / "simulations"
    monkeypatch.setattr(ProjectManager, "PROJECTS_DIR", str(projects_dir))
    monkeypatch.setattr(SimulationRunner, "RUN_STATE_DIR", str(simulations_dir))
    monkeypatch.setattr(Config, "UPLOAD_FOLDER", str(tmp_path / "uploads"))
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
        research_goal="Test parent fork.",
    )
    project = ProjectManager.create_project(name="Parent Fork Test")
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

    sim_dir = simulations_dir / "sim_parent_fork"
    sim_dir.mkdir(parents=True, exist_ok=True)
    (sim_dir / "simulation_config.json").write_text(
        json.dumps(
            {
                "project_id": project.project_id,
                "project_type": "consumer_test",
                "consumer_mode": True,
                "pinned_brief_summary": "Pinned BusinessBrief Summary: yogurt pouch",
                "time_config": {"total_simulation_hours": 1, "minutes_per_round": 30},
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

    branches_dir = sim_dir / "branches"
    int_mgr = ConsumerInterventionManager(branches_dir=str(branches_dir))
    parent = int_mgr.create_branch("sim_parent_fork", name="Parent", fork_round=0)

    # Write parent branch rounds
    parent_rounds_path = branches_dir / parent.branch_id / "rounds.jsonl"
    parent_rounds_path.parent.mkdir(parents=True, exist_ok=True)
    parent_rounds_path.write_text(
        json.dumps(
            {"round_num": 0, "agent_id": "M01", "attitude_label": "positive", "bucket": "resonance"}
        )
        + "\n",
        encoding="utf-8",
    )

    child = int_mgr.create_branch(
        "sim_parent_fork", name="Child", fork_round=1, parent_branch_id=parent.branch_id
    )

    config = {
        "project_id": project.project_id,
        "consumer_mode": True,
        "pinned_brief_summary": "Pinned BusinessBrief Summary: yogurt pouch",
        "time_config": {"total_simulation_hours": 1, "minutes_per_round": 30},
        "total_rounds": 2,
    }

    SimulationRunner.run_branch_simulation("sim_parent_fork", child.branch_id, config)

    child_rounds_path = branches_dir / child.branch_id / "rounds.jsonl"
    snapshot_lines = child_rounds_path.read_text(encoding="utf-8").splitlines()
    snapshots = [json.loads(line) for line in snapshot_lines]

    # Should seed round 0 from parent branch
    round0 = [s for s in snapshots if s["round_num"] == 0]
    assert len(round0) == 1
    assert round0[0]["attitude_label"] == "positive"

    # Should generate round 1 (8 personas)
    round1 = [s for s in snapshots if s["round_num"] == 1]
    assert len(round1) == 8


def test_branch_fork_state_initialization_carries_resonance_state(tmp_path, monkeypatch):
    """Seeded resonance rounds should reconstruct agent state so that social
    reinforcement count affects generated branch behavior.

    M01 is seeded with 3 rounds of bucket='resonance' (social_reinforcement=3).
    When the branch generates round 3 with non-risk visible nodes, M01's
    medium herd tendency would normally yield neutral/question, but the
    carried state flips it to positive/resonance.  M03 (also medium herd,
    no seeded state) remains neutral/question, proving the state caused
    the difference.
    """
    from app.config import Config
    from app.services.consumer.intervention_manager import ConsumerInterventionManager

    projects_dir = tmp_path / "uploads" / "projects"
    simulations_dir = tmp_path / "uploads" / "simulations"
    monkeypatch.setattr(ProjectManager, "PROJECTS_DIR", str(projects_dir))
    monkeypatch.setattr(SimulationRunner, "RUN_STATE_DIR", str(simulations_dir))
    monkeypatch.setattr(Config, "UPLOAD_FOLDER", str(tmp_path / "uploads"))
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
        research_goal="Test fork state carry.",
    )
    project = ProjectManager.create_project(name="Fork State Test")
    project.project_type = "consumer_test"
    project.graph_id = f"consumer_{project.project_id}"
    project.consumer_brief = brief.to_summary()
    ProjectManager.save_project(project)
    # Use "Background." so no RiskPoint nodes are created in the graph
    ProjectManager.save_consumer_graph_payload(
        project.project_id,
        ConsumerGraphBuilder().build(
            brief=brief,
            background_text="Background.",
            graph_id=project.graph_id,
        ),
    )

    sim_dir = simulations_dir / "sim_fork_state"
    sim_dir.mkdir(parents=True, exist_ok=True)
    (sim_dir / "simulation_config.json").write_text(
        json.dumps(
            {
                "project_id": project.project_id,
                "project_type": "consumer_test",
                "consumer_mode": True,
                "pinned_brief_summary": "Pinned BusinessBrief Summary: yogurt pouch",
                "time_config": {"total_simulation_hours": 1, "minutes_per_round": 30},
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

    # Write 3 base rounds for M01 with resonance (builds social_reinforcement_count=3)
    base_lines = []
    for r in range(3):
        base_lines.append(
            json.dumps(
                {
                    "round_num": r,
                    "agent_id": "M01",
                    "attitude_label": "positive",
                    "bucket": "resonance",
                    "engagement": 5 + r,
                    "visible_nodes": [
                        {"type": "ProductConcept", "visibility": "Initial", "text": "yogurt pouch"}
                    ],
                }
            )
        )
    base_rounds_path = sim_dir / "consumer_rounds.jsonl"
    base_rounds_path.write_text("\n".join(base_lines) + "\n", encoding="utf-8")

    # Create branch with fork_round=3
    branches_dir = sim_dir / "branches"
    int_mgr = ConsumerInterventionManager(branches_dir=str(branches_dir))
    branch = int_mgr.create_branch("sim_fork_state", name="State Branch", fork_round=3)

    config = {
        "project_id": project.project_id,
        "consumer_mode": True,
        "pinned_brief_summary": "Pinned BusinessBrief Summary: yogurt pouch",
        "time_config": {"total_simulation_hours": 1, "minutes_per_round": 30},
        "total_rounds": 4,
    }

    SimulationRunner.run_branch_simulation("sim_fork_state", branch.branch_id, config)

    child_rounds_path = branches_dir / branch.branch_id / "rounds.jsonl"
    snapshot_lines = child_rounds_path.read_text(encoding="utf-8").splitlines()
    snapshots = [json.loads(line) for line in snapshot_lines]

    # Seeded rounds 0-2 for M01 should be present
    round0 = [s for s in snapshots if s["round_num"] == 0]
    assert len(round0) == 1
    assert round0[0]["agent_id"] == "M01"
    assert round0[0]["bucket"] == "resonance"

    # Generated round 3 should have 8 snapshots (one per persona)
    round3 = [s for s in snapshots if s["round_num"] == 3]
    assert len(round3) == 8

    # M01 (medium herd, 3 seeded resonance rounds) should flip to resonance
    # because social_reinforcement_count=3 pushes neutral/question → positive/resonance
    m01_snap = next(s for s in round3 if s["agent_id"] == "M01")
    assert m01_snap["bucket"] == "resonance", (
        f"M01 should carry resonance from seeded state, got bucket={m01_snap['bucket']!r}"
    )

    # M03 (also medium herd, no seeded state) should remain question,
    # proving the state reconstruction (not herd tendency) caused M01's resonance.
    m03_snap = next(s for s in round3 if s["agent_id"] == "M03")
    assert m03_snap["bucket"] == "question", (
        f"M03 without seeded state should be question, got bucket={m03_snap['bucket']!r}"
    )

    # At minimum: M01's generated round should differ from M03's, showing
    # that prior state reconstruction did not start empty for M01.
    assert m01_snap["attitude_label"] != m03_snap["attitude_label"], (
        "M01 and M03 (both medium herd) should diverge because M01 carries seeded state"
    )
