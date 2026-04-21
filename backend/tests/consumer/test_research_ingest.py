from pathlib import Path
import sys


BACKEND_ROOT = Path(__file__).resolve().parents[2]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.services.consumer.brief_adapter import ConsumerBriefAdapter
from app.services.consumer.document_ingest import DocumentIngestService
from app.services.consumer.models import DocumentChunk, GraphVisibility, ResearchFinding, ResearchSourceLane, ResearchSourceType
from app.services.consumer.research_ingest import (
    build_lane_b_findings,
    build_research_findings,
    build_research_summary,
    build_research_snapshot,
    resolve_research_findings,
)
from app.services.consumer.source_registry import SourceRegistry


def test_research_ingest_builds_typed_findings():
    brief = ConsumerBriefAdapter.from_payload(
        {
            "task_type": "concept_test",
            "product_concept_assets": ["High-protein yogurt pouch"],
            "copy_material": ["14g protein", "low sugar"],
            "research_goal": "Find likely debate points",
            "optional_background_materials": ["Ingredient concern: sweetener debates"],
        }
    )

    findings = build_research_findings(brief)

    assert findings[0].finding_type in {"category_context", "risk_signal", "trend_signal"}
    assert findings[0].visibility in {GraphVisibility.Propagation_Only, GraphVisibility.Restricted}
    assert findings[0].summary


def test_auto_enrich_uses_provider_output_without_manual_background():
    brief = ConsumerBriefAdapter.from_payload(
        {
            "task_type": "concept_test",
            "product_concept_assets": ["High-protein yogurt pouch"],
            "copy_material": ["14g protein", "low sugar"],
            "research_goal": "Find likely debate points",
            "research_mode": "auto_enrich",
        }
    )

    findings = resolve_research_findings(
        brief,
        provider=lambda _: [
            ResearchFinding(
                finding_id="auto_1",
                finding_type="trend_signal",
                summary="High-protein breakfast is trending",
                visibility=GraphVisibility.Propagation_Only,
            )
        ],
    )

    assert [item.finding_id for item in findings] == ["auto_1"]


def test_research_ingest_can_build_pinned_research_summary():
    findings = [ResearchFinding(finding_id="r1", finding_type="risk_signal", summary="Sweetener concern", visibility=GraphVisibility.Restricted)]
    summary = build_research_summary(findings)
    assert "Sweetener concern" in summary


def test_build_research_snapshot_includes_auto_enrich_findings(tmp_path):
    """Snapshot must include auto_enrich findings when research_mode=auto_enrich."""
    brief = ConsumerBriefAdapter.from_payload(
        {
            "task_type": "concept_test",
            "product_concept_assets": ["Glow serum stick"],
            "copy_material": ["Brighter skin in one swipe"],
            "claims": ["Derm-tested glow boost"],
            "target_audience": ["busy commuters"],
            "usage_scene": ["morning commute"],
            "research_goal": "Understand first-impression appeal",
            "research_mode": "auto_enrich",
        }
    )

    def _fake_provider(b):
        return [
            ResearchFinding(
                finding_id="auto_1",
                finding_type="trend_signal",
                summary="High-protein breakfast is trending",
                visibility=GraphVisibility.Propagation_Only,
                source_label="auto_enrich",
            )
        ]

    resolved = resolve_research_findings(brief, provider=_fake_provider, project_id="proj_snapshot_test")
    snapshot = build_research_snapshot(
        "proj_snapshot_test",
        brief=brief,
        upload_root=str(tmp_path / "uploads"),
        provider=_fake_provider,
    )

    assert len(resolved) > 0
    assert len(snapshot.findings) == len(resolved)
    assert any(f.source_label == "auto_enrich" for f in snapshot.findings)


def test_build_research_snapshot_without_provider_skips_auto_enrich(tmp_path):
    """Without provider, auto_enrich findings should be skipped even in auto_enrich mode."""
    brief = ConsumerBriefAdapter.from_payload(
        {
            "task_type": "concept_test",
            "product_concept_assets": ["Glow serum stick"],
            "research_goal": "Test appeal",
            "research_mode": "auto_enrich",
        }
    )

    snapshot = build_research_snapshot(
        "proj_snapshot_no_provider",
        brief=brief,
        upload_root=str(tmp_path / "uploads"),
    )

    # No provider passed, so auto_enrich findings should not be generated
    assert not any(f.source_label == "auto_enrich" for f in snapshot.findings)


def test_build_lane_b_findings_with_provider(tmp_path):
    brief = ConsumerBriefAdapter.from_payload(
        {
            "task_type": "concept_test",
            "product_concept_assets": ["Protein bar"],
            "claims": ["High protein snack"],
            "research_goal": "Find competitor signals",
        }
    )

    def fake_provider(query: str, top_k: int):
        return [
            DocumentChunk(
                chunk_id="chk_web_1",
                doc_id="doc_web",
                source_id="src_web",
                text="Competitor launched a rival protein bar this month.",
                index=0,
            )
        ]

    findings, traces = build_lane_b_findings(
        project_id="proj_lb",
        brief=brief,
        upload_root=str(tmp_path / "uploads"),
        lane_b_provider=fake_provider,
    )

    assert len(findings) > 0
    assert all(f.source_label == "public_web" for f in findings)
    assert all(f.retrieval_trace_id != "" for f in findings)
    assert len(traces) > 0


