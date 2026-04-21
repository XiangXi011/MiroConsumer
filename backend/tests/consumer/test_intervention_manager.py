import json
from pathlib import Path

import pytest

from app.services.consumer.intervention_manager import (
    ConsumerBranch,
    ConsumerIntervention,
    ConsumerInterventionManager,
    InterventionType,
)


def test_create_branch_persists_to_disk(tmp_path):
    branches_dir = tmp_path / "simulations" / "sim_001" / "branches"
    mgr = ConsumerInterventionManager(branches_dir=str(branches_dir))

    branch = mgr.create_branch(
        simulation_id="sim_001",
        name="Clarification branch",
        fork_round=2,
        description="Inject clarification at round 2",
    )

    assert branch.simulation_id == "sim_001"
    assert branch.fork_round == 2
    assert branch.parent_branch_id is None
    assert branch.status == "active"
    assert branch.branch_id != ""

    branch_file = branches_dir / branch.branch_id / "branch.json"
    assert branch_file.exists()
    loaded = json.loads(branch_file.read_text(encoding="utf-8"))
    assert loaded["name"] == "Clarification branch"


def test_list_branches_filters_by_simulation(tmp_path):
    branches_dir = tmp_path / "simulations"
    mgr = ConsumerInterventionManager(branches_dir=str(branches_dir))

    b1 = mgr.create_branch(simulation_id="sim_a", name="Branch A", fork_round=1)
    mgr.create_branch(simulation_id="sim_b", name="Branch B", fork_round=1)

    sim_a_branches = mgr.list_branches("sim_a")
    assert len(sim_a_branches) == 1
    assert sim_a_branches[0].branch_id == b1.branch_id


def test_get_branch_returns_none_for_missing(tmp_path):
    mgr = ConsumerInterventionManager(branches_dir=str(tmp_path))
    assert mgr.get_branch("sim_x", "missing_id") is None


def test_add_intervention_persists_and_lists(tmp_path):
    branches_dir = tmp_path / "simulations"
    mgr = ConsumerInterventionManager(branches_dir=str(branches_dir))

    branch = mgr.create_branch(simulation_id="sim_002", name="Test", fork_round=1)

    intervention = mgr.add_intervention(
        simulation_id="sim_002",
        branch_id=branch.branch_id,
        intervention_type=InterventionType.clarification_injection,
        payload={"message": "Clarify sugar claim"},
        target_round=2,
    )

    assert intervention.intervention_type == InterventionType.clarification_injection
    assert intervention.payload["message"] == "Clarify sugar claim"
    assert intervention.target_round == 2

    interventions = mgr.list_interventions("sim_002", branch_id=branch.branch_id)
    assert len(interventions) == 1
    assert interventions[0].intervention_id == intervention.intervention_id


def test_add_intervention_rejects_invalid_type(tmp_path):
    mgr = ConsumerInterventionManager(branches_dir=str(tmp_path))
    branch = mgr.create_branch(simulation_id="sim_003", name="Test", fork_round=1)

    with pytest.raises(ValueError, match="Unsupported intervention_type"):
        mgr.add_intervention(
            simulation_id="sim_003",
            branch_id=branch.branch_id,
            intervention_type="invalid_type",
            payload={},
        )


def test_intervention_type_enum_values():
    assert InterventionType.clarification_injection == "clarification_injection"
    assert InterventionType.revised_claim_injection == "revised_claim_injection"
    assert InterventionType.evidence_reveal == "evidence_reveal"


def test_build_comparison_context_with_base_branch(tmp_path):
    branches_dir = tmp_path / "simulations"
    mgr = ConsumerInterventionManager(branches_dir=str(branches_dir))

    base = mgr.create_branch(simulation_id="sim_004", name="Base", fork_round=0)
    branch = mgr.create_branch(
        simulation_id="sim_004",
        name="Variant",
        fork_round=1,
        parent_branch_id=base.branch_id,
    )

    mgr.add_intervention(
        simulation_id="sim_004",
        branch_id=branch.branch_id,
        intervention_type=InterventionType.evidence_reveal,
        payload={"evidence": "New study shows 0g sugar"},
        target_round=1,
    )

    # Write minimal base rounds artifact
    base_rounds_path = (
        branches_dir / "sim_004" / "branches" / base.branch_id / "rounds.jsonl"
    )
    base_rounds_path.parent.mkdir(parents=True, exist_ok=True)
    base_rounds_path.write_text(
        json.dumps(
            {"round_num": 0, "agent_id": "a1", "attitude_label": "neutral", "bucket": "question"}
        )
        + "\n",
        encoding="utf-8",
    )

    # Write branch rounds artifact
    branch_rounds_path = (
        branches_dir / "sim_004" / "branches" / branch.branch_id / "rounds.jsonl"
    )
    branch_rounds_path.parent.mkdir(parents=True, exist_ok=True)
    branch_rounds_path.write_text(
        json.dumps(
            {"round_num": 0, "agent_id": "a1", "attitude_label": "positive", "bucket": "resonance"}
        )
        + "\n",
        encoding="utf-8",
    )

    ctx = mgr.build_comparison_context("sim_004", branch.branch_id)

    assert ctx["branch_id"] == branch.branch_id
    assert ctx["base_branch_id"] == base.branch_id
    assert ctx["fork_round"] == 1
    assert len(ctx["interventions"]) == 1
    assert ctx["interventions"][0]["intervention_type"] == InterventionType.evidence_reveal
    assert "base_summary" in ctx
    assert "branch_summary" in ctx


