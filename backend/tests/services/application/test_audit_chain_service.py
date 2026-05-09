"""Phase 7D audit chain service tests."""

from types import SimpleNamespace


class StubReportRepo:
    def __init__(self, report):
        self.report = report

    def get_report(self, report_id):
        if report_id == self.report.report_id:
            return self.report
        return None


def test_audit_chain_builds_complete_fixed_chain_from_report_payload():
    from app.services.application.audit_chain_service import AuditChainService

    report = SimpleNamespace(
        report_id="report_1",
        created_at="2026-04-30T00:00:00",
        to_dict=lambda: {
            "report_id": "report_1",
            "audit_chain": {
                "finding_id": "finding_1",
                "source_id": "source_1",
                "round_snapshot_id": "round_1",
                "event_id": "event_1",
                "agent_id": "agent_1",
                "channel_id": "xiaohongshu",
                "task_id": "task_1",
                "trace_id": "trace_1",
            },
        },
    )

    chain = AuditChainService(report_repo=StubReportRepo(report)).build_report_chain("report_1")

    assert chain["report_id"] == "report_1"
    assert chain["complete"] is True
    assert [node["type"] for node in chain["chain"]] == [
        "report_conclusion",
        "finding",
        "source",
        "round_snapshot",
        "event",
        "agent",
        "channel",
        "task",
        "trace",
    ]
    for node in chain["chain"]:
        assert node["resource_id"]
        assert node["timestamp"]


def test_audit_chain_missing_report_raises_not_found():
    import pytest

    from app.contracts.errors import NotFoundError
    from app.services.application.audit_chain_service import AuditChainService

    service = AuditChainService(report_repo=SimpleNamespace(get_report=lambda report_id: None))

    with pytest.raises(NotFoundError):
        service.build_report_chain("missing")


def test_evidence_graph_builds_finding_evidence_source_nodes_with_confidence():
    from app.services.application.audit_chain_service import AuditChainService

    report = SimpleNamespace(
        report_id="report_graph",
        created_at="2026-05-09T00:00:00",
        to_dict=lambda: {
            "report_id": "report_graph",
            "report_context": {
                "source_catalog": [
                    {
                        "source_id": "src_brief",
                        "label": "Brief Background",
                        "uri": "file://brief.pdf",
                        "source_type": "upload",
                        "trust_tier": 2,
                    }
                ],
                "enriched_findings": [
                    {
                        "finding_id": "finding_risk",
                        "finding_type": "risk_signal",
                        "summary": "Sugar claim needs proof",
                        "source_id": "src_brief",
                        "source_title": "Brief Background",
                        "source_uri": "file://brief.pdf",
                        "evidence_preview": "Consumers asked for clinical evidence.",
                        "retrieval_trace_id": "trace_1",
                        "confidence_label": "low",
                        "confidence_score": 0.32,
                    }
                ],
                "report_confidence": {
                    "finding_confidence_summary": [
                        {
                            "finding_id": "finding_risk",
                            "confidence_label": "low",
                            "confidence_score": 0.32,
                            "confidence_reasons": ["evidence_validated_weak"],
                        }
                    ]
                },
            },
        },
    )

    graph = AuditChainService(report_repo=StubReportRepo(report)).build_evidence_graph("report_graph")

    assert graph["report_id"] == "report_graph"
    assert graph["complete"] is True
    assert graph["node_count"] == 3
    assert graph["edge_count"] == 2
    node_by_id = {node["id"]: node for node in graph["nodes"]}
    assert node_by_id["finding:finding_risk"]["type"] == "finding"
    assert node_by_id["finding:finding_risk"]["confidence_label"] == "low"
    assert node_by_id["finding:finding_risk"]["low_confidence"] is True
    assert node_by_id["evidence:finding_risk:0"]["text_preview"] == "Consumers asked for clinical evidence."
    assert node_by_id["source:src_brief"]["uri"] == "file://brief.pdf"
    assert graph["edges"] == [
        {
            "id": "finding:finding_risk->evidence:finding_risk:0",
            "source": "finding:finding_risk",
            "target": "evidence:finding_risk:0",
            "type": "supported_by",
            "traceable_fields": [
                "report_context.enriched_findings[0].evidence_preview",
                "report_context.report_confidence.finding_confidence_summary[0]",
            ],
        },
        {
            "id": "evidence:finding_risk:0->source:src_brief",
            "source": "evidence:finding_risk:0",
            "target": "source:src_brief",
            "type": "sourced_from",
            "traceable_fields": [
                "report_context.enriched_findings[0].source_id",
                "report_context.source_catalog[0]",
            ],
        },
    ]


def test_evidence_graph_reports_empty_context_as_incomplete():
    from app.services.application.audit_chain_service import AuditChainService

    report = SimpleNamespace(
        report_id="report_empty",
        created_at="2026-05-09T00:00:00",
        to_dict=lambda: {"report_id": "report_empty", "report_context": {}},
    )

    graph = AuditChainService(report_repo=StubReportRepo(report)).build_evidence_graph("report_empty")

    assert graph["report_id"] == "report_empty"
    assert graph["complete"] is False
    assert graph["nodes"] == []
    assert graph["edges"] == []
    assert "no_enriched_findings" in graph["warnings"]


def test_evidence_graph_traces_evidence_snippet_fallback():
    from app.services.application.audit_chain_service import AuditChainService

    report = SimpleNamespace(
        report_id="report_snippet",
        created_at="2026-05-09T00:00:00",
        to_dict=lambda: {
            "report_id": "report_snippet",
            "report_context": {
                "source_catalog": [
                    {"source_id": "src_review", "label": "Review notes", "uri": "file://review.md"}
                ],
                "enriched_findings": [
                    {
                        "finding_id": "finding_snippet",
                        "summary": "Snippet fallback",
                        "source_id": "src_review",
                        "evidence_snippets": ["Snippet from source."],
                    }
                ],
            },
        },
    )

    graph = AuditChainService(report_repo=StubReportRepo(report)).build_evidence_graph("report_snippet")

    node_by_id = {node["id"]: node for node in graph["nodes"]}
    evidence = node_by_id["evidence:finding_snippet:0"]
    assert evidence["text_preview"] == "Snippet from source."
    assert evidence["traceable_fields"] == [
        "report_context.enriched_findings[0].evidence_snippets[0]"
    ]
    assert graph["edges"][0]["traceable_fields"] == [
        "report_context.enriched_findings[0].evidence_snippets[0]"
    ]
