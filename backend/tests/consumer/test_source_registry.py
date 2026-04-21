from pathlib import Path

from app.services.consumer.models import ResearchSourceLane, ResearchSourceType
from app.services.consumer.source_registry import SourceRegistry


def test_register_and_list_lane_a_sources(tmp_path):
    registry = SourceRegistry("proj_test", upload_root=str(tmp_path / "uploads"))

    src = registry.register_source(
        lane=ResearchSourceLane.LaneA,
        source_type=ResearchSourceType.Upload,
        label="User upload: market_report.pdf",
        uri="/projects/proj_test/files/market_report.pdf",
    )

    assert src.lane == ResearchSourceLane.LaneA
    assert src.trust_tier == 1
    assert src.source_id.startswith("src_")

    sources = registry.list_sources()
    assert len(sources) == 1
    assert sources[0].label == "User upload: market_report.pdf"


def test_lane_b_has_lower_trust_tier(tmp_path):
    registry = SourceRegistry("proj_test", upload_root=str(tmp_path / "uploads"))

    src = registry.register_source(
        lane=ResearchSourceLane.LaneB,
        source_type=ResearchSourceType.PublicWeb,
        label="Public web: competitor news",
        uri="https://example.com/news",
    )

    assert src.lane == ResearchSourceLane.LaneB
    assert src.trust_tier == 2


def test_list_sources_filters_by_lane(tmp_path):
    registry = SourceRegistry("proj_test", upload_root=str(tmp_path / "uploads"))

    registry.register_source(
        lane=ResearchSourceLane.LaneA,
        source_type=ResearchSourceType.Upload,
        label="Upload 1",
    )
    registry.register_source(
        lane=ResearchSourceLane.LaneB,
        source_type=ResearchSourceType.PublicWeb,
        label="Web 1",
    )

    assert len(registry.list_sources(lane=ResearchSourceLane.LaneA)) == 1
    assert len(registry.list_sources(lane=ResearchSourceLane.LaneB)) == 1
    assert len(registry.list_sources()) == 2


def test_remove_source(tmp_path):
    registry = SourceRegistry("proj_test", upload_root=str(tmp_path / "uploads"))

    src = registry.register_source(
        lane=ResearchSourceLane.LaneA,
        source_type=ResearchSourceType.Url,
        label="URL source",
    )

    assert registry.remove_source(src.source_id) is True
    assert registry.remove_source(src.source_id) is False
    assert registry.source_count() == 0


def test_clear_lane(tmp_path):
    registry = SourceRegistry("proj_test", upload_root=str(tmp_path / "uploads"))

    registry.register_source(
        lane=ResearchSourceLane.LaneA,
        source_type=ResearchSourceType.Upload,
        label="Upload 1",
    )
    registry.register_source(
        lane=ResearchSourceLane.LaneA,
        source_type=ResearchSourceType.Upload,
        label="Upload 2",
    )
    registry.register_source(
        lane=ResearchSourceLane.LaneB,
        source_type=ResearchSourceType.PublicWeb,
        label="Web 1",
    )

    removed = registry.clear_lane(ResearchSourceLane.LaneA)
    assert removed == 2
    assert registry.source_count() == 1
    assert registry.source_count(lane=ResearchSourceLane.LaneB) == 1


def test_persistence_across_instances(tmp_path):
    root = str(tmp_path / "uploads")
    registry1 = SourceRegistry("proj_persist", upload_root=root)
    src = registry1.register_source(
        lane=ResearchSourceLane.LaneA,
        source_type=ResearchSourceType.Upload,
        label="Persistent source",
    )

    registry2 = SourceRegistry("proj_persist", upload_root=root)
    loaded = registry2.get_source(src.source_id)

    assert loaded is not None
    assert loaded.label == "Persistent source"


def test_to_dict_includes_counts(tmp_path):
    registry = SourceRegistry("proj_test", upload_root=str(tmp_path / "uploads"))

    registry.register_source(
        lane=ResearchSourceLane.LaneA,
        source_type=ResearchSourceType.Upload,
        label="Upload 1",
    )
    registry.register_source(
        lane=ResearchSourceLane.LaneB,
        source_type=ResearchSourceType.PublicWeb,
        label="Web 1",
    )

    d = registry.to_dict()
    assert d["project_id"] == "proj_test"
    assert d["source_count"] == 2
    assert d["lane_a_count"] == 1
    assert d["lane_b_count"] == 1


def test_get_or_register_source_dedupes_by_uri(tmp_path):
    registry = SourceRegistry("proj_dedup", upload_root=str(tmp_path / "uploads"))

    src1 = registry.get_or_register_source(
        lane=ResearchSourceLane.LaneB,
        source_type=ResearchSourceType.PublicWeb,
        label="Web article",
        uri="https://example.com/article",
    )
    src2 = registry.get_or_register_source(
        lane=ResearchSourceLane.LaneB,
        source_type=ResearchSourceType.PublicWeb,
        label="Different label",
        uri="https://example.com/article",
    )

    assert src1.source_id == src2.source_id
    assert registry.source_count(lane=ResearchSourceLane.LaneB) == 1


def test_get_or_register_source_creates_new_when_uri_differs(tmp_path):
    registry = SourceRegistry("proj_new", upload_root=str(tmp_path / "uploads"))

    src1 = registry.get_or_register_source(
        lane=ResearchSourceLane.LaneB,
        source_type=ResearchSourceType.PublicWeb,
        label="Article A",
        uri="https://example.com/a",
    )
    src2 = registry.get_or_register_source(
        lane=ResearchSourceLane.LaneB,
        source_type=ResearchSourceType.PublicWeb,
        label="Article B",
        uri="https://example.com/b",
    )

    assert src1.source_id != src2.source_id
    assert registry.source_count(lane=ResearchSourceLane.LaneB) == 2
