"""Dynamic what-if experiment deterministic coverage."""

import random

from app.services.consumer.interview.focus_group_service import FocusGroupService
from app.services.consumer.interview.interview_models import ConsumerInterviewRequest
from app.services.consumer.society.consumer_roles import ConsumerRole
from app.services.consumer.society.population_models import ConsumerSocietyAgent, ConsumerSocietySnapshot
from app.services.consumer.society.state_store import SocietyStateStore


class _Repo:
    def get_simulation(self, simulation_id):
        return type(
            "State",
            (),
            {
                "status": "READY",
                "project_id": "project-1",
                "graph_id": "graph-1",
                "project_type": "consumer_test",
                "consumer_mode": True,
            },
        )()


def _write_society_fixture(base_dir, simulation_id="sim-dynamic"):
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
                state={"attitude_start": "neutral", "attitude_latest": "skeptical"},
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
                agents_count=1,
                events=[
                    {
                        "event_id": "event-1",
                        "agent_id": "agent-skeptic",
                        "consumer_event_type": "ASK_PROOF",
                        "quote": "Show me proof before I believe this.",
                        "finding_ids": ["finding-price"],
                    },
                ],
            ),
        ],
    )
    store.write_channel_events(
        simulation_id,
        [
            {
                "event_id": "ch-1",
                "actor_id": "agent-skeptic",
                "consumer_event_type": "ASK_PROOF",
                "quote": "Show me proof before I believe this.",
            },
        ],
    )


def test_dynamic_what_if_experiments_are_deterministic_for_same_seed(tmp_path):
    """Same input context must produce the same what-if experiments."""
    _write_society_fixture(tmp_path, simulation_id="sim-seed-test")
    service = FocusGroupService(base_dir=tmp_path, simulation_repo=_Repo())

    target_context = {
        "task_type": "price_test",
        "finding_id": "finding-price",
        "claim": "29.9 price point",
        "risk_points": ["students resist 29.9 without stronger value proof"],
        "evidence_map": {
            "finding-price": {
                "support_level": "weak_support",
                "source_count": 1,
            }
        },
    }

    request = ConsumerInterviewRequest(
        simulation_id="sim-seed-test",
        topic="29.9 price point for low sugar yogurt",
        questions=[],
        agent_ids=["agent-skeptic"],
        roles=["skeptic"],
        mode="snapshot",
        max_agents=1,
        target_context=target_context,
    )

    session_a = service.run_focus_group(request, moderator_goal="Find price repair experiments")
    session_b = service.run_focus_group(request, moderator_goal="Find price repair experiments")

    assert session_a.next_what_if_experiments == session_b.next_what_if_experiments
    joined = " ".join(session_a.next_what_if_experiments)
    assert "finding-price" in joined
    assert "weak_support" in joined


def test_dynamic_what_if_experiments_differ_with_different_context(tmp_path):
    """Different risk points and evidence maps produce different experiments."""
    _write_society_fixture(tmp_path, simulation_id="sim-diff-test")
    service = FocusGroupService(base_dir=tmp_path, simulation_repo=_Repo())

    request_a = ConsumerInterviewRequest(
        simulation_id="sim-diff-test",
        topic="low sugar claim",
        questions=[],
        agent_ids=["agent-skeptic"],
        roles=["skeptic"],
        mode="snapshot",
        max_agents=1,
        target_context={
            "finding_id": "finding-a",
            "claim": "low sugar",
            "risk_points": ["allergen concern"],
            "evidence_map": {"finding-a": {"support_level": "supported"}},
        },
    )

    request_b = ConsumerInterviewRequest(
        simulation_id="sim-diff-test",
        topic="low sugar claim",
        questions=[],
        agent_ids=["agent-skeptic"],
        roles=["skeptic"],
        mode="snapshot",
        max_agents=1,
        target_context={
            "finding_id": "finding-b",
            "claim": "zero sugar",
            "risk_points": ["taste concern"],
            "evidence_map": {"finding-b": {"support_level": "insufficient_support"}},
        },
    )

    session_a = service.run_focus_group(request_a, moderator_goal="Explore concerns")
    session_b = service.run_focus_group(request_b, moderator_goal="Explore concerns")

    assert session_a.next_what_if_experiments != session_b.next_what_if_experiments


