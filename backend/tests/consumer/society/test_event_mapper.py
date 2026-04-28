from app.services.consumer.event_ontology import ConsumerEventType
from app.services.consumer.society.consumer_roles import ConsumerRole
from app.services.consumer.society.event_mapper import ConsumerSocietyEventMapper
from app.services.consumer.society.population_models import ConsumerSocietyAgent


def _agent(**overrides):
    defaults = dict(
        agent_id="agent-1",
        parent_persona_id="p1",
        layer="shadow",
        segment="成分党",
        role=ConsumerRole.Skeptic,
        traits={"risk_memory": 0.8},
        channel_affinity={},
        evidence_sensitivity=0.9,
        price_sensitivity=0.8,
        trust_baseline=0.2,
        share_propensity=0.3,
        skepticism=0.9,
        state={"trust": 0.2, "purchase_intent": 0.4},
    )
    defaults.update(overrides)
    return ConsumerSocietyAgent(**defaults)


def test_event_mapper_imports_phase6f_ontology_values():
    event = ConsumerSocietyEventMapper().map_agent_event(
        agent=_agent(role=ConsumerRole.Skeptic),
        round_index=1,
        visible_claims=["0糖"],
        previous_events=[],
        brief_context={"price_points": ["29.9"]},
        research_findings=[],
    )

    assert event["consumer_event_type"] == ConsumerEventType.ASK_PROOF.value
    assert event["agent_id"] == "agent-1"
    assert event["round_index"] == 1


def test_event_mapper_covers_price_sensitive_and_misreader_roles():
    mapper = ConsumerSocietyEventMapper()

    price_event = mapper.map_agent_event(
        agent=_agent(role=ConsumerRole.PriceSensitive),
        round_index=2,
        visible_claims=[],
        previous_events=[],
        brief_context={"price_points": ["39.9"]},
        research_findings=[],
    )
    misread_event = mapper.map_agent_event(
        agent=_agent(role=ConsumerRole.Misreader),
        round_index=2,
        visible_claims=["高蛋白"],
        previous_events=[],
        brief_context={},
        research_findings=[],
    )

    assert price_event["consumer_event_type"] == ConsumerEventType.PRICE_RESISTANCE.value
    assert misread_event["consumer_event_type"] == ConsumerEventType.MISREAD_CLAIM.value
