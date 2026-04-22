from pathlib import Path
import sys


BACKEND_ROOT = Path(__file__).resolve().parents[2]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.services.consumer.models import (
    ResearchFinding,
    ResearchSource,
    ResearchSourceLane,
    ResearchSourceType,
    GraphVisibility,
)
from app.services.consumer.source_quality import (
    evaluate_source,
    evaluate_sources,
    build_source_quality_summary,
    apply_source_quality_to_findings,
)
from app.services.consumer.project_research_persistence import (
    persist_source_quality,
    load_source_quality,
)
from app.services.consumer.source_registry import SourceRegistry
from app.services.consumer.research_ingest import (
    resolve_research_findings,
    build_research_snapshot,
)
from app.services.consumer.brief_adapter import ConsumerBriefAdapter


def test_evaluate_source_lane_a_upload():
    src = ResearchSource(
        source_id="src_1",
        lane=ResearchSourceLane.LaneA,
        source_type=ResearchSourceType.Upload,
        label="Upload",
    )
    scored = evaluate_source(src)
    assert scored.trust_tier == 1
    assert scored.source_confidence >= 0.85
    assert scored.freshness_score >= 60
    assert "user_provided" in scored.coverage_tags
    assert any("lane_a" in r for r in scored.quality_reasons)


def test_evaluate_source_lane_b_public_web():
    src = ResearchSource(
        source_id="src_2",
        lane=ResearchSourceLane.LaneB,
        source_type=ResearchSourceType.PublicWeb,
        label="Web",
    )
    scored = evaluate_source(src)
    assert scored.trust_tier == 2
    assert scored.source_confidence < 0.7
    assert scored.freshness_score < 60
    assert "public_web" in scored.coverage_tags
    assert any("lane_b" in r for r in scored.quality_reasons)


def test_evaluate_source_lane_a_url():
    src = ResearchSource(
        source_id="src_3",
        lane=ResearchSourceLane.LaneA,
        source_type=ResearchSourceType.Url,
        label="URL",
    )
    scored = evaluate_source(src)
    assert scored.trust_tier == 1
    assert scored.source_confidence >= 0.8
    assert "url" in scored.coverage_tags


def test_evaluate_sources_is_deterministic():
    srcs = [
        ResearchSource(
            source_id="src_a",
            lane=ResearchSourceLane.LaneA,
            source_type=ResearchSourceType.Upload,
            label="A",
        ),
        ResearchSource(
            source_id="src_b",
            lane=ResearchSourceLane.LaneB,
            source_type=ResearchSourceType.PublicWeb,
            label="B",
        ),
    ]
    scored1 = evaluate_sources(srcs)
    scored2 = evaluate_sources(srcs)
    for s1, s2 in zip(scored1, scored2):
        assert s1.source_confidence == s2.source_confidence
        assert s1.freshness_score == s2.freshness_score
        assert s1.coverage_tags == s2.coverage_tags
        assert s1.quality_reasons == s2.quality_reasons


def test_build_source_quality_summary_structure():
    srcs = [
        ResearchSource(
            source_id="src_a",
            lane=ResearchSourceLane.LaneA,
            source_type=ResearchSourceType.Upload,
            label="A",
            trust_tier=1,
            source_confidence=0.9,
            freshness_score=70,
            coverage_tags=["user_provided"],
            quality_reasons=["lane_a_user_upload"],
        ),
        ResearchSource(
            source_id="src_b",
            lane=ResearchSourceLane.LaneB,
            source_type=ResearchSourceType.PublicWeb,
            label="B",
            trust_tier=2,
            source_confidence=0.5,
            freshness_score=40,
            coverage_tags=["public_web"],
            quality_reasons=["lane_b_public_web"],
        ),
    ]
    summary = build_source_quality_summary(srcs)
    assert summary["source_count"] == 2
    assert summary["lane_a_count"] == 1
    assert summary["lane_b_count"] == 1
    assert "average_source_confidence" in summary
    assert "average_freshness_score" in summary
    assert "trust_tier_distribution" in summary
    assert summary["trust_tier_distribution"]["1"] == 1
    assert summary["trust_tier_distribution"]["2"] == 1


