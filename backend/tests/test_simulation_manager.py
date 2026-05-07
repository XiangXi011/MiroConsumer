import json
from pathlib import Path
import sys

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

import pytest
from app.services.simulation_manager import SimulationManager, SimulationStatus
from app.services.prepare_manifest import (
    CONSUMER_MANIFEST_FILE_NAME,
    MANIFEST_FILE_NAME,
    read_consumer_prepare_manifest,
    read_manifest,
)


def _configure_simulation_storage(tmp_path, monkeypatch):
    simulations_dir = tmp_path / "uploads" / "simulations"
    monkeypatch.setattr(SimulationManager, "SIMULATION_DATA_DIR", str(simulations_dir))
    return simulations_dir


class FakeZepFiltered:
    def __init__(self, entities, entity_types):
        self.filtered_count = len(entities)
        self.entities = entities
        self.entity_types = set(entity_types)


class FakeZepEntityReader:
    def __init__(self, entities=None, entity_types=None):
        self._entities = entities or []
        self._entity_types = entity_types or ["Student"]

    def filter_defined_entities(self, graph_id, defined_entity_types=None, enrich_with_edges=True):
        return FakeZepFiltered(self._entities, self._entity_types)


class FakeOasisProfileGenerator:
    def __init__(self, profiles=None, graph_id=None, **kwargs):
        self._profiles = profiles or [{"user_id": 0, "username": "test"}]

    def generate_profiles_from_entities(self, **kwargs):
        return self._profiles

    def save_profiles(self, profiles, file_path, platform):
        if platform == "reddit":
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(profiles, f, ensure_ascii=False, indent=2)
        elif platform == "twitter":
            import csv
            with open(file_path, "w", encoding="utf-8", newline="") as f:
                writer = csv.DictWriter(
                    f, fieldnames=["user_id", "name", "username", "user_char", "description"]
                )
                writer.writeheader()
                writer.writerows(profiles)


class FakeSimConfigGenerator:
    def generate_config(self, **kwargs):
        from app.services.simulation_config_generator import (
            SimulationParameters,
            TimeSimulationConfig,
            EventConfig,
            PlatformConfig,
        )

        return SimulationParameters(
            simulation_id=kwargs.get("simulation_id", "sim_test"),
            project_id=kwargs.get("project_id", "proj_test"),
            graph_id=kwargs.get("graph_id", "graph_test"),
            simulation_requirement=kwargs.get("simulation_requirement", ""),
            time_config=TimeSimulationConfig(),
            agent_configs=[],
            event_config=EventConfig(),
            twitter_config=PlatformConfig(platform="twitter"),
            reddit_config=PlatformConfig(platform="reddit"),
            generation_reasoning="fake reasoning",
        )


class FakeConsumerBriefAdapter:
    @classmethod
    def from_payload(cls, payload):
        from app.services.consumer.models import ConsumerBusinessBrief

        return ConsumerBusinessBrief(**payload)


def test_legacy_prepare_writes_manifest(tmp_path, monkeypatch):
    """Legacy prepare should write a prepare_manifest.json after successful completion."""
    simulations_dir = _configure_simulation_storage(tmp_path, monkeypatch)

    fake_entities = [{"uuid": "ent1", "name": "Test Entity", "type": "Student"}]
    monkeypatch.setattr(
        "app.services.simulation_manager.ZepEntityReader",
        lambda: FakeZepEntityReader(entities=fake_entities, entity_types=["Student"]),
    )
    monkeypatch.setattr(
        "app.services.simulation_manager.OasisProfileGenerator", FakeOasisProfileGenerator
    )
    monkeypatch.setattr(
        "app.services.simulation_manager.SimulationConfigGenerator", FakeSimConfigGenerator
    )

    mgr = SimulationManager()
    state = mgr.create_simulation(
        project_id="proj_legacy", graph_id="graph_legacy", project_type="default"
    )

    prepared = mgr.prepare_simulation(
        simulation_id=state.simulation_id,
        simulation_requirement="test requirement",
        document_text="test document",
    )

    assert prepared.status == SimulationStatus.READY

    sim_dir = simulations_dir / state.simulation_id
    manifest_path = sim_dir / MANIFEST_FILE_NAME
    assert manifest_path.exists()

    manifest = read_manifest(str(sim_dir))
    assert manifest is not None
    assert manifest.simulation_id == state.simulation_id
    assert manifest.project_id == "proj_legacy"
    assert manifest.project_type == "default"
    assert manifest.consumer_mode is False
    assert manifest.config_generated is True
    assert manifest.prepared_at != ""
    assert manifest.reuse_count == 0


