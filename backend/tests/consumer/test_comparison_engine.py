import json
from pathlib import Path

import pytest

from app.services.consumer.comparison_engine import (
    _comparisons_dir,
    compare_branch_vs_base,
    compare_project_vs_project,
    compare_run_vs_run,
    create_comparison,
    delete_comparison,
    get_comparison,
    list_comparisons,
)
from app.services.consumer.intervention_manager import ConsumerInterventionManager


def _write_consumer_rounds(base_path: Path, simulation_id: str, branch_id: str | None = None, events: list | None = None):
    if branch_id:
        rounds_path = base_path / "simulations" / simulation_id / "branches" / branch_id / "rounds.jsonl"
    else:
        rounds_path = base_path / "simulations" / simulation_id / "consumer_rounds.jsonl"
    rounds_path.parent.mkdir(parents=True, exist_ok=True)
    default_events = [
        {
            "round_num": 0,
            "agent_id": "persona_a",
            "attitude_label": "positive",
            "bucket": "resonance",
            "engagement": 9,
            "quote": "Great idea.",
            "visible_nodes": [{"type": "ProductConcept", "text": "breakfast yogurt pouch"}],
        },
        {
            "round_num": 1,
            "agent_id": "persona_a",
            "attitude_label": "negative",
            "bucket": "risk",
            "engagement": 8,
            "quote": "I don't trust that claim.",
            "visible_nodes": [{"type": "RiskPoint", "text": "sweetener debate"}],
        },
    ]
    use_events = events if events is not None else default_events
    rounds_path.write_text(
        "\n".join(json.dumps(e, ensure_ascii=False) for e in use_events) + "\n",
        encoding="utf-8",
    )


def _write_consumer_config(base_path: Path, simulation_id: str, findings: list | None = None):
    config_path = base_path / "simulations" / simulation_id / "consumer_config.json"
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config = {
        "research_findings": findings or [
            {
                "finding_id": "f1",
                "finding_type": "risk_signal",
                "summary": "Sweetener concern",
                "evidence_snippets": ["Sweetener concern"],
                "source_label": "brief_background",
                "visibility": "Restricted",
                "confidence": 0.6,
            }
        ],
        "research_snapshot": {"snapshot_id": "snap_1", "finding_count": 1},
        "retrieval_traces": [],
    }
    config_path.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")


def test_compare_run_vs_run_produces_snapshot(tmp_path):
    sim_left = "sim_left"
    sim_right = "sim_right"
    _write_consumer_rounds(tmp_path, sim_left)
    _write_consumer_rounds(tmp_path, sim_right)
    # Phase 6J: evidence must be semantically aligned, not merely long.
    _write_consumer_config(tmp_path, sim_left, findings=[
        {"finding_id": "f1", "finding_type": "category_context", "summary": "Sugar concern", "source_label": "brief_background", "evidence_snippets": ["Sugar concern evidence detail"]},
    ])
    _write_consumer_config(tmp_path, sim_right, findings=[
        {"finding_id": "f2", "finding_type": "category_context", "summary": "Price concern", "source_label": "public_web", "evidence_snippets": ["Price concern evidence detail"]},
    ])

    snapshot = compare_run_vs_run(sim_left, sim_right, upload_root=str(tmp_path))

    assert snapshot["mode"] == "run_vs_run"
    assert "comparison_id" in snapshot
    assert snapshot["left"]["kind"] == "run"
    assert snapshot["right"]["kind"] == "run"
    assert "acceptance_positive" in snapshot["left"]
    assert "acceptance_positive" in snapshot["right"]
    assert "evidence_backed_divergences" in snapshot
    assert len(snapshot["evidence_backed_divergences"]) > 0
    assert "acceptance_delta_pp" in snapshot


