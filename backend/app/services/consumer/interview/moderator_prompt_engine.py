"""Build moderator prompts for virtual focus groups."""

from typing import Any, Dict, List


class ModeratorPromptEngine:
    """Construct moderator prompts with research goal, claim context, participant roles and evidence rules."""

    def build(
        self,
        topic: str,
        moderator_goal: str,
        participant_roles: List[str],
        target_context: Dict[str, Any],
    ) -> Dict[str, Any]:
        claim = target_context.get("claim", topic)
        return {
            "research_goal": moderator_goal,
            "claim": claim,
            "branch_context": target_context.get("branch_id", ""),
            "channel_context": target_context.get("channel_id", ""),
            "evidence_context": target_context.get("source_ids", []),
            "participant_roles": participant_roles,
            "source_rule": "Do not fabricate sources; mark simulation-only statements as simulation evidence.",
            "main_question": f"What is your opinion on {topic}?",
            "followup_questions": [
                "Can you elaborate on your reasoning?",
                "What evidence would change your mind?",
            ],
            "conflict_points": ["Trust vs. enthusiasm", "Price vs. value"],
            "evidence_checkpoints": ["Source credibility", "Clinical data"],
            "what_if_directions": ["Lower price point", "Stronger claims"],
        }
