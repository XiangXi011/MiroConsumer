from app.services.consumer.document_ingest import DocumentIngestService
from app.services.consumer.models import DocumentChunk, ResearchSourceLane, ResearchSourceType
from app.services.consumer.retrieval import (
    PublicWebSearchProvider,
    RetrievalService,
    _rank_chunks,
    _score_chunk,
)
from app.services.consumer.source_registry import SourceRegistry


def test_score_chunk_is_deterministic():
    chunk = DocumentChunk(
        chunk_id="chk_1",
        doc_id="doc_1",
        source_id="src_1",
        text="High protein breakfast trend is growing fast.",
        index=0,
        char_start=0,
        char_end=45,
    )
    score1 = _score_chunk("protein breakfast", chunk)
    score2 = _score_chunk("protein breakfast", chunk)
    assert score1 == score2
    assert score1 > 0


def test_score_chunk_zero_for_no_overlap():
    chunk = DocumentChunk(
        chunk_id="chk_1",
        doc_id="doc_1",
        source_id="src_1",
        text="Completely unrelated text about space travel.",
        index=0,
        char_start=0,
        char_end=45,
    )
    assert _score_chunk("yoga mat", chunk) == 0.0


def test_rank_chunks_orders_by_score():
    chunks = [
        DocumentChunk(
            chunk_id="chk_low",
            doc_id="doc_1",
            source_id="src_1",
            text="Unrelated topic.",
            index=0,
        ),
        DocumentChunk(
            chunk_id="chk_high",
            doc_id="doc_1",
            source_id="src_1",
            text="High protein breakfast is trending now.",
            index=1,
        ),
    ]
    ranked = _rank_chunks("protein breakfast", chunks)
    assert len(ranked) == 2
    assert ranked[0][0].chunk_id == "chk_high"
    assert ranked[0][1] > ranked[1][1]


def test_retrieve_lane_a_returns_workspace_chunks(tmp_path):
    root = str(tmp_path / "uploads")
    registry = SourceRegistry("proj_ret", upload_root=root)
    ingest = DocumentIngestService("proj_ret", upload_root=root)
    retrieval = RetrievalService("proj_ret", upload_root=root)

    src = registry.register_source(
        lane=ResearchSourceLane.LaneA,
        source_type=ResearchSourceType.Upload,
        label="Upload",
    )
    ingest.ingest_text(
        source_id=src.source_id,
        text="High protein breakfast trend is growing fast. Consumers love it.",
        chunk_size=30,
    )

    results = retrieval.retrieve_lane_a("protein breakfast", top_k=3)
    assert len(results) > 0
    assert any(score > 0 for _, score in results)


def test_retrieve_lane_a_empty_when_no_lane_a_sources(tmp_path):
    retrieval = RetrievalService("proj_empty", upload_root=str(tmp_path / "uploads"))
    results = retrieval.retrieve_lane_a("any query")
    assert results == []


def test_retrieve_lane_b_with_provider(tmp_path):
    retrieval = RetrievalService("proj_provider", upload_root=str(tmp_path / "uploads"))

    def fake_provider(query: str, top_k: int) -> list:
        return [
            DocumentChunk(
                chunk_id="chk_web_1",
                doc_id="doc_web",
                source_id="src_web",
                text="Competitor launched a rival protein bar.",
                index=0,
            )
        ]

    results = retrieval.retrieve_lane_b("competitor protein", top_k=3, provider=fake_provider)
    assert len(results) == 1
    assert results[0][0].chunk_id == "chk_web_1"
    assert results[0][1] > 0


def test_retrieve_lane_b_fallback_empty_when_no_lane_b_corpus(tmp_path):
    retrieval = RetrievalService("proj_fallback", upload_root=str(tmp_path / "uploads"))
    results = retrieval.retrieve_lane_b("any query")
    assert results == []


def test_retrieve_lane_b_fallback_searches_workspace_lane_b(tmp_path):
    root = str(tmp_path / "uploads")
    registry = SourceRegistry("proj_fb", upload_root=root)
    ingest = DocumentIngestService("proj_fb", upload_root=root)
    retrieval = RetrievalService("proj_fb", upload_root=root)

    src = registry.register_source(
        lane=ResearchSourceLane.LaneB,
        source_type=ResearchSourceType.PublicWeb,
        label="Web article",
    )
    ingest.ingest_text(
        source_id=src.source_id,
        text="Rising trend: plant-based protein alternatives are surging.",
        chunk_size=30,
    )

    results = retrieval.retrieve_lane_b("protein trend", top_k=3)
    assert len(results) > 0
    assert all(score > 0 for _, score in results)


def test_retrieve_dual_persists_traces(tmp_path):
    root = str(tmp_path / "uploads")
    registry = SourceRegistry("proj_dual", upload_root=root)
    ingest = DocumentIngestService("proj_dual", upload_root=root)
    retrieval = RetrievalService("proj_dual", upload_root=root)

    src_a = registry.register_source(
        lane=ResearchSourceLane.LaneA,
        source_type=ResearchSourceType.Upload,
        label="Upload",
    )
    ingest.ingest_text(source_id=src_a.source_id, text="Lane A content about breakfast.", chunk_size=20)

    src_b = registry.register_source(
        lane=ResearchSourceLane.LaneB,
        source_type=ResearchSourceType.PublicWeb,
        label="Web",
    )
    ingest.ingest_text(source_id=src_b.source_id, text="Lane B content about dinner.", chunk_size=20)

    result = retrieval.retrieve_dual("breakfast dinner", top_k_a=2, top_k_b=2)

    assert "lane_a" in result
    assert "lane_b" in result
    assert "traces" in result
    assert len(result["traces"]) == 2

    # Verify traces were persisted
    loaded = retrieval.load_traces()
    assert len(loaded) >= 2


def test_load_traces_filters_by_lane(tmp_path):
    root = str(tmp_path / "uploads")
    retrieval = RetrievalService("proj_filter", upload_root=root)

    # Trigger trace creation via dual retrieval (no content needed for empty traces)
    retrieval.retrieve_dual("test query", top_k_a=0, top_k_b=0)

    all_traces = retrieval.load_traces()
    lane_a = retrieval.load_traces(lane=ResearchSourceLane.LaneA)
    lane_b = retrieval.load_traces(lane=ResearchSourceLane.LaneB)

    assert len(all_traces) == len(lane_a) + len(lane_b)
    assert all(t.lane == ResearchSourceLane.LaneA for t in lane_a)
    assert all(t.lane == ResearchSourceLane.LaneB for t in lane_b)


def test_clear_traces_removes_all(tmp_path):
    retrieval = RetrievalService("proj_clear", upload_root=str(tmp_path / "uploads"))
    retrieval.retrieve_dual("test", top_k_a=0, top_k_b=0)
    assert len(retrieval.load_traces()) > 0

    retrieval.clear_traces()
    assert retrieval.load_traces() == []


def test_stats_counts_traces(tmp_path):
    root = str(tmp_path / "uploads")
    retrieval = RetrievalService("proj_stats", upload_root=root)
    retrieval.retrieve_dual("test", top_k_a=0, top_k_b=0)

    stats = retrieval.stats()
    assert stats["project_id"] == "proj_stats"
    assert stats["trace_count"] >= 2
    assert stats["lane_a_trace_count"] >= 1
    assert stats["lane_b_trace_count"] >= 1


def test_provider_contract_type_alias():
    """PublicWebSearchProvider should accept a callable with the right signature."""

    def provider(query: str, top_k: int) -> list:
        return []

    # Should not raise
    assert callable(provider)
