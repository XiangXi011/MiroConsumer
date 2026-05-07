from app.services.consumer.society.profile_generator import ConsumerProfileGenerator


def test_consumer_profile_generator_uses_mirofish_adapter_hybrid_mode():
    generator = ConsumerProfileGenerator(seed=9, enable_llm_enrichment=False)

    profiles = generator.generate_profiles(
        brief={
            "product_category": "mother_baby",
            "task_type": "concept_test",
            "target_consumer": "新手妈妈",
            "claims": ["温和安全", "宝宝适用"],
            "risk_flags": ["过敏", "功效夸大"],
            "research_goal": "判断母婴人群是否信任温和安全卖点",
        },
        enabled_channels=["xiaohongshu", "wechat_group"],
        count=3,
        graph_id=None,
    )

    for profile in profiles:
        assert profile["bio"]
        assert profile["persona"]
        assert profile["age_range"]
        assert profile["purchase_channel"]
        assert profile["risk_sensitivities"]
        assert profile["source"] in ["mirofish_adapter", "rule_fallback", "hybrid"]
        assert "Care-driven urban mom" not in profile["bio"]
        assert profile["profile_source"] in ["rule", "evidence_enriched", "llm_enriched"]
        assert "supporting_evidence_ids" in profile
        assert "unsupported_fields" in profile
        assert "research_findings" in profile
