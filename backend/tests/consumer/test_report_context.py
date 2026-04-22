from app.services.consumer.models import (
    DocumentChunk,
    IngestedDocument,
    ResearchFinding,
    ResearchSnapshot,
    ResearchSource,
    RetrievalTrace,
)
from app.services.consumer.report_context import (
    ConsumerReportContextBuilder,
    _build_provenance_summary,
    _build_source_catalog,
    _enrich_finding,
    _enrich_trace,
    build_consumer_report_context,
    enrich_report_context_with_snapshot,
)
from app.services.consumer.scoring import ConsumerScoringService
from app.services.consumer.models import ConsumerBusinessBrief, ConsumerTaskType
from app.services.consumer.scoring import build_consumer_summary


def test_build_consumer_report_context_without_traces():
    summary = ConsumerScoringService().summarize(
        initial_labels=["positive", "neutral"],
        final_labels=["positive", "negative"],
    )
    findings = [
        ResearchFinding(
            finding_id="f1",
            finding_type="risk_signal",
            summary="Safety concern",
            visibility="Propagation_Only",
            source_label="brief_background",
        )
    ]
    events = []

    context = build_consumer_report_context(summary, findings, events)
    assert "retrieval_provenance" not in context
    assert "retrieval_traces" not in context


def test_build_consumer_report_context_with_traces():
    summary = ConsumerScoringService().summarize(
        initial_labels=["positive", "neutral"],
        final_labels=["positive", "negative"],
    )
    findings = [
        ResearchFinding(
            finding_id="f1",
            finding_type="risk_signal",
            summary="Safety concern",
            visibility="Propagation_Only",
            source_label="public_web",
            snippet_id="chk_1",
            retrieval_trace_id="trace_abc",
        )
    ]
    traces = [
        RetrievalTrace(
            trace_id="trace_abc",
            query="safety concerns",
            lane="lane_b",
            chunk_ids=["chk_1"],
            scores=[0.9],
        )
    ]
    events = []

    context = build_consumer_report_context(summary, findings, events, traces=traces)
    assert "retrieval_provenance" in context
    assert "retrieval_traces" in context
    prov = context["retrieval_provenance"]
    assert prov["trace_count"] == 1
    assert prov["lane_counts"]["lane_b"] == 1
    assert prov["findings"][0]["retrieval_trace_id"] == "trace_abc"
    assert prov["findings"][0]["retrieval_query"] == "safety concerns"


def test_build_provenance_summary_counts_lanes():
    findings = [
        ResearchFinding(
            finding_id="f1",
            finding_type="category_context",
            summary="A",
            source_label="brief_background",
        ),
        ResearchFinding(
            finding_id="f2",
            finding_type="risk_signal",
            summary="B",
            source_label="ingested_document",
        ),
        ResearchFinding(
            finding_id="f3",
            finding_type="trend_signal",
            summary="C",
            source_label="public_web",
        ),
    ]
    traces = []
    prov = _build_provenance_summary(findings, traces)
    assert prov["lane_counts"]["lane_a"] == 2
    assert prov["lane_counts"]["lane_b"] == 1
    assert prov["lane_counts"]["unknown"] == 0


def test_consumer_report_context_builder_loads_events():
    builder = ConsumerReportContextBuilder()
    events = builder.load_events("nonexistent_path.jsonl")
    assert events == []


