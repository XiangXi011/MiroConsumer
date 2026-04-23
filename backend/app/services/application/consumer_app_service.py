"""
Consumer application service

Encapsulates route-level orchestration for consumer-specific flows.
This is the bounded-context boundary: consumer modules own their
own orchestration instead of leaking logic into general API routes.
"""

from typing import Any, Dict, List, Optional

from ...models.project import ProjectManager
from ...repositories import ConsumerStateRepository, SimulationRepository
from ...repositories.filesystem import (
    FilesystemConsumerStateRepository,
    FilesystemSimulationRepository,
)
from ...services.consumer.api_guard import ConsumerApiGuard
from ...services.consumer.brief_adapter import ConsumerBriefAdapter
from ...services.consumer.report_context import ConsumerReportContextBuilder, build_consumer_report_context
from ...contracts.consumer_contracts import ConfidenceSummary, FindingConfidenceSummary
from ...services.consumer.scoring import build_consumer_summary
from ...services.simulation_manager import SimulationManager
from ...utils.locale import t
from ...utils.logger import get_logger

logger = get_logger("miroconsumer.app_service.consumer")


class ConsumerAppService:
    """Application service for consumer-specific simulation and report flows."""

    _simulation_repo: SimulationRepository = FilesystemSimulationRepository()
    _consumer_state_repo: ConsumerStateRepository = FilesystemConsumerStateRepository()

    @classmethod
    def get_consumer_summary(cls, simulation_id: str) -> Dict[str, Any]:
        """
        Build consumer propagation summary for a simulation.

        Raises ValueError on validation failure or missing data.
        """
        state = cls._simulation_repo.get_simulation(simulation_id)
        if not state:
            raise ValueError(t("api.simulationNotFound", id=simulation_id))

        ok, error = ConsumerApiGuard.check_consumer_simulation(state)
        if not ok:
            raise ValueError(error)

        accessor = cls._consumer_state_repo
        builder = ConsumerReportContextBuilder()
        snapshots = accessor.load_consumer_rounds(simulation_id)
        if not snapshots:
            raise ValueError(
                f"consumer round snapshots not found for simulation {simulation_id}"
            )

        # Build Phase 1 context (backward compatible)
        context = builder.build(snapshots)

        # Extract propagation events from snapshots for Phase 2 enrichment
        all_events: List[Dict[str, Any]] = []
        for snap in snapshots:
            for event_data in snap.get("propagation_events", []):
                all_events.append(event_data)

        # Load research findings and brief from consumer_config via consumer-owned accessor
        research_findings = accessor.load_research_findings(simulation_id)
        brief = accessor.load_brief(simulation_id)

        # Phase 4A: load project research snapshot for traces/chunks/sources if available
        traces: List[Any] = []
        chunks: List[Any] = []
        sources: List[Any] = []
        project = ProjectManager.get_project(state.project_id)
        if project and project.project_type == "consumer_test":
            from ...services.consumer.project_research_persistence import load_persisted_snapshot

            snapshot = load_persisted_snapshot(project.project_id)
            if brief is None and getattr(project, "consumer_brief", None):
                brief = ConsumerBriefAdapter.from_payload(project.consumer_brief)
            if snapshot:
                traces = snapshot.retrieval_traces or []
                chunks = snapshot.chunks or []
                sources = snapshot.sources or []

        # Merge Phase 2 fields when events are present
        if all_events:
            initial_labels = [
                s.get("attitude_label", "neutral")
                for s in snapshots
                if s.get("round_num") == 0
            ]
            # Use latest attitude per agent for final labels
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
                traces=traces,
                chunks=chunks,
                sources=sources,
                task_type=(brief.task_type.value if brief is not None else None),
                brief=brief,
            )
            phase2_context = build_consumer_report_context(
                summary=phase2_summary,
                findings=research_findings,
                events=all_events,
                traces=traces,
                report_confidence=phase2_summary.report_confidence,
                evidence_validation_summary=phase2_summary.evidence_validation_summary,
            )

            context["event_counts"] = phase2_summary.event_counts
            context["top_risk_findings"] = phase2_summary.top_risk_findings
            context["top_clarification_opportunities"] = phase2_summary.top_clarification_opportunities
            context["causal_voc_quotes"] = phase2_summary.causal_voc_quotes
            context["causal_chains"] = phase2_context["causal_chains"]
            context["event_led_reversals"] = phase2_context["event_led_reversals"]
            context["persona_group_signals"] = phase2_context["persona_group_signals"]
            context["cascade_metrics"] = phase2_context.get("cascade_metrics", {})
            context["task_type"] = phase2_context.get("task_type", "concept_test")
            for key, default in (
                ("top_packaging_hooks", []),
                ("top_trust_objections", []),
                ("top_confusion_triggers", []),
                ("winning_variant", ""),
                ("top_variant_deltas", []),
                ("top_persona_divergences", []),
                ("acceptable_price_points", []),
                ("resisted_price_points", []),
                ("top_price_objections", []),
                ("price_context", ""),
            ):
                context[key] = phase2_context.get(key, default)
            # Phase 4A confidence fields (consumer_test only)
            if phase2_summary.report_confidence is not None:
                # Use typed contract to reduce ad-hoc dict handling
                rc = phase2_summary.report_confidence
                if isinstance(rc, dict):
                    context["report_confidence"] = rc
                else:
                    conf = ConfidenceSummary(
                        confidence_label=rc.confidence_label,
                        confidence_score=rc.confidence_score,
                        confidence_reasons=rc.confidence_reasons,
                        support_summary=rc.support_summary,
                        replay_alignment=rc.replay_alignment,
                        finding_confidence_summary=[
                            FindingConfidenceSummary(
                                finding_id=fc.finding_id,
                                confidence_label=fc.confidence_label,
                                confidence_score=fc.confidence_score,
                            )
                            for fc in rc.finding_confidences
                        ],
                        low_confidence_findings=[
                            fc.model_dump()
                            for fc in rc.finding_confidences
                            if fc.confidence_label in ("low", "unknown")
                        ],
                    )
                    context["report_confidence"] = conf.model_dump()
            if phase2_summary.evidence_validation_summary is not None:
                context["evidence_validation_summary"] = phase2_summary.evidence_validation_summary
            if phase2_summary.evidence_gatekeeping_summary is not None:
                context["evidence_gatekeeping_summary"] = phase2_summary.evidence_gatekeeping_summary
            if phase2_summary.finding_confidences:
                context["finding_confidences"] = phase2_summary.finding_confidences

        return context
