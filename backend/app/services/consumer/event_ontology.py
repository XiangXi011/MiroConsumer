"""Consumer event ontology for Phase 6F semantic activation."""

from __future__ import annotations

from enum import Enum
from typing import Dict


class ConsumerEventType(str, Enum):
    """Exact consumer event ontology values."""

    VIEW_CLAIM = "VIEW_CLAIM"
    FIRST_IMPRESSION = "FIRST_IMPRESSION"
    ASK_PROOF = "ASK_PROOF"
    AMPLIFY_CLAIM = "AMPLIFY_CLAIM"
    MISREAD_CLAIM = "MISREAD_CLAIM"
    COMPARE_COMPETITOR = "COMPARE_COMPETITOR"
    PRICE_RESISTANCE = "PRICE_RESISTANCE"
    TRUST_DECAY = "TRUST_DECAY"
    TRUST_RECOVERY = "TRUST_RECOVERY"
    SHARE_TO_CHANNEL = "SHARE_TO_CHANNEL"
    BLOCK_PROPAGATION = "BLOCK_PROPAGATION"
    PURCHASE_INTENT_UP = "PURCHASE_INTENT_UP"
    PURCHASE_INTENT_DOWN = "PURCHASE_INTENT_DOWN"
    NEGATIVE_CASCADE = "NEGATIVE_CASCADE"
    PARTICIPATION_SKIPPED = "PARTICIPATION_SKIPPED"
    IGNORE = "IGNORE"


# Fixed legacy bucket/event to consumer event ontology mapping.
LEGACY_BUCKET_TO_CONSUMER_EVENT: Dict[str, ConsumerEventType] = {
    "positive_relay": ConsumerEventType.AMPLIFY_CLAIM,
    "skeptical_challenge": ConsumerEventType.ASK_PROOF,
    "misread_amplification": ConsumerEventType.MISREAD_CLAIM,
    "risk_discovery": ConsumerEventType.TRUST_DECAY,
    "clarification_recovery": ConsumerEventType.TRUST_RECOVERY,
}

# Legacy event_type to consumer_event_type mapping (same as bucket mapping
# because the legacy event_type values match the bucket names).
LEGACY_EVENT_TYPE_TO_CONSUMER_EVENT: Dict[str, ConsumerEventType] = {
    "positive_relay": ConsumerEventType.AMPLIFY_CLAIM,
    "skeptical_challenge": ConsumerEventType.ASK_PROOF,
    "misread_amplification": ConsumerEventType.MISREAD_CLAIM,
    "risk_discovery": ConsumerEventType.TRUST_DECAY,
    "clarification_recovery": ConsumerEventType.TRUST_RECOVERY,
}


def map_legacy_event_type_to_consumer(event_type: str) -> str:
    """Map a legacy event_type string to its consumer_event_type value.

    Returns the mapped ConsumerEventType value, or the original string
    if no mapping exists.
    """
    mapped = LEGACY_EVENT_TYPE_TO_CONSUMER_EVENT.get(event_type)
    if mapped is not None:
        return mapped.value
    return str(event_type)


def map_legacy_bucket_to_consumer_event(bucket: str) -> str:
    """Map a legacy bucket string to its consumer_event_type value.

    Returns the mapped ConsumerEventType value, or the original string
    if no mapping exists.
    """
    mapped = LEGACY_BUCKET_TO_CONSUMER_EVENT.get(bucket)
    if mapped is not None:
        return mapped.value
    return str(bucket)


__all__ = [
    "ConsumerEventType",
    "LEGACY_BUCKET_TO_CONSUMER_EVENT",
    "LEGACY_EVENT_TYPE_TO_CONSUMER_EVENT",
    "map_legacy_event_type_to_consumer",
    "map_legacy_bucket_to_consumer_event",
]
