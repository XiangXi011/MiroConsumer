from app.services.consumer.society.profile_generator import ConsumerProfileGenerator


def _brief(**overrides):
    data = {
        "product_category": "kitchenware",
        "task_type": "price_test",
        "target_consumer": "城市家庭",
        "price_context": {"price": 129, "price_band": "mid_premium"},
        "claims": ["316不锈钢", "儿童餐具"],
        "risk_flags": ["材质安全", "价格虚高"],
        "research_goal": "验证高价是否阻碍购买",
    }
    data.update(overrides)
    return data


def test_generator_rule_first_fields_are_stable_without_llm():
    generator = ConsumerProfileGenerator(seed=11, enable_llm_enrichment=False)

    first = generator.generate_profiles(
        brief=_brief(),
        enabled_channels=["xiaohongshu", "tmall", "douyin"],
        count=6,
    )
    second = generator.generate_profiles(
        brief=_brief(),
        enabled_channels=["xiaohongshu", "tmall", "douyin"],
        count=6,
    )

    assert first == second
    assert len(first) == 6
    for profile in first:
        assert profile["name"]
        assert profile["age_range"]
        assert profile["city_tier"]
        assert profile["income_level"]
        assert profile["family_structure"]
        assert profile["purchase_channel"]
        assert 0 <= profile["price_sensitivity"] <= 1
        assert 0 <= profile["evidence_sensitivity"] <= 1
        assert profile["risk_sensitivities"]
        assert profile["source"] in {"mirofish_adapter", "rule_fallback", "hybrid"}
        assert _brief()["research_goal"] not in profile["bio"]
        assert len(profile["bio"]) < 300


def test_generator_adjusts_profiles_by_category_task_price_and_channel():
    generator = ConsumerProfileGenerator(seed=5, enable_llm_enrichment=False)

    kitchenware = generator.generate_profiles(
        brief=_brief(product_category="kitchenware", task_type="price_test"),
        enabled_channels=["tmall", "offline_supermarket"],
        count=4,
    )
    food = generator.generate_profiles(
        brief=_brief(product_category="food_beverage", task_type="concept_test"),
        enabled_channels=["xiaohongshu", "douyin"],
        count=4,
    )

    assert any("材质安全" in p["risk_sensitivities"] for p in kitchenware)
    assert any("口味" in p["risk_sensitivities"] or "配料" in p["risk_sensitivities"] for p in food)
    assert any("天猫" in p["purchase_channel"] or "线下商超" in p["purchase_channel"] for p in kitchenware)
    assert any("小红书" in p["purchase_channel"] or "抖音" in p["purchase_channel"] for p in food)
    assert sum(p["price_sensitivity"] for p in kitchenware) / len(kitchenware) >= 0.45


def test_validator_blocks_english_default_persona_label_and_research_goal():
    generator = ConsumerProfileGenerator(seed=1, enable_llm_enrichment=False)

    profile = generator.validator.validate(
        {
            "persona_id": "M01",
            "name": "Care-driven urban mom",
            "age_range": "28-35",
            "city_tier": "一线",
            "income_level": "中高",
            "family_structure": "有孩子",
            "purchase_channel": ["小红书"],
            "category_usage_frequency": "每周多次",
            "price_sensitivity": 0.3,
            "evidence_sensitivity": 0.8,
            "risk_sensitivities": ["材质安全"],
            "expression_style": "谨慎",
            "bio": "Care-driven urban mom 正在验证高价是否阻碍购买",
            "persona": "",
            "source": "hybrid",
        },
        research_goal="验证高价是否阻碍购买",
    )

    assert "Care-driven urban mom" not in profile["name"]
    assert "Care-driven urban mom" not in profile["bio"]
    assert "验证高价是否阻碍购买" not in profile["bio"]
    assert profile["persona"]
