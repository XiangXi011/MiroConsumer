from app.services.consumer.interview.representative_sampler import RepresentativeSampler
from app.services.consumer.society.consumer_roles import ConsumerRole
from app.services.consumer.society.population_models import ConsumerSocietyAgent, ConsumerSocietySnapshot
from app.services.consumer.society.state_store import SocietyStateStore


def _write_society_fixture(base_dir, simulation_id="sim-sampler"):
    store = SocietyStateStore(base_dir=base_dir)
    store.write_population(
        simulation_id,
        [
            ConsumerSocietyAgent(
                agent_id="agent-skeptic",
                parent_persona_id="persona-1",
                layer="core",
                segment="ingredient readers",
                role=ConsumerRole.Skeptic,
                channel_affinity={"zhihu_qa": 0.9},
                price_sensitivity=0.7,
                share_propensity=0.2,
                skepticism=0.9,
                state={"attitude_start": "neutral", "attitude_latest": "skeptical"},
            ),
            ConsumerSocietyAgent(
                agent_id="agent-advocate",
                parent_persona_id="persona-2",
                layer="core",
                segment="busy parents",
                role=ConsumerRole.Advocate,
                channel_affinity={"xiaohongshu": 0.8},
                share_propensity=0.8,
                state={"attitude_start": "neutral", "attitude_latest": "positive"},
            ),
        ],
    )
    store.write_rounds(
        simulation_id,
        [
            ConsumerSocietySnapshot(
                simulation_id=simulation_id,
                run_id="run-1",
                round_index=0,
                agents_count=2,
                events=[
                    {
                        "event_id": "event-skeptic",
                        "agent_id": "agent-skeptic",
                        "consumer_event_type": "ASK_PROOF",
                        "quote": "Show me proof before I believe this.",
                        "finding_ids": ["finding-1"],
                    },
                    {
                        "event_id": "event-advocate",
                        "agent_id": "agent-advocate",
                        "consumer_event_type": "AMPLIFY_CLAIM",
                        "quote": "This is easy to recommend.",
                    },
                ],
            )
        ],
    )
    store.write_channel_metrics(
        simulation_id,
        {"channels": {"zhihu_qa": {"fit_score": 0.55}, "xiaohongshu": {"fit_score": 0.62}}},
    )
    store.write_channel_events(
        simulation_id,
        [
            {"event_id": "channel-1", "actor_id": "agent-skeptic", "channel_id": "zhihu_qa"},
            {"event_id": "channel-2", "actor_id": "agent-advocate", "channel_id": "xiaohongshu"},
        ],
    )
    return store


def test_representative_sampler_uses_society_roles_without_new_enum(tmp_path):
    _write_society_fixture(tmp_path)

    rows = RepresentativeSampler(base_dir=tmp_path).sample(
        "sim-sampler",
        roles=[ConsumerRole.Skeptic.value],
        limit=4,
    )

    assert len(rows) == 1
    assert rows[0]["role"] == ConsumerRole.Skeptic.value
    assert rows[0]["channel_id"] == "zhihu_qa"
    assert rows[0]["key_quote"] == "Show me proof before I believe this."
    assert rows[0]["event_ids"] == ["event-skeptic", "channel-1"]
    assert rows[0]["finding_ids"] == ["finding-1"]


def test_representative_sampler_prefers_channel_assignments_over_generic_affinity(tmp_path):
    simulation_id = "sim-assignment"
    store = SocietyStateStore(base_dir=tmp_path)
    store.write_population(
        simulation_id,
        [
            ConsumerSocietyAgent(
                agent_id="agent-assigned",
                parent_persona_id="persona-1",
                layer="core",
                segment="ingredient readers",
                role=ConsumerRole.Skeptic,
                channel_affinity={"consumer_society": 1.0},
            ),
            ConsumerSocietyAgent(
                agent_id="agent-other",
                parent_persona_id="persona-2",
                layer="core",
                segment="busy parents",
                role=ConsumerRole.Advocate,
                channel_affinity={"consumer_society": 1.0},
            ),
        ],
    )
    store.write_channel_assignments(
        simulation_id,
        {
            "xiaohongshu": ["agent-assigned"],
            "wechat_group": ["agent-other"],
        },
    )

    rows = RepresentativeSampler(base_dir=tmp_path).sample(
        simulation_id,
        roles=[ConsumerRole.Skeptic.value],
        limit=4,
    )

    assert rows[0]["channel_id"] == "xiaohongshu"
