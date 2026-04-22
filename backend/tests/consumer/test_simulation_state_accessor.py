"""Tests for ConsumerSimulationStateAccessor — consumer-owned simulation state I/O."""

import json

import pytest

from app.services.consumer.simulation_state_accessor import ConsumerSimulationStateAccessor
from app.services.consumer.models import ConsumerTaskType


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


@pytest.fixture
def monkeypatch_config_upload_folder(monkeypatch, tmp_path):
    from app.config import Config
    monkeypatch.setattr(Config, "UPLOAD_FOLDER", str(tmp_path / "uploads"))
    return tmp_path


def test_rounds_path(monkeypatch_config_upload_folder):
    path = ConsumerSimulationStateAccessor.rounds_path("sim_001")
    assert path.name == "consumer_rounds.jsonl"
    assert "simulations" in str(path)
    assert "sim_001" in str(path)


def test_config_path(monkeypatch_config_upload_folder):
    path = ConsumerSimulationStateAccessor.config_path("sim_001")
    assert path.name == "consumer_config.json"
    assert "simulations" in str(path)
    assert "sim_001" in str(path)


def test_load_consumer_config_missing(monkeypatch_config_upload_folder):
    config = ConsumerSimulationStateAccessor.load_consumer_config("sim_missing")
    assert config == {}


def test_load_consumer_config_present(monkeypatch_config_upload_folder, tmp_path):
    sim_dir = tmp_path / "uploads" / "simulations" / "sim_002"
    sim_dir.mkdir(parents=True)
    config_data = {"research_findings": [{"finding_id": "f1"}], "consumer_brief": _brief_payload()}
    (sim_dir / "consumer_config.json").write_text(json.dumps(config_data), encoding="utf-8")

    config = ConsumerSimulationStateAccessor.load_consumer_config("sim_002")
    assert config["research_findings"][0]["finding_id"] == "f1"


def test_load_consumer_rounds_missing(monkeypatch_config_upload_folder):
    rounds = ConsumerSimulationStateAccessor.load_consumer_rounds("sim_missing")
    assert rounds == []


def test_load_consumer_rounds_present(monkeypatch_config_upload_folder, tmp_path):
    sim_dir = tmp_path / "uploads" / "simulations" / "sim_003"
    sim_dir.mkdir(parents=True)
    events = [
        {"round_num": 0, "agent_id": "a1", "attitude_label": "positive"},
        {"round_num": 1, "agent_id": "a1", "attitude_label": "negative"},
    ]
    (sim_dir / "consumer_rounds.jsonl").write_text(
        "\n".join(json.dumps(e, ensure_ascii=False) for e in events) + "\n",
        encoding="utf-8",
    )

    rounds = ConsumerSimulationStateAccessor.load_consumer_rounds("sim_003")
    assert len(rounds) == 2
    assert rounds[0]["agent_id"] == "a1"


def test_load_brief_missing(monkeypatch_config_upload_folder):
    brief = ConsumerSimulationStateAccessor.load_brief("sim_missing")
    assert brief is None


def test_load_brief_present(monkeypatch_config_upload_folder, tmp_path):
    sim_dir = tmp_path / "uploads" / "simulations" / "sim_004"
    sim_dir.mkdir(parents=True)
    config_data = {"consumer_brief": _brief_payload()}
    (sim_dir / "consumer_config.json").write_text(json.dumps(config_data), encoding="utf-8")

    brief = ConsumerSimulationStateAccessor.load_brief("sim_004")
    assert brief is not None
    assert brief.task_type == ConsumerTaskType.ConceptTest
    assert brief.product_concept_assets == ["Glow serum stick"]


def test_load_research_findings_missing(monkeypatch_config_upload_folder):
    findings = ConsumerSimulationStateAccessor.load_research_findings("sim_missing")
    assert findings == []


def test_load_research_findings_present(monkeypatch_config_upload_folder, tmp_path):
    sim_dir = tmp_path / "uploads" / "simulations" / "sim_005"
    sim_dir.mkdir(parents=True)
    config_data = {"research_findings": [{"finding_id": "f2", "finding_type": "risk_signal"}]}
    (sim_dir / "consumer_config.json").write_text(json.dumps(config_data), encoding="utf-8")

    findings = ConsumerSimulationStateAccessor.load_research_findings("sim_005")
    assert len(findings) == 1
    assert findings[0]["finding_id"] == "f2"
