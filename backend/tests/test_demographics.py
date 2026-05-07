"""Tests for the enhanced demographics persona system."""

from __future__ import annotations

import sys
from unittest.mock import MagicMock

# Stub out heavy third-party deps that app.services.__init__ pulls in
_zep_mock = MagicMock()
for _mod_name in (
    "zep_cloud",
    "zep_cloud.client",
    "zep_cloud.external_clients",
    "zep_cloud.external_clients.ontology",
):
    if _mod_name not in sys.modules:
        sys.modules[_mod_name] = _zep_mock

import pytest

from app.services.consumer.demographics.persona import ConsumerPersona
from app.services.consumer.demographics.population import (
    PERSONA_TEMPLATES,
    PopulationGenerator,
    ShadowPersona,
)


class TestConsumerPersona:
    """ConsumerPersona.to_prompt_description tests."""

    def test_prompt_contains_age_range(self):
        p = ConsumerPersona(persona_id="t1", name="test", age_range=(20, 30))
        desc = p.to_prompt_description()
        assert "20-30岁" in desc

    def test_prompt_contains_income_level(self):
        p = ConsumerPersona(persona_id="t2", name="test", income_level="high")
        desc = p.to_prompt_description()
        assert "high收入" in desc

    def test_prompt_contains_city_tier(self):
        p = ConsumerPersona(persona_id="t3", name="test", city_tier=1)
        desc = p.to_prompt_description()
        assert "1线城市" in desc

    def test_prompt_contains_education(self):
        p = ConsumerPersona(persona_id="t4", name="test", education="graduate")
        desc = p.to_prompt_description()
        assert "graduate学历" in desc

    def test_prompt_contains_sensitivity_percentages(self):
        p = ConsumerPersona(
            persona_id="t5",
            name="test",
            price_sensitivity=0.75,
            brand_loyalty=0.60,
            claim_skepticism=0.40,
            evidence_sensitivity=0.80,
        )
        desc = p.to_prompt_description()
        assert "75%" in desc
        assert "60%" in desc
        assert "40%" in desc
        assert "80%" in desc

    def test_prompt_contains_expression_style(self):
        p = ConsumerPersona(persona_id="t6", name="test", expression_style="outspoken")
        desc = p.to_prompt_description()
        assert "outspoken" in desc

    def test_prompt_contains_channel_preference(self):
        p = ConsumerPersona(persona_id="t7", name="test", channel_preference="douyin")
        desc = p.to_prompt_description()
        assert "douyin" in desc

    def test_prompt_contains_occupation_and_region(self):
        p = ConsumerPersona(
            persona_id="t8",
            name="test",
            occupation="student",
            region="south",
            family_structure="couple",
        )
        desc = p.to_prompt_description()
        assert "student" in desc
        assert "south" in desc
        assert "couple" in desc


class TestPopulationGenerator:
    """PopulationGenerator tests."""

    def test_generate_from_template_returns_persona(self):
        gen = PopulationGenerator(seed=42)
        persona = gen.generate_from_template("price_sensitive_student")
        assert isinstance(persona, ConsumerPersona)
        assert persona.name == "价格敏感学生"
        assert persona.age_range == (18, 24)
        assert persona.price_sensitivity == pytest.approx(0.9)

    def test_generate_from_template_all_templates(self):
        gen = PopulationGenerator(seed=42)
        for template_name in PERSONA_TEMPLATES:
            persona = gen.generate_from_template(template_name)
            assert isinstance(persona, ConsumerPersona)
            assert persona.persona_id  # non-empty
            assert persona.name  # non-empty

    def test_generate_diverse_population_count(self):
        gen = PopulationGenerator(seed=42)
        pop = gen.generate_diverse_population(8)
        assert len(pop) == 8

    def test_generate_diverse_population_varies(self):
        gen = PopulationGenerator(seed=42)
        pop = gen.generate_diverse_population(8)
        names = [p.name for p in pop]
        # With 4 templates and 8 people, each template should appear twice
        assert len(set(names)) == 4

    def test_random_perturbation_stays_in_bounds(self):
        gen = PopulationGenerator(seed=42)
        pop = gen.generate_diverse_population(100)
        for p in pop:
            assert 0.0 <= p.price_sensitivity <= 1.0, f"price_sensitivity out of bounds: {p.price_sensitivity}"
            assert 0.0 <= p.brand_loyalty <= 1.0, f"brand_loyalty out of bounds: {p.brand_loyalty}"

    def test_perturbation_creates_variation(self):
        gen = PopulationGenerator(seed=42)
        pop = gen.generate_diverse_population(20)
        # After perturbation, not all price_sensitivities should be identical
        sensitivities = [p.price_sensitivity for p in pop]
        assert len(set(sensitivities)) > 1

    def test_seed_determinism(self):
        gen1 = PopulationGenerator(seed=123)
        gen2 = PopulationGenerator(seed=123)
        pop1 = gen1.generate_diverse_population(5)
        pop2 = gen2.generate_diverse_population(5)
        for a, b in zip(pop1, pop2):
            assert a.price_sensitivity == b.price_sensitivity
            assert a.brand_loyalty == b.brand_loyalty


