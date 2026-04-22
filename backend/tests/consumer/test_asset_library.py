import json
from pathlib import Path

import pytest

from app.services.consumer.asset_library import (
    _assets_dir,
    _build_asset_pack,
    delete_asset,
    export_asset,
    get_asset,
    list_assets,
)
from app.services.consumer.models import (
    ResearchFinding,
    ResearchSnapshot,
    ResearchSource,
    GraphVisibility,
)
from app.services.consumer.project_research_persistence import (
    persist_findings,
    persist_snapshot,
)


def _write_consumer_rounds(base_path: Path, simulation_id: str, branch_id: str | None = None):
    if branch_id:
        rounds_path = base_path / "simulations" / simulation_id / "branches" / branch_id / "rounds.jsonl"
    else:
        rounds_path = base_path / "simulations" / simulation_id / "consumer_rounds.jsonl"
    rounds_path.parent.mkdir(parents=True, exist_ok=True)
    events = [
        {
            "round_num": 0,
            "agent_id": "persona_a",
            "agent_name": "Value Seeker",
            "attitude_label": "positive",
            "bucket": "resonance",
            "engagement": 9,
            "quote": "This actually sounds like a real breakfast fix.",
            "visible_nodes": [{"type": "ProductConcept", "text": "breakfast yogurt pouch"}],
        },
        {
            "round_num": 0,
            "agent_id": "persona_b",
            "agent_name": "Proof First",
            "attitude_label": "neutral",
            "bucket": "question",
            "engagement": 5,
            "quote": "I get the idea, but I still want more proof.",
            "visible_nodes": [{"type": "CopyPoint", "text": "low sugar"}],
        },
        {
            "round_num": 1,
            "agent_id": "persona_a",
            "agent_name": "Value Seeker",
            "attitude_label": "negative",
            "bucket": "risk",
            "engagement": 8,
            "quote": "Low sugar? I don't trust that claim after the debate.",
            "visible_nodes": [{"type": "RiskPoint", "text": "sweetener debate"}],
        },
    ]
    rounds_path.write_text(
        "\n".join(json.dumps(event, ensure_ascii=False) for event in events) + "\n",
        encoding="utf-8",
    )


def _write_state(base_path: Path, simulation_id: str, project_id: str):
    state_path = base_path / "simulations" / simulation_id / "state.json"
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(
        json.dumps({"simulation_id": simulation_id, "project_id": project_id}),
        encoding="utf-8",
    )


