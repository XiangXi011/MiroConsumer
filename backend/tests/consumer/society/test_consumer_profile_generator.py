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


def test_profile_source_is_rule_without_research_findings():
    generator = ConsumerProfileGenerator(seed=1, enable_llm_enrichment=False)
    profiles = generator.generate_profiles(brief=_brief(), count=3)
    for profile in profiles:
        assert profile["profile_source"] == "rule"
        assert "evidence_enrichment" in profile["unsupported_fields"]
        assert profile["supporting_evidence_ids"] == []
        assert profile["research_findings"] == []


def test_profile_source_is_evidence_enriched_with_research_findings():
    generator = ConsumerProfileGenerator(seed=1, enable_llm_enrichment=False)
    findings = [
        {"finding_id": "F1", "source_id": "S1", "evidence_snippets": ["snippet1"], "summary": "summary1"},
        {"finding_id": "F2", "source_id": "S2", "evidence_snippets": ["snippet2"], "summary": "summary2"},
    ]
    profiles = generator.generate_profiles(brief=_brief(), count=3, research_findings=findings)
    for profile in profiles:
        assert profile["profile_source"] == "evidence_enriched"
        assert "evidence_enrichment" not in profile["unsupported_fields"]
        assert set(profile["supporting_evidence_ids"]) == {"F1", "F2"}
        assert len(profile["research_findings"]) == 2
        for finding in profile["research_findings"]:
            assert "finding_id" in finding
            assert "source_id" in finding
            assert "evidence_snippets" in finding
            assert "summary" in finding


def test_rule_first_fields_not_overwritten_by_evidence_enrichment():
    generator = ConsumerProfileGenerator(seed=1, enable_llm_enrichment=False)
    findings = [
        {"finding_id": "F1", "source_id": "S1", "evidence_snippets": ["x"], "summary": "y"},
    ]
    profiles = generator.generate_profiles(brief=_brief(), count=3, research_findings=findings)
    rule_first = generator.builder.build(_brief(), count=3)
    for i, profile in enumerate(profiles):
        for key in (
            "age_range",
            "city_tier",
            "income_level",
            "family_structure",
            "purchase_channel",
            "category_usage_frequency",
            "price_sensitivity",
            "evidence_sensitivity",
            "risk_sensitivities",
        ):
            assert profile[key] == rule_first[i][key]


def test_validator_repairs_missing_profile_evidence_fields():
    generator = ConsumerProfileGenerator(seed=1, enable_llm_enrichment=False)
    profile = generator.validator.validate({"persona_id": "M01"})
    assert profile["profile_source"] == "rule"
    assert profile["supporting_evidence_ids"] == []
    assert profile["unsupported_fields"] == ["evidence_enrichment"]
    assert profile["research_findings"] == []


def test_profile_source_remains_rule_when_llm_enabled_without_client():
    generator = ConsumerProfileGenerator(seed=1, enable_llm_enrichment=True)
    profiles = generator.generate_profiles(brief=_brief(), count=2)
    for profile in profiles:
        assert profile["profile_source"] == "rule"


def test_profile_source_is_llm_enriched_only_after_successful_enrichment():
    class FakeLLMClient:
        def chat_json(self, **kwargs):
            return {
                "bio": "她会结合真实使用反馈、材质证据和家庭预算判断是否购买。",
                "persona": "证据敏感且重视家庭使用场景的消费者",
                "expression_style": "谨慎追问证据",
                "interested_topics": ["材质证据", "家庭使用", "价格比较"],
            }

    from app.services.consumer.society.mirofish_profile_adapter import MiroFishProfileAdapter

    adapter = MiroFishProfileAdapter(seed=1, enable_llm_enrichment=True, llm_client=FakeLLMClient())
    generator = ConsumerProfileGenerator(seed=1, adapter=adapter)
    profiles = generator.generate_profiles(brief=_brief(), count=2)
    for profile in profiles:
        assert profile["profile_source"] == "llm_enriched"
        assert profile["bio"] == "她会结合真实使用反馈、材质证据和家庭预算判断是否购买。"
