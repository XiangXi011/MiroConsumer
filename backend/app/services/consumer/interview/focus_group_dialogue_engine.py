"""LLM-aware dialogue engine for virtual consumer focus groups."""

from __future__ import annotations

import os
from typing import Any, Callable, Dict, List, Mapping


class FocusGroupDialogueEngine:
    """Generate moderator instructions and participant responses from discussion context."""

    def __init__(self, llm_client_factory: Callable[[], Any] | None = None):
        self.llm_client_factory = llm_client_factory

    def build_moderator_instruction(
        self,
        *,
        turn_number: int,
        topic: str,
        moderator_prompt: str,
        participant_cards: List[Dict[str, Any]],
        target_context: Dict[str, Any],
        discussion_contexts: Dict[str, Dict[str, Any]],
        prior_turns: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        if self._llm_enabled():
            try:
                payload = self._client().chat_json(
                    messages=[
                        {
                            "role": "system",
                            "content": (
                                "You are a context-aware LLM moderator instruction engine for "
                                "MiroConsumer focus groups. Return JSON only."
                            ),
                        },
                        {
                            "role": "user",
                            "content": self._moderator_prompt(
                                turn_number=turn_number,
                                topic=topic,
                                moderator_prompt=moderator_prompt,
                                participant_cards=participant_cards,
                                target_context=target_context,
                                discussion_contexts=discussion_contexts,
                                prior_turns=prior_turns,
                            ),
                        },
                    ],
                    temperature=0.25,
                    max_tokens=500,
                )
                return {
                    "instruction": str(payload.get("instruction") or "").strip()
                    or self._template_moderator_instruction(turn_number, topic, target_context),
                    "source": "llm_moderator",
                    "reasoning_summary": str(payload.get("reasoning_summary", "")),
                }
            except Exception as exc:
                return {
                    "instruction": self._template_moderator_instruction(turn_number, topic, target_context),
                    "source": "template_moderator_fallback",
                    "reasoning_error": str(exc),
                }

        return {
            "instruction": self._template_moderator_instruction(turn_number, topic, target_context),
            "source": "template_moderator",
        }

    def generate_participant_response(
        self,
        *,
        turn_number: int,
        topic: str,
        card: Dict[str, Any],
        role_template: str,
        moderator_instruction: Dict[str, Any],
        discussion_context: Dict[str, Any],
        prior_turns: List[Dict[str, Any]],
        target_context: Dict[str, Any],
    ) -> Dict[str, Any]:
        if self._llm_enabled():
            try:
                payload = self._client().chat_json(
                    messages=[
                        {
                            "role": "system",
                            "content": (
                                "You are a memory-aware consumer participant response engine. "
                                "Stay inside the persona, use the provided history, and return JSON only."
                            ),
                        },
                        {
                            "role": "user",
                            "content": self._participant_prompt(
                                turn_number=turn_number,
                                topic=topic,
                                card=card,
                                role_template=role_template,
                                moderator_instruction=moderator_instruction,
                                discussion_context=discussion_context,
                                prior_turns=prior_turns,
                                target_context=target_context,
                            ),
                        },
                    ],
                    temperature=0.35,
                    max_tokens=700,
                )
                return {
                    "response": str(payload.get("response") or "").strip()
                    or self._template_participant_response(role_template, discussion_context, moderator_instruction),
                    "source": "llm_participant",
                    "reasoning_summary": str(payload.get("reasoning_summary", "")),
                }
            except Exception as exc:
                response = self._template_participant_response(
                    role_template,
                    discussion_context,
                    moderator_instruction,
                )
                return {
                    "response": response,
                    "source": "template_participant_fallback",
                    "reasoning_error": str(exc),
                }

        return {
            "response": self._template_participant_response(
                role_template,
                discussion_context,
                moderator_instruction,
            ),
            "source": "template_participant",
        }

    def _llm_enabled(self) -> bool:
        deterministic = os.environ.get("FOCUS_GROUP_DETERMINISTIC_MODE", "").strip().lower() == "mock"
        backend = os.environ.get("FOCUS_GROUP_DIALOGUE_BACKEND", "template").strip().lower()
        return backend == "llm" and not deterministic

    def _client(self) -> Any:
        if self.llm_client_factory is not None:
            return self.llm_client_factory()
        from ....utils.llm_client import LLMClient

        return LLMClient()

    def _template_moderator_instruction(
        self,
        turn_number: int,
        topic: str,
        target_context: Mapping[str, Any],
    ) -> str:
        finding = str(target_context.get("finding_id", "") or "the target finding")
        if turn_number == 1:
            return f"Ask each participant for their first grounded reaction to {topic} and {finding}."
        if turn_number == 2:
            return f"Ask participants to respond to disagreement around {topic} and {finding}."
        if turn_number == 3:
            return f"Ask for proof, trust repair conditions, and purchase blockers for {finding}."
        return f"Ask each participant to state attitude and purchase-intent movement after the debate."

    def _template_participant_response(
        self,
        role_template: str,
        discussion_context: Mapping[str, Any],
        moderator_instruction: Mapping[str, Any],
    ) -> str:
        details = [role_template]
        channel_id = discussion_context.get("channel_id", "")
        if channel_id:
            details.append(f"Channel context: {channel_id}.")
        event_stream = discussion_context.get("event_stream", [])
        if event_stream:
            quote = event_stream[0].get("quote", "")
            if quote:
                details.append(f"Observed event: {quote}")
        prior_answers = discussion_context.get("prior_answers", [])
        if prior_answers:
            prior = prior_answers[-1].get("answer", "")
            if prior:
                details.append(f"Prior answer: {prior}")
        target_finding = discussion_context.get("target_finding", "")
        if target_finding:
            details.append(f"Target finding: {target_finding}.")
        instruction = moderator_instruction.get("instruction", "")
        if instruction:
            details.append(f"Moderator asks: {instruction}")
        return " ".join(details)

    def _moderator_prompt(
        self,
        *,
        turn_number: int,
        topic: str,
        moderator_prompt: str,
        participant_cards: List[Dict[str, Any]],
        target_context: Dict[str, Any],
        discussion_contexts: Dict[str, Dict[str, Any]],
        prior_turns: List[Dict[str, Any]],
    ) -> str:
        return (
            "Task: build a moderator instruction for a multi-agent consumer debate.\n"
            f"turn_number: {turn_number}\n"
            f"topic: {topic}\n"
            f"moderator_prompt: {moderator_prompt}\n"
            f"participant_cards: {participant_cards}\n"
            f"target_context: {target_context}\n"
            f"discussion_contexts: {discussion_contexts}\n"
            f"prior_turns: {prior_turns}\n"
            "Return JSON with keys: instruction, reasoning_summary."
        )

    def _participant_prompt(
        self,
        *,
        turn_number: int,
        topic: str,
        card: Dict[str, Any],
        role_template: str,
        moderator_instruction: Dict[str, Any],
        discussion_context: Dict[str, Any],
        prior_turns: List[Dict[str, Any]],
        target_context: Dict[str, Any],
    ) -> str:
        return (
            "Task: generate one participant response in a consumer focus group.\n"
            f"turn_number: {turn_number}\n"
            f"topic: {topic}\n"
            f"card: {card}\n"
            f"role_template: {role_template}\n"
            f"moderator_instruction: {moderator_instruction}\n"
            f"discussion_context: {discussion_context}\n"
            f"prior_turns: {prior_turns}\n"
            f"target_context: {target_context}\n"
            "Return JSON with keys: response, reasoning_summary."
        )


__all__ = ["FocusGroupDialogueEngine"]