def test_dynamic_what_if_experiments_never_emit_banned_strings(tmp_path):
    """The three banned default strings must never appear in dynamic experiments."""
    _write_society_fixture(tmp_path, simulation_id="sim-ban-test")
    service = FocusGroupService(base_dir=tmp_path, simulation_repo=_Repo())

    banned = {
        "What if pricing were 20% lower?",
        "What if clinical evidence were front and center?",
        "What if packaging claims were simplified?",
    }

    request = ConsumerInterviewRequest(
        simulation_id="sim-ban-test",
        topic="packaging test topic",
        questions=[],
        agent_ids=["agent-skeptic"],
        roles=["skeptic"],
        mode="snapshot",
        max_agents=1,
        target_context={
            "finding_id": "finding-1",
            "claim": "test claim",
        },
    )

    session = service.run_focus_group(request, moderator_goal="Test")
    for exp in session.next_what_if_experiments:
        assert exp not in banned, f"Banned string found: {exp}"


def test_dynamic_what_if_experiments_include_finding_and_support_info(tmp_path):
    """Dynamic experiments must reference finding_id and support level when present."""
    _write_society_fixture(tmp_path, simulation_id="sim-ref-test")
    service = FocusGroupService(base_dir=tmp_path, simulation_repo=_Repo())

    request = ConsumerInterviewRequest(
        simulation_id="sim-ref-test",
        topic="price sensitivity",
        questions=[],
        agent_ids=["agent-skeptic"],
        roles=["skeptic"],
        mode="snapshot",
        max_agents=1,
        target_context={
            "finding_id": "finding-price-99",
            "claim": "$9.99 price point",
            "risk_points": ["budget shoppers resist above $8"],
            "evidence_map": {
                "finding-price-99": {"support_level": "weak_support", "source_count": 2}
            },
        },
    )

    session = service.run_focus_group(request, moderator_goal="Price test")
    joined = " ".join(session.next_what_if_experiments)
    assert "finding-price-99" in joined
    assert "weak_support" in joined


def test_branch_isolation_what_if_experiments_per_target_context(tmp_path):
    """Branch A and Branch B with different contexts must produce isolated experiments."""
    _write_society_fixture(tmp_path, simulation_id="sim-branch")
    service = FocusGroupService(base_dir=tmp_path, simulation_repo=_Repo())

    base_context = {
        "finding_id": "finding-base",
        "claim": "base claim",
        "risk_points": ["base risk"],
        "evidence_map": {"finding-base": {"support_level": "supported"}},
    }
    branch_context = {
        "finding_id": "finding-branch",
        "claim": "branch claim",
        "risk_points": ["branch risk"],
        "evidence_map": {"finding-branch": {"support_level": "insufficient_support"}},
    }

    base_request = ConsumerInterviewRequest(
        simulation_id="sim-branch",
        topic="base topic",
        questions=[],
        agent_ids=["agent-skeptic"],
        roles=["skeptic"],
        mode="snapshot",
        max_agents=1,
        target_context=base_context,
    )
    branch_request = ConsumerInterviewRequest(
        simulation_id="sim-branch",
        topic="branch topic",
        questions=[],
        agent_ids=["agent-skeptic"],
        roles=["skeptic"],
        mode="snapshot",
        max_agents=1,
        target_context=branch_context,
    )

    base_session = service.run_focus_group(base_request, moderator_goal="Base")
    branch_session = service.run_focus_group(branch_request, moderator_goal="Branch")

    # Experiments should reference their respective finding ids
    base_joined = " ".join(base_session.next_what_if_experiments)
    branch_joined = " ".join(branch_session.next_what_if_experiments)
    assert "finding-base" in base_joined
    assert "finding-branch" in branch_joined
    assert "finding-branch" not in base_joined
    assert "finding-base" not in branch_joined