class TestShadowPersona:
    """ShadowPersona tests."""

    def test_should_activate_uses_rng(self):
        import random
        persona = ConsumerPersona(persona_id="s1", name="shadow")
        shadow = ShadowPersona(base_persona=persona, activation_probability=0.5)
        rng = random.Random(42)

        activations = [shadow.should_activate(rng) for _ in range(1000)]
        true_count = sum(activations)
        # With p=0.5 and 1000 trials, expect ~500, allow wide margin
        assert 350 < true_count < 650

    def test_should_activate_low_probability(self):
        import random
        persona = ConsumerPersona(persona_id="s2", name="shadow")
        shadow = ShadowPersona(base_persona=persona, activation_probability=0.1)
        rng = random.Random(42)

        activations = [shadow.should_activate(rng) for _ in range(1000)]
        true_count = sum(activations)
        assert true_count < 200

    def test_generate_shadow_population_count(self):
        gen = PopulationGenerator(seed=42)
        shadows = gen.generate_shadow_population(10)
        assert len(shadows) == 10
        assert all(isinstance(s, ShadowPersona) for s in shadows)

    def test_generate_shadow_population_custom_probability(self):
        gen = PopulationGenerator(seed=42)
        shadows = gen.generate_shadow_population(5, activation_probability=0.8)
        for s in shadows:
            assert s.activation_probability == 0.8


class TestPopulationStats:
    """PopulationGenerator.get_population_stats tests."""

    def test_stats_basic_fields(self):
        gen = PopulationGenerator(seed=42)
        pop = gen.generate_diverse_population(20)
        stats = gen.get_population_stats(pop)

        assert stats["total"] == 20
        assert "avg_price_sensitivity" in stats
        assert "avg_brand_loyalty" in stats
        assert 0.0 <= stats["avg_price_sensitivity"] <= 1.0
        assert 0.0 <= stats["avg_brand_loyalty"] <= 1.0

    def test_stats_city_tier_distribution(self):
        gen = PopulationGenerator(seed=42)
        pop = gen.generate_diverse_population(20)
        stats = gen.get_population_stats(pop)

        tier_dist = stats["city_tier_distribution"]
        assert set(tier_dist.keys()) == {1, 2, 3, 4, 5}
        assert sum(tier_dist.values()) == 20

    def test_stats_income_distribution(self):
        gen = PopulationGenerator(seed=42)
        pop = gen.generate_diverse_population(20)
        stats = gen.get_population_stats(pop)

        income_dist = stats["income_distribution"]
        assert set(income_dist.keys()) == {"low", "middle", "high"}
        assert sum(income_dist.values()) == 20

    def test_stats_template_distribution(self):
        gen = PopulationGenerator(seed=42)
        pop = gen.generate_diverse_population(20)
        stats = gen.get_population_stats(pop)

        template_dist = stats["template_distribution"]
        assert sum(template_dist.values()) == 20
        assert len(template_dist) == 4  # 4 templates

    def test_stats_empty_population(self):
        gen = PopulationGenerator(seed=42)
        stats = gen.get_population_stats([])
        assert stats["total"] == 0

    def test_stats_with_shadow_personas(self):
        gen = PopulationGenerator(seed=42)
        shadows = gen.generate_shadow_population(10)
        stats = gen.get_population_stats(shadows)

        assert stats["total"] == 10
        assert "avg_price_sensitivity" in stats


class TestConsumerPersonaNewFields:
    """Test new fields and defaults on ConsumerPersona."""

    def test_new_field_defaults(self):
        p = ConsumerPersona(persona_id="n1", name="test")
        assert p.gender == "any"
        assert p.region == "east"
        assert p.family_structure == "single"
        assert p.occupation == "white_collar"
        assert p.purchase_channel == "online"
        assert p.category_usage_frequency == "weekly"
        assert p.claim_skepticism == 0.5
        assert p.evidence_sensitivity == 0.5
        assert p.novelty_seeking == 0.5
        assert p.risk_aversion == 0.5
        assert p.sharing_propensity == 0.5
        assert p.expression_style == "moderate"
        assert p.channel_preference == "weixin"
        assert p.category_pain_points == []
        assert p.decision_heuristics == []
        assert p.forbidden_assumptions == []
        assert p.source_basis == "template"
        assert p.quality_score == 0.5

    def test_source_basis_can_be_set(self):
        p = ConsumerPersona(persona_id="n2", name="test", source_basis="manual", quality_score=0.9)
        assert p.source_basis == "manual"
        assert p.quality_score == 0.9