def test_apply_source_quality_to_findings():
    sources = [
        ResearchSource(
            source_id="src_a",
            lane=ResearchSourceLane.LaneA,
            source_type=ResearchSourceType.Upload,
            label="A",
            trust_tier=1,
            source_confidence=0.9,
            quality_reasons=["lane_a_user_upload"],
        ),
    ]
    findings = [
        ResearchFinding(
            finding_id="f1",
            finding_type="risk_signal",
            summary="Risk",
            visibility=GraphVisibility.Restricted,
            source_id="src_a",
            confidence=0.5,
        ),
    ]
    updated = apply_source_quality_to_findings(findings, sources)
    assert updated[0].confidence >= 0.7
    assert updated[0].confidence_label != ""
    assert any("lane_a" in r for r in updated[0].confidence_reasons)


def test_apply_source_quality_to_findings_unknown_source():
    findings = [
        ResearchFinding(
            finding_id="f1",
            finding_type="risk_signal",
            summary="Risk",
            visibility=GraphVisibility.Restricted,
            source_id="unknown",
            confidence=0.5,
        ),
    ]
    updated = apply_source_quality_to_findings(findings, [])
    assert updated[0].confidence_label == "unknown"
    assert any("unknown" in r for r in updated[0].confidence_reasons)


def test_persist_and_load_source_quality(tmp_path):
    root = str(tmp_path / "uploads")
    summary = {
        "source_count": 2,
        "lane_a_count": 1,
        "lane_b_count": 1,
        "average_source_confidence": 0.7,
        "average_freshness_score": 55,
        "trust_tier_distribution": {"1": 1, "2": 1},
    }
    path = persist_source_quality("proj_sq", summary, upload_root=root)
    assert path.exists()

    loaded = load_source_quality("proj_sq", upload_root=root)
    assert loaded is not None
    assert loaded["source_count"] == 2
    assert loaded["average_source_confidence"] == 0.7


def test_load_source_quality_returns_none_when_missing(tmp_path):
    root = str(tmp_path / "uploads")
    loaded = load_source_quality("proj_missing", upload_root=root)
    assert loaded is None


def test_resolve_research_findings_includes_source_quality(tmp_path):
    root = str(tmp_path / "uploads")
    registry = SourceRegistry("proj_resolve_sq", upload_root=root)
    registry.register_source(
        lane=ResearchSourceLane.LaneA,
        source_type=ResearchSourceType.Upload,
        label="Upload",
    )

    brief = ConsumerBriefAdapter.from_payload(
        {
            "task_type": "concept_test",
            "product_concept_assets": ["Protein bar"],
            "research_goal": "Find signals",
            "optional_background_materials": ["Ingredient concern: sweetener debates"],
        }
    )

    findings = resolve_research_findings(
        brief,
        project_id="proj_resolve_sq",
        upload_root=root,
    )

    # At least one finding should have confidence_label populated
    assert any(f.confidence_label != "" for f in findings)


def test_build_research_snapshot_includes_source_quality_and_persists(tmp_path):
    root = str(tmp_path / "uploads")
    registry = SourceRegistry("proj_snap_sq", upload_root=root)
    registry.register_source(
        lane=ResearchSourceLane.LaneA,
        source_type=ResearchSourceType.Upload,
        label="Upload",
    )

    brief = ConsumerBriefAdapter.from_payload(
        {
            "task_type": "concept_test",
            "product_concept_assets": ["Protein bar"],
            "research_goal": "Find signals",
        }
    )

    snapshot = build_research_snapshot(
        "proj_snap_sq",
        brief=brief,
        upload_root=root,
    )

    # Sources in snapshot should have quality fields populated
    assert all(s.source_confidence > 0 for s in snapshot.sources)
    assert all(len(s.quality_reasons) > 0 for s in snapshot.sources)

    # Source quality should be persisted
    loaded = load_source_quality("proj_snap_sq", upload_root=root)
    assert loaded is not None
    assert loaded["source_count"] >= 1


def test_source_quality_backfill_for_old_projects(tmp_path):
    root = str(tmp_path / "uploads")
    # Simulate an old project with sources that lack Phase 4A fields
    registry = SourceRegistry("proj_old", upload_root=root)
    src = registry.register_source(
        lane=ResearchSourceLane.LaneA,
        source_type=ResearchSourceType.Upload,
        label="Old upload",
    )
    # Manually reset quality fields to simulate old data
    sources = registry.list_sources()
    assert sources[0].source_confidence == 0.0  # default from old model

    # Re-evaluate
    scored = evaluate_source(src)
    assert scored.source_confidence > 0
    assert len(scored.quality_reasons) > 0