def test_build_comparison_context_missing_branch(tmp_path):
    mgr = ConsumerInterventionManager(branches_dir=str(tmp_path))
    with pytest.raises(ValueError, match="Branch not found"):
        mgr.build_comparison_context("sim_x", "missing")


def test_branch_fork_metadata_round_n(tmp_path):
    mgr = ConsumerInterventionManager(branches_dir=str(tmp_path))
    branch = mgr.create_branch(simulation_id="sim_005", name="Fork at 3", fork_round=3)

    loaded = mgr.get_branch("sim_005", branch.branch_id)
    assert loaded is not None
    assert loaded.fork_round == 3
    assert loaded.parent_branch_id is None


def test_branch_with_parent_inherits_fork_round(tmp_path):
    mgr = ConsumerInterventionManager(branches_dir=str(tmp_path))
    parent = mgr.create_branch(simulation_id="sim_006", name="Parent", fork_round=2)
    child = mgr.create_branch(
        simulation_id="sim_006",
        name="Child",
        fork_round=4,
        parent_branch_id=parent.branch_id,
    )

    assert child.parent_branch_id == parent.branch_id
    assert child.fork_round == 4


def test_list_interventions_for_simulation_across_branches(tmp_path):
    mgr = ConsumerInterventionManager(branches_dir=str(tmp_path))
    b1 = mgr.create_branch(simulation_id="sim_007", name="B1", fork_round=1)
    b2 = mgr.create_branch(simulation_id="sim_007", name="B2", fork_round=1)

    mgr.add_intervention(
        simulation_id="sim_007",
        branch_id=b1.branch_id,
        intervention_type=InterventionType.revised_claim_injection,
        payload={"claim": "New claim"},
    )
    mgr.add_intervention(
        simulation_id="sim_007",
        branch_id=b2.branch_id,
        intervention_type=InterventionType.clarification_injection,
        payload={"message": "Clarify"},
    )

    all_interventions = mgr.list_interventions("sim_007")
    assert len(all_interventions) == 2


def test_load_branch_from_existing_file(tmp_path):
    branches_dir = tmp_path / "simulations"
    mgr = ConsumerInterventionManager(branches_dir=str(branches_dir))
    branch = mgr.create_branch(simulation_id="sim_008", name="Persisted", fork_round=1)

    # Create a fresh manager instance pointing at the same directory
    mgr2 = ConsumerInterventionManager(branches_dir=str(branches_dir))
    loaded = mgr2.get_branch("sim_008", branch.branch_id)

    assert loaded is not None
    assert loaded.name == "Persisted"
    assert loaded.fork_round == 1


def test_update_branch_status(tmp_path):
    mgr = ConsumerInterventionManager(branches_dir=str(tmp_path))
    branch = mgr.create_branch(simulation_id="sim_009", name="Running", fork_round=1)

    mgr.update_branch_status("sim_009", branch.branch_id, "completed")
    loaded = mgr.get_branch("sim_009", branch.branch_id)
    assert loaded is not None
    assert loaded.status == "completed"


def test_orchestrator_injects_intervention_into_prompt():
    from app.services.consumer.orchestrator import ConsumerSimulationOrchestrator

    orchestrator = ConsumerSimulationOrchestrator()
    intervention = ConsumerIntervention(
        intervention_id="i1",
        branch_id="b1",
        simulation_id="sim_1",
        intervention_type=InterventionType.clarification_injection,
        payload={"message": "Clarification: low sugar means less than 5g per serving"},
        target_round=1,
        created_at="2024-01-01T00:00:00",
    )

    prompt = orchestrator.build_round_prompt(
        round_num=1,
        agent_traits={"search_propensity": "high", "cognition_level": "high"},
        brief_summary="Pinned BusinessBrief Summary: yogurt pouch",
        visible_graph_nodes=[{"type": "ProductConcept", "text": "yogurt pouch"}],
        interventions=[intervention],
    )

    assert "Clarification: low sugar means less than 5g per serving" in prompt