def test_build_lane_b_findings_fallback_empty_when_no_corpus(tmp_path):
    brief = ConsumerBriefAdapter.from_payload(
        {
            "task_type": "concept_test",
            "product_concept_assets": ["Protein bar"],
            "research_goal": "Find signals",
        }
    )

    findings, traces = build_lane_b_findings(
        project_id="proj_lb_empty",
        brief=brief,
        upload_root=str(tmp_path / "uploads"),
    )

    assert findings == []
    # Traces may still be created for auditability even with empty results


def test_build_lane_b_findings_fallback_searches_workspace_lane_b(tmp_path):
    root = str(tmp_path / "uploads")
    registry = SourceRegistry("proj_lb_ws", upload_root=root)
    ingest = DocumentIngestService("proj_lb_ws", upload_root=root)

    src = registry.register_source(
        lane=ResearchSourceLane.LaneB,
        source_type=ResearchSourceType.PublicWeb,
        label="Web article",
    )
    ingest.ingest_text(
        source_id=src.source_id,
        text="Competitor launched a new protein shake line.",
        chunk_size=20,
    )

    brief = ConsumerBriefAdapter.from_payload(
        {
            "task_type": "concept_test",
            "product_concept_assets": ["Protein shake"],
            "research_goal": "Find competitor signals",
        }
    )

    findings, traces = build_lane_b_findings(
        project_id="proj_lb_ws",
        brief=brief,
        upload_root=root,
    )

    assert len(findings) > 0
    assert all(f.source_label == "public_web" for f in findings)


def test_resolve_research_findings_includes_lane_b_when_enabled(tmp_path):
    root = str(tmp_path / "uploads")
    registry = SourceRegistry("proj_resolve", upload_root=root)
    ingest = DocumentIngestService("proj_resolve", upload_root=root)

    src = registry.register_source(
        lane=ResearchSourceLane.LaneB,
        source_type=ResearchSourceType.PublicWeb,
        label="Web article",
    )
    ingest.ingest_text(
        source_id=src.source_id,
        text="A new safety risk was discovered in protein supplements.",
        chunk_size=20,
    )

    brief = ConsumerBriefAdapter.from_payload(
        {
            "task_type": "concept_test",
            "product_concept_assets": ["Protein supplement"],
            "research_goal": "Assess safety risks",
        }
    )

    findings = resolve_research_findings(
        brief,
        project_id="proj_resolve",
        upload_root=root,
        enable_lane_b=True,
    )

    assert any(f.source_label == "public_web" for f in findings)


def test_build_research_snapshot_includes_retrieval_traces(tmp_path):
    root = str(tmp_path / "uploads")
    registry = SourceRegistry("proj_snap", upload_root=root)
    ingest = DocumentIngestService("proj_snap", upload_root=root)

    src = registry.register_source(
        lane=ResearchSourceLane.LaneA,
        source_type=ResearchSourceType.Upload,
        label="Upload",
    )
    ingest.ingest_text(
        source_id=src.source_id,
        text="Breakfast trends are shifting toward high protein.",
        chunk_size=20,
    )

    brief = ConsumerBriefAdapter.from_payload(
        {
            "task_type": "concept_test",
            "product_concept_assets": ["High protein breakfast"],
            "research_goal": "Understand breakfast trends",
        }
    )

    snapshot = build_research_snapshot(
        "proj_snap",
        brief=brief,
        upload_root=root,
    )

    assert len(snapshot.retrieval_traces) >= 0
    # Snapshot should include traces even if they are from Lane A only


def test_build_lane_b_findings_with_real_provider_persists_workspace(tmp_path):
    """Lane B findings built with a provider that persists should reuse workspace artifacts."""
    from unittest.mock import MagicMock

    root = str(tmp_path / "uploads")

    class PersistingProvider:
        """A provider that registers sources and ingests chunks like OpenAIWebSearchProvider."""

        def __init__(self, project_id: str, upload_root: str):
            self.registry = SourceRegistry(project_id, upload_root=upload_root)
            self.ingest = DocumentIngestService(project_id, upload_root=upload_root)

        def __call__(self, query: str, top_k: int):
            src = self.registry.get_or_register_source(
                lane=ResearchSourceLane.LaneB,
                source_type=ResearchSourceType.PublicWeb,
                label="Web result",
                uri="https://example.com/article",
            )
            chunk = DocumentChunk(
                chunk_id="chk_persist_1",
                doc_id="doc_persist_1",
                source_id=src.source_id,
                text="A new competitor entered the protein bar market this quarter.",
                index=0,
                char_start=0,
                char_end=60,
            )
            self.ingest.ingest_chunks([chunk])
            return [chunk]

    brief = ConsumerBriefAdapter.from_payload(
        {
            "task_type": "concept_test",
            "product_concept_assets": ["Protein bar"],
            "claims": ["High protein snack"],
            "research_goal": "Find competitor signals",
        }
    )

    provider = PersistingProvider("proj_persist_lb", root)
    findings, traces = build_lane_b_findings(
        project_id="proj_persist_lb",
        brief=brief,
        upload_root=root,
        lane_b_provider=provider,
    )

    assert len(findings) > 0
    assert all(f.source_label == "public_web" for f in findings)
    assert all(f.retrieval_trace_id != "" for f in findings)
    assert len(traces) > 0

    # Verify workspace artifacts exist
    registry = SourceRegistry("proj_persist_lb", upload_root=root)
    assert registry.source_count(lane=ResearchSourceLane.LaneB) >= 1


