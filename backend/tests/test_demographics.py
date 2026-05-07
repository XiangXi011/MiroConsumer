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
            innovation_adoption=0.40,
        )
        desc = p.to_prompt_description()
        assert "75%" in desc
        assert "60%" in desc
        assert "40%" in desc

    def test_prompt_contains_screen_hours(self):
        p = ConsumerPersona(persona_id="t6", name="test", daily_screen_hours=5.0)
        desc = p.to_prompt_description()
        assert "5.0小时" in desc

    def test_prompt_contains_platforms(self):
        p = ConsumerPersona(
            persona_id="t7",
            name="test",
            social_platforms=["weixin", "douyin"],
        )
        desc = p.to_prompt_description()
        assert "weixin" in desc
        assert "douyin" in desc


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