def test_compare_branch_vs_base_produces_snapshot(tmp_path):
    simulation_id = "sim_branch_cmp"
    mgr = ConsumerInterventionManager(branches_dir=str(tmp_path / "simulations" / simulation_id / "branches"))
    base_branch = mgr.create_branch(simulation_id, name="Base", fork_round=0)
    variant_branch = mgr.create_branch(simulation_id, name="Variant", fork_round=1, parent_branch_id=base_branch.branch_id)

    _write_consumer_rounds(tmp_path, simulation_id, branch_id=base_branch.branch_id, events=[
        {"round_num": 0, "agent_id": "a1", "attitude_label": "neutral", "bucket": "question", "engagement": 5, "quote": "Hmm.", "visible_nodes": []},
    ])
    _write_consumer_rounds(tmp_path, simulation_id, branch_id=variant_branch.branch_id, events=[
        {"round_num": 0, "agent_id": "a1", "attitude_label": "positive", "bucket": "resonance", "engagement": 9, "quote": "Love it.", "visible_nodes": []},
    ])
    _write_consumer_config(tmp_path, simulation_id)

    snapshot = compare_branch_vs_base(simulation_id, variant_branch.branch_id, upload_root=str(tmp_path))

    assert snapshot["mode"] == "branch_vs_base"
    assert snapshot["left"]["kind"] == "branch"
    assert snapshot["right"]["kind"] == "branch"
    assert snapshot["right"]["id"] == variant_branch.branch_id
    assert "acceptance_positive" in snapshot["left"]
    assert "acceptance_positive" in snapshot["right"]


def test_compare_project_vs_project_produces_snapshot(tmp_path):
    left_project = "proj_left"
    right_project = "proj_right"

    from app.services.consumer.models import ResearchFinding, GraphVisibility
    from app.services.consumer.project_research_persistence import persist_findings

    # Phase 6J: evidence must be semantically aligned, not merely long.
    persist_findings(left_project, [
        ResearchFinding(finding_id="f1", finding_type="category_context", summary="Sugar concern", visibility=GraphVisibility.Propagation_Only, source_label="brief_background", evidence_snippets=["Sugar concern evidence detail"]),
    ], upload_root=str(tmp_path))
    persist_findings(right_project, [
        ResearchFinding(finding_id="f2", finding_type="category_context", summary="Market shift", visibility=GraphVisibility.Propagation_Only, source_label="public_web", evidence_snippets=["Market shift evidence detail"]),
    ], upload_root=str(tmp_path))

    snapshot = compare_project_vs_project(left_project, right_project, upload_root=str(tmp_path))

    assert snapshot["mode"] == "project_vs_project"
    assert snapshot["left"]["kind"] == "project"
    assert snapshot["right"]["kind"] == "project"
    assert left_project in snapshot["project_ids"]
    assert right_project in snapshot["project_ids"]
    assert len(snapshot["evidence_backed_divergences"]) > 0


def test_create_comparison_persists_file(tmp_path):
    sim_left = "sim_persist_left"
    sim_right = "sim_persist_right"
    _write_consumer_rounds(tmp_path, sim_left)
    _write_consumer_rounds(tmp_path, sim_right)
    _write_consumer_config(tmp_path, sim_left)
    _write_consumer_config(tmp_path, sim_right)

    snapshot = create_comparison(
        mode="run_vs_run",
        left_simulation_id=sim_left,
        right_simulation_id=sim_right,
        upload_root=str(tmp_path),
    )

    comp_id = snapshot["comparison_id"]
    path = _comparisons_dir(str(tmp_path)) / f"{comp_id}.json"
    assert path.exists()
    loaded = json.loads(path.read_text(encoding="utf-8"))
    assert loaded["comparison_id"] == comp_id


def test_list_comparisons_includes_project_vs_project(tmp_path):
    left_project = "proj_list_left"
    right_project = "proj_list_right"

    from app.services.consumer.models import ResearchFinding, GraphVisibility
    from app.services.consumer.project_research_persistence import persist_findings

    persist_findings(left_project, [
        ResearchFinding(finding_id="f1", finding_type="risk_signal", summary="A", visibility=GraphVisibility.Propagation_Only, source_label="brief_background"),
    ], upload_root=str(tmp_path))
    persist_findings(right_project, [
        ResearchFinding(finding_id="f2", finding_type="trend_signal", summary="B", visibility=GraphVisibility.Propagation_Only, source_label="public_web"),
    ], upload_root=str(tmp_path))

    snapshot = create_comparison(
        mode="project_vs_project",
        left_project_id=left_project,
        right_project_id=right_project,
        upload_root=str(tmp_path),
    )

    items = list_comparisons(left_project, upload_root=str(tmp_path))
    assert len(items) == 1
    assert items[0]["comparison_id"] == snapshot["comparison_id"]


