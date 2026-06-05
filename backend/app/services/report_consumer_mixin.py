"""Consumer report generation helpers for ReportAgent."""

from __future__ import annotations

import json
import os
import time
from collections import Counter
from dataclasses import asdict
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

from ..config import Config
from ..models.project import ProjectManager
from ..utils.locale import t
from ..utils.logger import get_logger
from .consumer.project_research_persistence import (
    artifacts_exist,
    load_persisted_findings,
    load_persisted_snapshot,
)
from .consumer.report_context import ConsumerReportContextBuilder
from .report_manager import ReportManager
from .report_models import Report, ReportOutline, ReportSection, ReportStatus

try:
    from .consumer.selling_point_analyzer import analyze_selling_points
except ImportError:
    analyze_selling_points = None  # type: ignore[assignment]

try:
    from .consumer.compliance_checker import check_compliance
except ImportError:
    check_compliance = None  # type: ignore[assignment]

logger = get_logger('miroconsumer.report_agent')


class ConsumerReportMixin:
    def _generate_consumer_report(
        self,
        report: Report,
        report_id: str,
        start_time: datetime,
        completed_section_titles: List[str],
        progress_callback: Optional[Callable[[str, int, str], None]] = None,
    ) -> Report:
        if self.report_logger:
            self.report_logger.log_planning_start()

        ReportManager.update_progress(
            report_id, "planning", 10, "正在整理消费者传播证据",
            completed_sections=completed_section_titles,
        )
        if progress_callback:
            progress_callback("planning", 10, "正在整理消费者传播证据")

        context = self._build_consumer_report_context()
        report.report_context = context
        outline = self._build_consumer_outline(context)
        report.outline = outline
        report.status = ReportStatus.GENERATING
        ReportManager.save_outline(report_id, outline)
        ReportManager.save_report(report)

        if self.report_logger:
            self.report_logger.log_planning_complete(outline.to_dict())

        total_sections = len(outline.sections)
        generated_section_contents: List[str] = []
        for index, section in enumerate(outline.sections, start=1):
            progress = 20 + int(((index - 1) / max(total_sections, 1)) * 70)
            ReportManager.update_progress(
                report_id,
                "generating",
                progress,
                f"正在生成章节：{section.title}",
                current_section=section.title,
                completed_sections=completed_section_titles,
            )
            if progress_callback:
                progress_callback("generating", progress, f"正在生成章节：{section.title}")

            section.content = self._render_consumer_section_with_optional_llm(
                section=section,
                outline=outline,
                context=context,
                previous_sections=generated_section_contents,
            )
            ReportManager.save_section(report_id, index, section)
            completed_section_titles.append(section.title)
            generated_section_contents.append(f"## {section.title}\n\n{section.content}".strip())

            if self.report_logger:
                self.report_logger.log_section_full_complete(
                    section_title=section.title,
                    section_index=index,
                    full_content=f"## {section.title}\n\n{section.content}".strip(),
                )

        report.markdown_content = ReportManager.assemble_full_report(report_id, outline)
        report.status = ReportStatus.COMPLETED
        report.completed_at = datetime.now().isoformat()

        total_time_seconds = (datetime.now() - start_time).total_seconds()
        if self.report_logger:
            self.report_logger.log_report_complete(
                total_sections=total_sections,
                total_time_seconds=total_time_seconds,
            )

        ReportManager.save_report(report)
        ReportManager.update_progress(
            report_id, "completed", 100, t('progress.reportComplete'),
            completed_sections=completed_section_titles,
        )
        if progress_callback:
            progress_callback("completed", 100, t('progress.reportComplete'))

        if self.console_logger:
            self.console_logger.close()
            self.console_logger = None

        return report

    def _consumer_report_llm_enabled(self) -> bool:
        return os.environ.get("CONSUMER_REPORT_LLM_ENABLED", "").strip().lower() in {
            "1",
            "true",
            "yes",
            "on",
        }

    def _render_consumer_section_with_optional_llm(
        self,
        *,
        section: ReportSection,
        outline: ReportOutline,
        context: Dict[str, Any],
        previous_sections: List[str],
    ) -> str:
        if not self._consumer_report_llm_enabled():
            return self._render_consumer_section(section.title, context)

        stats = getattr(
            self,
            "consumer_report_llm_stats",
            {"attempted": 0, "succeeded": 0, "failed": 0, "latencies": []},
        )
        stats["attempted"] += 1
        started_at = time.time()
        try:
            context_preview = json.dumps(context, ensure_ascii=False, default=str)[:4000]
            llm_previous_sections = [
                f"consumer_report_context:\n{context_preview}",
                *previous_sections,
            ]
            content = self._generate_section_react(section, outline, llm_previous_sections)
            stats["succeeded"] += 1
            stats["latencies"].append(round(time.time() - started_at, 4))
            self.consumer_report_llm_stats = stats
            return content
        except Exception as exc:
            stats["failed"] += 1
            stats["latencies"].append(round(time.time() - started_at, 4))
            self.consumer_report_llm_stats = stats
            logger.warning("Consumer report LLM section failed; falling back to template: %s", exc)
            return self._render_consumer_section(section.title, context)
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

    def _build_consumer_outline(self, context: Dict[str, Any]) -> ReportOutline:
        summary = context["summary"]
        task_type = str(context.get("task_type", "")).strip().lower()
        research_findings_value = context.get("research_findings", [])
        research_findings_count = int(
            context.get("research_findings_count")
            or (len(research_findings_value) if isinstance(research_findings_value, list) else 0)
        )

        # Determine concept recommendation for summary
        post_pos = summary['post_propagation_acceptance']['positive']
        init_pos = summary['initial_acceptance']['positive']
        shift_rate = summary['attitude_shift_rate']
        neg_growth = summary['post_propagation_acceptance']['negative'] - summary['initial_acceptance']['negative']
        if post_pos > init_pos and shift_rate > 0.1:
            recommendation = "建议继续推进"
        elif neg_growth > 0.1:
            recommendation = "建议暂缓"
        else:
            recommendation = "建议优化后继续"

        outline_summary = (
            f"本报告基于 {research_findings_count} 条研究发现与消费者原声综合生成，"
            f"概念决策：{recommendation}。"
            f"初始正向接受度 {init_pos:.0%}，"
            f"传播后正向接受度 {post_pos:.0%}，"
            f"态度转向率 {shift_rate:.0%}。"
        )

        sections = [
            # Layer 1: Executive Summary
            ReportSection(title="总裁结论页", content=""),
            # Layer 2: Action Playbook
            ReportSection(title="卖点决策表", content=""),
            ReportSection(title="合规话术边界", content=""),
            ReportSection(title="渠道策略与执行建议", content=""),
            # Layer 3: Technical Appendix
            ReportSection(title="测试概览", content=""),
            ReportSection(title="研究发现综合", content=""),
            ReportSection(title="传播演化", content=""),
            ReportSection(title="风险与误读", content=""),
            ReportSection(title="代表性消费者原声", content=""),
        ]

        # Task-specific sections still appended to Layer 3
        if task_type == "price_test":
            sections.insert(7, ReportSection(title="价格敏感度与 WTP 分析", content=""))
            sections.insert(8, ReportSection(title="价格接受区间与弹性", content=""))
        elif task_type == "packaging_test":
            sections.insert(7, ReportSection(title="视觉认知与货架吸引力", content=""))
            sections.insert(8, ReportSection(title="包装识别与注意力路径", content=""))
        elif task_type == "ab_test":
            sections.insert(7, ReportSection(title="偏好对比与统计显著性", content=""))
            sections.insert(8, ReportSection(title="版本差异与选择理由", content=""))

        return ReportOutline(
            title="消费者传播测试与市场决策报告",
            summary=outline_summary,
            sections=sections,
        )

    # ── Layer 1 & 2 rendering methods ──────────────────────────────────

    def _render_executive_summary(self, context: Dict[str, Any]) -> str:
        """Render 总裁结论页 — Layer 1 executive summary."""
        summary = context["summary"]
        init_pos = summary['initial_acceptance']['positive']
        post_pos = summary['post_propagation_acceptance']['positive']
        shift_rate = summary['attitude_shift_rate']
        neg_growth = summary['post_propagation_acceptance']['negative'] - summary['initial_acceptance']['negative']

        # Concept recommendation
        if post_pos > init_pos and shift_rate > 0.1:
            recommendation = "建议继续推进"
        elif neg_growth > 0.1:
            recommendation = "建议暂缓"
        else:
            recommendation = "建议优化后继续"

        lines: List[str] = []
        lines.append(f"## 概念决策：{recommendation}")
        lines.append("")

        # Core findings — top 3 resonance points
        lines.append("## 核心发现")
        resonance = context.get('top_resonance_points', [])
        for point in resonance[:3]:
            lines.append(f"- {point}")
        if not resonance:
            lines.append("- 暂无显著共鸣点")
        lines.append("")

        # Biggest opportunity & biggest risk
        top_opportunity = resonance[0] if resonance else "暂无"
        risk_points = context.get('top_risk_points', [])
        top_risk = risk_points[0] if risk_points else "暂无"
        lines.append(f"## 最大机会\n{top_opportunity}")
        lines.append("")
        lines.append(f"## 最大风险\n{top_risk}")
        lines.append("")

        # Main selling point suggestion
        sp_report = context.get('selling_point_report')
        main_rec = None
        if isinstance(sp_report, dict):
            main_rec = sp_report.get('main_recommendation')
            if not main_rec:
                analyses = sp_report.get('analyses') or sp_report.get('recommendations') or []
                if analyses:
                    a = analyses[0]
                    main_rec = a.get('claim_text', a.get('claim', '')) if isinstance(a, dict) else getattr(a, 'claim_text', '')
        elif sp_report is not None:
            main_rec = getattr(sp_report, 'main_recommendation', None)
            if not main_rec:
                analyses = getattr(sp_report, 'analyses', None) or getattr(sp_report, 'recommendations', None) or []
                if analyses:
                    main_rec = getattr(analyses[0], 'claim_text', '')
        if main_rec:
            lines.append(f"## 主卖点建议\n{main_rec}")
        else:
            anchor = resonance[0] if resonance else "暂无"
            lines.append(f"## 主卖点建议\n围绕核心共鸣点「{anchor}」构建主传播叙事")
        lines.append("")

        # Next steps
        lines.append("## 下一步行动")
        lines.append(f"1. 根据概念决策（{recommendation}），明确下一阶段资源配置")
        if resonance:
            lines.append(f"2. 围绕「{resonance[0]}」打磨核心文案与传播素材")
        if risk_points:
            lines.append(f"3. 针对风险点「{risk_points[0]}」准备应对话术与证据")
        lines.append("4. 参阅执行页（Layer 2）获取卖点、合规、渠道的具体落地方案")
        return "\n".join(lines)

    def _render_selling_point_table(self, context: Dict[str, Any]) -> str:
        """Render 卖点决策表 — Layer 2 selling point decision table."""
        sp_report = context.get('selling_point_report')
        # Handle both dict (model_dump) and object forms
        analyses = None
        if isinstance(sp_report, dict):
            analyses = sp_report.get('analyses') or sp_report.get('recommendations')
        elif sp_report is not None:
            analyses = getattr(sp_report, 'analyses', None) or getattr(sp_report, 'recommendations', None)
        if analyses:
            lines: List[str] = []
            lines.append("## 卖点决策表")
            lines.append("")
            lines.append("| 排名 | 卖点 | 建议角色 | 共鸣度 | 风险度 | 最佳渠道 | 处理方式 |")
            lines.append("| --- | --- | --- | --- | --- | --- | --- |")
            for a in analyses:
                if isinstance(a, dict):
                    rank = a.get('priority_rank', a.get('rank', ''))
                    claim = a.get('claim_text', a.get('claim', ''))
                    role = a.get('role', '')
                    resonance = a.get('resonance_score', 0)
                    risk = a.get('risk_score', 0)
                    best_ch = a.get('best_channel', '')
                    handling = a.get('handling_suggestion', a.get('handling', ''))
                else:
                    rank = getattr(a, 'priority_rank', '')
                    claim = getattr(a, 'claim_text', '')
                    role = getattr(a, 'role', '')
                    resonance = getattr(a, 'resonance_score', 0)
                    risk = getattr(a, 'risk_score', 0)
                    best_ch = getattr(a, 'best_channel', '')
                    handling = getattr(a, 'handling_suggestion', '')
                try:
                    resonance_str = f"{float(resonance):.0%}"
                except (ValueError, TypeError):
                    resonance_str = str(resonance)
                try:
                    risk_str = f"{float(risk):.0%}"
                except (ValueError, TypeError):
                    risk_str = str(risk)
                lines.append(
                    f"| {rank} | {claim} | {role} | {resonance_str} | {risk_str} | {best_ch} | {handling} |"
                )
            return "\n".join(lines)

        # Fallback: simplified table from existing context data
        lines = []
        lines.append("## 卖点决策表")
        lines.append("")
        lines.append("| 卖点 | 建议角色 | 原因 | 风险 | 处理方式 |")
        lines.append("| --- | --- | --- | --- | --- |")
        resonance = context.get('top_resonance_points', [])
        risk_points = context.get('top_risk_points', [])
        for i, point in enumerate(resonance[:5]):
            role = "主打卖点" if i == 0 else "辅助卖点"
            reason = "消费者高共鸣" if i == 0 else "强化概念支撑"
            risk = risk_points[i] if i < len(risk_points) else "暂无已知风险"
            handling = "持续强化传播" if i == 0 else "配合主卖点使用"
            lines.append(f"| {point} | {role} | {reason} | {risk} | {handling} |")
        if not resonance:
            lines.append("| 暂无 | - | - | - | - |")
        return "\n".join(lines)

    def _render_compliance_table(self, context: Dict[str, Any]) -> str:
        """Render 合规话术边界 — Layer 2 compliance boundary table."""
        comp_report = context.get('compliance_report')
        # Handle both dict (model_dump) and object forms
        findings = None
        if isinstance(comp_report, dict):
            findings = comp_report.get('findings')
        elif comp_report is not None:
            findings = getattr(comp_report, 'findings', None)
        if findings:
            lines: List[str] = []
            lines.append("## 合规话术边界")
            lines.append("")
            lines.append("| 高风险表达 | 风险原因 | 建议替代表达 |")
            lines.append("| --- | --- | --- |")
            for finding in findings:
                if isinstance(finding, dict):
                    expr = finding.get('expression', '')
                    reason = finding.get('risk_reason', '')
                    alternative = finding.get('suggested_alternative', '')
                else:
                    expr = getattr(finding, 'expression', '')
                    reason = getattr(finding, 'risk_reason', '')
                    alternative = getattr(finding, 'suggested_alternative', '')
                lines.append(f"| {expr} | {reason} | {alternative} |")
            return "\n".join(lines)

        # Fallback: derive from misreads and risk points
        lines = []
        lines.append("## 合规话术边界")
        lines.append("")
        lines.append("| 高风险表达 | 风险原因 | 建议替代表达 |")
        lines.append("| --- | --- | --- |")
        misreads = context.get('top_misreads', [])
        for misread in misreads[:3]:
            lines.append(f"| {misread} | 消费者误读/歧义 | 建议使用更明确、具体化表述 |")
        risk_points = context.get('top_risk_points', [])
        for risk in risk_points[:3]:
            lines.append(f"| {risk} | 可能引发负面解读 | 建议补充证据支撑或弱化表述 |")
        if not misreads and not risk_points:
            lines.append("| 暂无 | - | - |")
        lines.append("")
        lines.append("> 注：以上为自动生成的初步筛查，正式发布前请法务/合规团队复核。")
        return "\n".join(lines)

    def _render_channel_strategy(self, context: Dict[str, Any]) -> str:
        """Render 渠道策略与执行建议 — Layer 2 channel strategy."""
        channel_metrics = context.get('channel_metrics', {})
        channel_fit = context.get('channel_fit_scores', {})
        resonance = context.get('top_resonance_points', [])
        risk_points = context.get('top_risk_points', [])
        main_hook = resonance[0] if resonance else "产品核心价值"
        main_risk = risk_points[0] if risk_points else "暂无已知风险"

        lines: List[str] = []
        lines.append("## 渠道策略与执行建议")
        lines.append("")

        # Per-channel recommendations
        channels = [
            ("小红书", "种草笔记 + 素人口碑", "图文笔记、合集测评、素人试用分享"),
            ("抖音", "短视频 + 信息流", "15-60秒短视频、达人合作、信息流投放"),
            ("直播间", "即时转化场景", "主播话术、互动引导、限时促销"),
            ("详情页", "深度说服场景", "长图文、对比数据、FAQ、用户证言"),
        ]
        for name, positioning, format_hint in channels:
            fit_score = channel_fit.get(name, channel_fit.get(name.lower(), ""))
            fit_label = f"（适配度: {fit_score}）" if fit_score else ""
            ch_metric = channel_metrics.get(name, channel_metrics.get(name.lower(), {}))
            lines.append(f"### {name} {fit_label}")
            lines.append(f"- 定位：{positioning}")
            lines.append(f"- 推荐形式：{format_hint}")
            lines.append(f"- 核心传播锚点：「{main_hook}」")
            if ch_metric and isinstance(ch_metric, dict):
                for k, v in ch_metric.items():
                    lines.append(f"- {k}: {v}")
            lines.append("")

        # 直播间FAQ预埋
        lines.append("## 直播间FAQ预埋")
        lines.append("")
        faq_items = [
            (f"这个产品的核心优势是什么？", f"核心优势在于「{main_hook}」，这是我们测试中消费者最认可的点。"),
            ("跟竞品相比有什么不同？", "我们的差异化在于经过消费者传播验证的独特卖点组合。"),
            ("适合什么样的人群？", f"目标人群画像详见报告，核心受众对「{main_hook}」有强需求。"),
            ("有没有什么需要注意的？", f"关于「{main_risk}」的疑问，我们准备了专业的解答话术。"),
            ("效果怎么样？有数据吗？", "消费者传播测试显示了明确的正向接受度，具体数据可在详情页查看。"),
        ]
        for i, (q, a) in enumerate(faq_items, 1):
            lines.append(f"**Q{i}: {q}**")
            lines.append(f"A: {a}")
            lines.append("")

        # 短视频脚本建议
        lines.append("## 短视频脚本建议")
        lines.append("")
        angles = [
            ("痛点切入", f"从消费者常见痛点出发，引出「{main_hook}」作为解决方案"),
            ("对比实验", f"通过与现有方案的对比，直观展示「{main_hook}」的优势"),
            ("用户证言", f"用真实消费者原声包装，围绕「{main_hook}」讲述使用体验"),
        ]
        for i, (title, desc) in enumerate(angles, 1):
            lines.append(f"**角度{i}: {title}**")
            lines.append(f"- {desc}")
            lines.append("")

        # 评论区回复模板
        lines.append("## 评论区回复模板")
        lines.append("")
        lines.append("**正面评论回复：**")
        lines.append(f"「感谢认可！「{main_hook}」确实是我们最引以为傲的特点，感谢您的支持！」")
        lines.append("")
        lines.append("**质疑/负面评论回复：**")
        lines.append(f"「感谢您的反馈。关于您提到的「{main_risk}」，我们非常重视，这里补充一些说明……」")
        lines.append("")
        lines.append("**咨询类评论回复：**")
        lines.append(f"「您好！关于产品详情，核心卖点是「{main_hook}」，详情页有完整的数据和说明，欢迎查看～」")
        return "\n".join(lines)

    # ── Layer 3 rendering (existing) ───────────────────────────────────

    def _render_consumer_section(self, section_title: str, context: Dict[str, Any]) -> str:
        # Layer 1 & 2 sections — delegate to dedicated renderers
        if section_title == "总裁结论页":
            return self._render_executive_summary(context)
        if section_title == "卖点决策表":
            return self._render_selling_point_table(context)
        if section_title == "合规话术边界":
            return self._render_compliance_table(context)
        if section_title == "渠道策略与执行建议":
            return self._render_channel_strategy(context)

        # Layer 3 sections — existing template-based rendering
        summary = context["summary"]
        task_type = str(context.get("task_type", "")).strip().lower()
        research_findings_value = context.get("research_findings", [])
        research_findings_count = int(
            context.get("research_findings_count")
            or (len(research_findings_value) if isinstance(research_findings_value, list) else 0)
        )

        if section_title == "测试概览":
            lines = [
                f"- 事件样本数：{context['events_count']}",
                f"- 研究发现总数：{research_findings_count}",
                f"- 证据原子数：{context.get('evidence_atom_count', 0)}",
                f"- 初始接受度：{self._format_acceptance(summary['initial_acceptance'])}",
                f"- 传播后接受度：{self._format_acceptance(summary['post_propagation_acceptance'])}",
                f"- 态度转向率：{summary['attitude_shift_rate']:.0%}",
            ]
            if task_type == "packaging_test" and context.get("top_packaging_hooks"):
                lines.append(f"- 包装吸引点：{self._format_points(context['top_packaging_hooks'])}")
            if task_type == "ab_test" and context.get("winning_variant"):
                lines.append(f"- 占优 variant：{context['winning_variant']}")
            if task_type == "price_test" and context.get("price_context"):
                lines.append(f"- 价格背景：{context['price_context']}")
            return "\n".join(lines)

        if section_title == "研究发现综合":
            type_counts = context.get("research_finding_type_counts") or {}
            pillars = context.get("research_insight_pillars") or []
            quote_groups = context.get("representative_voc_quotes") or {}
            lines = [
                f"- 研究发现总数：{research_findings_count}",
                f"- 主题分布：{self._format_finding_type_counts(type_counts)}",
                f"- 综合洞察：{context.get('research_insight_summary') or '暂无'}",
            ]
            if pillars:
                lines.append("- 关键研究主线：")
                for pillar in pillars[:4]:
                    lines.append(f"  - [{pillar.get('finding_type_label', pillar.get('finding_type', ''))}] {pillar.get('summary', '')}")
                    evidence_preview = str(pillar.get("evidence_preview", "") or "").strip()
                    if evidence_preview:
                        lines.append(f"    - 证据：{evidence_preview}")
            quote_bridge: List[str] = []
            if quote_groups.get("resonance"):
                quote_bridge.append(f'正向："{quote_groups["resonance"][0].get("quote", "")}"')
            if quote_groups.get("risk"):
                quote_bridge.append(f'风险："{quote_groups["risk"][0].get("quote", "")}"')
            if quote_groups.get("misread"):
                quote_bridge.append(f'误读："{quote_groups["misread"][0].get("quote", "")}"')
            if quote_bridge:
                lines.append("- 原声印证：")
                for item in quote_bridge:
                    lines.append(f"  - {item}")
            return "\n".join(lines)

        if section_title == "初始反应":
            lines = [
                f"- 高共鸣点：{self._format_points(context['top_resonance_points'])}",
                f"- 代表性正向原声：\n{self._format_quotes(context['representative_voc_quotes']['resonance'])}",
            ]
            if task_type == "packaging_test" and context.get("top_packaging_hooks"):
                lines.append(f"- 包装第一眼吸引：{self._format_points(context['top_packaging_hooks'])}")
            if task_type == "ab_test" and context.get("top_variant_deltas"):
                lines.append("- Variant 差异感知：")
                for delta in context["top_variant_deltas"][:3]:
                    d_type = delta.get("type", "")
                    d_quote = delta.get("quote", "")
                    lines.append(f"  - [{d_type}] {d_quote}")
            if task_type == "price_test" and context.get("acceptable_price_points"):
                lines.append(f"- 可接受价格：{self._format_points(context['acceptable_price_points'])}")
            return "\n".join(lines)

        if section_title == "传播演化":
            lines = [
                f"- 传播后接受度：{self._format_acceptance(summary['post_propagation_acceptance'])}",
                f"- 态度转向率：{summary['attitude_shift_rate']:.0%}",
                f"- 扩散中的高频讨论点：{self._format_points(context['top_resonance_points'])}",
            ]
            if task_type == "packaging_test" and context.get("top_trust_objections"):
                lines.append(f"- 信任疑虑：{self._format_points(context['top_trust_objections'])}")
            if task_type == "ab_test" and context.get("top_persona_divergences"):
                lines.append(f"- 人群差异：{self._format_points(context['top_persona_divergences'])}")
            if task_type == "price_test" and context.get("resisted_price_points"):
                lines.append(f"- 抗拒价格：{self._format_points(context['resisted_price_points'])}")
            return "\n".join(lines)

        if section_title == "价格敏感度与 WTP 分析":
            return "\n".join([
                f"- 可接受价格：{self._format_points(context.get('acceptable_price_points', []))}",
                f"- 抗拒价格：{self._format_points(context.get('resisted_price_points', []))}",
                f"- 价格异议：{self._format_points(context.get('top_price_objections', []))}",
            ])

        if section_title == "价格接受区间与弹性":
            return "\n".join([
                f"- 价格背景：{context.get('price_context', '') or '暂无'}",
                "- WTP 分布应结合真实价格带和传播后接受度共同解释。",
            ])

        if section_title == "视觉认知与货架吸引力":
            return "\n".join([
                f"- 包装吸引点：{self._format_points(context.get('top_packaging_hooks', []))}",
                f"- 混淆触发点：{self._format_points(context.get('top_confusion_triggers', []))}",
            ])

        if section_title == "包装识别与注意力路径":
            return "\n".join([
                f"- 信任疑虑：{self._format_points(context.get('top_trust_objections', []))}",
                "- 货架吸引力应结合第一眼理解、证据位置和包装差异化判断。",
            ])

        if section_title == "偏好对比与统计显著性":
            lines = [f"- 占优 variant：{context.get('winning_variant', '') or '暂无'}"]
            for delta in context.get("top_variant_deltas", [])[:3]:
                lines.append(f"  - {delta.get('quote', delta)}")
            lines.append("- 统计显著性需结合样本量、重复种子和置信度输出。")
            return "\n".join(lines)

        if section_title == "版本差异与选择理由":
            return "\n".join([
                f"- 人群差异：{self._format_points(context.get('top_persona_divergences', []))}",
                "- 版本选择理由应优先引用差异化 VOC 与事件链。",
            ])

        if section_title == "风险与误读":
            lines = [
                f"- 高风险点：{self._format_points(context['top_risk_points'])}",
                f"- 高误读点：{self._format_points(context['top_misreads'])}",
                f"- 风险原声：\n{self._format_quotes(context['representative_voc_quotes']['risk'])}",
                f"- 误读/疑问原声：\n{self._format_quotes(context['representative_voc_quotes']['misread'])}",
            ]
            if task_type == "packaging_test" and context.get("top_confusion_triggers"):
                lines.append(f"- 包装混淆点：{self._format_points(context['top_confusion_triggers'])}")
            if task_type == "price_test" and context.get("top_price_objections"):
                lines.append(f"- 价格异议：{self._format_points(context['top_price_objections'])}")
            if context.get("top_risk_findings"):
                lines.append("- 因果触发发现：")
                for finding in context["top_risk_findings"]:
                    lines.append(f"  - [{finding['finding_type']}] {finding['summary']}")
            if context.get("causal_chains"):
                lines.append("- 事件因果链：")
                for chain in context["causal_chains"][:3]:
                    lines.append(f"  - 发现 {chain['finding_summary']} 触发了事件 {', '.join(chain['event_ids'])}")
            return "\n".join(lines)

        if section_title == "代表性消费者原声":
            lines = [
                f"**正向原声**\n{self._format_quotes(context['representative_voc_quotes']['resonance'])}",
                f"**风险原声**\n{self._format_quotes(context['representative_voc_quotes']['risk'])}",
                f"**误读/疑问原声**\n{self._format_quotes(context['representative_voc_quotes']['misread'])}",
            ]
            if task_type == "packaging_test" and context.get("top_packaging_hooks"):
                lines.append(f"**包装相关原声**\n{self._format_task_quotes(context['top_packaging_hooks'])}")
            if task_type == "price_test" and context.get("top_price_objections"):
                lines.append(f"**价格相关原声**\n{self._format_task_quotes(context['top_price_objections'])}")
            return "\n\n".join(lines)

        if section_title == "行动建议":
            resonance_point = self._first_point(context["top_resonance_points"], "现有核心卖点")
            risk_point = self._first_point(context["top_risk_points"], "潜在争议点")
            misread_point = self._first_point(context["top_misreads"], "传播中的模糊表述")
            lines = [
                f"- 放大高共鸣表达：围绕“{resonance_point}”继续强化概念与文案。",
                f"- 提前澄清风险：针对“{risk_point}”准备更直接的解释与证据。",
                f"- 修正文案误读：对“{misread_point}”补充更具体、更少歧义的表述。",
            ]
            pillars = context.get("research_insight_pillars") or []
            if pillars:
                anchor = self._first_point([str(p.get("summary", "")).strip() for p in pillars if str(p.get("summary", "")).strip()], "研究发现")
                lines.append(f"- 综合传播锚点：优先围绕“{anchor}”统一原声、证据和文案。")
            if task_type == "packaging_test":
                trust = self._first_point(context.get("top_trust_objections", []), "信任疑虑")
                confusion = self._first_point(context.get("top_confusion_triggers", []), "混淆点")
                lines.append(f"- 优化包装信任感：针对“{trust}”增加背书或认证信息。")
                lines.append(f"- 消除包装混淆：对“{confusion}”简化设计或增加说明。")
            if task_type == "ab_test":
                variant = context.get("winning_variant", "") or "占优 variant"
                lines.append(f"- 推广优胜 variant：重点投放“{variant}”并分析其优势要素。")
            if task_type == "price_test":
                acceptable = self._first_point(context.get("acceptable_price_points", []), "可接受价格带")
                resisted = self._first_point(context.get("resisted_price_points", []), "抗拒价格点")
                lines.append(f"- 锚定合理价格：以“{acceptable}”为传播锚点强化价值感知。")
                lines.append(f"- 规避价格雷区：针对“{resisted}”提前准备价值解释或促销话术。")
            if context.get("top_risk_findings"):
                lines.append("- 针对风险发现的优先行动：")
                for finding in context["top_risk_findings"][:3]:
                    lines.append(f"  - 处理 [{finding['finding_type']}] {finding['summary']}")
            if context.get("event_counts"):
                lines.append(f"- 事件类型分布：{context['event_counts']}")
            return "\n".join(lines)

        return ""

    def _format_task_quotes(self, items: List[str]) -> str:
        if not items:
            return "- 暂无"
        lines = []
        for item in items:
            lines.append(f'- "{item}"')
        return "\n".join(lines)

    def _format_acceptance(self, acceptance: Dict[str, float]) -> str:
        return (
            f"正向 {acceptance.get('positive', 0.0):.0%} / "
            f"中立 {acceptance.get('neutral', 0.0):.0%} / "
            f"负向 {acceptance.get('negative', 0.0):.0%}"
        )

    def _format_points(self, points: List[str]) -> str:
        if not points:
            return "暂无显著点位"
        return "；".join(points)

    def _format_finding_type_counts(self, counts: Any) -> str:
        if not isinstance(counts, dict) or not counts:
            return "暂无"

        preferred_order = [
            "category_context",
            "competitor_signal",
            "risk_signal",
            "trend_signal",
            "propagation_signal",
        ]
        lines: List[str] = []
        seen: set[str] = set()
        for finding_type in preferred_order:
            if finding_type in counts:
                seen.add(finding_type)
                lines.append(
                    f"{self._finding_type_label(finding_type)} {int(counts.get(finding_type, 0) or 0)}"
                )
        for finding_type, value in counts.items():
            if finding_type in seen:
                continue
            lines.append(f"{self._finding_type_label(str(finding_type))} {int(value or 0)}")
        return "，".join(lines) if lines else "暂无"

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

    def _format_quotes(self, quotes: List[Dict[str, Any]]) -> str:
        if not quotes:
            return "- 暂无代表性原声"

        def is_template_generated(item: Dict[str, Any]) -> bool:
            metadata = item.get("quote_metadata") or {}
            if isinstance(metadata, dict) and "template_generated" in metadata:
                return bool(metadata.get("template_generated"))
            return True

        sorted_quotes = sorted(quotes, key=is_template_generated)
        llm_count = sum(1 for item in sorted_quotes if not is_template_generated(item))
        template_count = len(sorted_quotes) - llm_count
        lines = [f"- Source: LLM\u751f\u6210 {llm_count} / \u6a21\u62df\u751f\u6210 {template_count}"]
        for item in sorted_quotes:
            quote = str(item.get("quote", "")).strip()
            if not quote:
                continue
            engagement = item.get("engagement", 0)
            source_label = " [\u6a21\u62df\u751f\u6210\uff0c\u975eLLM\u63a8\u7406]" if is_template_generated(item) else ""
            lines.append(f'- "{quote}"{source_label} (engagement {engagement})')
        return "\n".join(lines) if len(lines) > 1 else "- 暂无代表性原声"
