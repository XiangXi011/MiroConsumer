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
from ..reasoning_trace import append_reasoning_traces


class SimulationRunnerLiveInterviewClient:
    """Thin adapter over the legacy live interview IPC path."""

    def check_env_alive(self, simulation_id: str) -> bool:
        from ...simulation_runner import SimulationRunner

        return SimulationRunner.check_env_alive(simulation_id)

    def interview_agents_batch(
        self,
        *,
        simulation_id: str,
        interviews: list[dict[str, Any]],
        platform: str | None = None,
        timeout: float = 120.0,
    ) -> dict[str, Any]:
        from ...simulation_runner import SimulationRunner

        return SimulationRunner.interview_agents_batch(
            simulation_id=simulation_id,
            interviews=interviews,
            platform=platform,
            timeout=timeout,
        )


class SingleInterviewService:
    """Run single-consumer interviews with evidence binding and history persistence."""

    def __init__(self, base_dir=None, simulation_repo=None, live_runner=None):
        self.base_dir = base_dir
        self.simulation_repo = simulation_repo
        self.live_runner = live_runner or SimulationRunnerLiveInterviewClient()
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
        if self.live_runner is None:
            return False
        try:
            return bool(self.live_runner.check_env_alive(simulation_id))
        except Exception:
            return False

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

    def _legacy_agent_id_for_card(self, card: dict, fallback_index: int) -> int:
        candidates = [
            card.get("legacy_agent_id"),
            card.get("oasis_agent_id"),
            card.get("raw_agent_id"),
            card.get("state", {}).get("legacy_agent_id") if isinstance(card.get("state"), dict) else None,
            card.get("traits", {}).get("legacy_agent_id") if isinstance(card.get("traits"), dict) else None,
            card.get("agent_id"),
        ]
        for value in candidates:
            if value is None:
                continue
            if isinstance(value, int):
                return value
            text = str(value).strip()
            if text.isdigit():
                return int(text)
        return fallback_index

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

    def _trace_for_answer(self, answer_record: dict[str, Any]) -> dict[str, Any]:
        source = str(answer_record.get("source", "snapshot_template"))
        if source == "legacy_live_interview":
            backend = "llm"
            llm_invoked = True
            fallback_reason = ""
        elif source == "snapshot_template":
            backend = "template_fallback"
            llm_invoked = False
            fallback_reason = "snapshot_template"
        else:
            backend = "rules"
            llm_invoked = False
            fallback_reason = ""
        return {
            "reasoning_backend": backend,
            "llm_invoked": llm_invoked,
            "source": source,
            "fallback_reason": fallback_reason,
            "model": "",
            "latency_ms": 0.0,
            "reasoning_summary": str(answer_record.get("answer", "")),
        }

    def _extract_legacy_response_text(self, payload: dict) -> str:
        if not isinstance(payload, dict):
            return str(payload)
        if payload.get("response"):
            return str(payload["response"])
        result = payload.get("result")
        if isinstance(result, dict):
            for key in ("response", "answer", "text", "content"):
                if result.get(key):
                    return str(result[key])
        for key in ("answer", "text", "content"):
            if payload.get(key):
                return str(payload[key])
        return str(payload)

    def _run_live_interview(
        self,
        *,
        request: ConsumerInterviewRequest,
        cards: list[dict],
        questions: list[str],
    ) -> list[dict[str, Any]]:
        interviews = []
        refs = []
        for index, card in enumerate(cards):
            for question in questions:
                prompt = self._build_prompt(card, question, request.target_context)
                legacy_agent_id = self._legacy_agent_id_for_card(card, index)
                interviews.append({"agent_id": legacy_agent_id, "prompt": prompt})
                refs.append(
                    {
                        "legacy_agent_id": legacy_agent_id,
                        "consumer_agent_id": card["agent_id"],
                        "card": card,
                        "question": question,
                        "prompt": prompt,
                    }
                )

        if not interviews:
            return []

        result = self.live_runner.interview_agents_batch(
            simulation_id=request.simulation_id,
            interviews=interviews,
            platform=request.target_context.get("platform"),
            timeout=float(request.target_context.get("timeout", 120)),
        )
        if not result.get("success", False):
            raise LiveInterviewUnavailable(str(result.get("error") or "live interview failed"))

        raw_results = result.get("result", {}).get("results", {})
        if isinstance(raw_results, list):
            iterable_results = list(enumerate(raw_results))
        elif isinstance(raw_results, dict):
            iterable_results = list(raw_results.items())
        else:
            iterable_results = []

        answers = []
        used_ref_indexes: set[int] = set()
        for key, payload in iterable_results:
            if not isinstance(payload, dict):
                payload = {"response": payload}
            legacy_agent_id = payload.get("agent_id")
            ref_index = None
            for idx, ref in enumerate(refs):
                if idx in used_ref_indexes:
                    continue
                if legacy_agent_id is None or ref["legacy_agent_id"] == legacy_agent_id:
                    ref_index = idx
                    break
            if ref_index is None and refs:
                ref_index = 0
            if ref_index is None:
                continue
            used_ref_indexes.add(ref_index)
            ref = refs[ref_index]
            card = ref["card"]
            answers.append(
                {
                    "agent_id": card["agent_id"],
                    "consumer_agent_id": card["agent_id"],
                    "legacy_agent_id": ref["legacy_agent_id"],
                    "role": card.get("role", ""),
                    "question": ref["question"],
                    "answer": self._extract_legacy_response_text(payload),
                    "prompt": ref["prompt"],
                    "platform": payload.get("platform"),
                    "live_result_key": str(key),
                    "source": "legacy_live_interview",
                }
            )

        if not answers:
            raise LiveInterviewUnavailable("live interview returned no answers")
        return answers

    def run(self, request: ConsumerInterviewRequest) -> ConsumerInterviewResult:
        self._validate_simulation(request.simulation_id)

        mode = request.mode
        requested_mode = mode
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

        if mode == "live":
            try:
                answers = self._run_live_interview(request=request, cards=cards, questions=questions)
            except LiveInterviewUnavailable:
                if requested_mode == "auto":
                    mode = "snapshot"
                    answers = []
                else:
                    raise

        for card in cards:
            agent_id = card["agent_id"]
            card_answers = [a for a in answers if a.get("agent_id") == agent_id]
            if not card_answers:
                for question in questions:
                    prompt = self._build_prompt(card, question, request.target_context)
                    answer_text = self._generate_answer(card, question, prompt)
                    card_answers.append(
                        {
                            "agent_id": agent_id,
                            "role": card.get("role", ""),
                            "question": question,
                            "answer": answer_text,
                            "prompt": prompt,
                            "source": "snapshot_template",
                        }
                    )
                answers.extend(card_answers)

            for answer_record in card_answers:
                answer_record = {
                    **answer_record,
                    "role": card.get("role", ""),
                }
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
        append_reasoning_traces(
            str(self.history_store.base_dir / request.simulation_id),
            [self._trace_for_answer(answer) for answer in answers],
        )
        return result
