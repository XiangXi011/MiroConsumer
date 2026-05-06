"""Phase 7D audit chain assembly."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List

from ...contracts.errors import NotFoundError
from ...repositories.factory import create_repository_bundle

CHAIN_TYPES = [
    ("report_conclusion", "report_id"),
    ("finding", "finding_id"),
    ("source", "source_id"),
    ("round_snapshot", "round_snapshot_id"),
    ("event", "event_id"),
    ("agent", "agent_id"),
    ("channel", "channel_id"),
    ("task", "task_id"),
    ("trace", "trace_id"),
]


class AuditChainService:
    """Build report-conclusion to trace_id lineage from existing payloads."""

    def __init__(self, report_repo: Any | None = None):
        if report_repo is None:
            report_repo = create_repository_bundle().report_repo
        self.report_repo = report_repo

    def build_report_chain(self, report_id: str) -> Dict[str, Any]:
        report = self.report_repo.get_report(report_id)
        if report is None:
            raise NotFoundError(f"Report not found: {report_id}")

        report_payload = report.to_dict() if hasattr(report, "to_dict") else dict(report)
        audit_payload = self._extract_audit_payload(report, report_payload)
        timestamp = (
            report_payload.get("created_at")
            or getattr(report, "created_at", "")
            or datetime.now(timezone.utc).isoformat()
        )
        chain = self._build_nodes(report_id, audit_payload, timestamp)
        complete = all(node["resource_id"] for node in chain)
        return {
            "report_id": report_id,
            "complete": complete,
            "chain": chain,
        }

    def _extract_audit_payload(self, report: Any, report_payload: Dict[str, Any]) -> Dict[str, Any]:
        audit_payload = {}
        for source in (
            getattr(report, "audit_chain", None),
            report_payload.get("audit_chain"),
            report_payload.get("details", {}).get("audit_chain") if isinstance(report_payload.get("details"), dict) else None,
        ):
            if isinstance(source, dict):
                audit_payload.update(source)
        return audit_payload

    def _build_nodes(
        self,
        report_id: str,
        audit_payload: Dict[str, Any],
        timestamp: str,
    ) -> List[Dict[str, Any]]:
        nodes = []
        for node_type, key in CHAIN_TYPES:
            resource_id = report_id if key == "report_id" else str(audit_payload.get(key) or f"unknown_{key}")
            nodes.append(
                {
                    "type": node_type,
                    "resource_id": resource_id,
                    "timestamp": str(audit_payload.get(f"{key}_timestamp") or timestamp),
                }
            )
        return nodes
