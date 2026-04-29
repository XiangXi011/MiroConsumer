from app.services.consumer.event_ontology import ConsumerEventType
from app.services.consumer.society.channel_runtime import ConsumerChannelRuntime
from app.services.consumer.society.consumer_roles import ConsumerRole
from app.services.consumer.society.population_models import ConsumerSocietyAgent


def _agent(index, role=ConsumerRole.Advocate, layer="core"):
    return ConsumerSocietyAgent(
        agent_id=f"agent-{index}",
        parent_persona_id=f"persona-{index % 8}",
        layer=layer,
        segment=f"segment-{index % 4}",
        role=role,
        channel_affinity={
            "xiaohongshu": 0.8 if index % 3 == 0 else 0.2,
            "douyin": 0.8 if index % 3 == 1 else 0.2,
            "wechat_group": 0.8 if index % 3 == 2 else 0.2,
            "ecommerce_review": 0.6,
            "zhihu_qa": 0.4,
            "offline_word_of_mouth": 0.3,
            "livestream": 0.2,
            "sales_assistant": 0.2,
        },
    )


def _society_event(index, event_type=ConsumerEventType.FIRST_IMPRESSION.value, round_index=0):
    return {
        "event_id": f"society-{index}",
        "round_index": round_index,
        "agent_id": f"agent-{index}",
        "segment": f"segment-{index % 4}",
        "consumer_event_type": event_type,
        "claim": "low sugar",
        "quote": "consumer quote",
    }


def test_channel_runtime_assigns_agents_and_emits_channel_events():
    population = [_agent(i, layer="core" if i < 8 else "shadow") for i in range(24)]
    society_events = [_society_event(i, round_index=i % 2) for i in range(24)]

    result = ConsumerChannelRuntime().run(
        population=population,
        society_events=society_events,
        mode="standard",
        enabled_channels=["xiaohongshu", "douyin", "wechat_group"],
        seed=7,
    )

    assert set(result["assignments"]) == {"xiaohongshu", "douyin", "wechat_group"}
    assert all(len(agent_ids) >= 2 for agent_ids in result["assignments"].values())

    assigned_core_agents = {
        agent_id
        for agent_ids in result["assignments"].values()
        for agent_id in agent_ids
        if agent_id in {f"agent-{i}" for i in range(8)}
    }
    assert assigned_core_agents == {f"agent-{i}" for i in range(8)}

    assert result["events"]
    first = result["events"][0]
    assert first["channel_id"] in {"xiaohongshu", "douyin", "wechat_group"}
    assert first["channel_label"]
    assert first["actor_id"].startswith("agent-")
    assert first["segment"] == "segment-0"
    assert first["consumer_event_type"] in {event.value for event in ConsumerEventType}
    assert 0.0 <= first["strength"] <= 1.0
    assert "channel_metrics" in result


def test_channel_runtime_triggers_cross_channel_migration_paths():
    population = [_agent(i, role=ConsumerRole.Misreader) for i in range(12)]
    society_events = [
        _society_event(i, ConsumerEventType.NEGATIVE_CASCADE.value, round_index=i % 2)
        for i in range(12)
    ]

    result = ConsumerChannelRuntime().run(
        population=population,
        society_events=society_events,
        mode="standard",
        enabled_channels=["douyin", "wechat_group", "ecommerce_review"],
        seed=3,
    )

    migration_events = [event for event in result["events"] if event["cross_channel"]]
    assert migration_events
    assert any(
        event["source_channel_id"] == "douyin" and event["target_channel_id"] == "wechat_group"
        for event in migration_events
    )
    assert result["propagation_paths"]
    path = result["propagation_paths"][0]
    assert {"source_channel_id", "target_channel_id", "trigger_metric", "affected_segments"}.issubset(path)
    assert all(segment.startswith("segment-") for segment in path["affected_segments"])