def test_consumer_prepare_writes_manifest(tmp_path, monkeypatch):
    """Consumer prepare should write a prepare_manifest.json after successful completion."""
    simulations_dir = _configure_simulation_storage(tmp_path, monkeypatch)

    from app.models.project import ProjectManager

    projects_dir = tmp_path / "uploads" / "projects"
    monkeypatch.setattr(ProjectManager, "PROJECTS_DIR", str(projects_dir))

    project = ProjectManager.create_project(name="Consumer Manifest")
    project.project_type = "consumer_test"
    project.graph_id = f"consumer_{project.project_id}"
    project.consumer_brief = {
        "task_type": "concept_test",
        "product_concept_assets": ["Glow serum stick"],
        "copy_material": ["Brighter skin in one swipe"],
        "claims": ["Derm-tested glow boost"],
        "target_audience": ["busy commuters"],
        "usage_scene": ["morning commute"],
        "research_goal": "Understand first-impression appeal",
    }
    ProjectManager.save_project(project)
    ProjectManager.save_extracted_text(project.project_id, "Some extracted text.")

    monkeypatch.setattr(
        "app.services.simulation_manager.ConsumerBriefAdapter", FakeConsumerBriefAdapter
    )

    mgr = SimulationManager()
    state = mgr.create_simulation(
        project_id=project.project_id,
        graph_id=project.graph_id,
        project_type="consumer_test",
    )

    prepared = mgr.prepare_simulation(
        simulation_id=state.simulation_id,
        simulation_requirement="",
        document_text="",
    )

    assert prepared.status == SimulationStatus.READY

    sim_dir = simulations_dir / state.simulation_id
    manifest_path = sim_dir / MANIFEST_FILE_NAME
    assert manifest_path.exists()

    manifest = read_manifest(str(sim_dir))
    assert manifest is not None
    assert manifest.simulation_id == state.simulation_id
    assert manifest.project_id == project.project_id
    assert manifest.project_type == "consumer_test"
    assert manifest.consumer_mode is True
    assert manifest.config_generated is True
    assert manifest.prepared_at != ""
    assert manifest.reuse_count == 0
    assert manifest.persona_pack_id == "default_persona_pack"

    consumer_manifest_path = sim_dir / CONSUMER_MANIFEST_FILE_NAME
    assert consumer_manifest_path.exists()
    consumer_manifest = read_consumer_prepare_manifest(str(sim_dir))
    assert consumer_manifest is not None
    assert consumer_manifest["consumer_mode"] is True
    assert consumer_manifest["ready_files"] == {
        "profile_snapshot": "society/profile_snapshot.json",
        "society_config": "society/society_config.json",
        "population_preview": "society/population_preview.json",
    }
    profile_snapshot = json.loads((sim_dir / "society" / "profile_snapshot.json").read_text(encoding="utf-8"))
    society_config = json.loads((sim_dir / "society" / "society_config.json").read_text(encoding="utf-8"))
    population_preview = json.loads((sim_dir / "society" / "population_preview.json").read_text(encoding="utf-8"))
    assert profile_snapshot["profiles"]
    assert society_config["mode"] == "quick"
    assert len(population_preview) == society_config["core_persona_count"]


