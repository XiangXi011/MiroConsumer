"""Sample representative consumers from Phase 6G society state."""

from typing import Any, Dict, List

from ..society.state_store import SocietyStateStore


class RepresentativeSampler:
    """Load society agent state and sample consumers by ConsumerRole."""

    def __init__(self, base_dir=None):
        self.store = SocietyStateStore(base_dir=base_dir)

    def sample(self, simulation_id: str, roles: List[str], limit: int) -> List[Dict[str, Any]]:
        population = self.store.read_population(simulation_id)
        rounds = self.store.read_rounds(simulation_id)
        channel_events = self.store.read_channel_events(simulation_id)
        assignments = self.store.read_channel_assignments(simulation_id)
        assignment_by_agent = {
            str(agent_id): str(channel_id)
            for channel_id, agent_ids in assignments.items()
            for agent_id in agent_ids
        }

        if roles:
            population = [a for a in population if a.get("role") in roles]

        population = population[:limit]

        result = []
        for agent in population:
            agent_id = agent["agent_id"]
            role = agent.get("role", "")

            affinities = agent.get("channel_affinity", {})
            channel_id = assignment_by_agent.get(agent_id, "")
            if not channel_id:
                real_affinities = {
                    channel: score
                    for channel, score in affinities.items()
                    if channel != "consumer_society"
                }
                channel_id = max(real_affinities, key=real_affinities.get) if real_affinities else ""

            event_ids = []
            finding_ids = []
            key_quote = ""

            for rd in rounds:
                for event in rd.get("events", []):
                    if event.get("agent_id") == agent_id:
                        eid = event.get("event_id")
                        if eid:
                            event_ids.append(eid)
                        quote = event.get("quote", "")
                        if quote and not key_quote:
                            key_quote = quote
                        fids = event.get("finding_ids", [])
                        if fids:
                            finding_ids.extend(fids)

            for ce in channel_events:
                if ce.get("actor_id") == agent_id:
                    if not channel_id and ce.get("channel_id"):
                        channel_id = str(ce.get("channel_id"))
                    ceid = ce.get("event_id")
                    if ceid:
                        event_ids.append(ceid)

            result.append({
                "agent_id": agent_id,
                "role": role,
                "channel_id": channel_id,
                "key_quote": key_quote,
                "event_ids": event_ids,
                "finding_ids": finding_ids,
                "segment": agent.get("segment", ""),
                "state": agent.get("state", {}),
            })

        return result
