"""Tests for consumer event ontology (Phase 6F)."""

from app.services.consumer.event_ontology import (
    ConsumerEventType,
    LEGACY_BUCKET_TO_CONSUMER_EVENT,
    LEGACY_EVENT_TYPE_TO_CONSUMER_EVENT,
    map_legacy_bucket_to_consumer_event,
    map_legacy_event_type_to_consumer,
)


class TestConsumerEventType:
    def test_all_ontology_values_present(self):
        expected = {
            "VIEW_CLAIM",
            "FIRST_IMPRESSION",
            "ASK_PROOF",
            "AMPLIFY_CLAIM",
            "MISREAD_CLAIM",
            "COMPARE_COMPETITOR",
            "PRICE_RESISTANCE",
            "TRUST_DECAY",
            "TRUST_RECOVERY",
            "SHARE_TO_CHANNEL",
            "BLOCK_PROPAGATION",
            "PURCHASE_INTENT_UP",
            "PURCHASE_INTENT_DOWN",
            "NEGATIVE_CASCADE",
        }
        actual = {member.value for member in ConsumerEventType}
        assert actual == expected

    def test_legacy_bucket_mapping(self):
        assert LEGACY_BUCKET_TO_CONSUMER_EVENT["positive_relay"] == ConsumerEventType.AMPLIFY_CLAIM
        assert LEGACY_BUCKET_TO_CONSUMER_EVENT["skeptical_challenge"] == ConsumerEventType.ASK_PROOF
        assert LEGACY_BUCKET_TO_CONSUMER_EVENT["misread_amplification"] == ConsumerEventType.MISREAD_CLAIM
        assert LEGACY_BUCKET_TO_CONSUMER_EVENT["risk_discovery"] == ConsumerEventType.TRUST_DECAY
        assert LEGACY_BUCKET_TO_CONSUMER_EVENT["clarification_recovery"] == ConsumerEventType.TRUST_RECOVERY

    def test_legacy_event_type_mapping(self):
        assert LEGACY_EVENT_TYPE_TO_CONSUMER_EVENT["positive_relay"] == ConsumerEventType.AMPLIFY_CLAIM
        assert LEGACY_EVENT_TYPE_TO_CONSUMER_EVENT["skeptical_challenge"] == ConsumerEventType.ASK_PROOF
        assert LEGACY_EVENT_TYPE_TO_CONSUMER_EVENT["misread_amplification"] == ConsumerEventType.MISREAD_CLAIM
        assert LEGACY_EVENT_TYPE_TO_CONSUMER_EVENT["risk_discovery"] == ConsumerEventType.TRUST_DECAY
        assert LEGACY_EVENT_TYPE_TO_CONSUMER_EVENT["clarification_recovery"] == ConsumerEventType.TRUST_RECOVERY

    def test_map_legacy_event_type_to_consumer_known(self):
        assert map_legacy_event_type_to_consumer("positive_relay") == "AMPLIFY_CLAIM"
        assert map_legacy_event_type_to_consumer("risk_discovery") == "TRUST_DECAY"

    def test_map_legacy_event_type_to_consumer_unknown(self):
        assert map_legacy_event_type_to_consumer("unknown_event") == "unknown_event"

    def test_map_legacy_bucket_to_consumer_event_known(self):
        assert map_legacy_bucket_to_consumer_event("skeptical_challenge") == "ASK_PROOF"
        assert map_legacy_bucket_to_consumer_event("clarification_recovery") == "TRUST_RECOVERY"

    def test_map_legacy_bucket_to_consumer_event_unknown(self):
        assert map_legacy_bucket_to_consumer_event("random_bucket") == "random_bucket"
