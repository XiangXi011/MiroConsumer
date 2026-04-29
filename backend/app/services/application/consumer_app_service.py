"""
Consumer application service

Encapsulates route-level orchestration for consumer-specific flows.
This is the bounded-context boundary: consumer modules own their
own orchestration instead of leaking logic into general API routes.
"""

from typing import Any, Dict, List, Optional

from ...repositories import (
    ConsumerProjectResearchProvider,
    ConsumerStateRepository,
    SimulationRepository,
)
from ...repositories.filesystem import (
    FilesystemConsumerProjectResearchProvider,
    FilesystemConsumerStateRepository,
    FilesystemSimulationRepository,
)
from ...services.consumer.api_guard import ConsumerApiGuard
from ...services.consumer.brief_adapter import ConsumerBriefAdapter
from ...services.consumer.report_context import ConsumerReportContextBuilder, build_consumer_report_context
from ...services.consumer.society.channel_report_adapter import ChannelReportAdapter
from ...services.consumer.society.report_adapter import SocietyReportAdapter
from ...services.consumer.society.state_store import SocietyStateStore
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
    _project_research_provider: ConsumerProjectResearchProvider = (
        FilesystemConsumerProjectResearchProvider()
    )

    @classmethod
    def _require_consumer_simulation(cls, simulation_id: str) -> Any:
        state = cls._simulation_repo.get_simulation(simulation_id)
        if not state:
            raise ValueError(t("api.simulationNotFound", id=simulation_id))
        ok, error = ConsumerApiGuard.check_consumer_simulation(state)
        if not ok:
            raise ValueError(error)
        return state

    @classmethod
    def get_consumer_summary(cls, simulation_id: str) -> Dict[str, Any]:
        """
        Build consumer propagation summary for a simulation.

        Raises ValueError on validation failure or missing data.
        """
        state = cls._require_consumer_simulation(simulation_id)

        accessor = cls._consumer_state_repo
        builder = ConsumerReportContextBuilder()
        snapshots = accessor.load_consumer_rounds(simulation_id)
        if not snapshots:
            society_context = SocietyReportAdapter().build_report_context(simulation_id)
            if society_context.get("society_agents_count", 0) > 0:
                return society_context
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

        # Phase 4A: load project research snapshot for traces/chunks/sources via provider
        traces: List[Any] = []
        chunks: List[Any] = []
        sources: List[Any] = []
        ctx = cls._project_research_provider.get_context(state.project_id)
        if ctx.is_consumer_project:
            if brief is None and ctx.brief_payload is not None:
                brief = ConsumerBriefAdapter.from_payload(ctx.brief_payload)
            traces = ctx.traces
            chunks = ctx.chunks
            sources = ctx.sources

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

        society_context = SocietyReportAdapter().build_report_context(simulation_id)
        return SocietyReportAdapter().merge_into_context(context, society_context)

    @classmethod
    def get_channel_summary(cls, simulation_id: str) -> Dict[str, Any]:
        cls._require_consumer_simulation(simulation_id)
        return ChannelReportAdapter().build_report_context(simulation_id)

    @classmethod
    def get_channel_events(cls, simulation_id: str) -> Dict[str, Any]:
        cls._require_consumer_simulation(simulation_id)
        return {"events": SocietyStateStore().read_channel_events(simulation_id)}

    @classmethod
    def get_propagation_paths(cls, simulation_id: str) -> Dict[str, Any]:
        cls._require_consumer_simulation(simulation_id)
        return {"paths": SocietyStateStore().read_propagation_paths(simulation_id)}

    # ============== Phase 6I: Interview & Focus Group ==============

    @classmethod
    def list_representative_agents(cls, simulation_id: str) -> Dict[str, Any]:
        cls._require_consumer_simulation(simulation_id)
        from ...services.consumer.interview.representative_card_builder import RepresentativeCardBuilder
        cards = RepresentativeCardBuilder().build_cards(simulation_id, roles=[], limit=100)
        return {"items": cards}

    @classmethod
    def run_consumer_interview(cls, simulation_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        cls._require_consumer_simulation(simulation_id)
        from ...services.consumer.interview.interview_models import ConsumerInterviewRequest, LiveInterviewUnavailable
        from ...services.consumer.interview.single_interview_service import SingleInterviewService
        request = ConsumerInterviewRequest(
            simulation_id=simulation_id,
            topic=payload.get("topic", ""),
            questions=payload.get("questions", []),
            agent_ids=payload.get("agent_ids", []),
            roles=payload.get("roles", []),
            mode=payload.get("mode", "snapshot"),
            max_agents=payload.get("max_agents", 1),
            target_context=payload.get("target_context", {}),
        )
        try:
            result = SingleInterviewService(simulation_repo=cls._simulation_repo).run(request)
        except LiveInterviewUnavailable as exc:
            raise ValueError(str(exc)) from exc
        return {
            "interview_id": result.interview_id,
            "simulation_id": result.simulation_id,
            "topic": result.topic,
            "mode": result.mode,
            "answers": result.answers,
            "evidence_map": result.evidence_map,
            "summary": result.summary,
            "followup_questions": result.followup_questions,
        }

    @classmethod
    def run_focus_group(cls, simulation_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        cls._require_consumer_simulation(simulation_id)
        from ...services.consumer.interview.interview_models import ConsumerInterviewRequest
        from ...services.consumer.interview.focus_group_service import FocusGroupService
        request = ConsumerInterviewRequest(
            simulation_id=simulation_id,
            topic=payload.get("topic", ""),
            questions=payload.get("questions", []),
            agent_ids=payload.get("agent_ids", []),
            roles=payload.get("roles", []),
            mode=payload.get("mode", "snapshot"),
            max_agents=payload.get("max_agents", 8),
            target_context=payload.get("target_context", {}),
        )
        result = FocusGroupService(simulation_repo=cls._simulation_repo).run_focus_group(
            request, moderator_goal=payload.get("moderator_goal", "")
        )
        return {
            "focus_group_id": result.focus_group_id,
            "simulation_id": result.simulation_id,
            "topic": result.topic,
            "moderator_goal": result.moderator_goal,
            "participant_cards": result.participant_cards,
            "turns": result.turns,
            "consensus": result.consensus,
            "disagreements": result.disagreements,
            "next_what_if_experiments": result.next_what_if_experiments,
            "evidence_map": result.evidence_map,
        }

    @classmethod
    def list_interview_history(cls, simulation_id: str) -> Dict[str, Any]:
        cls._require_consumer_simulation(simulation_id)
        from ...services.consumer.interview.history_store import HistoryStore
        history = HistoryStore().list_interviews(simulation_id)
        if not history:
            raise ValueError("history not found")
        return {"items": history}

    @classmethod
    def list_focus_group_history(cls, simulation_id: str) -> Dict[str, Any]:
        cls._require_consumer_simulation(simulation_id)
        from ...services.consumer.interview.history_store import HistoryStore
        history = HistoryStore().list_focus_groups(simulation_id)
        if not history:
            raise ValueError("history not found")
        return {"items": history}
