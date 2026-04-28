from app.services.consumer.persona_pack import load_default_persona_pack
from app.services.consumer.society.persona_variation_generator import PersonaVariationGenerator
from app.services.consumer.society.consumer_roles import ConsumerRole


def test_persona_variation_generator_keeps_segment_and_inherited_traits():
    persona = load_default_persona_pack()[0]
    variation = PersonaVariationGenerator(seed=11).generate(persona, index=3, layer="expanded")

    assert variation["segment"] == persona["label"]
    assert variation["traits"]["attention_drivers"] == persona["attention_drivers"]
    assert variation["traits"]["risk_sensitivities"] == persona["risk_sensitivities"]
    assert isinstance(variation["role"], ConsumerRole)


def test_persona_variation_generator_numeric_features_stay_in_range():
    persona = load_default_persona_pack()[0]
    variation = PersonaVariationGenerator(seed=12).generate(persona, index=7, layer="shadow")

    for key in [
        "evidence_sensitivity",
        "price_sensitivity",
        "trust_baseline",
        "share_propensity",
        "skepticism",
        "category_familiarity",
        "social_influence_weight",
    ]:
        assert 0.0 <= variation[key] <= 1.0

    assert 0.0 <= variation["traits"]["risk_memory"] <= 1.0