def _write_consumer_config(base_path: Path, simulation_id: str):
    config_path = base_path / "simulations" / simulation_id / "consumer_config.json"
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config = {
        "research_findings": [
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


def test_build_asset_pack_with_project_artifacts(tmp_path):
    project_id = "proj_test"
    simulation_id = "sim_test"
    _write_state(tmp_path, simulation_id, project_id)
    _write_consumer_rounds(tmp_path, simulation_id)

    findings = [
        ResearchFinding(
            finding_id="f1",
            finding_type="risk_signal",
            summary="Sweetener concern",
            visibility=GraphVisibility.Propagation_Only,
            source_label="brief_background",
        )
    ]
    snapshot = ResearchSnapshot(
        snapshot_id=f"rsnap_{project_id}",
        project_id=project_id,
        created_at="2026-04-22T10:00:00+00:00",
        sources=[
            ResearchSource(
                source_id="src_1",
                lane="lane_a",
                source_type="upload",
                label="Background",
                uri="file://brief.pdf",
            )
        ],
        findings=findings,
    )
    persist_findings(project_id, findings, upload_root=str(tmp_path))
    persist_snapshot(project_id, snapshot, upload_root=str(tmp_path))

    pack = _build_asset_pack(project_id, simulation_id, upload_root=str(tmp_path))

    assert pack["asset_type"] == "consumer_research_pack"
    assert pack["project_id"] == project_id
    assert pack["simulation_id"] == simulation_id
    assert "asset_id" in pack
    assert "created_at" in pack
    assert pack["summary"]["finding_count"] == 1
    assert pack["summary"]["source_count"] == 1
    assert pack["summary"]["resonance_points"] >= 0
    assert pack["summary"]["risk_points"] >= 0
    assert len(pack["research_findings"]) == 1
    assert len(pack["source_catalog"]) == 1
    assert pack["source_catalog"][0]["source_id"] == "src_1"
    assert "representative_voc_quotes" in pack
    assert "evidence_bundle" in pack


def test_build_asset_pack_fallback_to_consumer_config(tmp_path):
    project_id = "proj_fb"
    simulation_id = "sim_fb"
    _write_state(tmp_path, simulation_id, project_id)
    _write_consumer_rounds(tmp_path, simulation_id)
    _write_consumer_config(tmp_path, simulation_id)

    pack = _build_asset_pack(project_id, simulation_id, upload_root=str(tmp_path))

    assert pack["asset_type"] == "consumer_research_pack"
    assert pack["summary"]["finding_count"] == 1
    assert pack["research_snapshot"]["snapshot_id"] == "snap_1"


def test_build_asset_pack_with_branch(tmp_path):
    project_id = "proj_branch"
    simulation_id = "sim_branch"
    branch_id = "branch_001"
    _write_state(tmp_path, simulation_id, project_id)
    _write_consumer_rounds(tmp_path, simulation_id, branch_id=branch_id)

    pack = _build_asset_pack(project_id, simulation_id, branch_id=branch_id, upload_root=str(tmp_path))

    assert pack["branch_id"] == branch_id
    assert pack["simulation_id"] == simulation_id


def test_export_asset_persists_file(tmp_path):
    project_id = "proj_exp"
    simulation_id = "sim_exp"
    _write_state(tmp_path, simulation_id, project_id)
    _write_consumer_rounds(tmp_path, simulation_id)

    pack = export_asset(project_id, simulation_id, upload_root=str(tmp_path))
    asset_id = pack["asset_id"]

    path = _assets_dir(str(tmp_path)) / f"{asset_id}.json"
    assert path.exists()
    loaded = json.loads(path.read_text(encoding="utf-8"))
    assert loaded["asset_id"] == asset_id


def test_list_assets_filters_by_project(tmp_path):
    project_id = "proj_list"
    simulation_id = "sim_list"
    _write_state(tmp_path, simulation_id, project_id)
    _write_consumer_rounds(tmp_path, simulation_id)

    export_asset(project_id, simulation_id, name="Asset A", upload_root=str(tmp_path))
    export_asset(project_id, simulation_id, name="Asset B", upload_root=str(tmp_path))
    export_asset("other_proj", simulation_id, name="Asset C", upload_root=str(tmp_path))

    items = list_assets(project_id, upload_root=str(tmp_path))
    assert len(items) == 2
    assert all(i["project_id"] == project_id for i in items)


def test_get_asset_returns_data(tmp_path):
    project_id = "proj_get"
    simulation_id = "sim_get"
    _write_state(tmp_path, simulation_id, project_id)
    _write_consumer_rounds(tmp_path, simulation_id)

    pack = export_asset(project_id, simulation_id, upload_root=str(tmp_path))
    fetched = get_asset(pack["asset_id"], upload_root=str(tmp_path))

    assert fetched is not None
    assert fetched["asset_id"] == pack["asset_id"]


def test_get_asset_missing_returns_none(tmp_path):
    assert get_asset("asset_missing", upload_root=str(tmp_path)) is None


def test_delete_asset_removes_file(tmp_path):
    project_id = "proj_del"
    simulation_id = "sim_del"
    _write_state(tmp_path, simulation_id, project_id)
    _write_consumer_rounds(tmp_path, simulation_id)

    pack = export_asset(project_id, simulation_id, upload_root=str(tmp_path))
    assert delete_asset(pack["asset_id"], upload_root=str(tmp_path)) is True
    assert get_asset(pack["asset_id"], upload_root=str(tmp_path)) is None


def test_delete_asset_missing_returns_false(tmp_path):
    assert delete_asset("asset_noexist", upload_root=str(tmp_path)) is False