def _make_snapshot() -> ResearchSnapshot:
    return ResearchSnapshot(
        snapshot_id="snap_1",
        project_id="proj_1",
        created_at="2024-01-01T00:00:00+00:00",
        sources=[
            ResearchSource(
                source_id="src_a",
                lane="lane_a",
                source_type="upload",
                label="Brief Background",
                uri="file://brief.pdf",
                trust_tier=2,
            ),
            ResearchSource(
                source_id="src_b",
                lane="lane_b",
                source_type="public_web",
                label="Web Article",
                uri="https://example.com/article",
                trust_tier=1,
            ),
        ],
        documents=[
            IngestedDocument(doc_id="doc_1", source_id="src_a", title="Brief"),
        ],
        chunks=[
            DocumentChunk(
                chunk_id="chk_1",
                doc_id="doc_1",
                source_id="src_a",
                text="Sugar content is higher than claimed.",
            ),
            DocumentChunk(
                chunk_id="chk_2",
                doc_id="doc_1",
                source_id="src_b",
                text="Market trends show increasing skepticism.",
            ),
        ],
        findings=[
            ResearchFinding(
                finding_id="f1",
                finding_type="risk_signal",
                summary="Sugar concern",
                source_id="src_a",
                snippet_id="chk_1",
                source_label="ingested_document",
            ),
        ],
        retrieval_traces=[
            RetrievalTrace(
                trace_id="t1",
                query="sugar claims",
                lane="lane_a",
                chunk_ids=["chk_1", "chk_2"],
            ),
        ],
    )


def test_build_source_catalog_returns_readable_entries():
    snapshot = _make_snapshot()
    catalog = _build_source_catalog(snapshot)
    assert len(catalog) == 2

    src_a = next(c for c in catalog if c["source_id"] == "src_a")
    assert src_a["label"] == "Brief Background"
    assert src_a["uri"] == "file://brief.pdf"
    assert src_a["lane"] == "lane_a"
    assert src_a["source_type"] == "upload"
    assert src_a["trust_tier"] == 2
    assert src_a["document_count"] == 1
    assert src_a["chunk_count"] == 1

    src_b = next(c for c in catalog if c["source_id"] == "src_b")
    assert src_b["lane"] == "lane_b"
    assert src_b["source_type"] == "public_web"


def test_enrich_finding_resolves_source_and_preview():
    snapshot = _make_snapshot()
    source_by_id = {s.source_id: s for s in snapshot.sources}
    chunk_by_id = {c.chunk_id: c for c in snapshot.chunks}
    finding = snapshot.findings[0]

    enriched = _enrich_finding(finding, source_by_id, chunk_by_id)
    assert enriched["finding_id"] == "f1"
    assert enriched["source_title"] == "Brief Background"
    assert enriched["source_uri"] == "file://brief.pdf"
    assert enriched["source_lane"] == "lane_a"
    assert enriched["source_type"] == "upload"
    assert enriched["trust_tier"] == 2
    assert "Sugar content" in enriched["evidence_preview"]


def test_enrich_finding_falls_back_to_evidence_snippets():
    snapshot = _make_snapshot()
    source_by_id = {s.source_id: s for s in snapshot.sources}
    chunk_by_id = {c.chunk_id: c for c in snapshot.chunks}
    finding = ResearchFinding(
        finding_id="f2",
        finding_type="trend_signal",
        summary="Trend",
        source_id="src_b",
        evidence_snippets=["Snippet from doc."],
    )

    enriched = _enrich_finding(finding, source_by_id, chunk_by_id)
    assert enriched["source_title"] == "Web Article"
    assert enriched["evidence_preview"] == "Snippet from doc."


def test_enrich_finding_graceful_when_source_missing():
    snapshot = _make_snapshot()
    source_by_id = {s.source_id: s for s in snapshot.sources}
    chunk_by_id = {c.chunk_id: c for c in snapshot.chunks}
    finding = ResearchFinding(
        finding_id="f3",
        finding_type="category_context",
        summary="Category",
        source_id="",
    )

    enriched = _enrich_finding(finding, source_by_id, chunk_by_id)
    assert "source_title" not in enriched
    assert "evidence_preview" not in enriched


