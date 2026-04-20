from app.models.project import Project, ProjectStatus


def test_project_round_trip_preserves_consumer_metadata():
    project = Project(
        project_id="proj_123",
        name="Consumer Simulation",
        status=ProjectStatus.CREATED,
        created_at="2026-04-20T10:00:00",
        updated_at="2026-04-20T10:05:00",
        project_type="consumer_simulation",
        consumer_brief={
            "audience": "first-time buyers",
            "goals": ["validate demand", "test onboarding"],
        },
        consumer_context={
            "region": "CN",
            "channels": ["wechat", "xiaohongshu"],
        },
    )

    payload = project.to_dict()
    restored = Project.from_dict(payload)

    assert restored == project
    assert payload["project_type"] == "consumer_simulation"
    assert payload["consumer_brief"] == project.consumer_brief
    assert payload["consumer_context"] == project.consumer_context


def test_project_from_dict_defaults_legacy_fields():
    project = Project.from_dict(
        {
            "project_id": "proj_legacy",
            "name": "Legacy Project",
            "status": "created",
            "created_at": "2026-04-20T09:00:00",
            "updated_at": "2026-04-20T09:05:00",
        }
    )

    assert project.project_type == "default"
    assert project.consumer_brief is None
    assert project.consumer_context is None
    assert project.files == []
    assert project.total_text_length == 0