def test_get_comparison_returns_data(tmp_path):
    sim_left = "sim_get_left"
    sim_right = "sim_get_right"
    _write_consumer_rounds(tmp_path, sim_left)
    _write_consumer_rounds(tmp_path, sim_right)
    _write_consumer_config(tmp_path, sim_left)
    _write_consumer_config(tmp_path, sim_right)

    snapshot = create_comparison(
        mode="run_vs_run",
        left_simulation_id=sim_left,
        right_simulation_id=sim_right,
        upload_root=str(tmp_path),
    )

    fetched = get_comparison(snapshot["comparison_id"], upload_root=str(tmp_path))
    assert fetched is not None
    assert fetched["comparison_id"] == snapshot["comparison_id"]


def test_get_comparison_missing_returns_none(tmp_path):
    assert get_comparison("cmp_missing", upload_root=str(tmp_path)) is None


def test_delete_comparison_removes_file(tmp_path):
    sim_left = "sim_del_left"
    sim_right = "sim_del_right"
    _write_consumer_rounds(tmp_path, sim_left)
    _write_consumer_rounds(tmp_path, sim_right)
    _write_consumer_config(tmp_path, sim_left)
    _write_consumer_config(tmp_path, sim_right)

    snapshot = create_comparison(
        mode="run_vs_run",
        left_simulation_id=sim_left,
        right_simulation_id=sim_right,
        upload_root=str(tmp_path),
    )

    assert delete_comparison(snapshot["comparison_id"], upload_root=str(tmp_path)) is True
    assert get_comparison(snapshot["comparison_id"], upload_root=str(tmp_path)) is None


def test_delete_comparison_missing_returns_false(tmp_path):
    assert delete_comparison("cmp_noexist", upload_root=str(tmp_path)) is False


def test_create_comparison_invalid_mode_raises(tmp_path):
    with pytest.raises(ValueError, match="Unsupported comparison mode"):
        create_comparison(mode="invalid_mode", upload_root=str(tmp_path))


def test_create_comparison_run_vs_run_missing_id_raises(tmp_path):
    with pytest.raises(ValueError, match="run_vs_run requires left_simulation_id and right_simulation_id"):
        create_comparison(mode="run_vs_run", left_simulation_id="s1", upload_root=str(tmp_path))


def _write_consumer_rounds_with_acceptance(base_path: Path, simulation_id: str, branch_id: str | None = None, attitude_labels: list[str] | None = None):
    """Write rounds so post_propagation_acceptance can be predicted from attitudes."""
    events = []
    for i, label in enumerate(attitude_labels or ["positive", "negative", "positive"]):
        events.append({
            "round_num": i,
            "agent_id": f"agent_{i}",
            "attitude_label": label,
            "bucket": "resonance" if label == "positive" else "risk",
            "engagement": 5,
            "quote": "x",
            "visible_nodes": [],
        })
    _write_consumer_rounds(base_path, simulation_id, branch_id, events)


def test_acceptance_delta_pp_is_percentage_points_run_vs_run(tmp_path):
    sim_left = "sim_pp_left"
    sim_right = "sim_pp_right"
    # Left: 1 positive out of 2 = 0.5
    _write_consumer_rounds_with_acceptance(tmp_path, sim_left, attitude_labels=["positive", "negative"])
    # Right: 2 positive out of 2 = 1.0
    _write_consumer_rounds_with_acceptance(tmp_path, sim_right, attitude_labels=["positive", "positive"])
    _write_consumer_config(tmp_path, sim_left)
    _write_consumer_config(tmp_path, sim_right)

    snapshot = compare_run_vs_run(sim_left, sim_right, upload_root=str(tmp_path))

    # 1.0 - 0.5 = 0.5 ratio → 50.0 percentage points
    assert snapshot["acceptance_delta_pp"] == 50.0


def test_acceptance_delta_pp_is_percentage_points_branch_vs_base(tmp_path):
    simulation_id = "sim_branch_pp"
    mgr = ConsumerInterventionManager(branches_dir=str(tmp_path / "simulations" / simulation_id / "branches"))
    base_branch = mgr.create_branch(simulation_id, name="Base", fork_round=0)
    variant_branch = mgr.create_branch(simulation_id, name="Variant", fork_round=1, parent_branch_id=base_branch.branch_id)

    # Base: 1 positive out of 2 = 0.5
    _write_consumer_rounds_with_acceptance(tmp_path, simulation_id, base_branch.branch_id, attitude_labels=["positive", "negative"])
    # Variant: 2 positive out of 2 = 1.0
    _write_consumer_rounds_with_acceptance(tmp_path, simulation_id, variant_branch.branch_id, attitude_labels=["positive", "positive"])
    _write_consumer_config(tmp_path, simulation_id)

    snapshot = compare_branch_vs_base(simulation_id, variant_branch.branch_id, upload_root=str(tmp_path))

    # 1.0 - 0.5 = 0.5 ratio → 50.0 percentage points
    assert snapshot["acceptance_delta_pp"] == 50.0


