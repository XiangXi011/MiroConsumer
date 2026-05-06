from pathlib import Path

from app.services.consumer.society.mirofish_profile_adapter import MiroFishProfileAdapter


def _brief():
    return {
        "product_category": "kitchenware",
        "task_type": "concept_test",
        "target_consumer": "有孩子的城市家庭",
        "price_context": {"price": 129, "price_band": "mid_premium"},
        "claims": ["316不锈钢", "儿童餐具", "易清洗"],
        "risk_flags": ["材质安全", "营销夸大"],
        "research_goal": "测试316不锈钢卖点是否有传播力",
    }


def test_adapter_returns_consumer_and_oasis_rich_fields_without_graph_id(tmp_path):
    adapter = MiroFishProfileAdapter(seed=7)

    profiles = adapter.generate_profiles(
        brief=_brief(),
        blueprints=[
            {
                "persona_id": "M01",
                "name": "一线城市精致妈妈",
                "age_range": "28-35",
                "city_tier": "一线/新一线",
                "income_level": "中高",
                "family_structure": "有1个3-8岁孩子",
                "purchase_channel": ["小红书", "天猫"],
                "category_usage_frequency": "每周多次",
                "price_sensitivity": 0.42,
                "evidence_sensitivity": 0.81,
                "risk_sensitivities": ["材质安全", "营销夸大"],
                "expression_style": "谨慎但愿意尝新",
            }
        ],
        enabled_channels=["xiaohongshu", "tmall"],
        research_findings=[{"summary": "材质证明会提升信任"}],
        graph_id=None,
    )

    profile = profiles[0]
    for key in [
        "bio",
        "persona",
        "age",
        "gender",
        "mbti",
        "country",
        "profession",
        "interested_topics",
        "persona_id",
        "name",
        "age_range",
        "city_tier",
        "income_level",
        "family_structure",
        "purchase_channel",
        "category_usage_frequency",
        "price_sensitivity",
        "evidence_sensitivity",
        "risk_sensitivities",
        "expression_style",
        "source",
    ]:
        assert key in profile

    assert profile["zep_context_status"] == "unavailable"
    assert profile["source"] in {"mirofish_adapter", "rule_fallback", "hybrid"}
    assert "Care-driven urban mom" not in profile["bio"]
    assert _brief()["research_goal"] not in profile["bio"]


def test_adapter_exports_oasis_compatible_profiles(tmp_path):
    adapter = MiroFishProfileAdapter(seed=3)
    profiles = adapter.generate_profiles(
        brief=_brief(),
        blueprints=[
            {
                "persona_id": "M02",
                "name": "价格比较型宝妈",
                "age_range": "30-39",
                "city_tier": "二线",
                "income_level": "中等",
                "family_structure": "两代同住",
                "purchase_channel": ["天猫", "线下商超"],
                "category_usage_frequency": "每周多次",
                "price_sensitivity": 0.78,
                "evidence_sensitivity": 0.67,
                "risk_sensitivities": ["价格虚高", "材质安全"],
                "expression_style": "直接比较",
            }
        ],
    )

    export_dir = tmp_path / "oasis_profiles"
    result = adapter.export_oasis_profiles(profiles, export_dir)

    assert Path(result["reddit_profiles_path"]).exists()
    assert Path(result["twitter_profiles_path"]).exists()
    reddit_payload = Path(result["reddit_profiles_path"]).read_text(encoding="utf-8")
    twitter_payload = Path(result["twitter_profiles_path"]).read_text(encoding="utf-8")
    assert "user_id" in reddit_payload
    assert "interested_topics" in reddit_payload
    assert "user_id,user_name" in twitter_payload
