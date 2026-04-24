"""Tests proving ConsumerAppService uses provider boundary without
ProjectManager / load_persisted_snapshot imports.
"""

import json

import pytest

from app.repositories import ConsumerProjectResearchContext, ConsumerProjectResearchProvider
from app.services.application.consumer_app_service import ConsumerAppService
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


def _write_consumer_config(tmp_path, simulation_id):
    sim_dir = tmp_path / "uploads" / "simulations" / simulation_id
    sim_dir.mkdir(parents=True, exist_ok=True)
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


class FakeConsumerProjectResearchProvider(ConsumerProjectResearchProvider):
    """Fake provider that never touches ProjectManager or persistence."""

    def __init__(self, ctx: ConsumerProjectResearchContext = None):
        self.ctx = ctx or ConsumerProjectResearchContext()

    def get_context(self, project_id: str) -> ConsumerProjectResearchContext:
        return self.ctx


@pytest.fixture
def monkeypatch_config_upload_folder(monkeypatch, tmp_path):
    from app.config import Config
    from app.services.simulation_manager import SimulationManager
    sim_dir = tmp_path / "uploads" / "simulations"
    monkeypatch.setattr(Config, "UPLOAD_FOLDER", str(tmp_path / "uploads"))
    monkeypatch.setattr(Config, "OASIS_SIMULATION_DATA_DIR", str(sim_dir))
    monkeypatch.setattr(SimulationManager, "SIMULATION_DATA_DIR", str(sim_dir))
    return tmp_path


def test_consumer_app_service_uses_fake_provider_without_project_manager(
    monkeypatch_config_upload_folder, tmp_path
):
    """ConsumerAppService.get_consumer_summary must work with a fake provider
    and must not require ProjectManager or load_persisted_snapshot.
    """
    project = ProjectManager.create_project(name="Provider Boundary")
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

    # Inject a fake provider that supplies traces/chunks/sources without
    # touching ProjectManager or persistence.
    fake_provider = FakeConsumerProjectResearchProvider(
        ctx=ConsumerProjectResearchContext(
            is_consumer_project=True,
            brief_payload=_brief_payload(),
            traces=[{"trace_id": "t1"}],
            chunks=[{"chunk_id": "c1"}],
            sources=[{"source_id": "s1"}],
        )
    )
    original_provider = ConsumerAppService._project_research_provider
    ConsumerAppService._project_research_provider = fake_provider
    try:
        data = ConsumerAppService.get_consumer_summary(state.simulation_id)
    finally:
        ConsumerAppService._project_research_provider = original_provider

    assert "event_counts" in data
    assert data["event_counts"]["risk_discovery"] == 1
    assert "cascade_metrics" in data


def test_consumer_app_service_has_no_project_manager_or_persistence_imports():
    """Static check: the service module must not contain the strings
    'ProjectManager' or 'load_persisted_snapshot'.
    """
    import app.services.application.consumer_app_service as svc_mod
    import inspect

    source = inspect.getsource(svc_mod)
    assert "ProjectManager" not in source, "ConsumerAppService imports ProjectManager directly"
    assert "load_persisted_snapshot" not in source, (
        "ConsumerAppService imports load_persisted_snapshot directly"
    )
