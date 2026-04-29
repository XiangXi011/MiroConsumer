import pytest

from app.services.consumer.event_ontology import ConsumerEventType
from app.services.consumer.society.channel_policy import (
    CHANNEL_IDS,
    DEFAULT_CHANNEL_IDS,
    DEFAULT_CHANNEL_POLICIES,
    ConsumerChannelPolicy,
    validate_enabled_channels,
)


def test_default_consumer_channels_are_fixed_and_use_phase6f_events():
    assert CHANNEL_IDS == (
        "xiaohongshu",
        "douyin",
        "wechat_group",
        "ecommerce_review",
        "zhihu_qa",
        "offline_word_of_mouth",
        "livestream",
        "sales_assistant",
    )
    assert DEFAULT_CHANNEL_IDS == ("xiaohongshu", "wechat_group", "ecommerce_review")
    assert set(DEFAULT_CHANNEL_POLICIES) == set(CHANNEL_IDS)

    ontology_values = {event.value for event in ConsumerEventType}
    for policy in DEFAULT_CHANNEL_POLICIES.values():
        policy.validate()
        assert set(policy.allowed_event_types).issubset(ontology_values)


def test_channel_policy_rejects_out_of_range_values_and_unknown_events():
    with pytest.raises(ValueError, match="amplification_factor"):
        ConsumerChannelPolicy(
            channel_id="xiaohongshu",
            amplification_factor=1.2,
            misread_factor=0.1,
            evidence_demand_factor=0.1,
            price_sensitivity_factor=0.1,
            trust_repair_factor=0.1,
            purchase_intent_factor=0.1,
            cross_channel_spread_factor=0.1,
            allowed_event_types=[ConsumerEventType.FIRST_IMPRESSION.value],
        ).validate()

    with pytest.raises(ValueError, match="allowed_event_types"):
        ConsumerChannelPolicy(
            channel_id="xiaohongshu",
            amplification_factor=0.1,
            misread_factor=0.1,
            evidence_demand_factor=0.1,
            price_sensitivity_factor=0.1,
            trust_repair_factor=0.1,
            purchase_intent_factor=0.1,
            cross_channel_spread_factor=0.1,
            allowed_event_types=["NEW_CHANNEL_ONLY_EVENT"],
        ).validate()


def test_validate_enabled_channels_applies_defaults_limits_and_illegal_id_errors():
    assert validate_enabled_channels(None, mode="quick") == list(DEFAULT_CHANNEL_IDS)
    assert validate_enabled_channels(["douyin", "wechat_group"], mode="quick") == [
        "douyin",
        "wechat_group",
    ]

    with pytest.raises(ValueError, match="Unsupported channel id"):
        validate_enabled_channels(["twitter"], mode="standard")

    with pytest.raises(ValueError, match="quick mode supports at most 3"):
        validate_enabled_channels(
            ["xiaohongshu", "douyin", "wechat_group", "ecommerce_review"],
            mode="quick",
        )

    with pytest.raises(ValueError, match="standard mode supports at most 5"):
        validate_enabled_channels(
            ["xiaohongshu", "douyin", "wechat_group", "ecommerce_review", "zhihu_qa", "livestream"],
            mode="standard",
        )

    assert len(validate_enabled_channels(list(CHANNEL_IDS), mode="large_society")) == 8