def test_orchestrator_ignores_interventions_for_different_round():
    from app.services.consumer.orchestrator import ConsumerSimulationOrchestrator

    orchestrator = ConsumerSimulationOrchestrator()
    intervention = ConsumerIntervention(
        intervention_id="i1",
        branch_id="b1",
        simulation_id="sim_1",
        intervention_type=InterventionType.clarification_injection,
        payload={"message": "Round 2 only"},
        target_round=2,
        created_at="2024-01-01T00:00:00",
    )

    prompt = orchestrator.build_round_prompt(
        round_num=1,
        agent_traits={"search_propensity": "high", "cognition_level": "high"},
        brief_summary="Pinned BusinessBrief Summary: yogurt pouch",
        visible_graph_nodes=[{"type": "ProductConcept", "text": "yogurt pouch"}],
        interventions=[intervention],
    )

    assert "Round 2 only" not in prompt


def test_create_branch_rejects_missing_parent(tmp_path):
    mgr = ConsumerInterventionManager(branches_dir=str(tmp_path))
    with pytest.raises(ValueError, match="Parent branch not found"):
        mgr.create_branch(
            simulation_id="sim_010",
            name="Orphan",
            fork_round=1,
            parent_branch_id="missing_parent",
        )


def test_add_intervention_rejects_missing_branch(tmp_path):
    mgr = ConsumerInterventionManager(branches_dir=str(tmp_path))
    with pytest.raises(ValueError, match="Branch not found"):
        mgr.add_intervention(
            simulation_id="sim_011",
            branch_id="missing_branch",
            intervention_type=InterventionType.clarification_injection,
            payload={"message": "x"},
        )


def test_list_interventions_rejects_missing_branch(tmp_path):
    mgr = ConsumerInterventionManager(branches_dir=str(tmp_path))
    with pytest.raises(ValueError, match="Branch not found"):
        mgr.list_interventions("sim_012", branch_id="missing_branch")


def test_build_comparison_context_without_parent_uses_base_simulation(tmp_path, monkeypatch):
    from app.config import Config

    branches_dir = tmp_path / "simulations"
    monkeypatch.setattr(Config, "UPLOAD_FOLDER", str(tmp_path / "uploads"))
    mgr = ConsumerInterventionManager(branches_dir=str(branches_dir))

    branch = mgr.create_branch(simulation_id="sim_013", name="Variant", fork_round=1)

    # Seed base simulation rounds (not branch rounds)
    base_rounds_path = tmp_path / "uploads" / "simulations" / "sim_013" / "consumer_rounds.jsonl"
    base_rounds_path.parent.mkdir(parents=True, exist_ok=True)
    base_rounds_path.write_text(
        json.dumps(
            {"round_num": 0, "agent_id": "a1", "attitude_label": "neutral", "bucket": "question"}
        )
        + "\n",
        encoding="utf-8",
    )

    # Seed branch rounds (branches_dir is used directly as the branches root)
    branch_rounds_path = branches_dir / branch.branch_id / "rounds.jsonl"
    branch_rounds_path.parent.mkdir(parents=True, exist_ok=True)
    branch_rounds_path.write_text(
        json.dumps(
            {"round_num": 0, "agent_id": "a1", "attitude_label": "positive", "bucket": "resonance"}
        )
        + "\n",
        encoding="utf-8",
    )

    ctx = mgr.build_comparison_context("sim_013", branch.branch_id)

    assert ctx["branch_id"] == branch.branch_id
    assert ctx["base_branch_id"] is None
    assert ctx["base_summary"]["has_data"] is True
    assert ctx["branch_summary"]["has_data"] is True


def test_branch_run_status_round_trip(tmp_path):
    branches_dir = tmp_path / "simulations"
    mgr = ConsumerInterventionManager(branches_dir=str(branches_dir))
    branch = mgr.create_branch(simulation_id="sim_014", name="Test", fork_round=0)

    status = mgr.get_branch_run_status("sim_014", branch.branch_id)
    assert status["status"] == "idle"

    mgr.update_branch_run_status("sim_014", branch.branch_id, {"status": "running", "current_round": 2})
    status = mgr.get_branch_run_status("sim_014", branch.branch_id)
    assert status["status"] == "running"
    assert status["current_round"] == 2


def test_branch_run_status_file_isolated_per_branch(tmp_path):
    branches_dir = tmp_path / "simulations"
    mgr = ConsumerInterventionManager(branches_dir=str(branches_dir))
    b1 = mgr.create_branch(simulation_id="sim_015", name="B1", fork_round=0)
    b2 = mgr.create_branch(simulation_id="sim_015", name="B2", fork_round=0)

    mgr.update_branch_run_status("sim_015", b1.branch_id, {"status": "completed"})
    mgr.update_branch_run_status("sim_015", b2.branch_id, {"status": "failed"})

    assert mgr.get_branch_run_status("sim_015", b1.branch_id)["status"] == "completed"
    assert mgr.get_branch_run_status("sim_015", b2.branch_id)["status"] == "failed"
