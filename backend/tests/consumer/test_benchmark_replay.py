from pathlib import Path

from app.services.consumer.benchmark_registry import register_benchmark
from app.services.consumer.benchmark_replay import (
    _replay_runs_dir,
    extract_stable_signals,
    compare_replay_result,
    replay_benchmark,
    get_replay_result,
    list_replay_results,
)


def test_extract_stable_signals_from_report_context():
    context = {
        "summary": {
            "post_propagation_acceptance": {"positive": 0.7, "neutral": 0.2, "negative": 0.1},
        },
        "top_resonance_points": ["Great taste", "Convenient packaging"],
        "top_risk_points": ["Price too high"],
        "top_misreads": ["Contains artificial sweetener"],
        "top_clarification_opportunities": [],
        "cascade_metrics": {
            "narrative_takeover_score": 0.15,
            "cross_community_event_count": 3,
        },
    }
    signals = extract_stable_signals(context)
    assert signals["acceptance_band"] == "positive_lean"
    assert signals["top_resonance_labels"] == ["Great taste", "Convenient packaging"]
    assert signals["top_risk_labels"] == ["Price too high"]
    assert signals["misread_present"] is True
    assert signals["clarification_recovery_present"] is False
    assert signals["cascade_band"] == "spreading"


def test_extract_stable_signals_negative_lean():
    context = {
        "summary": {
            "post_propagation_acceptance": {"positive": 0.1, "neutral": 0.2, "negative": 0.7},
        },
        "top_resonance_points": [],
        "top_risk_points": ["Bad taste"],
        "top_misreads": [],
        "top_clarification_opportunities": ["Clarified ingredient"],
        "cascade_metrics": {
            "narrative_takeover_score": 0.8,
            "cross_community_event_count": 10,
        },
    }
    signals = extract_stable_signals(context)
    assert signals["acceptance_band"] == "negative_lean"
    assert signals["misread_present"] is False
    assert signals["clarification_recovery_present"] is True
    assert signals["cascade_band"] == "takeover"


def test_compare_replay_result_aligned():
    expected = {
        "acceptance_band": "positive_lean",
        "top_resonance_labels": ["Great taste"],
        "top_risk_labels": ["Price too high"],
        "misread_present": True,
        "clarification_recovery_present": False,
        "cascade_band": "contained",
    }
    actual = {
        "acceptance_band": "positive_lean",
        "top_resonance_labels": ["Great taste"],
        "top_risk_labels": ["Price too high"],
        "misread_present": True,
        "clarification_recovery_present": False,
        "cascade_band": "contained",
    }
    result = compare_replay_result(expected, actual)
    assert result["alignment_status"] == "aligned"
    assert result["drift_signals"] == []
    assert result["metric_deltas"]["acceptance_band_match"] == 1.0


def test_compare_replay_result_drift():
    expected = {
        "acceptance_band": "positive_lean",
        "top_resonance_labels": ["Great taste"],
        "top_risk_labels": ["Price too high"],
        "misread_present": True,
        "clarification_recovery_present": False,
        "cascade_band": "contained",
    }
    actual = {
        "acceptance_band": "negative_lean",
        "top_resonance_labels": ["Bad taste"],
        "top_risk_labels": ["Price too high", "Allergen concern"],
        "misread_present": False,
        "clarification_recovery_present": True,
        "cascade_band": "takeover",
    }
    result = compare_replay_result(expected, actual)
    assert result["alignment_status"] == "drift"
    assert len(result["drift_signals"]) > 0
    assert result["metric_deltas"]["acceptance_band_match"] == 0.0
    assert result["metric_deltas"]["resonance_overlap"] == 0.0


def test_replay_benchmark_persists_result(tmp_path):
    root = str(tmp_path / "uploads")
    benchmark = register_benchmark(
        name="Replay Bench",
        source_pack_lineage="pack_replay",
        expected_signals={
            "acceptance_band": "positive_lean",
            "top_resonance_labels": ["Great taste"],
            "top_risk_labels": ["Price too high"],
            "misread_present": False,
            "clarification_recovery_present": False,
            "cascade_band": "contained",
        },
        upload_root=root,
    )

    report_context = {
        "summary": {
            "post_propagation_acceptance": {"positive": 0.7, "neutral": 0.2, "negative": 0.1},
        },
        "top_resonance_points": ["Great taste"],
        "top_risk_points": ["Price too high"],
        "top_misreads": [],
        "top_clarification_opportunities": [],
        "cascade_metrics": {
            "narrative_takeover_score": 0.1,
            "cross_community_event_count": 0,
        },
    }

    replay = replay_benchmark(
        benchmark_id=benchmark["benchmark_id"],
        report_context=report_context,
        project_id="proj_1",
        simulation_id="sim_1",
        upload_root=root,
    )

    assert "replay_id" in replay
    assert replay["benchmark_id"] == benchmark["benchmark_id"]
    assert replay["project_id"] == "proj_1"
    assert replay["simulation_id"] == "sim_1"
    assert replay["alignment_status"] == "aligned"
    assert "replay_summary" in replay

    # File persisted
    replay_path = _replay_runs_dir(root) / f"{replay['replay_id']}.json"
    assert replay_path.exists()


