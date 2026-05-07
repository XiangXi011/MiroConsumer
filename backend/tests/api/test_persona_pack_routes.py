import io
import json
from pathlib import Path

from app import create_app
from app.config import Config
from app.models.project import ProjectManager


def _persona_pack_payload() -> str:
    return json.dumps(
        [
            {
                "persona_id": "CRM01",
                "label": "CRM Moms",
                "attention_drivers": ["safety"],
                "risk_sensitivities": ["price"],
                "expression_style": "practical",
                "search_propensity": "high",
                "cognition_level": "high",
                "herd_tendency": "medium",
                "influence_weight": 0.7,
            }
        ]
    )


def test_upload_project_persona_pack_and_list_with_project_id(tmp_path, monkeypatch):
    monkeypatch.setattr(Config, "UPLOAD_FOLDER", str(tmp_path / "uploads"))
    monkeypatch.setattr(ProjectManager, "PROJECTS_DIR", str(tmp_path / "uploads" / "projects"))

    project = ProjectManager.create_project(name="Persona Upload")
    ProjectManager.save_project(project)

    app = create_app()
    app.config["TESTING"] = True
    with app.test_client() as client:
        response = client.post(
            f"/api/graph/project/{project.project_id}/persona-packs",
            data={
                "label": "CRM Segment Pack",
                "pack_class": "custom",
                "pack_origin": "crm_segment_pack",
                "persona_pack_file": (
                    io.BytesIO(_persona_pack_payload().encode("utf-8")),
                    "crm_segment.json",
                ),
            },
            content_type="multipart/form-data",
        )
        assert response.status_code == 200
        payload = response.get_json()["data"]
        assert payload["source"] == "custom"
        assert payload["pack_origin"] == "crm_segment_pack"

        listed = client.get(f"/api/graph/persona-packs?project_id={project.project_id}")
        assert listed.status_code == 200
        pack_ids = {item["pack_id"] for item in listed.get_json()["data"]}
        assert payload["pack_id"] in pack_ids

    stored_files = list((Path(Config.UPLOAD_FOLDER) / "projects" / project.project_id / "persona_packs").glob("*.json"))
    assert stored_files