def test_acceptance_delta_pp_negative_when_right_lower(tmp_path):
    sim_left = "sim_pp_neg_left"
    sim_right = "sim_pp_neg_right"
    # Left: 2 positive out of 2 = 1.0
    _write_consumer_rounds_with_acceptance(tmp_path, sim_left, attitude_labels=["positive", "positive"])
    # Right: 0 positive out of 2 = 0.0
    _write_consumer_rounds_with_acceptance(tmp_path, sim_right, attitude_labels=["negative", "negative"])
    _write_consumer_config(tmp_path, sim_left)
    _write_consumer_config(tmp_path, sim_right)

    snapshot = compare_run_vs_run(sim_left, sim_right, upload_root=str(tmp_path))

    # 0.0 - 1.0 = -1.0 ratio → -100.0 percentage points
    assert snapshot["acceptance_delta_pp"] == -100.0


# Phase 5C: Evidence gatekeeping in comparison engine tests

def test_side_confidence_downweighted_when_findings_blocked(tmp_path):
    from app.services.consumer.comparison_engine import _side_confidence_from_findings

    findings = [
        {
            "finding_id": "f1",
            "finding_type": "category_context",
            "summary": "Sugar concern",
            "evidence_snippets": ["Sugar concern evidence detail"],
            "source_label": "brief_background",
            "confidence": 0.9,
        },
        {
            "finding_id": "f2",
            "finding_type": "risk_signal",
            "summary": "Price concern",
            # No evidence snippets - will be blocked
        },
    ]
    result = _side_confidence_from_findings(findings)
    assert "evidence_gatekeeping_summary" in result
    assert result["evidence_gatekeeping_summary"]["blocked_count"] == 1
    assert result["evidence_gatekeeping_summary"]["downgraded_count"] == 1
    # Should be down-weighted due to blocked finding penalty
    assert result["confidence_score"] < 0.9
    assert any("blocked_findings_penalty" in r for r in result["confidence_reasons"])


def test_side_confidence_unknown_when_all_findings_blocked():
    from app.services.consumer.comparison_engine import _side_confidence_from_findings

    findings = [
        {
            "finding_id": "f1",
            "finding_type": "risk_signal",
            "summary": "No evidence",
        },
    ]
    result = _side_confidence_from_findings(findings)
    assert result["confidence_label"] == "unknown"
    assert result["confidence_score"] == 0.0
    assert any("all_findings_blocked_by_evidence_gatekeeping" in r for r in result["confidence_reasons"])


def test_compare_run_vs_run_excludes_blocked_findings_from_divergences(tmp_path):
    sim_left = "sim_gate_left"
    sim_right = "sim_gate_right"
    _write_consumer_rounds(tmp_path, sim_left)
    _write_consumer_rounds(tmp_path, sim_right)
    # Phase 6J: evidence must be semantically aligned, not merely long.
    _write_consumer_config(tmp_path, sim_left, findings=[
        {"finding_id": "f1", "finding_type": "category_context", "summary": "Sugar concern", "source_label": "brief_background", "evidence_snippets": ["Sugar concern evidence detail"]},
        {"finding_id": "f2", "finding_type": "risk_signal", "summary": "No evidence blocked", "source_label": "public_web"},
    ])
    _write_consumer_config(tmp_path, sim_right, findings=[
        {"finding_id": "f3", "finding_type": "category_context", "summary": "Price concern", "source_label": "public_web", "evidence_snippets": ["Price concern evidence detail"]},
    ])

    snapshot = compare_run_vs_run(sim_left, sim_right, upload_root=str(tmp_path))

    # Divergences should only include signals from allowed findings
    divergences = snapshot["evidence_backed_divergences"]
    signals = {d["signal"] for d in divergences}
    # "No evidence blocked" should NOT appear because it is gatekept out
    assert "No evidence blocked" not in signals
    assert "Sugar concern" in signals
    assert "Price concern" in signals

    # Comparison confidence should include gatekeeping summaries
    assert "evidence_gatekeeping_summary" in snapshot["left_confidence"]
    assert "evidence_gatekeeping_summary" in snapshot["right_confidence"]
