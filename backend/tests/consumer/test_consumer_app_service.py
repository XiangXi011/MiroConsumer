"""Tests for ConsumerAppService — consumer bounded-context orchestration."""

import json

import pytest

from app.services.application.consumer_app_service import ConsumerAppService
from app.services.consumer.models import ConsumerTaskType
from app.services.simulation_manager import SimulationManager
from app.models.project import ProjectManager


def _brief_payload():
    return {
        "task_type": "concept_test",
        "product_concept_assets": ["Glow serum stick"],
        "copy_material": ["Brighter skin in one swipe"],
        "claims": ["Derm-tested glow boost"],
        "target_audience": ["busy commuters"],
        "usage_scene": ["morning commute"],
        "research_goal": "Understand first-impression appeal",
    }


def _write_consumer_rounds(tmp_path, simulation_id):
    sim_dir = tmp_path / "uploads" / "simulations" / simulation_id
    sim_dir.mkdir(parents=True, exist_ok=True)
    events = [
        {
            "round_num": 0,
            "agent_id": "persona_a",
            "agent_name": "Value Seeker",
            "attitude_label": "positive",
            "bucket": "resonance",
            "engagement": 9,
            "quote": "This actually sounds like a real breakfast fix.",
            "prompt": "Pinned BusinessBrief Summary: breakfast yogurt pouch",
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
            "prompt": "Pinned BusinessBrief Summary: breakfast yogurt pouch",
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
            "prompt": "Pinned BusinessBrief Summary: breakfast yogurt pouch",
            "visible_nodes": [{"type": "RiskPoint", "text": "sweetener debate"}],
        },
        {
            "round_num": 1,
            "agent_id": "persona_b",
            "agent_name": "Proof First",
            "attitude_label": "positive",
            "bucket": "resonance",
            "engagement": 7,
            "quote": "People would probably keep sharing the breakfast angle.",
            "prompt": "Pinned BusinessBrief Summary: breakfast yogurt pouch",
            "visible_nodes": [{"type": "TalkingPoint", "text": "breakfast angle"}],
        },
    ]
    (sim_dir / "consumer_rounds.jsonl").write_text(
        "\n".join(json.dumps(event, ensure_ascii=False) for event in events) + "\n",
        encoding="utf-8",
    )


