"""Consumer report context assembly helpers for ReportAgent."""

from __future__ import annotations

import json
import os
from collections import Counter
from dataclasses import asdict
from typing import Any, Dict, List, Optional

from ..config import Config
from ..models.project import ProjectManager
from ..utils.logger import get_logger
from .consumer.project_research_persistence import (
    artifacts_exist,
    load_persisted_findings,
    load_persisted_snapshot,
)
from .consumer.report_context import ConsumerReportContextBuilder

try:
    from .consumer.selling_point_analyzer import analyze_selling_points
except ImportError:
    analyze_selling_points = None  # type: ignore[assignment]

try:
    from .consumer.compliance_checker import check_compliance
except ImportError:
    check_compliance = None  # type: ignore[assignment]

logger = get_logger('miroconsumer.report_agent')


class ConsumerReportContextMixin:
    def _build_consumer_report_context(self) -> Dict[str, Any]:
        rounds_path = os.path.join(
            Config.UPLOAD_FOLDER,
            "simulations",
            self.simulation_id,
            "consumer_rounds.jsonl",
        )
        builder = ConsumerReportContextBuilder()
        snapshots = builder.load_events(rounds_path)
        context: Dict[str, Any]
        if not snapshots:
            from .consumer.society.report_adapter import SocietyReportAdapter

            society_context = SocietyReportAdapter().build_report_context(self.simulation_id)
            if society_context.get("society_agents_count", 0) > 0:
                context = self._build_consumer_context_from_society_context(society_context)
            else:
                raise ValueError(f"消费者传播快照不存在: {self.simulation_id}")
        else:
            # Phase 1 baseline context
            context = builder.build(snapshots)

        # Extract propagation events for Phase 2 enrichment
        all_events = []
        for snap in snapshots:
            for event_data in snap.get("propagation_events", []):
                all_events.append(event_data)

        # Load research findings and snapshot
        # Prefer project-level persisted artifacts when available
        research_findings: List[Any] = []
        retrieval_traces: List[Any] = []
        research_snapshot: Dict[str, Any] = {}

        project_id = self.project_id
        if project_id is None:
            # Fall back to reading project_id from simulation state
            state_path = os.path.join(
                Config.UPLOAD_FOLDER, "simulations", self.simulation_id, "state.json"
            )
            if os.path.exists(state_path):
                with open(state_path, "r", encoding="utf-8") as f:
                    state_data = json.load(f)
                project_id = state_data.get("project_id")

        loaded_from_project = False
        if project_id and artifacts_exist(project_id, upload_root=Config.UPLOAD_FOLDER):
            persisted_findings = load_persisted_findings(
                project_id, upload_root=Config.UPLOAD_FOLDER
            )
            persisted_snapshot = load_persisted_snapshot(
                project_id, upload_root=Config.UPLOAD_FOLDER
            )
            if persisted_findings is not None and persisted_snapshot is not None:
                research_findings = [f.model_dump() for f in persisted_findings]
                research_snapshot = {
                    "snapshot_id": persisted_snapshot.snapshot_id,
                    "source_count": len(persisted_snapshot.sources),
                    "document_count": len(persisted_snapshot.documents),
                    "chunk_count": len(persisted_snapshot.chunks),
                    "finding_count": len(persisted_snapshot.findings),
                    "retrieval_trace_count": len(persisted_snapshot.retrieval_traces),
                }
                retrieval_traces = [
                    t.model_dump() for t in persisted_snapshot.retrieval_traces
                ]
                loaded_from_project = True

        consumer_config: Dict[str, Any] = {}
        consumer_config_path = os.path.join(
            Config.UPLOAD_FOLDER, "simulations", self.simulation_id, "consumer_config.json"
        )
        if os.path.exists(consumer_config_path):
            with open(consumer_config_path, "r", encoding="utf-8") as f:
                consumer_config = json.load(f)
        if not loaded_from_project:
            research_findings = consumer_config.get("research_findings", [])
            retrieval_traces = consumer_config.get("retrieval_traces", [])
            research_snapshot = consumer_config.get("research_snapshot", {})
        # When loaded_from_project is True, project-level artifacts are authoritative
        # for research_findings/retrieval_traces/research_snapshot. consumer_config is
        # still read above for consumer_brief/task_type extraction below.
        # However, if propagation events reference finding_ids not present in project
        # findings, append matching consumer_config findings/traces as supplemental.
        supplemental_merged = False
        if loaded_from_project and consumer_config and all_events:
            event_finding_ids = set()
            for event in all_events:
                for fid in event.get("trigger_finding_ids", []):
                    if fid:
                        event_finding_ids.add(fid)
            project_finding_ids = {
                f.get("finding_id") for f in research_findings if f.get("finding_id")
            }
            missing_ids = event_finding_ids - project_finding_ids
            if missing_ids:
                cc_findings = consumer_config.get("research_findings", [])
                cc_traces = consumer_config.get("retrieval_traces", [])
                existing_trace_ids = {
                    t.get("trace_id") for t in retrieval_traces if t.get("trace_id")
                }
                for finding in cc_findings:
                    if finding.get("finding_id") in missing_ids:
                        research_findings.append(finding)
                        supplemental_merged = True
                        trace_id = finding.get("retrieval_trace_id")
                        if trace_id:
                            for t in cc_traces:
                                if t.get("trace_id") == trace_id and trace_id not in existing_trace_ids:
                                    retrieval_traces.append(t)
                                    existing_trace_ids.add(trace_id)
                                    break

        # Extract task_type from consumer brief when available
        task_type: Optional[str] = None
        brief = None
        consumer_brief_summary = consumer_config.get("consumer_brief", {})
        if isinstance(consumer_brief_summary, dict) and consumer_brief_summary.get("task_type"):
            task_type = consumer_brief_summary.get("task_type")
            from ..services.consumer.brief_adapter import ConsumerBriefAdapter
            brief = ConsumerBriefAdapter.from_payload(consumer_brief_summary)
        elif self.project_id:
            project = ProjectManager.get_project(self.project_id)
            if project and getattr(project, "consumer_brief", None):
                from ..services.consumer.brief_adapter import ConsumerBriefAdapter
                brief = ConsumerBriefAdapter.from_payload(project.consumer_brief)
                task_type = brief.task_type.value

        # Include research snapshot and findings in report context
        context["research_snapshot"] = research_snapshot
        context["research_findings"] = research_findings
        context["retrieval_traces"] = retrieval_traces
        context["task_type"] = task_type or "concept_test"
        brief_summary = consumer_brief_summary if isinstance(consumer_brief_summary, dict) else {}
        context["industry"] = brief_summary.get("category") or (
            getattr(brief, "category", "")
            if brief is not None
            else ""
        ) or brief_summary.get("industry", "")
        context["target_audience"] = (
            brief.target_audience if brief is not None and getattr(brief, "target_audience", None) else brief_summary.get("target_audience", [])
        )

        # Merge Phase 2 fields when we have propagation events or research findings.
        if all_events or research_findings:
            from ..services.consumer.scoring import build_consumer_summary
            from ..services.consumer.report_context import build_consumer_report_context

            initial_labels = [s.get("attitude_label", "neutral") for s in snapshots if s.get("round_num") == 0]
            latest_attitudes: Dict[str, str] = {}
            for s in snapshots:
                agent_id = s.get("agent_id", "")
                if agent_id:
                    latest_attitudes[agent_id] = s.get("attitude_label", "neutral")
            final_labels = list(latest_attitudes.values())

            phase2_summary = build_consumer_summary(
                events=all_events,
                findings=research_findings,
                initial_labels=initial_labels,
                final_labels=final_labels,
                traces=retrieval_traces,
                task_type=task_type,
                brief=brief,
            )
            # Avoid revalidating against an empty snapshot; phase2_summary already
            # carries the gatekeeping result built from consumer_config traces.
            report_snapshot = persisted_snapshot if loaded_from_project else None
            if report_snapshot is not None and not getattr(report_snapshot, "chunks", None) and not getattr(report_snapshot, "sources", None):
                report_snapshot = None
            # If supplemental simulation-level evidence was merged, do not re-run
            # gatekeeping against an incomplete project snapshot; let phase2_summary
            # supply the gatekeeping result. Snapshot enrichment is still applied.
            if supplemental_merged and report_snapshot is not None:
                phase2_context = build_consumer_report_context(
                    summary=phase2_summary,
                    findings=research_findings,
                    events=all_events,
                    traces=retrieval_traces,
                    snapshot=None,
                )
                from ..services.consumer.report_context import enrich_report_context_with_snapshot
                enrich_report_context_with_snapshot(
                    phase2_context, research_findings, retrieval_traces, report_snapshot
                )
            else:
                phase2_context = build_consumer_report_context(
                    summary=phase2_summary,
                    findings=research_findings,
                    events=all_events,
                    traces=retrieval_traces,
                    snapshot=report_snapshot,
                )

            if all_events:
                context["event_counts"] = phase2_summary.event_counts
                context["top_risk_findings"] = phase2_summary.top_risk_findings
                context["causal_chains"] = phase2_context["causal_chains"]
                context["event_led_reversals"] = phase2_context["event_led_reversals"]

            context["retrieval_provenance"] = phase2_context.get("retrieval_provenance")
            context["source_catalog"] = phase2_context.get("source_catalog")
            context["enriched_findings"] = phase2_context.get("enriched_findings")
            context["enriched_traces"] = phase2_context.get("enriched_traces")
            context["finding_evidence_atoms"] = phase2_context.get(
                "finding_evidence_atoms",
                context.get("finding_evidence_atoms", []),
            )
            context["evidence_atom_count"] = phase2_context.get(
                "evidence_atom_count",
                context.get("evidence_atom_count", 0),
            )
            context["evidence_gatekeeping_summary"] = (
                phase2_summary.evidence_gatekeeping_summary
                if supplemental_merged
                else (
                    phase2_context.get("evidence_gatekeeping_summary")
                    or phase2_summary.evidence_gatekeeping_summary
                )
            )

            # Inject task-aware fields from Phase 2 summary into context
            context["top_packaging_hooks"] = phase2_summary.top_packaging_hooks or context.get("top_packaging_hooks", [])
            context["top_trust_objections"] = phase2_summary.top_trust_objections or context.get("top_trust_objections", [])
            context["top_confusion_triggers"] = phase2_summary.top_confusion_triggers or context.get("top_confusion_triggers", [])
            context["winning_variant"] = phase2_summary.winning_variant or context.get("winning_variant", "")
            context["top_variant_deltas"] = phase2_summary.top_variant_deltas or context.get("top_variant_deltas", [])
            context["top_persona_divergences"] = phase2_summary.top_persona_divergences or context.get("top_persona_divergences", [])
            context["acceptable_price_points"] = phase2_summary.acceptable_price_points or context.get("acceptable_price_points", [])
            context["resisted_price_points"] = phase2_summary.resisted_price_points or context.get("resisted_price_points", [])
            context["top_price_objections"] = phase2_summary.top_price_objections or context.get("top_price_objections", [])
            context["price_context"] = phase2_summary.price_context or context.get("price_context", "")

        context.update(self._build_research_synthesis(context))

        # Phase 4A: include latest replay alignment for this simulation if available
        context["replay_alignment"] = self._load_latest_replay_alignment()

        # Phase 5: Selling point analysis & compliance check
        context['all_events'] = all_events
        claims = self._extract_claims_from_context(context)
        try:
            if analyze_selling_points is not None and claims:
                sp_report = analyze_selling_points(
                    claims=claims,
                    events=context.get('all_events', []),
                    voc_quotes=context.get('representative_voc_quotes', {}),
                    channel_metrics=context.get('channel_metrics'),
                    event_counts=context.get('consumer_event_counts', {}),
                )
                # Ensure JSON-serializable storage in context
                if hasattr(sp_report, 'to_dict'):
                    context['selling_point_report'] = sp_report.to_dict()
                elif hasattr(sp_report, '__dataclass_fields__'):
                    context['selling_point_report'] = asdict(sp_report)
                else:
                    context['selling_point_report'] = sp_report
        except Exception as e:
            logger.warning("Selling point analysis failed: %s", e)

        try:
            if check_compliance is not None and claims:
                comp_report = check_compliance(
                    claims=claims,
                    misread_quotes=context.get('representative_voc_quotes', {}).get('misread', []),
                    risk_quotes=context.get('representative_voc_quotes', {}).get('risk', []),
                )
                # Ensure JSON-serializable storage in context
                comp_dict = asdict(comp_report) if hasattr(comp_report, '__dataclass_fields__') else comp_report
                # findings is a property on ComplianceReport, not a field — add manually
                if isinstance(comp_dict, dict) and 'findings' not in comp_dict:
                    try:
                        comp_dict['findings'] = [
                            {
                                'expression': f.expression,
                                'risk_reason': f.risk_reason,
                                'suggested_alternative': f.suggested_alternative,
                            }
                            for f in comp_report.findings
                        ]
                    except Exception:
                        comp_dict['findings'] = []
                context['compliance_report'] = comp_dict
        except Exception as e:
            logger.warning("Compliance check failed: %s", e)

        from .consumer.society.report_adapter import SocietyReportAdapter

        society_adapter = SocietyReportAdapter()
        return society_adapter.merge_into_context(
            context,
            society_adapter.build_report_context(self.simulation_id),
        )

    def _build_consumer_context_from_society_context(
        self, society_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        context = dict(society_context)
        event_counts = {
            str(key): int(value or 0)
            for key, value in dict(context.get("society_event_summary") or {}).items()
        }
        total_events = sum(event_counts.values())

        positive_events = {
            "ADVOCACY",
            "FIRST_IMPRESSION",
            "PURCHASE_SIGNAL",
            "TRUST_RECOVERY",
        }
        negative_events = {
            "ASK_PROOF",
            "MISREAD_CLAIM",
            "PRICE_RESISTANCE",
            "TRUST_OBJECTION",
        }

        positive_count = sum(event_counts.get(name, 0) for name in positive_events)
        negative_count = sum(event_counts.get(name, 0) for name in negative_events)
        neutral_count = max(total_events - positive_count - negative_count, 0)

        if total_events > 0:
            post_acceptance = {
                "positive": positive_count / total_events,
                "neutral": neutral_count / total_events,
                "negative": negative_count / total_events,
            }
        else:
            post_acceptance = {"positive": 0.0, "neutral": 1.0, "negative": 0.0}

        initial_acceptance = {"positive": 0.0, "neutral": 1.0, "negative": 0.0}
        summary = {
            "initial_acceptance": initial_acceptance,
            "post_propagation_acceptance": post_acceptance,
            "attitude_shift_rate": abs(post_acceptance["positive"] - initial_acceptance["positive"]),
        }

        metrics = dict(context.get("society_metrics") or {})
        risk_points = self._string_list(context.get("society_top_risk_points"))
        if not risk_points:
            if metrics.get("misread_rate", 0) > 0:
                risk_points.append("功效边界和光学修色容易触发误读")
            if metrics.get("price_resistance_index", 0) > 0:
                risk_points.append("价格需要与同类产品形成清晰价值解释")
            if metrics.get("evidence_demand_rate", 0) > 0:
                risk_points.append("需要补充检测证明、备案信息和真实用户反馈")

        resonance_points = self._string_list(context.get("society_top_resonance_points"))
        if not resonance_points and positive_count:
            resonance_points = ["核心宣称有第一眼记忆点，但需要真实场景支撑"]

        misread_points = self._string_list(context.get("society_top_misreads"))
        if not misread_points and event_counts.get("MISREAD_CLAIM", 0):
            misread_points = ["核心宣称容易被误读为全场景承诺或短期强承诺"]

        representative_voc_quotes = self._voc_quote_groups(
            context.get("representative_voc_quotes")
        )
        if not any(representative_voc_quotes.values()):
            representative_voc_quotes = self._voc_quote_groups(
                context.get("society_representative_voc_quotes")
            )

        context.update(
            {
                "summary": summary,
                "initial_acceptance": initial_acceptance,
                "post_propagation_acceptance": post_acceptance,
                "attitude_shift_rate": summary["attitude_shift_rate"],
                "events_count": total_events,
                "event_counts": event_counts,
                "consumer_event_counts": event_counts,
                "top_resonance_points": resonance_points,
                "top_risk_points": risk_points,
                "top_misreads": misread_points,
                "representative_voc_quotes": representative_voc_quotes,
                "evidence_bundle": {},
                "top_risk_findings": context.get("top_risk_findings", []),
                "causal_chains": context.get("causal_chains", []),
                "event_led_reversals": context.get("event_led_reversals", []),
                "top_packaging_hooks": context.get("top_packaging_hooks", []),
                "top_trust_objections": context.get("top_trust_objections", []),
                "top_confusion_triggers": context.get("top_confusion_triggers", []),
                "winning_variant": context.get("winning_variant", ""),
                "top_variant_deltas": context.get("top_variant_deltas", []),
                "top_persona_divergences": context.get("top_persona_divergences", []),
                "acceptable_price_points": context.get("acceptable_price_points", []),
                "resisted_price_points": context.get("resisted_price_points", []),
                "top_price_objections": context.get("top_price_objections", []),
                "price_context": context.get("price_context", ""),
            }
        )
        context.update(self._build_research_synthesis(context))
        return context

    @staticmethod
    def _string_list(value: Any) -> List[str]:
        if not isinstance(value, list):
            return []
        return [str(item).strip() for item in value if str(item).strip()]

    @staticmethod
    def _voc_quote_groups(value: Any) -> Dict[str, List[Dict[str, Any]]]:
        groups = {"resonance": [], "risk": [], "misread": []}
        if not isinstance(value, dict):
            return groups
        for key in groups:
            raw_items = value.get(key, [])
            if not isinstance(raw_items, list):
                continue
            groups[key] = [
                dict(item)
                for item in raw_items
                if isinstance(item, dict) and str(item.get("quote", "")).strip()
            ]
        return groups

    def _build_research_synthesis(self, context: Dict[str, Any]) -> Dict[str, Any]:
        findings = self._research_finding_records(context)
        if not findings:
            return {
                "research_findings_count": int(context.get("research_findings_count", 0) or 0),
                "research_finding_type_counts": dict(context.get("research_finding_type_counts", {}) or {}),
                "research_insight_pillars": list(context.get("research_insight_pillars", []) or []),
                "research_insight_summary": str(
                    context.get("research_insight_summary") or "暂无研究发现综合。"
                ),
            }

        type_counts: Counter[str] = Counter()
        grouped: Dict[str, List[Dict[str, Any]]] = {}
        for finding in findings:
            finding_type = str(finding.get("finding_type") or "unknown").strip() or "unknown"
            type_counts[finding_type] += 1
            grouped.setdefault(finding_type, []).append(finding)

        preferred_order = [
            "category_context",
            "competitor_signal",
            "risk_signal",
            "trend_signal",
            "propagation_signal",
        ]
        ordered_types = [ftype for ftype in preferred_order if ftype in grouped]
        ordered_types.extend(sorted(ftype for ftype in grouped if ftype not in preferred_order))

        pillars = [
            self._build_research_pillar(finding_type, grouped[finding_type])
            for finding_type in ordered_types
        ]
        summary_chunks = [
            f"{pillar['finding_type_label']}：{pillar['summary']}"
            for pillar in pillars[:4]
            if pillar.get("summary")
        ]
        if summary_chunks:
            summary_text = f"基于 {len(findings)} 条研究发现，" + "；".join(summary_chunks)
        else:
            summary_text = f"基于 {len(findings)} 条研究发现，已形成多条可执行洞察。"

        quote_parts: List[str] = []
        resonance_point = self._first_point(self._string_list(context.get("top_resonance_points")), "")
        risk_point = self._first_point(self._string_list(context.get("top_risk_points")), "")
        misread_point = self._first_point(self._string_list(context.get("top_misreads")), "")
        if resonance_point:
            quote_parts.append(f"正向原声指向“{resonance_point}”")
        if risk_point:
            quote_parts.append(f"风险原声集中在“{risk_point}”")
        if misread_point:
            quote_parts.append(f"误读点落在“{misread_point}”")
        if quote_parts:
            summary_text += "；" + "，".join(quote_parts)
        summary_text += "。"

        result: Dict[str, Any] = {
            "research_findings_count": len(findings),
            "research_finding_type_counts": dict(type_counts),
            "research_insight_pillars": pillars,
            "research_insight_summary": summary_text,
        }
        if not context.get("top_risk_findings"):
            result["top_risk_findings"] = self._research_risk_findings(findings)
        return result

    def _research_finding_records(self, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        candidates = context.get("enriched_findings") or context.get("research_findings") or []
        if not isinstance(candidates, list):
            return []
        records: List[Dict[str, Any]] = []
        for item in candidates:
            record = self._normalize_finding_record(item)
            if record is not None:
                records.append(record)
        return records

    def _normalize_finding_record(self, item: Any) -> Optional[Dict[str, Any]]:
        if isinstance(item, dict):
            record = dict(item)
        else:
            record = {
                "finding_id": getattr(item, "finding_id", ""),
                "finding_type": getattr(item, "finding_type", ""),
                "summary": getattr(item, "summary", ""),
                "evidence_snippets": list(getattr(item, "evidence_snippets", []) or []),
                "source_label": getattr(item, "source_label", ""),
                "source_title": getattr(item, "source_title", ""),
                "source_id": getattr(item, "source_id", ""),
                "confidence": getattr(item, "confidence", 0),
                "confidence_label": getattr(item, "confidence_label", ""),
                "gatekeeping_status": getattr(item, "gatekeeping_status", ""),
                "evidence_preview": getattr(item, "evidence_preview", ""),
                "visibility": getattr(item, "visibility", ""),
            }

        record["finding_id"] = str(record.get("finding_id", "") or "").strip()
        record["finding_type"] = str(record.get("finding_type", "") or "unknown").strip() or "unknown"
        summary = str(record.get("summary") or record.get("claim") or record.get("finding_id") or "").strip()
        if not summary:
            return None
        record["summary"] = summary
        record["source_label"] = str(record.get("source_label") or "").strip()
        record["source_title"] = str(record.get("source_title") or record.get("source_label") or "").strip()
        record["source_id"] = str(record.get("source_id") or "").strip()
        record["confidence_label"] = str(record.get("confidence_label") or "").strip()
        record["gatekeeping_status"] = str(record.get("gatekeeping_status") or "").strip().lower()
        record["evidence_preview"] = self._finding_evidence_preview(record)
        return record

    @staticmethod
    def _finding_evidence_preview(finding: Dict[str, Any]) -> str:
        preview = str(finding.get("evidence_preview") or "").strip()
        if preview:
            return preview[:240]
        snippets = finding.get("evidence_snippets")
        if isinstance(snippets, list):
            for snippet in snippets:
                text = str(snippet or "").strip()
                if text:
                    return text[:240]
        for key in ("summary", "claim"):
            text = str(finding.get(key) or "").strip()
            if text:
                return text[:240]
        return ""

    @staticmethod
    def _finding_digest_sort_key(finding: Dict[str, Any]) -> tuple[int, float, int, str]:
        status_rank = {
            "allowed": 0,
            "downgraded": 1,
            "blocked": 2,
        }.get(str(finding.get("gatekeeping_status") or "").strip().lower(), 3)
        confidence_value = finding.get("confidence", 0)
        try:
            confidence_score = float(confidence_value)
        except (TypeError, ValueError):
            confidence_score = {
                "high": 0.9,
                "medium": 0.6,
                "low": 0.3,
            }.get(str(finding.get("confidence_label") or "").strip().lower(), 0.0)
        evidence_rank = 0 if str(finding.get("evidence_preview") or "").strip() else 1
        summary = str(finding.get("summary") or "").strip().casefold()
        return (status_rank, -confidence_score, evidence_rank, summary)

    @staticmethod
    def _finding_type_label(finding_type: str) -> str:
        labels = {
            "category_context": "品类背景",
            "competitor_signal": "竞品信号",
            "risk_signal": "风险信号",
            "trend_signal": "趋势信号",
            "propagation_signal": "传播信号",
        }
        cleaned = str(finding_type or "").strip()
        return labels.get(cleaned, cleaned or "未分类")

    def _build_research_pillar(self, finding_type: str, candidates: List[Dict[str, Any]]) -> Dict[str, Any]:
        best = min(candidates, key=self._finding_digest_sort_key)
        return {
            "finding_type": finding_type,
            "finding_type_label": self._finding_type_label(finding_type),
            "finding_id": str(best.get("finding_id", "") or ""),
            "summary": str(best.get("summary", "") or ""),
            "evidence_preview": str(best.get("evidence_preview", "") or ""),
            "source_title": str(best.get("source_title", "") or ""),
            "source_label": str(best.get("source_label", "") or ""),
            "confidence": best.get("confidence", 0),
            "confidence_label": str(best.get("confidence_label", "") or ""),
            "gatekeeping_status": str(best.get("gatekeeping_status", "") or ""),
        }

    def _research_risk_findings(self, findings: List[Dict[str, Any]], limit: int = 3) -> List[Dict[str, Any]]:
        risk_candidates = [
            finding for finding in findings
            if str(finding.get("finding_type") or "").strip() == "risk_signal"
        ]
        if not risk_candidates:
            risk_candidates = list(findings)
        selected = sorted(risk_candidates, key=self._finding_digest_sort_key)[:limit]
        result: List[Dict[str, Any]] = []
        for finding in selected:
            result.append(
                {
                    "finding_id": str(finding.get("finding_id", "") or ""),
                    "finding_type": str(finding.get("finding_type", "") or ""),
                    "summary": str(finding.get("summary", "") or ""),
                    "source_id": str(finding.get("source_id", "") or ""),
                    "source_title": str(finding.get("source_title", "") or ""),
                    "evidence_preview": str(finding.get("evidence_preview", "") or ""),
                    "confidence": finding.get("confidence", 0),
                }
            )
        return result

    def _load_latest_replay_alignment(self) -> Dict[str, Any]:
        """Load the latest replay result for this simulation, if any."""
        replay_dir = os.path.join(Config.UPLOAD_FOLDER, "benchmarks", "replay_runs")
        if not os.path.exists(replay_dir):
            return {"status": "not_replayed", "replay_id": None, "benchmark_id": None}

        latest_replay: Optional[Dict[str, Any]] = None
        latest_at = ""
        for filename in os.listdir(replay_dir):
            if not filename.startswith("replay_") or not filename.endswith(".json"):
                continue
            path = os.path.join(replay_dir, filename)
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if data.get("simulation_id") != self.simulation_id:
                    continue
                replayed_at = data.get("replayed_at", "")
                if replayed_at > latest_at:
                    latest_at = replayed_at
                    latest_replay = data
            except Exception:
                continue

        if latest_replay is None:
            return {"status": "not_replayed", "replay_id": None, "benchmark_id": None}

        return {
            "status": latest_replay.get("alignment_status", "unknown"),
            "replay_id": latest_replay.get("replay_id"),
            "benchmark_id": latest_replay.get("benchmark_id"),
            "overall_score": latest_replay.get("overall_score", 0.0),
            "drift_signals": latest_replay.get("drift_signals", []),
            "replay_summary": latest_replay.get("replay_summary", ""),
        }

    def _first_point(self, points: List[str], fallback: str) -> str:
        return points[0] if points else fallback

    def _extract_claims_from_context(self, context: Dict[str, Any]) -> List[str]:
        """Extract selling-point claims from consumer config or business brief."""
        claims: List[str] = []
        # Try resonance points as primary claims
        resonance = context.get("top_resonance_points", [])
        if resonance:
            claims.extend(resonance[:5])
        # Try consumer_brief claims
        brief_summary = context.get("consumer_brief", {})
        if isinstance(brief_summary, dict):
            brief_claims = brief_summary.get("claims") or brief_summary.get("selling_points") or []
            for c in brief_claims:
                if isinstance(c, str) and c not in claims:
                    claims.append(c)
        # Try research insight pillars
        for pillar in context.get("research_insight_pillars", []):
            summary_text = str(pillar.get("summary", "")).strip()
            if summary_text and summary_text not in claims:
                claims.append(summary_text)
        return claims
