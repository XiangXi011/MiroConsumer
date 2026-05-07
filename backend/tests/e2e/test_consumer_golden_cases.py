import json

import pytest

from app.services.consumer.society.profile_generator import ENGLISH_DEFAULT_LABELS
from app.services.consumer.society.population_models import ConsumerSocietyRunConfig
from app.services.consumer.society.society_runtime import ConsumerSocietyRuntime


GOLDEN_CASES = [
    {
        "case_id": "oral_care_concept",
        "product_category": "oral_care",
        "task_type": "concept_test",
        "claims": ["anti-sensitivity repair"],
        "research_goal": "Check oral care concept credibility",
    },
    {
        "case_id": "premium_toothpaste_price",
        "product_category": "oral_care",
        "task_type": "price_test",
        "claims": ["clinical whitening toothpaste"],
        "price_context": {"price_band": "premium"},
        "research_goal": "Check high-price toothpaste resistance",
    },
    {
        "case_id": "xiaohongshu_copy_ab",
        "product_category": "beauty_personal_care",
        "task_type": "ab_test",
        "claims": ["overnight glow"],
        "research_goal": "Compare two Xiaohongshu copy variants",
    },
    {
        "case_id": "mother_baby_safety_claim",
        "product_category": "mother_baby",
        "task_type": "concept_test",
        "claims": ["baby-safe material"],
        "research_goal": "Check mother-baby safety proof demand",
    },
    {
        "case_id": "low_sugar_misread",
        "product_category": "food_beverage",
        "task_type": "copy_feedback",
        "claims": ["low sugar formula"],
        "research_goal": "Check whether low sugar claim is misread",
    },
]


def _config() -> ConsumerSocietyRunConfig:
    return ConsumerSocietyRunConfig(
        mode="quick",
        core_persona_count=8,
        expanded_persona_count=0,
        shadow_agent_count=0,
        max_rounds=1,
        random_seed=17,
        llm_budget_limit=0,
        audit_sample_size=0,
        enabled_channels=["xiaohongshu", "wechat_group", "ecommerce_review"],
        channel_seed=17,
    )


@pytest.mark.parametrize("case", GOLDEN_CASES, ids=[case["case_id"] for case in GOLDEN_CASES])
def test_consumer_golden_case_runtime_structure(tmp_path, case):
    runtime = ConsumerSocietyRuntime(base_dir=tmp_path)
    result = runtime.run(
        simulation_id=case["case_id"],
        run_id=f"{case['case_id']}:golden",
        config=_config(),
        persona_pack=[],
        brief_context=case,
        research_findings=[],
    )

    society_dir = tmp_path / case["case_id"] / "society"
    profile_snapshot = json.loads((society_dir / "profile_snapshot.json").read_text(encoding="utf-8"))
    progress = json.loads((society_dir / "progress.json").read_text(encoding="utf-8"))
    round_snapshot = json.loads((society_dir / "rounds" / "round_0.json").read_text(encoding="utf-8"))
    channel_events = [
        json.loads(line)
        for line in (society_dir / "channel_events.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]

    assert profile_snapshot["product_category"] == f"{case['product_category']}_zh"
    assert profile_snapshot["profiles"]
    for profile in profile_snapshot["profiles"]:
        assert profile["name"]
        assert profile["risk_sensitivities"]
        assert not any(label in profile["name"] or label in profile["bio"] for label in ENGLISH_DEFAULT_LABELS)

    events = round_snapshot["events"]
    event_types = {event["consumer_event_type"] for event in events}
    assert "FIRST_IMPRESSION" in event_types
    assert event_types & {"ASK_PROOF", "MISREAD_CLAIM", "PRICE_RESISTANCE", "BLOCK_PROPAGATION"}
    assert all(event.get("quote") for event in events)
    assert channel_events
    assert result["society_event_summary"]

    assert progress["status"] == "completed"
    assert progress["completed_agents"] == 8
    assert progress["total_agents"] == 8
    assert progress["current_agent_id"]
