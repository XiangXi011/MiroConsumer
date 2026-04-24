"""Tests for FilesystemConsumerProjectResearchProvider."""

import pytest

from app.repositories import ConsumerProjectResearchContext
from app.repositories.filesystem import FilesystemConsumerProjectResearchProvider
from app.models.project import ProjectManager
from app.services.consumer.models import (
    DocumentChunk,
    GraphVisibility,
    ResearchFinding,
    ResearchSnapshot,
    ResearchSource,
    ResearchSourceLane,
    ResearchSourceType,
    RetrievalTrace,
)
from app.services.consumer.project_research_persistence import (
    persist_snapshot,
)


def test_returns_empty_context_for_missing_project():
    provider = FilesystemConsumerProjectResearchProvider()
    ctx = provider.get_context("proj_does_not_exist")
    assert ctx.is_consumer_project is False
    assert ctx.brief_payload is None
    assert ctx.traces == []
    assert ctx.chunks == []
    assert ctx.sources == []


def test_returns_empty_context_for_non_consumer_project():
    project = ProjectManager.create_project(name="General Project")
    project.project_type = "default"
    ProjectManager.save_project(project)

    provider = FilesystemConsumerProjectResearchProvider()
    ctx = provider.get_context(project.project_id)
    assert ctx.is_consumer_project is False
    assert ctx.brief_payload is None
    assert ctx.traces == []
    assert ctx.chunks == []
    assert ctx.sources == []


def test_returns_consumer_context_with_brief_and_snapshot(tmp_path, monkeypatch):
    from app.config import Config
    monkeypatch.setattr(Config, "UPLOAD_FOLDER", str(tmp_path / "uploads"))

    project = ProjectManager.create_project(name="Consumer Project")
    project.project_type = "consumer_test"
    brief = {
        "task_type": "concept_test",
        "product_concept_assets": ["Widget"],
        "copy_material": ["Amazing widget"],
        "claims": ["Best widget"],
        "target_audience": ["techies"],
        "usage_scene": ["office"],
        "research_goal": "Test appeal",
    }
    project.consumer_brief = brief
    ProjectManager.save_project(project)

    snapshot = ResearchSnapshot(
        snapshot_id="snap_1",
        project_id=project.project_id,
        created_at="2026-04-24T10:00:00+00:00",
        sources=[
            ResearchSource(
                source_id="s1",
                lane=ResearchSourceLane.LaneA,
                source_type=ResearchSourceType.Upload,
                label="Source 1",
            )
        ],
        documents=[],
        chunks=[
            DocumentChunk(
                chunk_id="c1",
                doc_id="d1",
                source_id="s1",
                text="chunk text",
            )
        ],
        findings=[
            ResearchFinding(
                finding_id="f1",
                finding_type="risk_signal",
                summary="Risk",
                visibility=GraphVisibility.Restricted,
            )
        ],
        retrieval_traces=[
            RetrievalTrace(
                trace_id="t1",
                query="test query",
                lane=ResearchSourceLane.LaneA,
                chunk_ids=["c1"],
            )
        ],
        summary="Summary",
    )
    persist_snapshot(project.project_id, snapshot)

    provider = FilesystemConsumerProjectResearchProvider()
    ctx = provider.get_context(project.project_id)

    assert ctx.is_consumer_project is True
    assert ctx.brief_payload == brief
    assert len(ctx.traces) == 1
    assert ctx.traces[0].trace_id == "t1"
    assert len(ctx.chunks) == 1
    assert ctx.chunks[0].chunk_id == "c1"
    assert len(ctx.sources) == 1
    assert ctx.sources[0].source_id == "s1"


def test_returns_consumer_context_without_snapshot_when_missing(
    tmp_path, monkeypatch
):
    from app.config import Config
    monkeypatch.setattr(Config, "UPLOAD_FOLDER", str(tmp_path / "uploads"))

    project = ProjectManager.create_project(name="Consumer No Snapshot")
    project.project_type = "consumer_test"
    brief = {
        "task_type": "price_test",
        "product_concept_assets": ["Gadget"],
        "copy_material": ["Cool gadget"],
        "claims": ["Best gadget"],
        "target_audience": ["everyone"],
        "usage_scene": ["home"],
        "research_goal": "Test price",
        "price_points": ["$9.99"],
    }
    project.consumer_brief = brief
    ProjectManager.save_project(project)

    provider = FilesystemConsumerProjectResearchProvider()
    ctx = provider.get_context(project.project_id)

    assert ctx.is_consumer_project is True
    assert ctx.brief_payload == brief
    assert ctx.traces == []
    assert ctx.chunks == []
    assert ctx.sources == []
