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
