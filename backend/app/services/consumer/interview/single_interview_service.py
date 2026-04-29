"""Single consumer interview service supporting snapshot, live and auto modes."""

import uuid
from typing import Any

from ..society.consumer_roles import ConsumerRole
from .evidence_binder import InterviewEvidenceBinder
from .followup_question_engine import FollowupQuestionEngine
from .history_store import HistoryStore
from .interview_models import ConsumerInterviewRequest, ConsumerInterviewResult, LiveInterviewUnavailable
from .representative_card_builder import RepresentativeCardBuilder
from .summary_synthesizer import InterviewSummarySynthesizer


class SingleInterviewService:
    """Run single-consumer interviews with evidence binding and history persistence."""

    def __init__(self, base_dir=None, simulation_repo=None):
        self.base_dir = base_dir
        self.simulation_repo = simulation_repo
        self.card_builder = RepresentativeCardBuilder(base_dir=base_dir)
        self.evidence_binder = InterviewEvidenceBinder()
        self.followup_engine = FollowupQuestionEngine()
        self.summary_synthesizer = InterviewSummarySynthesizer()
        self.history_store = HistoryStore(base_dir=base_dir)

    def _validate_simulation(self, simulation_id: str) -> None:
        if self.simulation_repo is None:
            return
        sim = self.simulation_repo.get_simulation(simulation_id)
        if sim is None:
            raise ValueError(f"simulation not found: {simulation_id}")
        project_type = getattr(sim, "project_type", "")
        consumer_mode = getattr(sim, "consumer_mode", False)
        if project_type != "consumer_test" and not consumer_mode:
            raise ValueError("Simulation is not a consumer_test simulation")

    def _is_live_available(self, simulation_id: str) -> bool:
        if self.simulation_repo is None:
            return False
        sim = self.simulation_repo.get_simulation(simulation_id)
        if sim is None:
            return False
        from ...simulation_manager import SimulationStatus
        return getattr(sim, "status", None) == SimulationStatus.RUNNING

    def _select_agents(self, request: ConsumerInterviewRequest) -> list:
        cards = []
        if request.agent_ids:
            all_cards = self.card_builder.build_cards(
                request.simulation_id, roles=[], limit=100
            )
            cards = [c for c in all_cards if c["agent_id"] in request.agent_ids]
        elif request.roles:
            cards = self.card_builder.build_cards(
                request.simulation_id, roles=request.roles, limit=request.max_agents
            )
        else:
            cards = self.card_builder.build_cards(
                request.simulation_id, roles=[], limit=request.max_agents
            )
        return cards[:request.max_agents]

    def _build_prompt(self, card: dict, question: str, target_context: dict) -> str:
        segment = card.get("segment", "general")
        role = card.get("role", "")
        key_quote = card.get("key_quote", "")
        attitude_start = card.get("attitude_start", "neutral")
        attitude_latest = card.get("attitude_latest", "neutral")
        event_ids = ", ".join(card.get("event_ids", []))

        prompt_parts = [
            f"You are a consumer persona. Segment: '{segment}'. Your persona segment defines how you evaluate products.",
            f"Your role is: {role}.",
            f"Your key quote: '{key_quote}'.",
            f"Your attitude history: started as {attitude_start}, now {attitude_latest}.",
            f"consumer events you participated in: {event_ids}.",
            f"evidence context: {target_context}.",
            f"Target question: {question}",
        ]
        return " ".join(prompt_parts)

    def _generate_answer(self, card: dict, question: str, prompt: str) -> str:
        role = card.get("role", "")
        if role == ConsumerRole.Skeptic.value:
            return (
                f"As a skeptical consumer, I would need more proof before being convinced. "
                f"The question '{question}' raises valid concerns about trust and evidence."
            )
        elif role == ConsumerRole.Advocate.value:
            return (
                f"As an advocate, I see the value clearly and would share this with others. "
                f"The question '{question}' highlights what I already believe about the product."
            )
        elif role == ConsumerRole.Misreader.value:
            return (
                f"I might have misunderstood the claim initially. "
                f"The question '{question}' makes me want clearer wording and simpler messaging."
            )
        elif role == ConsumerRole.PriceSensitive.value:
            return (
                f"Price matters a lot to my purchase decision. "
                f"Regarding '{question}', I need to know if the value justifies the cost."
            )
        elif role == ConsumerRole.Amplifier.value:
            return (
                f"I am eager to spread the word when I find something worthwhile. "
                f"The question '{question}' touches on what would make me share this more widely."
            )
        elif role == ConsumerRole.TrustRepairable.value:
            return (
                f"My trust was shaken but can be restored with the right actions. "
                f"The question '{question}' points to what would rebuild my confidence."
            )
        else:
            return (
                f"I have a cautious view on this topic. "
                f"The question '{question}' makes me think more carefully before deciding."
            )

    def run(self, request: ConsumerInterviewRequest) -> ConsumerInterviewResult:
        self._validate_simulation(request.simulation_id)

        mode = request.mode
        if mode == "live":
            if not self._is_live_available(request.simulation_id):
                raise LiveInterviewUnavailable("live mode environment is not running")
        elif mode == "auto":
            if self._is_live_available(request.simulation_id):
                mode = "live"
            else:
                mode = "snapshot"

        cards = self._select_agents(request)
        if not cards:
            all_cards = self.card_builder.build_cards(
                request.simulation_id, roles=request.roles or [], limit=request.max_agents
            )
            cards = all_cards

        questions = request.questions
        if not questions:
            questions = [f"What do you think about {request.topic}?"]

        answers = []
        evidence_map = {}

        for card in cards:
            agent_id = card["agent_id"]
            for question in questions:
                prompt = self._build_prompt(card, question, request.target_context)
                answer_text = self._generate_answer(card, question, prompt)
                answer_record = {
                    "agent_id": agent_id,
                    "role": card.get("role", ""),
                    "question": question,
                    "answer": answer_text,
                    "prompt": prompt,
                }
                answers.append(answer_record)
                evidence = self.evidence_binder.bind_answer(
                    card=card,
                    answer=answer_record,
                    target_context=request.target_context,
                )
                evidence_map[agent_id] = evidence

        followup_result = self.followup_engine.generate(
            topic=request.topic, target_context=request.target_context
        )
        followup_questions = [
            fq["question"] for fq in followup_result.get("followup_questions", [])
        ]

        summary = self.summary_synthesizer.synthesize_interview(
            answers=answers,
            evidence_map=evidence_map,
            followup_questions=followup_result.get("followup_questions", []),
        )

        interview_id = f"interview-{uuid.uuid4().hex[:8]}"
        result = ConsumerInterviewResult(
            interview_id=interview_id,
            simulation_id=request.simulation_id,
            topic=request.topic,
            mode=mode,
            answers=answers,
            evidence_map=evidence_map,
            summary=summary,
            followup_questions=followup_questions,
        )

        record = {
            "interview_id": result.interview_id,
            "simulation_id": result.simulation_id,
            "topic": result.topic,
            "mode": result.mode,
            "answers": result.answers,
            "evidence_map": result.evidence_map,
            "summary": result.summary,
            "followup_questions": result.followup_questions,
        }
        self.history_store.write_interview(request.simulation_id, record)
        return result
