"""Virtual focus group service with fixed 4-turn structure."""

import uuid
from typing import Any, Dict, List

from ..society.consumer_roles import ConsumerRole
from .evidence_binder import InterviewEvidenceBinder
from .followup_question_engine import FollowupQuestionEngine
from .history_store import HistoryStore
from .interview_models import ConsumerInterviewRequest, FocusGroupSession
from .disagreement_detector import DisagreementDetector
from .focus_group_dialogue_engine import FocusGroupDialogueEngine
from .moderator_prompt_engine import ModeratorPromptEngine
from .representative_card_builder import RepresentativeCardBuilder


class FocusGroupService:
    """Run multi-agent focus groups with consensus/disagreement detection and history persistence."""

    def __init__(self, base_dir=None, simulation_repo=None, dialogue_engine=None):
        self.base_dir = base_dir
        self.simulation_repo = simulation_repo
        self.card_builder = RepresentativeCardBuilder(base_dir=base_dir)
        self.evidence_binder = InterviewEvidenceBinder()
        self.followup_engine = FollowupQuestionEngine()
        self.history_store = HistoryStore(base_dir=base_dir)
        self.moderator_prompt_engine = ModeratorPromptEngine()
        self.disagreement_detector = DisagreementDetector()
        self.dialogue_engine = dialogue_engine or FocusGroupDialogueEngine()

    def _build_next_what_if_experiments(
        self,
        topic: str,
        target_context: Dict[str, Any],
        disagreements: List[str],
    ) -> List[str]:
        """Build dynamic what-if experiments from target context and disagreements."""
        task_type = str(target_context.get("task_type", "concept_test") or "concept_test")
        finding_id = str(target_context.get("finding_id", "") or "")
        claim = str(target_context.get("claim", "") or "")
        risk_points = list(target_context.get("risk_points") or [])
        evidence_map = dict(target_context.get("evidence_map", {}) or {})

        experiments: List[str] = []

        # Experiment 1: finding-specific probe
        parts: List[str] = []
        if finding_id:
            parts.append(f"finding {finding_id}")
        if claim:
            parts.append(f"claim '{claim}'")
        if topic:
            parts.append(f"topic '{topic}'")
        if parts:
            experiments.append(f"What if we test a revised version addressing {', '.join(parts)}?")

        # Experiment 2: risk-point probe
        if risk_points:
            experiments.append(f"What if we resolve the risk: {risk_points[0]}?")
        elif claim:
            experiments.append(f"What if we resolve the main concern around '{claim}'?")
        else:
            experiments.append(f"What if we address the top concern for '{topic}'?")

        # Experiment 3: evidence-map support probe
        support_parts: List[str] = []
        for fid, info in evidence_map.items():
            level = str(info.get("support_level", "") or "") if isinstance(info, dict) else ""
            if level:
                support_parts.append(f"{fid} ({level})")
        if support_parts:
            experiments.append(f"What if we strengthen evidence for {', '.join(support_parts)}?")
        elif disagreements:
            experiments.append(f"What if we reconcile the disagreement: {disagreements[0]}?")
        else:
            experiments.append(f"What if we validate assumptions for '{task_type}'?")

        # Experiment 4: task-type specific probe
        experiments.append(f"What if we redesign the '{task_type}' experiment based on focus group feedback?")

        # Ensure we never emit the three banned exact strings
        banned = {
            "What if pricing were 20% lower?",
            "What if clinical evidence were front and center?",
            "What if packaging claims were simplified?",
        }
        for i, exp in enumerate(experiments):
            if exp in banned:
                experiments[i] = f"What if we re-evaluate the approach for '{topic}'?"

        return experiments

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

    def _role_template(self, turn_number: int, topic: str, card: Dict[str, Any]) -> str:
        role = card.get("role", "")
        if turn_number == 1:
            if role == ConsumerRole.Skeptic.value:
                return f"As a skeptic, I have doubts about {topic} and want more proof."
            if role == ConsumerRole.Advocate.value:
                return f"As an advocate, I support {topic} and see clear value."
            if role == ConsumerRole.Misreader.value:
                return f"I find {topic} confusing and need clearer messaging."
            if role == ConsumerRole.PriceSensitive.value:
                return f"My concern about {topic} is whether the price feels justified."
            if role == ConsumerRole.Amplifier.value:
                return f"If {topic} resonates, I would share it widely with my network."
            if role == ConsumerRole.TrustRepairable.value:
                return f"Regarding {topic}, I need reassurance before I can trust again."
            if role == ConsumerRole.Blocker.value:
                return f"I remain opposed to {topic} based on current information."
            return f"I have a neutral opinion on {topic}."

        if turn_number == 2:
            if role == ConsumerRole.Skeptic.value:
                return "I disagree with the optimistic view and want independent verification."
            if role == ConsumerRole.Advocate.value:
                return "I think the concerns are overblown; the product has real merit."
            if role == ConsumerRole.Misreader.value:
                return "I see now why others interpreted it differently from me."
            if role == ConsumerRole.PriceSensitive.value:
                return "Price is still my main barrier, regardless of what others say."
            return "I see both sides of the argument and need more time to decide."

        if turn_number == 3:
            if role == ConsumerRole.Skeptic.value:
                return "I need clinical proof before I can trust this claim."
            if role == ConsumerRole.Advocate.value:
                return "I trust the brand based on my positive past experience."
            if role == ConsumerRole.Misreader.value:
                return "Simpler wording would prevent the confusion I experienced."
            if role == ConsumerRole.PriceSensitive.value:
                return "A discount or guarantee would ease my price concern."
            return "I would like to see independent third-party verification."

        start = card.get("attitude_start", "neutral")
        latest = card.get("attitude_latest", "neutral")
        return f"My attitude changed from {start} to {latest} during this discussion."

    def _run_turn(
        self,
        turn_number: int,
        topic: str,
        participant_cards: List[Dict[str, Any]],
        moderator_prompt: str,
        target_context: Dict[str, Any],
        discussion_contexts: Dict[str, Dict[str, Any]],
        prior_turns: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        moderator_instruction = self.dialogue_engine.build_moderator_instruction(
            turn_number=turn_number,
            topic=topic,
            moderator_prompt=moderator_prompt,
            participant_cards=participant_cards,
            target_context=target_context,
            discussion_contexts=discussion_contexts,
            prior_turns=prior_turns,
        )
        turn = {
            "turn": turn_number,
            "moderator_instruction": moderator_instruction,
            "responses": [],
        }
        if turn_number == 3:
            turn["moderator_prompt"] = moderator_instruction.get("instruction", "")

        for card in participant_cards:
            agent_id = card["agent_id"]
            role = card.get("role", "")
            context = discussion_contexts.get(agent_id, {})
            role_template = self._role_template(turn_number, topic, card)
            generated = self.dialogue_engine.generate_participant_response(
                turn_number=turn_number,
                topic=topic,
                card=card,
                role_template=role_template,
                moderator_instruction=moderator_instruction,
                discussion_context=context,
                prior_turns=prior_turns,
                target_context=target_context,
            )
            turn["responses"].append(
                {
                    "agent_id": agent_id,
                    "role": role,
                    "response": generated.get("response", ""),
                    "source": generated.get("source", "unknown"),
                    "reasoning_summary": generated.get("reasoning_summary", ""),
                    "role_template": role_template,
                    "context": context,
                }
            )

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
                turns,
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

        next_what_if = self._build_next_what_if_experiments(
            request.topic, request.target_context, disagreements
        )

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