def test_consumer_prepare_readiness_does_not_require_legacy_profile_files(tmp_path, monkeypatch):
    simulations_dir = _configure_simulation_storage(tmp_path, monkeypatch)

    from app.config import Config
    from app.models.project import ProjectManager

    monkeypatch.setattr(Config, "OASIS_SIMULATION_DATA_DIR", str(simulations_dir))
    projects_dir = tmp_path / "uploads" / "projects"
    monkeypatch.setattr(ProjectManager, "PROJECTS_DIR", str(projects_dir))

    project = ProjectManager.create_project(name="Consumer Ready")
    project.project_type = "consumer_test"
    project.graph_id = f"consumer_{project.project_id}"
    project.consumer_brief = {
        "task_type": "concept_test",
        "product_concept_assets": ["316 stainless bowl"],
        "copy_material": ["Safer family meals"],
        "claims": ["316 stainless steel"],
        "target_audience": ["young families"],
        "usage_scene": ["family dinner"],
        "research_goal": "Understand consumer trust barriers",
    }
    ProjectManager.save_project(project)
    ProjectManager.save_extracted_text(project.project_id, "Some extracted text.")
    monkeypatch.setattr(
        "app.services.simulation_manager.ConsumerBriefAdapter", FakeConsumerBriefAdapter
    )

    mgr = SimulationManager()
    state = mgr.create_simulation(
        project_id=project.project_id,
        graph_id=project.graph_id,
        project_type="consumer_test",
    )
    prepared = mgr.prepare_simulation(
        simulation_id=state.simulation_id,
        simulation_requirement="",
        document_text="",
    )
    assert prepared.status == SimulationStatus.READY

    sim_dir = simulations_dir / state.simulation_id
    (sim_dir / "reddit_profiles.json").unlink()
    (sim_dir / "twitter_profiles.csv").unlink()

    from app.api.simulation import _check_simulation_prepared

    is_prepared, info = _check_simulation_prepared(state.simulation_id)
    assert is_prepared is True
    assert info["consumer_ready_model"] == "consumer_test"
    assert info["consumer_prepare_manifest"]["project_type"] == "consumer_test"
    assert info["profiles_count"] == prepared.profiles_count


def test_record_manifest_reuse_increments_counter(tmp_path, monkeypatch):
    """record_manifest_reuse should increment reuse_count and set last_reused_at."""
    simulations_dir = _configure_simulation_storage(tmp_path, monkeypatch)

    fake_entities = [{"uuid": "ent1", "name": "Test Entity", "type": "Student"}]
    monkeypatch.setattr(
        "app.services.simulation_manager.ZepEntityReader",
        lambda: FakeZepEntityReader(entities=fake_entities, entity_types=["Student"]),
    )
    monkeypatch.setattr(
        "app.services.simulation_manager.OasisProfileGenerator", FakeOasisProfileGenerator
    )
    monkeypatch.setattr(
        "app.services.simulation_manager.SimulationConfigGenerator", FakeSimConfigGenerator
    )

    mgr = SimulationManager()
    state = mgr.create_simulation(
        project_id="proj_reuse", graph_id="graph_reuse", project_type="default"
    )
    mgr.prepare_simulation(
        simulation_id=state.simulation_id,
        simulation_requirement="test",
        document_text="test",
    )

    manifest_dict = mgr.record_manifest_reuse(state.simulation_id)
    assert manifest_dict is not None
    assert manifest_dict["reuse_count"] == 1
    assert manifest_dict["last_reused_at"] is not None

    manifest_dict2 = mgr.record_manifest_reuse(state.simulation_id)
    assert manifest_dict2["reuse_count"] == 2


def test_get_prepare_manifest_returns_none_for_legacy_workspace(tmp_path, monkeypatch):
    """Simulations created before manifest support should gracefully return None."""
    simulations_dir = _configure_simulation_storage(tmp_path, monkeypatch)

    from app.config import Config
    monkeypatch.setattr(Config, "OASIS_SIMULATION_DATA_DIR", str(simulations_dir))

    mgr = SimulationManager()
    state = mgr.create_simulation(
        project_id="proj_old", graph_id="graph_old", project_type="default"
    )

    # Simulate an old workspace: state.json exists but no manifest
    sim_dir = simulations_dir / state.simulation_id
    state_path = sim_dir / "state.json"
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(
        json.dumps(
            {
                "simulation_id": state.simulation_id,
                "project_id": "proj_old",
                "graph_id": "graph_old",
                "status": "ready",
                "config_generated": True,
                "entities_count": 5,
                "profiles_count": 5,
                "entity_types": ["Student"],
                "created_at": "2026-04-20T00:00:00",
                "updated_at": "2026-04-20T00:00:00",
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    # Also write required files so _check_simulation_prepared passes
    (sim_dir / "simulation_config.json").write_text("{}", encoding="utf-8")
    (sim_dir / "reddit_profiles.json").write_text("[]", encoding="utf-8")
    (sim_dir / "twitter_profiles.csv").write_text("user_id,name,username,user_char,description\n", encoding="utf-8")

    assert mgr.get_prepare_manifest(state.simulation_id) is None

    # _check_simulation_prepared should still work without crashing
    from app.api.simulation import _check_simulation_prepared

    is_prepared, info = _check_simulation_prepared(state.simulation_id)
    assert is_prepared is True
    assert "prepare_manifest" not in info
