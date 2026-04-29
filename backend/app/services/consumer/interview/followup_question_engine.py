"""Generate deterministic follow-up questions for consumer interviews."""

from typing import Any, Dict, List

from ..society.consumer_roles import ConsumerRole


class FollowupQuestionEngine:
    """Produce fixed-type follow-up questions mapped to existing ConsumerRole values."""

    _QUESTION_TYPES = [
        ("trust_repair", "What specific evidence or action would restore your trust in this claim?"),
        ("misread_clarification", "What wording would make the claim clearer and prevent misinterpretation?"),
        ("price_resistance", "At what price point would this offering feel fair versus overpriced?"),
        ("evidence_demand", "What type of proof, clinical, testimonial, or third-party, would convince you?"),
        ("competitor_comparison", "How does this compare to alternatives you currently trust or use?"),
        ("purchase_intent", "What remaining concerns would prevent you from purchasing today?"),
        ("share_intent", "What would make you comfortable recommending this to someone you know?"),
    ]

    def generate(self, topic: str, target_context: Dict[str, Any]) -> Dict[str, Any]:
        role_values = [r.value for r in ConsumerRole]
        questions = []
        for idx, (qtype, template) in enumerate(self._QUESTION_TYPES):
            role = role_values[idx % len(role_values)]
            questions.append({
                "type": qtype,
                "question": f"{template} (regarding: {topic})",
                "target_role": role,
            })

        return {"followup_questions": questions}