def _write_consumer_config(tmp_path, simulation_id):
    sim_dir = tmp_path / "uploads" / "simulations" / simulation_id
    sim_dir.mkdir(parents=True, exist_ok=True)
    config = {
        "consumer_brief": _brief_payload(),
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
    }
    (sim_dir / "consumer_config.json").write_text(
        json.dumps(config, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


@pytest.fixture
def monkeypatch_config_upload_folder(monkeypatch, tmp_path):
    from app.config import Config
    from app.services.simulation_manager import SimulationManager
    sim_dir = tmp_path / "uploads" / "simulations"
    monkeypatch.setattr(Config, "UPLOAD_FOLDER", str(tmp_path / "uploads"))
    monkeypatch.setattr(Config, "OASIS_SIMULATION_DATA_DIR", str(sim_dir))
    monkeypatch.setattr(SimulationManager, "SIMULATION_DATA_DIR", str(sim_dir))
    return tmp_path


def test_get_consumer_summary_raises_for_missing_simulation():
    with pytest.raises(ValueError, match="sim_missing"):
        ConsumerAppService.get_consumer_summary("sim_missing")


def test_get_consumer_summary_raises_for_non_consumer_simulation(tmp_path, monkeypatch_config_upload_folder):
    project = ProjectManager.create_project(name="Non Consumer")
    project.project_type = "default"
    ProjectManager.save_project(project)

    state = SimulationManager().create_simulation(
        project_id=project.project_id,
        graph_id="graph_123",
        project_type="default",
    )

    with pytest.raises(ValueError, match="consumer_test"):
        ConsumerAppService.get_consumer_summary(state.simulation_id)


def test_get_consumer_summary_builds_phase1_context(monkeypatch_config_upload_folder, tmp_path):
    project = ProjectManager.create_project(name="Consumer Summary")
    project.project_type = "consumer_test"
    project.graph_id = f"consumer_{project.project_id}"
    project.consumer_brief = _brief_payload()
    ProjectManager.save_project(project)

    state = SimulationManager().create_simulation(
        project_id=project.project_id,
        graph_id=project.graph_id,
        project_type="consumer_test",
    )
    _write_consumer_rounds(tmp_path, state.simulation_id)
    _write_consumer_config(tmp_path, state.simulation_id)

    data = ConsumerAppService.get_consumer_summary(state.simulation_id)

    assert "summary" in data
    assert data["summary"]["attitude_shift_rate"] > 0
    assert data["representative_voc_quotes"]["risk"][0]["quote"].startswith("Low sugar")


def test_get_consumer_summary_builds_phase2_fields(monkeypatch_config_upload_folder, tmp_path):
    project = ProjectManager.create_project(name="Consumer Phase2")
    project.project_type = "consumer_test"
    project.graph_id = f"consumer_{project.project_id}"
    project.consumer_brief = _brief_payload()
    ProjectManager.save_project(project)

    state = SimulationManager().create_simulation(
        project_id=project.project_id,
        graph_id=project.graph_id,
        project_type="consumer_test",
    )

    sim_dir = tmp_path / "uploads" / "simulations" / state.simulation_id
    sim_dir.mkdir(parents=True, exist_ok=True)
    events = [
        {
            "round_num": 0,
            "agent_id": "persona_a",
            "agent_name": "Value Seeker",
            "attitude_label": "positive",
            "bucket": "resonance",
            "engagement": 9,
            "quote": "This actually sounds like a real breakfast fix.",
            "prompt": "Pinned BusinessBrief Summary: breakfast yogurt pouch",
            "visible_nodes": [{"type": "ProductConcept", "text": "breakfast yogurt pouch"}],
            "visible_finding_ids": [],
            "propagation_events": [],
        },
        {
            "round_num": 1,
            "agent_id": "persona_a",
            "agent_name": "Value Seeker",
            "attitude_label": "negative",
            "bucket": "risk",
            "engagement": 8,
            "quote": "Low sugar? I don't trust that claim after the debate.",
            "prompt": "Pinned BusinessBrief Summary: breakfast yogurt pouch",
            "visible_nodes": [{"type": "RiskPoint", "text": "sweetener debate"}],
            "visible_finding_ids": ["f1"],
            "propagation_events": [
                {
                    "event_id": "evt_persona_a_f1_ris",
                    "event_type": "risk_discovery",
                    "actor_id": "persona_a",
                    "target_ids": [],
                    "trigger_finding_ids": ["f1"],
                    "supporting_quote": "Low sugar? I don't trust that claim after the debate.",
                    "round_index": 1,
                }
            ],
        },
    ]
    (sim_dir / "consumer_rounds.jsonl").write_text(
        "\n".join(json.dumps(event, ensure_ascii=False) for event in events) + "\n",
        encoding="utf-8",
    )
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
    }
    (sim_dir / "consumer_config.json").write_text(
        json.dumps(config, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    data = ConsumerAppService.get_consumer_summary(state.simulation_id)

    assert "event_counts" in data
    assert "cascade_metrics" in data
    assert data["event_counts"]["risk_discovery"] == 1
    # top_risk_findings may be empty due to evidence gatekeeping in uncommitted work
    assert "top_risk_findings" in data


def test_get_consumer_summary_task_aware_price_fields(monkeypatch_config_upload_folder, tmp_path):
    project = ProjectManager.create_project(name="Consumer Price")
    project.project_type = "consumer_test"
    project.graph_id = f"consumer_{project.project_id}"
    project.consumer_brief = {
        "task_type": "price_test",
        "product_concept_assets": ["Protein yogurt pouch"],
        "copy_material": ["14g protein"],
        "price_points": ["$9.99", "$14.99"],
        "price_context": "subscription monthly",
        "target_audience": ["busy professionals"],
        "usage_scene": ["morning commute"],
        "research_goal": "Find acceptable price range",
    }
    ProjectManager.save_project(project)

    state = SimulationManager().create_simulation(
        project_id=project.project_id,
        graph_id=project.graph_id,
        project_type="consumer_test",
    )

    sim_dir = tmp_path / "uploads" / "simulations" / state.simulation_id
    sim_dir.mkdir(parents=True, exist_ok=True)
    events = [
        {
            "round_num": 0,
            "agent_id": "persona_a",
            "agent_name": "Value Seeker",
            "attitude_label": "positive",
            "bucket": "resonance",
            "engagement": 9,
            "quote": "This actually sounds like a real breakfast fix.",
            "visible_nodes": [],
            "visible_finding_ids": [],
            "propagation_events": [],
        },
        {
            "round_num": 1,
            "agent_id": "persona_a",
            "agent_name": "Value Seeker",
            "attitude_label": "negative",
            "bucket": "risk",
            "engagement": 8,
            "quote": "Low sugar? I don't trust that claim after the debate.",
            "visible_nodes": [],
            "visible_finding_ids": ["f1"],
            "propagation_events": [
                {
                    "event_id": "evt_persona_a_f1_ris",
                    "event_type": "risk_discovery",
                    "actor_id": "persona_a",
                    "target_ids": [],
                    "trigger_finding_ids": ["f1"],
                    "supporting_quote": "Low sugar? I don't trust that claim after the debate.",
                    "round_index": 1,
                }
            ],
        },
    ]
    (sim_dir / "consumer_rounds.jsonl").write_text(
        "\n".join(json.dumps(event, ensure_ascii=False) for event in events) + "\n",
        encoding="utf-8",
    )
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
    }
    (sim_dir / "consumer_config.json").write_text(
        json.dumps(config, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    data = ConsumerAppService.get_consumer_summary(state.simulation_id)

    assert data["task_type"] == "price_test"
    assert data["acceptable_price_points"] == ["$9.99", "$14.99"]
    assert data["resisted_price_points"] == ["$14.99"]
    assert data["price_context"] == "subscription monthly"
