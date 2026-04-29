from app.services.consumer.interview.followup_question_engine import FollowupQuestionEngine
from app.services.consumer.society.consumer_roles import ConsumerRole


def test_followup_question_engine_outputs_fixed_types_and_existing_roles():
    result = FollowupQuestionEngine().generate(
        topic="low sugar claim",
        target_context={"claim": "low sugar", "branch_id": "branch-1"},
    )

    assert [item["type"] for item in result["followup_questions"]] == [
        "trust_repair",
        "misread_clarification",
        "price_resistance",
        "evidence_demand",
        "competitor_comparison",
        "purchase_intent",
        "share_intent",
    ]
    valid_roles = {role.value for role in ConsumerRole}
    assert all(item["target_role"] in valid_roles for item in result["followup_questions"])
    assert all("question" in item and item["question"] for item in result["followup_questions"])
