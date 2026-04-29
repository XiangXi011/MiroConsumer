from app.services.consumer.interview.representative_card_builder import RepresentativeCardBuilder
from app.services.consumer.society.consumer_roles import ConsumerRole
from test_representative_sampler import _write_society_fixture


def test_representative_card_builder_returns_complete_card_fields(tmp_path):
    _write_society_fixture(tmp_path, simulation_id="sim-cards")

    cards = RepresentativeCardBuilder(base_dir=tmp_path).build_cards(
        "sim-cards",
        roles=[ConsumerRole.Skeptic.value, ConsumerRole.Advocate.value],
        limit=8,
    )

    assert len(cards) == 2
    first = cards[0]
    assert set(first) == {
        "agent_id",
        "display_name",
        "role",
        "segment",
        "channel_id",
        "attitude_start",
        "attitude_latest",
        "purchase_intent_start",
        "purchase_intent_latest",
        "key_quote",
        "influence_score",
        "evidence_ids",
        "event_ids",
    }
    assert first["role"] in {role.value for role in ConsumerRole}
    assert first["display_name"].startswith("Consumer ")
    assert 0.0 <= first["purchase_intent_latest"] <= 1.0
    assert 0.0 <= first["influence_score"] <= 1.0
