from app.services.consumer.social_topology import (
    SocialTopology,
    build_social_topology,
    select_topology_aware_targets,
)


def test_topology_yields_multiple_communities_and_roles():
    topology = build_social_topology()

    assert len(topology.communities) >= 2
    all_personas = set()
    for members in topology.communities.values():
        all_personas.update(members)
    assert len(all_personas) == 8

    expected_roles = {"bridge", "amplifier", "skeptic", "lurker", "regular"}
    actual_roles = set(topology.persona_role.values())
    assert expected_roles & actual_roles
    assert topology.bridges
    assert topology.amplifiers
    assert topology.skeptics
    assert topology.lurkers


def test_bridge_nodes_can_target_outside_own_community():
    topology = build_social_topology()
    all_persona_ids = list(topology.persona_community.keys())

    for bridge_id in topology.bridges:
        targets = select_topology_aware_targets(
            actor_id=bridge_id,
            event_type="positive_relay",
            topology=topology,
            all_persona_ids=all_persona_ids,
            round_index=1,
        )
        own_community = topology.persona_community.get(bridge_id, "")
        target_communities = {topology.persona_community.get(t) for t in targets}
        if len(topology.communities) > 1 and targets:
            assert any(tc != own_community for tc in target_communities)


def test_lurkers_have_lower_reach_than_amplifiers():
    topology = build_social_topology()
    all_persona_ids = list(topology.persona_community.keys())

    for lurker_id in topology.lurkers:
        lurker_targets = select_topology_aware_targets(
            actor_id=lurker_id,
            event_type="positive_relay",
            topology=topology,
            all_persona_ids=all_persona_ids,
            round_index=1,
        )
        assert len(lurker_targets) <= 1

    for amp_id in topology.amplifiers:
        amp_targets = select_topology_aware_targets(
            actor_id=amp_id,
            event_type="positive_relay",
            topology=topology,
            all_persona_ids=all_persona_ids,
            round_index=1,
        )
        assert len(amp_targets) >= len(lurker_targets)


def test_role_assignments_are_deterministic():
    topology_a = build_social_topology()
    topology_b = build_social_topology()

    assert topology_a.persona_role == topology_b.persona_role
    assert topology_a.persona_community == topology_b.persona_community
    assert topology_a.communities == topology_b.communities


def test_topology_aware_targets_excludes_self():
    topology = build_social_topology()
    all_persona_ids = list(topology.persona_community.keys())

    for pid in all_persona_ids:
        targets = select_topology_aware_targets(
            actor_id=pid,
            event_type="positive_relay",
            topology=topology,
            all_persona_ids=all_persona_ids,
            round_index=1,
        )
        assert pid not in targets


def test_select_targets_respects_skeptic_lower_reach():
    topology = build_social_topology()
    all_persona_ids = list(topology.persona_community.keys())

    for skeptic_id in topology.skeptics:
        targets = select_topology_aware_targets(
            actor_id=skeptic_id,
            event_type="skeptical_challenge",
            topology=topology,
            all_persona_ids=all_persona_ids,
            round_index=1,
        )
        assert len(targets) <= 1
