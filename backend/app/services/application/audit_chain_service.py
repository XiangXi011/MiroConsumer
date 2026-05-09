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

    def build_evidence_graph(self, report_id: str) -> Dict[str, Any]:
        """Build a finding -> evidence -> source graph from report context."""
        report = self.report_repo.get_report(report_id)
        if report is None:
            raise NotFoundError(f"Report not found: {report_id}")

        report_payload = report.to_dict() if hasattr(report, "to_dict") else dict(report)
        context = self._extract_report_context(report, report_payload)
        enriched_findings = context.get("enriched_findings") or []
        source_catalog = context.get("source_catalog") or []
        source_by_id = {
            str(source.get("source_id")): source
            for source in source_catalog
            if isinstance(source, dict) and source.get("source_id")
        }
        source_trace_by_id = {
            str(source.get("source_id")): f"report_context.source_catalog[{index}]"
            for index, source in enumerate(source_catalog)
            if isinstance(source, dict) and source.get("source_id")
        }
        confidence_by_finding, confidence_trace_by_finding = self._confidence_by_finding_id(context)

        nodes: List[Dict[str, Any]] = []
        edges: List[Dict[str, Any]] = []
        node_ids = set()
        warnings: List[str] = []

        if not enriched_findings:
            warnings.append("no_enriched_findings")

        for index, finding in enumerate(enriched_findings):
            if not isinstance(finding, dict):
                continue
            finding_id = str(finding.get("finding_id") or f"finding_{index}")
            confidence = confidence_by_finding.get(finding_id, {})
            confidence_label = str(
                finding.get("confidence_label")
                or confidence.get("confidence_label")
                or "unknown"
            )
            confidence_score = finding.get("confidence_score", confidence.get("confidence_score", 0))
            low_confidence = self._is_low_confidence(confidence_label, confidence_score)

            finding_node_id = f"finding:{finding_id}"
            self._add_node(
                nodes,
                node_ids,
                {
                    "id": finding_node_id,
                    "type": "finding",
                    "resource_id": finding_id,
                    "label": finding.get("summary") or finding_id,
                    "summary": finding.get("summary") or "",
                    "finding_type": finding.get("finding_type") or "",
                    "confidence_label": confidence_label,
                    "confidence_score": confidence_score,
                    "confidence_reasons": confidence.get("confidence_reasons", []),
                    "low_confidence": low_confidence,
                    "traceable_fields": [f"report_context.enriched_findings[{index}]"],
                },
            )

            evidence_preview, evidence_trace_field = self._evidence_preview_with_trace(finding, index)
            if not evidence_preview:
                warnings.append(f"missing_evidence:{finding_id}")
                continue

            evidence_node_id = f"evidence:{finding_id}:0"
            self._add_node(
                nodes,
                node_ids,
                {
                    "id": evidence_node_id,
                    "type": "evidence",
                    "resource_id": evidence_node_id,
                    "label": evidence_preview[:80],
                    "text_preview": evidence_preview,
                    "source_id": finding.get("source_id") or "",
                    "retrieval_trace_id": finding.get("retrieval_trace_id") or "",
                    "confidence_label": confidence_label,
                    "confidence_score": confidence_score,
                    "low_confidence": low_confidence,
                    "traceable_fields": [evidence_trace_field],
                },
            )
            supported_trace_fields = [evidence_trace_field]
            confidence_trace = confidence_trace_by_finding.get(finding_id)
            if confidence_trace:
                supported_trace_fields.append(confidence_trace)
            edges.append(
                {
                    "id": f"{finding_node_id}->{evidence_node_id}",
                    "source": finding_node_id,
                    "target": evidence_node_id,
                    "type": "supported_by",
                    "traceable_fields": supported_trace_fields,
                }
            )

            source_id = str(finding.get("source_id") or "")
            source = source_by_id.get(source_id, {}) if source_id else {}
            if not source_id:
                warnings.append(f"missing_source:{finding_id}")
                continue

            source_node_id = f"source:{source_id}"
            source_trace = source_trace_by_id.get(source_id)
            source_node_trace_fields = (
                [source_trace]
                if source_trace
                else [f"report_context.enriched_findings[{index}].source_id"]
            )
            self._add_node(
                nodes,
                node_ids,
                {
                    "id": source_node_id,
                    "type": "source",
                    "resource_id": source_id,
                    "label": source.get("label") or finding.get("source_title") or source_id,
                    "uri": source.get("uri") or finding.get("source_uri") or "",
                    "source_type": source.get("source_type") or finding.get("source_type") or "",
                    "lane": source.get("lane") or finding.get("source_lane") or "",
                    "trust_tier": source.get("trust_tier", finding.get("trust_tier", 0)),
                    "traceable_fields": source_node_trace_fields,
                },
            )
            source_trace_fields = [f"report_context.enriched_findings[{index}].source_id"]
            if source_trace:
                source_trace_fields.append(source_trace)
            edges.append(
                {
                    "id": f"{evidence_node_id}->{source_node_id}",
                    "source": evidence_node_id,
                    "target": source_node_id,
                    "type": "sourced_from",
                    "traceable_fields": source_trace_fields,
                }
            )

        return {
            "report_id": report_id,
            "complete": bool(enriched_findings) and not any(
                warning.startswith("missing_") for warning in warnings
            ),
            "nodes": nodes,
            "edges": edges,
            "node_count": len(nodes),
            "edge_count": len(edges),
            "warnings": warnings,
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

    def _extract_report_context(self, report: Any, report_payload: Dict[str, Any]) -> Dict[str, Any]:
        for source in (
            getattr(report, "report_context", None),
            report_payload.get("report_context"),
            report_payload.get("details", {}).get("report_context") if isinstance(report_payload.get("details"), dict) else None,
        ):
            if isinstance(source, dict):
                return source
        return {}

    def _confidence_by_finding_id(self, context: Dict[str, Any]):
        report_confidence = context.get("report_confidence") if isinstance(context.get("report_confidence"), dict) else {}
        confidence_items = (
            report_confidence.get("finding_confidence_summary")
            or report_confidence.get("finding_confidences")
            or context.get("finding_confidences")
            or []
        )
        result: Dict[str, Dict[str, Any]] = {}
        trace_by_finding: Dict[str, str] = {}
        for index, item in enumerate(confidence_items):
            if isinstance(item, dict) and item.get("finding_id"):
                finding_id = str(item["finding_id"])
                result[finding_id] = item
                trace_by_finding[finding_id] = (
                    "report_context.report_confidence.finding_confidence_summary"
                    f"[{index}]"
                )
        return result, trace_by_finding

    def _is_low_confidence(self, label: str, score: Any) -> bool:
        try:
            numeric_score = float(score)
        except (TypeError, ValueError):
            numeric_score = 0
        return label in {"low", "unknown", ""} or numeric_score < 0.5

    def _evidence_preview_with_trace(self, finding: Dict[str, Any], finding_index: int):
        if finding.get("evidence_preview"):
            return (
                str(finding["evidence_preview"]),
                f"report_context.enriched_findings[{finding_index}].evidence_preview",
            )
        snippets = finding.get("evidence_snippets") or []
        if snippets:
            return (
                str(snippets[0]),
                f"report_context.enriched_findings[{finding_index}].evidence_snippets[0]",
            )
        evidence = finding.get("evidence")
        if isinstance(evidence, dict):
            for key in ("text_preview", "snippet", "summary"):
                if evidence.get(key):
                    return (
                        str(evidence[key]),
                        f"report_context.enriched_findings[{finding_index}].evidence.{key}",
                    )
        return "", f"report_context.enriched_findings[{finding_index}]"

    def _add_node(
        self,
        nodes: List[Dict[str, Any]],
        node_ids: set,
        node: Dict[str, Any],
    ) -> None:
        if node["id"] in node_ids:
            return
        node_ids.add(node["id"])
        nodes.append(node)

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