def test_get_replay_result_returns_data(tmp_path):
    root = str(tmp_path / "uploads")
    benchmark = register_benchmark(
        name="Replay Bench Get",
        source_pack_lineage="pack_get",
        expected_signals={"acceptance_band": "positive_lean"},
        upload_root=root,
    )

    report_context = {
        "summary": {
            "post_propagation_acceptance": {"positive": 0.6, "neutral": 0.3, "negative": 0.1},
        },
        "top_resonance_points": [],
        "top_risk_points": [],
        "top_misreads": [],
        "top_clarification_opportunities": [],
        "cascade_metrics": {},
    }

    replay = replay_benchmark(
        benchmark_id=benchmark["benchmark_id"],
        report_context=report_context,
        project_id="proj_2",
        simulation_id="sim_2",
        upload_root=root,
    )

    fetched = get_replay_result(replay["replay_id"], upload_root=root)
    assert fetched is not None
    assert fetched["replay_id"] == replay["replay_id"]
    assert fetched["benchmark_id"] == benchmark["benchmark_id"]


def test_get_replay_result_missing_returns_none(tmp_path):
    root = str(tmp_path / "uploads")
    assert get_replay_result("replay_missing", upload_root=root) is None


def test_list_replay_results_for_benchmark(tmp_path):
    root = str(tmp_path / "uploads")
    benchmark = register_benchmark(
        name="Replay Bench List",
        source_pack_lineage="pack_list",
        expected_signals={"acceptance_band": "mixed"},
        upload_root=root,
    )

    report_context = {
        "summary": {
            "post_propagation_acceptance": {"positive": 0.5, "neutral": 0.3, "negative": 0.2},
        },
        "top_resonance_points": [],
        "top_risk_points": [],
        "top_misreads": [],
        "top_clarification_opportunities": [],
        "cascade_metrics": {},
    }

    replay1 = replay_benchmark(
        benchmark_id=benchmark["benchmark_id"],
        report_context=report_context,
        project_id="proj_3",
        simulation_id="sim_3",
        upload_root=root,
    )
    replay2 = replay_benchmark(
        benchmark_id=benchmark["benchmark_id"],
        report_context=report_context,
        project_id="proj_3",
        simulation_id="sim_4",
        upload_root=root,
    )

    results = list_replay_results(benchmark["benchmark_id"], upload_root=root)
    assert len(results) == 2
    replay_ids = {r["replay_id"] for r in results}
    assert replay_ids == {replay1["replay_id"], replay2["replay_id"]}


def test_replay_benchmark_with_drift(tmp_path):
    root = str(tmp_path / "uploads")
    benchmark = register_benchmark(
        name="Replay Bench Drift",
        source_pack_lineage="pack_drift",
        expected_signals={
            "acceptance_band": "positive_lean",
            "top_resonance_labels": ["Great taste"],
            "top_risk_labels": ["Price too high"],
            "misread_present": False,
            "clarification_recovery_present": False,
            "cascade_band": "contained",
        },
        upload_root=root,
    )

    report_context = {
        "summary": {
            "post_propagation_acceptance": {"positive": 0.2, "neutral": 0.2, "negative": 0.6},
        },
        "top_resonance_points": ["Bad aftertaste"],
        "top_risk_points": ["Allergen concern"],
        "top_misreads": ["Contains MSG"],
        "top_clarification_opportunities": ["Clarified no MSG"],
        "cascade_metrics": {
            "narrative_takeover_score": 0.9,
            "cross_community_event_count": 8,
        },
    }

    replay = replay_benchmark(
        benchmark_id=benchmark["benchmark_id"],
        report_context=report_context,
        project_id="proj_drift",
        simulation_id="sim_drift",
        upload_root=root,
    )

    assert replay["alignment_status"] == "drift"
    assert len(replay["drift_signals"]) > 0
    assert replay["metric_deltas"]["acceptance_band_match"] == 0.0


def test_extract_stable_signals_defaults_when_keys_missing():
    context = {}
    signals = extract_stable_signals(context)
    assert signals["acceptance_band"] == "mixed"
    assert signals["top_resonance_labels"] == []
    assert signals["top_risk_labels"] == []
    assert signals["misread_present"] is False
    assert signals["clarification_recovery_present"] is False
    assert signals["cascade_band"] == "contained"