def test_enrich_trace_resolves_primary_source_and_previews():
    snapshot = _make_snapshot()
    chunk_by_id = {c.chunk_id: c for c in snapshot.chunks}
    source_by_id = {s.source_id: s for s in snapshot.sources}
    trace = snapshot.retrieval_traces[0]

    enriched = _enrich_trace(trace, chunk_by_id, source_by_id)
    assert enriched["trace_id"] == "t1"
    assert enriched["query"] == "sugar claims"
    assert enriched["source_title"] == "Brief Background"
    assert enriched["source_count"] == 2
    assert len(enriched["chunk_previews"]) == 2
    assert "Sugar content" in enriched["chunk_previews"][0]["text_preview"]


def test_enrich_trace_graceful_when_chunks_missing():
    snapshot = _make_snapshot()
    chunk_by_id = {}
    source_by_id = {s.source_id: s for s in snapshot.sources}
    trace = snapshot.retrieval_traces[0]

    enriched = _enrich_trace(trace, chunk_by_id, source_by_id)
    assert enriched["trace_id"] == "t1"
    assert "source_title" not in enriched
    assert enriched["chunk_previews"] == []
    assert enriched["source_count"] == 0


def test_enrich_report_context_with_snapshot_adds_readable_fields():
    snapshot = _make_snapshot()
    context = {}
    enrich_report_context_with_snapshot(
        context, snapshot.findings, snapshot.retrieval_traces, snapshot
    )

    assert "source_catalog" in context
    assert len(context["source_catalog"]) == 2
    assert "enriched_findings" in context
    assert len(context["enriched_findings"]) == 1
    assert context["enriched_findings"][0]["source_title"] == "Brief Background"
    assert "enriched_traces" in context
    assert len(context["enriched_traces"]) == 1


def test_build_consumer_report_context_with_snapshot():
    summary = ConsumerScoringService().summarize(
        initial_labels=["positive", "neutral"],
        final_labels=["positive", "negative"],
    )
    snapshot = _make_snapshot()
    findings = [f.model_dump() for f in snapshot.findings]
    traces = [t.model_dump() for t in snapshot.retrieval_traces]

    context = build_consumer_report_context(
        summary, findings, [], traces=traces, snapshot=snapshot
    )
    assert "source_catalog" in context
    assert "enriched_findings" in context
    assert "enriched_traces" in context
    assert context["enriched_findings"][0]["source_title"] == "Brief Background"


def test_build_consumer_report_context_without_snapshot_omits_enrichment():
    summary = ConsumerScoringService().summarize(
        initial_labels=["positive", "neutral"],
        final_labels=["positive", "negative"],
    )
    findings = [
        ResearchFinding(
            finding_id="f1",
            finding_type="risk_signal",
            summary="Safety concern",
            visibility="Propagation_Only",
            source_label="brief_background",
        )
    ]
    context = build_consumer_report_context(summary, findings, [])
    assert "source_catalog" not in context
    assert "enriched_findings" not in context


def test_build_consumer_summary_and_context_surface_price_task_fields():
    brief = ConsumerBusinessBrief(
        task_type=ConsumerTaskType.PriceTest,
        product_concept_assets=[],
        price_points=["$9.99", "$14.99"],
        price_context="subscription monthly",
        research_goal="Test price sensitivity",
    )
    events = [
        {
            "event_id": "ev_1",
            "event_type": "risk_discovery",
            "actor_id": "M01",
            "target_ids": [],
            "trigger_finding_ids": [],
            "supporting_quote": "This price feels expensive for a daily purchase.",
            "round_index": 1,
        }
    ]

    summary = build_consumer_summary(
        events=events,
        findings=[],
        initial_labels=["neutral"],
        final_labels=["negative"],
        task_type="price_test",
        brief=brief,
    )
    context = build_consumer_report_context(summary, [], events)

    assert summary.task_type == "price_test"
    assert summary.acceptable_price_points == ["$9.99", "$14.99"]
    assert summary.resisted_price_points == ["$14.99"]
    assert context["task_type"] == "price_test"
    assert context["price_context"] == "subscription monthly"
    assert context["acceptable_price_points"] == ["$9.99", "$14.99"]
