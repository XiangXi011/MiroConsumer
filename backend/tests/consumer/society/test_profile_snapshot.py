from app.services.consumer.society.profile_generator import ConsumerProfileGenerator
from app.services.consumer.society.state_store import SocietyStateStore


def test_profile_snapshot_is_persisted_and_reused_for_same_simulation(tmp_path):
    store = SocietyStateStore(base_dir=tmp_path)
    generator = ConsumerProfileGenerator(seed=12, enable_llm_enrichment=False)
    brief = {
        "product_category": "kitchenware",
        "task_type": "concept_test",
        "claims": ["316不锈钢"],
        "research_goal": "验证卖点传播",
    }

    snapshot = generator.build_snapshot(
        brief=brief,
        enabled_channels=["xiaohongshu", "tmall"],
        count=4,
    )
    store.write_profile_snapshot("sim-profile", snapshot)

    loaded = store.read_profile_snapshot("sim-profile")
    assert loaded == snapshot
    assert loaded["profile_version"] == "phase7g_v1"
    assert loaded["generator_mode"] == "rule_first"
    assert loaded["product_category"] == "kitchenware_zh"
    assert len(loaded["profiles"]) == 4


def test_profile_snapshot_generation_is_stable_for_same_seed_and_brief():
    generator = ConsumerProfileGenerator(seed=21, enable_llm_enrichment=False)
    brief = {
        "product_category": "food_beverage",
        "task_type": "price_test",
        "claims": ["低糖"],
    }

    first = generator.build_snapshot(brief=brief, enabled_channels=["douyin"], count=3)
    second = generator.build_snapshot(brief=brief, enabled_channels=["douyin"], count=3)

    assert first == second