# Phase 5C: Evidence gatekeeping in benchmark replay tests

def test_replay_benchmark_penalizes_blocked_findings(tmp_path):
    root = str(tmp_path / "uploads")
    benchmark = register_benchmark(
        name="Replay Gatekeeping",
        source_pack_lineage="pack_gate",
        expected_signals={
            "acceptance_band": "positive_lean",
            "top_resonance_labels": ["Great taste"],
            "top_risk_labels": ["Price too high"],
            "misread_present": False,
            "clarification_recovery_present": False,
            "cascade_band": "contained",
        },
        upload_root=root,
    )

    report_context = {
        "summary": {
            "post_propagation_acceptance": {"positive": 0.7, "neutral": 0.2, "negative": 0.1},
        },
        "top_resonance_points": ["Great taste"],
        "top_risk_points": ["Price too high"],
        "top_misreads": [],
        "top_clarification_opportunities": [],
        "cascade_metrics": {
            "narrative_takeover_score": 0.1,
            "cross_community_event_count": 0,
        },
        # Phase 5C: evidence gatekeeping summary with blocked findings
        "evidence_gatekeeping_summary": {
            "finding_count": 4,
            "allowed_count": 2,
            "downgraded_count": 0,
            "blocked_count": 2,
        },
    }

    replay = replay_benchmark(
        benchmark_id=benchmark["benchmark_id"],
        report_context=report_context,
        project_id="proj_gate",
        simulation_id="sim_gate",
        upload_root=root,
    )

    # Should still be aligned but with a penalty
    assert "evidence_gatekeeping_summary" in replay
    assert any(
        "evidence_gatekeeping_blocked" in ds for ds in replay["drift_signals"]
    )
    # Score should be penalized: base aligned is 1.0, penalty for 2/4 blocked
    assert replay["overall_score"] < 1.0


def test_replay_benchmark_downgraded_findings_add_drift_signals(tmp_path):
    root = str(tmp_path / "uploads")
    benchmark = register_benchmark(
        name="Replay Downgraded",
        source_pack_lineage="pack_down",
        expected_signals={
            "acceptance_band": "positive_lean",
            "top_resonance_labels": ["Great taste"],
            "top_risk_labels": [],
            "misread_present": False,
            "clarification_recovery_present": False,
            "cascade_band": "contained",
        },
        upload_root=root,
    )

    report_context = {
        "summary": {
            "post_propagation_acceptance": {"positive": 0.7, "neutral": 0.2, "negative": 0.1},
        },
        "top_resonance_points": ["Great taste"],
        "top_risk_points": [],
        "top_misreads": [],
        "top_clarification_opportunities": [],
        "cascade_metrics": {
            "narrative_takeover_score": 0.1,
            "cross_community_event_count": 0,
        },
        "evidence_gatekeeping_summary": {
            "finding_count": 4,
            "allowed_count": 2,
            "downgraded_count": 2,
            "blocked_count": 0,
        },
    }

    replay = replay_benchmark(
        benchmark_id=benchmark["benchmark_id"],
        report_context=report_context,
        project_id="proj_down",
        simulation_id="sim_down",
        upload_root=root,
    )

    assert any(
        "evidence_gatekeeping_downgraded" in ds for ds in replay["drift_signals"]
    )
    assert "evidence_gatekeeping_summary" in replay


def test_replay_benchmark_no_gatekeeping_summary_unchanged(tmp_path):
    root = str(tmp_path / "uploads")
    benchmark = register_benchmark(
        name="Replay No Gatekeeping",
        source_pack_lineage="pack_none",
        expected_signals={
            "acceptance_band": "positive_lean",
            "top_resonance_labels": ["Great taste"],
            "top_risk_labels": ["Price too high"],
            "misread_present": False,
            "clarification_recovery_present": False,
            "cascade_band": "contained",
        },
        upload_root=root,
    )

    report_context = {
        "summary": {
            "post_propagation_acceptance": {"positive": 0.7, "neutral": 0.2, "negative": 0.1},
        },
        "top_resonance_points": ["Great taste"],
        "top_risk_points": ["Price too high"],
        "top_misreads": [],
        "top_clarification_opportunities": [],
        "cascade_metrics": {
            "narrative_takeover_score": 0.1,
            "cross_community_event_count": 0,
        },
        # No evidence_gatekeeping_summary
    }

    replay = replay_benchmark(
        benchmark_id=benchmark["benchmark_id"],
        report_context=report_context,
        project_id="proj_none",
        simulation_id="sim_none",
        upload_root=root,
    )

    # Should be aligned with no gatekeeping-related drift signals
    assert replay["alignment_status"] == "aligned"
    assert not any(
        "evidence_gatekeeping" in ds for ds in replay["drift_signals"]
    )
    assert "evidence_gatekeeping_summary" not in replay
