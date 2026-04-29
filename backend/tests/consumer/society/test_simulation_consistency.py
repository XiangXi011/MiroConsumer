"""Simulation consistency deterministic coverage."""

import random

from app.services.consumer.society.consumer_roles import ConsumerRole
from app.services.consumer.society.population_models import (
    ConsumerSocietyAgent,
    ConsumerSocietyRunConfig,
    ConsumerSocietySnapshot,
)
from app.services.consumer.society.state_store import SocietyStateStore


def test_same_seed_produces_deterministic_agent_selection():
    """Same random seed must produce the same agent selection order."""
    agents = [
        ConsumerSocietyAgent(
            agent_id=f"agent-{i}",
            parent_persona_id=f"persona-{i % 3}",
            layer="core",
            segment="testers",
            role=ConsumerRole.Skeptic,
        )
        for i in range(10)
    ]

    def select_with_seed(seed):
        rng = random.Random(seed)
        indices = list(range(len(agents)))
        rng.shuffle(indices)
        return [agents[i].agent_id for i in indices[:5]]

    run_a = select_with_seed(42)
    run_b = select_with_seed(42)
    run_c = select_with_seed(99)

    assert run_a == run_b
    assert run_a != run_c


def test_same_seed_produces_deterministic_event_sequences(tmp_path):
    """Same seed must produce the same synthetic event sequence."""
    store = SocietyStateStore(base_dir=tmp_path)

    def generate_events(seed, simulation_id):
        rng = random.Random(seed)
        events = []
        for i in range(5):
            events.append({
                "event_id": f"evt-{i}",
                "agent_id": f"agent-{rng.randint(0, 9)}",
                "consumer_event_type": rng.choice(["ASK_PROOF", "POSITIVE_RELAY", "SKEPTICAL_CHALLENGE"]),
                "quote": f"quote-{rng.random()}",
            })
        return events

    events_a = generate_events(123, "sim-1")
    events_b = generate_events(123, "sim-1")
    events_c = generate_events(456, "sim-1")

    assert events_a == events_b
    assert events_a != events_c


def test_branch_base_isolation_state_storage(tmp_path):
    """Branch and base simulations must have independent state stores."""
    store = SocietyStateStore(base_dir=tmp_path)

    base_sim = "sim-base"
    branch_sim = "sim-branch"

    base_agents = [
        ConsumerSocietyAgent(
            agent_id="agent-base-1",
            parent_persona_id="persona-1",
            layer="core",
            segment="base segment",
            role=ConsumerRole.Advocate,
        ),
    ]
    branch_agents = [
        ConsumerSocietyAgent(
            agent_id="agent-branch-1",
            parent_persona_id="persona-2",
            layer="core",
            segment="branch segment",
            role=ConsumerRole.Skeptic,
        ),
    ]

    store.write_population(base_sim, base_agents)
    store.write_population(branch_sim, branch_agents)

    base_loaded = store.read_population(base_sim)
    branch_loaded = store.read_population(branch_sim)

    assert len(base_loaded) == 1
    assert len(branch_loaded) == 1
    assert base_loaded[0]["agent_id"] == "agent-base-1"
    assert branch_loaded[0]["agent_id"] == "agent-branch-1"
    assert base_loaded[0]["segment"] == "base segment"
    assert branch_loaded[0]["segment"] == "branch segment"


def test_run_config_same_seed_same_population_size():
    """Same seed in run config must not change deterministic population targets."""
    config_a = ConsumerSocietyRunConfig(
        mode="quick",
        core_persona_count=8,
        expanded_persona_count=2,
        shadow_agent_count=0,
        max_rounds=3,
        random_seed=42,
    )
    config_b = ConsumerSocietyRunConfig(
        mode="quick",
        core_persona_count=8,
        expanded_persona_count=2,
        shadow_agent_count=0,
        max_rounds=3,
        random_seed=42,
    )

    assert config_a.target_population_size == config_b.target_population_size == 10
    assert config_a.random_seed == config_b.random_seed
    assert config_a.to_dict() == config_b.to_dict()


def test_snapshot_rounds_are_isolated_between_simulations(tmp_path):
    """Rounds written to different simulation IDs must not leak."""
    store = SocietyStateStore(base_dir=tmp_path)

    sim_a = "sim-a"
    sim_b = "sim-b"

    store.write_rounds(sim_a, [
        ConsumerSocietySnapshot(
            simulation_id=sim_a,
            run_id="run-1",
            round_index=0,
            agents_count=2,
            events=[{"event_id": "evt-a-1"}],
        ),
    ])
    store.write_rounds(sim_b, [
        ConsumerSocietySnapshot(
            simulation_id=sim_b,
            run_id="run-1",
            round_index=0,
            agents_count=3,
            events=[{"event_id": "evt-b-1"}],
        ),
    ])

    rounds_a = store.read_rounds(sim_a)
    rounds_b = store.read_rounds(sim_b)

    assert len(rounds_a) == 1
    assert len(rounds_b) == 1
    assert rounds_a[0]["events"][0]["event_id"] == "evt-a-1"
    assert rounds_b[0]["events"][0]["event_id"] == "evt-b-1"


def test_deterministic_role_assignment_with_fixed_seed():
    """Fixed seed must produce deterministic role assignments."""
    def assign_roles(agents, seed):
        rng = random.Random(seed)
        roles = list(ConsumerRole)
        assignments = {}
        for agent in agents:
            assignments[agent["agent_id"]] = rng.choice(roles).value
        return assignments

    agents = [{"agent_id": f"a{i}"} for i in range(5)]

    assign_a = assign_roles(agents, 777)
    assign_b = assign_roles(agents, 777)
    assign_c = assign_roles(agents, 888)

    assert assign_a == assign_b
    assert assign_a != assign_c


def test_fake_llm_deterministic_output_across_simulations():
    """Fake LLM with fixed payload must produce identical outputs regardless of simulation context."""
    class FakeLLM:
        def __init__(self, fixed_payload):
            self.fixed_payload = fixed_payload
            self.call_count = 0

        def chat_json(self, **kwargs):
            self.call_count += 1
            return dict(self.fixed_payload)

    payload = {"response": "fixed", "trust": 0.5, "confidence": 0.9}
    llm = FakeLLM(payload)

    results = []
    for sim_id in ["sim-1", "sim-2", "sim-3"]:
        result = llm.chat_json(
            messages=[{"role": "user", "content": f"Sim {sim_id}"}],
        )
        results.append(result)

    assert all(r == payload for r in results)
    assert llm.call_count == 3


def test_state_store_isolation_prevents_cross_simulation_reads(tmp_path):
    """Reading from one simulation must not return data from another."""
    store = SocietyStateStore(base_dir=tmp_path)

    store.write_population("sim-x", [
        ConsumerSocietyAgent(
            agent_id="agent-x",
            parent_persona_id="p-x",
            layer="core",
            segment="seg-x",
            role=ConsumerRole.Advocate,
        ),
    ])

    empty_pop = store.read_population("sim-y")
    empty_rounds = store.read_rounds("sim-y")
    empty_events = store.read_channel_events("sim-y")

    assert empty_pop == []
    assert empty_rounds == []
    assert empty_events == []