class TestSourceBasisInGenerationModes:
    """Test source_basis is correctly set in each generation mode."""

    def test_template_mode_sets_source_basis(self):
        gen = PopulationGenerator(seed=42)
        persona = gen.generate_from_template("urban_professional")
        assert persona.source_basis == "template"

    def test_brief_mode_sets_source_basis(self):
        gen = PopulationGenerator(seed=42)
        brief = {"target_age": (20, 30), "target_income": "high"}
        personas = gen.generate_from_brief(brief, count=3)
        assert len(personas) == 3
        for p in personas:
            assert p.source_basis == "brief"

    def test_calibrated_mode_sets_source_basis(self):
        gen = PopulationGenerator(seed=42)
        cal_data = {
            "age_ranges": [(18, 25), (25, 35), (35, 50)],
            "income_level_distribution": {"low": 0.3, "middle": 0.5, "high": 0.2},
            "price_sensitivity": (0.6, 0.1),
        }
        personas = gen.generate_calibrated(cal_data, count=5)
        assert len(personas) == 5
        for p in personas:
            assert p.source_basis == "data_calibrated"


class TestPopulationCoverage:
    """Test population_coverage in stats."""

    def test_population_coverage_present(self):
        gen = PopulationGenerator(seed=42)
        pop = gen.generate_diverse_population(20)
        stats = gen.get_population_stats(pop)
        assert "population_coverage" in stats
        cov = stats["population_coverage"]
        assert "age_coverage" in cov
        assert "income_coverage" in cov
        assert "city_tier_coverage" in cov
        assert "source_basis_distribution" in cov

    def test_source_basis_distribution_in_coverage(self):
        gen = PopulationGenerator(seed=42)
        pop = gen.generate_diverse_population(8)
        stats = gen.get_population_stats(pop)
        sbd = stats["population_coverage"]["source_basis_distribution"]
        assert "template" in sbd
        assert sbd["template"] == 8

    def test_mixed_source_basis_coverage(self):
        gen = PopulationGenerator(seed=42)
        templates = gen.generate_diverse_population(4)
        brief = gen.generate_from_brief({"target_income": "low"}, count=2)
        mixed = templates + brief
        stats = gen.get_population_stats(mixed)
        sbd = stats["population_coverage"]["source_basis_distribution"]
        assert sbd["template"] == 4
        assert sbd["brief"] == 2


class TestGenerateFromBrief:
    """Test generate_from_brief method."""

    def test_brief_applies_age_range(self):
        gen = PopulationGenerator(seed=42)
        brief = {"target_age": (25, 35)}
        personas = gen.generate_from_brief(brief, count=2)
        for p in personas:
            assert p.age_range == (25, 35)

    def test_brief_applies_income_level(self):
        gen = PopulationGenerator(seed=42)
        brief = {"target_income": "high"}
        personas = gen.generate_from_brief(brief, count=3)
        for p in personas:
            assert p.income_level == "high"

    def test_brief_applies_city_tier(self):
        gen = PopulationGenerator(seed=42)
        brief = {"target_city_tier": 1}
        personas = gen.generate_from_brief(brief, count=2)
        for p in personas:
            assert p.city_tier == 1

    def test_brief_applies_all_params(self):
        gen = PopulationGenerator(seed=42)
        brief = {
            "target_age": (20, 30),
            "target_gender": "female",
            "target_income": "high",
            "target_education": "graduate",
            "target_city_tier": 1,
            "target_region": "south",
            "target_family_structure": "couple",
            "target_occupation": "freelance",
            "price_sensitivity": 0.8,
            "brand_loyalty": 0.3,
            "claim_skepticism": 0.9,
            "expression_style": "outspoken",
            "category_pain_points": ["too expensive", "poor quality"],
        }
        personas = gen.generate_from_brief(brief, count=1)
        p = personas[0]
        assert p.age_range == (20, 30)
        assert p.gender == "female"
        assert p.income_level == "high"
        assert p.education == "graduate"
        assert p.city_tier == 1
        assert p.region == "south"
        assert p.family_structure == "couple"
        assert p.occupation == "freelance"
        assert p.expression_style == "outspoken"
        assert p.category_pain_points == ["too expensive", "poor quality"]

    def test_brief_defaults_when_empty(self):
        gen = PopulationGenerator(seed=42)
        personas = gen.generate_from_brief({}, count=2)
        p = personas[0]
        assert p.age_range == (18, 65)
        assert p.income_level == "middle"
        assert p.source_basis == "brief"

    def test_brief_adds_diversity_via_perturbation(self):
        gen = PopulationGenerator(seed=42)
        brief = {"price_sensitivity": 0.5, "brand_loyalty": 0.5}
        personas = gen.generate_from_brief(brief, count=10)
        sensitivities = [p.price_sensitivity for p in personas]
        assert len(set(sensitivities)) > 1
