"""Virtual focus group service with fixed 4-turn structure."""

import uuid
from typing import Any, Dict, List

from ..society.consumer_roles import ConsumerRole
from .evidence_binder import InterviewEvidenceBinder
from .followup_question_engine import FollowupQuestionEngine
from .history_store import HistoryStore
from .interview_models import ConsumerInterviewRequest, FocusGroupSession
from .disagreement_detector import DisagreementDetector
from .moderator_prompt_engine import ModeratorPromptEngine
from .representative_card_builder import RepresentativeCardBuilder


class FocusGroupService:
    """Run multi-agent focus groups with consensus/disagreement detection and history persistence."""

    def __init__(self, base_dir=None, simulation_repo=None):
        self.base_dir = base_dir
        self.simulation_repo = simulation_repo
        self.card_builder = RepresentativeCardBuilder(base_dir=base_dir)
        self.evidence_binder = InterviewEvidenceBinder()
        self.followup_engine = FollowupQuestionEngine()
        self.history_store = HistoryStore(base_dir=base_dir)
        self.moderator_prompt_engine = ModeratorPromptEngine()
        self.disagreement_detector = DisagreementDetector()

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

    def _select_participants(self, simulation_id: str, roles: List[str], max_agents: int) -> List[Dict[str, Any]]:
        cards = self.card_builder.build_cards(
            simulation_id, roles=roles or [], limit=max_agents
        )
        return cards[:min(max_agents, 8)]

    def _build_moderator_prompt(self, topic: str, moderator_goal: str, participant_cards: List[Dict[str, Any]], target_context: Dict[str, Any]) -> str:
        roles = [c.get("role", "") for c in participant_cards]
        plan = self.moderator_prompt_engine.build(
            topic=topic,
            moderator_goal=moderator_goal,
            participant_roles=roles,
            target_context=target_context,
        )
        return (
            f"Moderator goal: {plan['research_goal']}. "
            f"Claim: {plan['claim']}. "
            f"Participants: {', '.join(plan['participant_roles'])}. "
            f"Source rule: {plan['source_rule']}."
        )

    def _build_discussion_contexts(
        self,
        simulation_id: str,
        participant_cards: List[Dict[str, Any]],
        target_context: Dict[str, Any],
    ) -> Dict[str, Dict[str, Any]]:
        rounds = self.card_builder.store.read_rounds(simulation_id)
        channel_events = self.card_builder.store.read_channel_events(simulation_id)
        channel_metrics = self.card_builder.store.read_channel_metrics(simulation_id).get("channels", {})
        prior_interviews = self.history_store.list_interviews(simulation_id)
        evidence_map = dict(target_context.get("evidence_map", {}) or {})
        target_finding = str(target_context.get("finding_id", ""))

        contexts: Dict[str, Dict[str, Any]] = {}
        for card in participant_cards:
            agent_id = card["agent_id"]
            event_stream = []
            for snapshot in rounds:
                for event in snapshot.get("events", []):
                    if event.get("agent_id") == agent_id:
                        event_stream.append(
                            {
                                "event_id": event.get("event_id", ""),
                                "event_type": event.get("consumer_event_type", ""),
                                "quote": event.get("quote", ""),
                                "finding_ids": list(event.get("finding_ids", []) or []),
                            }
                        )

            agent_channel_events = [
                event
                for event in channel_events
                if event.get("actor_id") == agent_id
                or event.get("agent_id") == agent_id
                or event.get("source_agent_id") == agent_id
            ]

            prior_answers = []
            for interview in prior_interviews:
                for answer in interview.get("answers", []):
                    if answer.get("agent_id") == agent_id or answer.get("consumer_agent_id") == agent_id:
                        prior_answers.append(
                            {
                                "interview_id": interview.get("interview_id", ""),
                                "answer": answer.get("answer", ""),
                                "question": answer.get("question", ""),
                            }
                        )

            channel_id = card.get("channel_id", "")
            contexts[agent_id] = {
                "agent_history": {
                    "attitude_start": card.get("attitude_start", "neutral"),
                    "attitude_latest": card.get("attitude_latest", "neutral"),
                    "purchase_intent_start": card.get("purchase_intent_start", 0.5),
                    "purchase_intent_latest": card.get("purchase_intent_latest", 0.5),
                    "key_quote": card.get("key_quote", ""),
                },
                "event_stream": event_stream[:5],
                "channel_id": channel_id,
                "channel_context": {
                    "channel_id": channel_id,
                    "metrics": dict(channel_metrics.get(channel_id, {}) or {}),
                    "events": agent_channel_events[:5],
                },
                "evidence_map": evidence_map,
                "prior_answers": prior_answers[-5:],
                "target_finding": target_finding,
            }
        return contexts

    def _contextualize_response(self, base_response: str, context: Dict[str, Any]) -> str:
        channel_id = context.get("channel_id", "")
        event_quote = ""
        if context.get("event_stream"):
            event_quote = context["event_stream"][0].get("quote", "")
        prior_answer = ""
        if context.get("prior_answers"):
            prior_answer = context["prior_answers"][-1].get("answer", "")
        target_finding = context.get("target_finding", "")

        details = []
        if channel_id:
            details.append(f"Channel context: {channel_id}.")
        if event_quote:
            details.append(f"Observed event: {event_quote}")
        if prior_answer:
            details.append(f"Prior answer: {prior_answer}")
        if target_finding:
            details.append(f"Target finding: {target_finding}.")
        if not details:
            return base_response
        return f"{base_response} {' '.join(details)}"

    def _run_turn(
        self,
        turn_number: int,
        topic: str,
        participant_cards: List[Dict[str, Any]],
        moderator_prompt: str,
        target_context: Dict[str, Any],
        discussion_contexts: Dict[str, Dict[str, Any]],
    ) -> Dict[str, Any]:
        turn = {"turn": turn_number, "responses": []}

        if turn_number == 1:
            for card in participant_cards:
                agent_id = card["agent_id"]
                role = card.get("role", "")
                if role == ConsumerRole.Skeptic.value:
                    response = f"As a skeptic, I have doubts about {topic} and want more proof."
                elif role == ConsumerRole.Advocate.value:
                    response = f"As an advocate, I support {topic} and see clear value."
                elif role == ConsumerRole.Misreader.value:
                    response = f"I find {topic} confusing and need clearer messaging."
                elif role == ConsumerRole.PriceSensitive.value:
                    response = f"My concern about {topic} is whether the price feels justified."
                elif role == ConsumerRole.Amplifier.value:
                    response = f"If {topic} resonates, I would share it widely with my network."
                elif role == ConsumerRole.TrustRepairable.value:
                    response = f"Regarding {topic}, I need reassurance before I can trust again."
                elif role == ConsumerRole.Blocker.value:
                    response = f"I remain opposed to {topic} based on current information."
                else:
                    response = f"I have a neutral opinion on {topic}."
                context = discussion_contexts.get(agent_id, {})
                response = self._contextualize_response(response, context)
                turn["responses"].append({"agent_id": agent_id, "role": role, "response": response, "context": context})

        elif turn_number == 2:
            for card in participant_cards:
                agent_id = card["agent_id"]
                role = card.get("role", "")
                if role == ConsumerRole.Skeptic.value:
                    response = "I disagree with the optimistic view and want independent verification."
                elif role == ConsumerRole.Advocate.value:
                    response = "I think the concerns are overblown; the product has real merit."
                elif role == ConsumerRole.Misreader.value:
                    response = "I see now why others interpreted it differently from me."
                elif role == ConsumerRole.PriceSensitive.value:
                    response = "Price is still my main barrier, regardless of what others say."
                else:
                    response = "I see both sides of the argument and need more time to decide."
                context = discussion_contexts.get(agent_id, {})
                response = self._contextualize_response(response, context)
                turn["responses"].append({"agent_id": agent_id, "role": role, "response": response, "context": context})

        elif turn_number == 3:
            turn["moderator_prompt"] = (
                "Moderator asks: Can anyone provide evidence for their claim? "
                "What about price concerns? Any trust issues or misreadings to clarify?"
            )
            for card in participant_cards:
                agent_id = card["agent_id"]
                role = card.get("role", "")
                if role == ConsumerRole.Skeptic.value:
                    response = "I need clinical proof before I can trust this claim."
                elif role == ConsumerRole.Advocate.value:
                    response = "I trust the brand based on my positive past experience."
                elif role == ConsumerRole.Misreader.value:
                    response = "Simpler wording would prevent the confusion I experienced."
                elif role == ConsumerRole.PriceSensitive.value:
                    response = "A discount or guarantee would ease my price concern."
                else:
                    response = "I would like to see independent third-party verification."
                context = discussion_contexts.get(agent_id, {})
                response = self._contextualize_response(response, context)
                turn["responses"].append({"agent_id": agent_id, "role": role, "response": response, "context": context})

        elif turn_number == 4:
            for card in participant_cards:
                agent_id = card["agent_id"]
                role = card.get("role", "")
                start = card.get("attitude_start", "neutral")
                latest = card.get("attitude_latest", "neutral")
                response = f"My attitude changed from {start} to {latest} during this discussion."
                context = discussion_contexts.get(agent_id, {})
                response = self._contextualize_response(response, context)
                turn["responses"].append({"agent_id": agent_id, "role": role, "response": response, "context": context})

        return turn

    def run_focus_group(self, request: ConsumerInterviewRequest, moderator_goal: str) -> FocusGroupSession:
        self._validate_simulation(request.simulation_id)

        participants = self._select_participants(
            request.simulation_id,
            request.roles,
            min(request.max_agents, 8),
        )

        moderator_prompt = self._build_moderator_prompt(
            request.topic, moderator_goal, participants, request.target_context
        )
        discussion_contexts = self._build_discussion_contexts(
            request.simulation_id,
            participants,
            request.target_context,
        )

        turns = []
        for turn_num in range(1, 5):
            turn = self._run_turn(
                turn_num,
                request.topic,
                participants,
                moderator_prompt,
                request.target_context,
                discussion_contexts,
            )
            turns.append(turn)

        evidence_map = {}
        for card in participants:
            agent_id = card["agent_id"]
            answer = {"answer": f"Participated in focus group on {request.topic}."}
            evidence = self.evidence_binder.bind_answer(
                card=card, answer=answer, target_context=request.target_context
            )
            evidence_map[agent_id] = evidence

        consensus = self.disagreement_detector.detect_consensus(turns)
        disagreements = self.disagreement_detector.detect(turns)

        next_what_if = [
            "What if pricing were 20% lower?",
            "What if clinical evidence were front and center?",
            "What if packaging claims were simplified?",
        ]

        focus_group_id = f"focus-group-{uuid.uuid4().hex[:8]}"
        session = FocusGroupSession(
            focus_group_id=focus_group_id,
            simulation_id=request.simulation_id,
            topic=request.topic,
            moderator_goal=moderator_goal,
            participant_cards=[{"agent_id": c["agent_id"], "role": c.get("role", "")} for c in participants],
            turns=turns,
            consensus=consensus,
            disagreements=disagreements,
            next_what_if_experiments=next_what_if,
            evidence_map=evidence_map,
        )

        record = {
            "focus_group_id": session.focus_group_id,
            "simulation_id": session.simulation_id,
            "topic": session.topic,
            "moderator_goal": session.moderator_goal,
            "participant_cards": session.participant_cards,
            "turns": session.turns,
            "consensus": session.consensus,
            "disagreements": session.disagreements,
            "next_what_if_experiments": session.next_what_if_experiments,
            "evidence_map": session.evidence_map,
        }
        self.history_store.write_focus_group(request.simulation_id, record)
        return session