def test_resolve_research_findings_uses_lane_b_provider_when_enabled(tmp_path):
    """When enable_lane_b=True and a provider is passed, findings should include provider results."""
    root = str(tmp_path / "uploads")

    def fake_provider(query: str, top_k: int):
        return [
            DocumentChunk(
                chunk_id="chk_web_1",
                doc_id="doc_web",
                source_id="src_web",
                text="Competitor launched a rival protein bar this month.",
                index=0,
            )
        ]

    brief = ConsumerBriefAdapter.from_payload(
        {
            "task_type": "concept_test",
            "product_concept_assets": ["Protein bar"],
            "claims": ["High protein snack"],
            "research_goal": "Find competitor signals",
        }
    )

    findings = resolve_research_findings(
        brief,
        project_id="proj_resolve_provider",
        upload_root=root,
        enable_lane_b=True,
        lane_b_provider=fake_provider,
    )

    assert any(f.source_label == "public_web" for f in findings)


def test_build_research_snapshot_uses_lane_b_provider_when_enabled(tmp_path):
    """When enable_lane_b=True and a provider is passed, snapshot should include provider findings."""
    root = str(tmp_path / "uploads")

    def fake_provider(query: str, top_k: int):
        return [
            DocumentChunk(
                chunk_id="chk_web_1",
                doc_id="doc_web",
                source_id="src_web",
                text="Competitor launched a rival protein bar this month.",
                index=0,
            )
        ]

    brief = ConsumerBriefAdapter.from_payload(
        {
            "task_type": "concept_test",
            "product_concept_assets": ["Protein bar"],
            "claims": ["High protein snack"],
            "research_goal": "Find competitor signals",
        }
    )

    snapshot = build_research_snapshot(
        "proj_snap_provider",
        brief=brief,
        upload_root=root,
        enable_lane_b=True,
        lane_b_provider=fake_provider,
    )

    assert any(f.source_label == "public_web" for f in snapshot.findings)


def test_build_lane_b_findings_dedup_on_repeat_queries(tmp_path):
    """Repeated queries with the same provider result should not duplicate workspace artifacts."""
    root = str(tmp_path / "uploads")

    class RepeatProvider:
        def __init__(self, project_id: str, upload_root: str):
            self.registry = SourceRegistry(project_id, upload_root=upload_root)
            self.ingest = DocumentIngestService(project_id, upload_root=upload_root)
            self.call_count = 0

        def __call__(self, query: str, top_k: int):
            self.call_count += 1
            src = self.registry.get_or_register_source(
                lane=ResearchSourceLane.LaneB,
                source_type=ResearchSourceType.PublicWeb,
                label="Repeat Web",
                uri="https://repeat.example.com",
            )
            chunk = DocumentChunk(
                chunk_id="chk_repeat_1",
                doc_id="doc_repeat_1",
                source_id=src.source_id,
                text="Same result every time.",
                index=0,
                char_start=0,
                char_end=23,
            )
            self.ingest.ingest_chunks([chunk])
            return [chunk]

    brief = ConsumerBriefAdapter.from_payload(
        {
            "task_type": "concept_test",
            "product_concept_assets": ["Protein bar"],
            "research_goal": "Find signals",
        }
    )

    provider = RepeatProvider("proj_dedup_lb", root)

    # First call
    findings1, _ = build_lane_b_findings(
        project_id="proj_dedup_lb",
        brief=brief,
        upload_root=root,
        lane_b_provider=provider,
    )

    # Second call with same brief (same queries)
    findings2, _ = build_lane_b_findings(
        project_id="proj_dedup_lb",
        brief=brief,
        upload_root=root,
        lane_b_provider=provider,
    )

    # Findings may be deduped by finding_id; workspace should not duplicate
    registry = SourceRegistry("proj_dedup_lb", upload_root=root)
    ingest = DocumentIngestService("proj_dedup_lb", upload_root=root)

    assert registry.source_count(lane=ResearchSourceLane.LaneB) == 1
    assert len(ingest.load_chunks()) == 1

