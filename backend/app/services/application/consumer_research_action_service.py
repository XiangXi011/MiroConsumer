"""Consumer research action service for Phase 6F semantic activation."""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, Optional

from ...repositories import SimulationRepository
from ...repositories.filesystem import FilesystemSimulationRepository
from ...services.consumer.api_guard import ConsumerApiGuard
from ...services.consumer.event_ontology import map_legacy_event_type_to_consumer
from ...services.consumer.report_context import build_consumer_report_context
from ...services.consumer.research_tool_semantics import (
    get_consumer_tool_label,
)
from ...services.consumer.scoring import ConsumerScoringService, build_consumer_summary
from ...services.zep_tools import ZepToolsService
from .branch_app_service import BranchAppService


class ConsumerResearchActionType(str, Enum):
    """Supported consumer research action types."""

    DEEP_DIVE_CONCLUSION = "deep_dive_conclusion"
    EXPLAIN_PROPAGATION_PATH = "explain_propagation_path"
    VERIFY_EVIDENCE = "verify_evidence"
    INTERVIEW_CONSUMERS = "interview_consumers"
    COMPARE_BRANCH_DELTA = "compare_branch_delta"


class ConsumerResearchActionService:
    """Application service for consumer research actions.

    Deterministic under tests and easy to monkeypatch via class-level
    dependency overrides.
    """

    _simulation_repo: SimulationRepository = FilesystemSimulationRepository()
    _zep_tools_class = ZepToolsService
    _branch_app_service_class = BranchAppService

    @classmethod
    def run_action(cls, simulation_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a consumer research action.

        Args:
            simulation_id: The simulation ID.
            payload: Must contain ``action_type`` and ``target`` keys.
                ``target`` must be a dict with optional ``kind``, ``id``, ``text``.
                ``context`` is an optional dict.

        Returns:
            Unified Phase 6F response shape with exactly these top-level keys:
            action_type, simulation_id, target, title, summary,
            details_markdown, evidence, tool_trace, handoff.

        Raises:
            ValueError: On validation failures (missing simulation, non-consumer
                simulation, unknown action, missing target, non-dict target).
        """
        state = cls._simulation_repo.get_simulation(simulation_id)
        if state is None:
            raise ValueError(f"Simulation not found: {simulation_id}")

        ok, error = ConsumerApiGuard.check_consumer_simulation(state)
        if not ok:
            raise ValueError(error)

        action_type_str = str(payload.get("action_type", "")).strip()
        if not action_type_str:
            raise ValueError("action_type is required")

        try:
            action_type = ConsumerResearchActionType(action_type_str)
        except ValueError:
            raise ValueError(f"Unknown action_type: {action_type_str}")

        target = payload.get("target")
        if target is None:
            raise ValueError("target is required")
        if not isinstance(target, dict):
            raise ValueError("target must be a dict")

        context = payload.get("context") or {}
        if not isinstance(context, dict):
            context = {}

        report_ctx = cls._load_report_context(simulation_id)

        if action_type == ConsumerResearchActionType.DEEP_DIVE_CONCLUSION:
            return cls._deep_dive_conclusion(
                simulation_id, target, context, state, report_ctx
            )

        if action_type == ConsumerResearchActionType.EXPLAIN_PROPAGATION_PATH:
            return cls._explain_propagation_path(
                simulation_id, target, context, state
            )

        if action_type == ConsumerResearchActionType.VERIFY_EVIDENCE:
            return cls._verify_evidence(
                simulation_id, target, context, state, report_ctx
            )

        if action_type == ConsumerResearchActionType.INTERVIEW_CONSUMERS:
            return cls._interview_consumers(
                simulation_id, target, context
            )

        if action_type == ConsumerResearchActionType.COMPARE_BRANCH_DELTA:
            return cls._compare_branch_delta(
                simulation_id, target, context
            )

        raise ValueError(f"Unhandled action_type: {action_type.value}")

    @classmethod
    def _deep_dive_conclusion(
        cls,
        simulation_id: str,
        target: Dict[str, Any],
        context: Dict[str, Any],
        state: Any,
        report_ctx: Dict[str, Any],
    ) -> Dict[str, Any]:
        query = target.get("text") or target.get("id") or ""
        zep = cls._zep_tools_class()
        result = zep.insight_forge(
            graph_id=getattr(state, "graph_id", ""),
            query=str(query),
            simulation_requirement=getattr(state, "simulation_requirement", ""),
            report_context=report_ctx,
        )
        result_text = result.to_text() if hasattr(result, "to_text") else str(result)
        support_level = "medium" if result_text else "insufficient"
        quote_count = result_text.count(">") if result_text else 0
        return {
            "action_type": ConsumerResearchActionType.DEEP_DIVE_CONCLUSION.value,
            "simulation_id": simulation_id,
            "target": target,
            "title": get_consumer_tool_label("insight_forge", "zh"),
            "summary": result_text,
            "details_markdown": result_text,
            "evidence": {
                "support_level": support_level,
                "source_count": 0,
                "simulation_quote_count": quote_count,
                "gatekeeping_status": "pending",
            },
            "tool_trace": {
                "tool_name": "insight_forge",
                "consumer_tool_label": get_consumer_tool_label("insight_forge"),
                "query": str(query),
            },
            "handoff": {
                "handoff_type": "",
                "target_context": {},
            },
        }

    @classmethod
    def _explain_propagation_path(
        cls,
        simulation_id: str,
        target: Dict[str, Any],
        context: Dict[str, Any],
        state: Any,
    ) -> Dict[str, Any]:
        query = target.get("text") or target.get("id") or ""
        zep = cls._zep_tools_class()
        result = zep.panorama_search(
            graph_id=getattr(state, "graph_id", ""),
            query=str(query),
            include_expired=True,
        )
        result_text = result.to_text() if hasattr(result, "to_text") else str(result)
        support_level = "medium" if result_text else "insufficient"
        return {
            "action_type": ConsumerResearchActionType.EXPLAIN_PROPAGATION_PATH.value,
            "simulation_id": simulation_id,
            "target": target,
            "title": get_consumer_tool_label("panorama_search", "zh"),
            "summary": result_text,
            "details_markdown": result_text,
            "evidence": {
                "support_level": support_level,
                "source_count": 0,
                "simulation_quote_count": 0,
                "gatekeeping_status": "pending",
            },
            "tool_trace": {
                "tool_name": "panorama_search",
                "consumer_tool_label": get_consumer_tool_label("panorama_search"),
                "query": str(query),
            },
            "handoff": {
                "handoff_type": "",
                "target_context": {},
            },
        }

    @classmethod
    def _verify_evidence(
        cls,
        simulation_id: str,
        target: Dict[str, Any],
        context: Dict[str, Any],
        state: Any,
        report_ctx: Dict[str, Any],
    ) -> Dict[str, Any]:
        query = target.get("text") or target.get("id") or ""
        evidence_lookup = cls._lookup_evidence(report_ctx, str(query))
        zep = cls._zep_tools_class()
        search_result = zep.quick_search(
            graph_id=getattr(state, "graph_id", ""),
            query=str(query),
            limit=10,
        )
        search_text = (
            search_result.to_text()
            if hasattr(search_result, "to_text")
            else str(search_result)
        )

        match_count = evidence_lookup.get("match_count", 0)
        if match_count > 0 and search_text:
            support_level = "strong"
        elif match_count > 0:
            support_level = "medium"
        elif search_text:
            support_level = "weak"
        else:
            support_level = "insufficient"

        source_count = match_count + (1 if search_text else 0)
        details = "## 报告上下文证据检索\n\n"
        details += f"查询: `{evidence_lookup.get('query', '')}`\n\n"
        details += f"匹配数: {match_count}\n\n"
        if evidence_lookup.get("matches"):
            for m in evidence_lookup["matches"]:
                details += f"- {m}\n"
        details += "\n## Zep 快速搜索结果\n\n"
        details += search_text or "（无结果）"

        return {
            "action_type": ConsumerResearchActionType.VERIFY_EVIDENCE.value,
            "simulation_id": simulation_id,
            "target": target,
            "title": get_consumer_tool_label("quick_search", "zh"),
            "summary": f"证据校验完成: support_level={support_level}",
            "details_markdown": details,
            "evidence": {
                "support_level": support_level,
                "source_count": source_count,
                "simulation_quote_count": 0,
                "gatekeeping_status": "pending",
            },
            "tool_trace": {
                "tool_name": "quick_search",
                "consumer_tool_label": get_consumer_tool_label("quick_search"),
                "query": str(query),
            },
            "handoff": {
                "handoff_type": "",
                "target_context": {},
            },
        }

    @classmethod
    def _interview_consumers(
        cls,
        simulation_id: str,
        target: Dict[str, Any],
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        finding_id = ""
        if target.get("kind") == "finding":
            finding_id = target.get("id") or ""

        target_context = {
            "report_id": context.get("report_id", ""),
            "section_index": context.get("section_index", ""),
            "finding_id": finding_id,
            "claim": context.get("claim", target.get("text", "")),
            "branch_id": context.get("branch_id", ""),
        }

        return {
            "action_type": ConsumerResearchActionType.INTERVIEW_CONSUMERS.value,
            "simulation_id": simulation_id,
            "target": target,
            "title": "追问消费者",
            "summary": "已生成 Phase 6I 访谈上下文",
            "details_markdown": "",
            "evidence": {
                "support_level": "simulation_only",
                "source_count": 0,
                "simulation_quote_count": 0,
                "gatekeeping_status": "handoff",
            },
            "tool_trace": {
                "tool_name": "",
                "consumer_tool_label": "",
                "query": "",
            },
            "handoff": {
                "handoff_type": "phase6i_interview",
                "target_context": target_context,
            },
        }

    @classmethod
    def _compare_branch_delta(
        cls,
        simulation_id: str,
        target: Dict[str, Any],
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        branch_id = (
            context.get("branch_id")
            or target.get("id")
            or target.get("text")
            or ""
        )
        result = cls._branch_app_service_class.get_branch_comparison(
            simulation_id, str(branch_id)
        )
        result_text = (
            result.to_text()
            if hasattr(result, "to_text")
            else str(result)
        )
        return {
            "action_type": ConsumerResearchActionType.COMPARE_BRANCH_DELTA.value,
            "simulation_id": simulation_id,
            "target": target,
            "title": "比较分支差异",
            "summary": result_text,
            "details_markdown": result_text,
            "evidence": {
                "support_level": "medium",
                "source_count": 0,
                "simulation_quote_count": 0,
                "gatekeeping_status": "pending",
            },
            "tool_trace": {
                "tool_name": "",
                "consumer_tool_label": "",
                "query": "",
            },
            "handoff": {
                "handoff_type": "",
                "target_context": {},
            },
        }

    @classmethod
    def _load_report_context(cls, simulation_id: str) -> Dict[str, Any]:
        """Load a minimal report context for passing to Zep tools."""
        from ...services.consumer.report_context import ConsumerReportContextBuilder
        from ...repositories.filesystem import FilesystemConsumerStateRepository

        accessor = FilesystemConsumerStateRepository()
        snapshots = accessor.load_consumer_rounds(simulation_id)
        if not snapshots:
            return {}

        builder = ConsumerReportContextBuilder()
        context = builder.build(snapshots)

        all_events = []
        for snap in snapshots:
            for event_data in snap.get("propagation_events", []):
                all_events.append(event_data)

        if all_events:
            initial_labels = [
                s.get("attitude_label", "neutral")
                for s in snapshots
                if s.get("round_num") == 0
            ]
            latest_attitudes: Dict[str, str] = {}
            for s in snapshots:
                agent_id = s.get("agent_id", "")
                if agent_id:
                    latest_attitudes[agent_id] = s.get("attitude_label", "neutral")
            final_labels = list(latest_attitudes.values())

            summary = build_consumer_summary(
                events=all_events,
                findings=[],
                initial_labels=initial_labels,
                final_labels=final_labels,
            )
            ctx = build_consumer_report_context(summary, [], all_events)
            context.update({k: v for k, v in ctx.items() if k not in context})

        return context

    @classmethod
    def _lookup_evidence(cls, report_ctx: Dict[str, Any], target: str) -> Dict[str, Any]:
        """Search report context for evidence matching the target query."""
        target_lower = target.lower()
        matches: list[dict] = []

        for finding in report_ctx.get("enriched_findings", []):
            summary = str(finding.get("summary", ""))
            if target_lower in summary.lower():
                matches.append({
                    "finding_id": finding.get("finding_id", ""),
                    "finding_type": finding.get("finding_type", ""),
                    "summary": summary,
                })

        for chain in report_ctx.get("causal_chains", []):
            summary = str(chain.get("finding_summary", ""))
            if target_lower in summary.lower():
                matches.append({
                    "trigger_finding_ids": chain.get("trigger_finding_ids", []),
                    "finding_summary": summary,
                    "event_types": chain.get("event_types", []),
                })

        return {
            "query": target,
            "match_count": len(matches),
            "matches": matches,
        }


__all__ = [
    "ConsumerResearchActionType",
    "ConsumerResearchActionService",
]
