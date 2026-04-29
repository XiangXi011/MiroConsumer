"""Phase 6H multi-channel consumer propagation runtime."""

from __future__ import annotations

import math
import random
from typing import Any, Dict, Iterable, List, Mapping, Sequence

from ..event_ontology import ConsumerEventType
from .channel_event_mapper import ChannelEventMapper
from .channel_metrics import ChannelMetricsAggregator
from .channel_models import ConsumerChannelEvent
from .channel_policy import (
    DEFAULT_CHANNEL_POLICIES,
    get_channel_policies,
    resolve_runtime_channels,
)
from .population_models import ConsumerSocietyAgent


MIGRATION_RULES = (
    ("douyin", "wechat_group", "negative_cascade_probability", 0.6, ConsumerEventType.NEGATIVE_CASCADE),
    ("xiaohongshu", "ecommerce_review", "purchase_intent_delta", 0.4, ConsumerEventType.SHARE_TO_CHANNEL),
    ("zhihu_qa", "wechat_group", "evidence_demand", 0.5, ConsumerEventType.ASK_PROOF),
    ("livestream", "ecommerce_review", "price_resistance", 0.5, ConsumerEventType.PRICE_RESISTANCE),
    ("offline_word_of_mouth", "wechat_group", "trust_decay", 0.4, ConsumerEventType.TRUST_DECAY),
    ("sales_assistant", "ecommerce_review", "trial_objection_intensity", 0.4, ConsumerEventType.ASK_PROOF),
)


class ConsumerChannelRuntime:
    """Run deterministic consumer channel propagation on top of society events."""

    def __init__(
        self,
        mapper: ChannelEventMapper | None = None,
        metrics_aggregator: ChannelMetricsAggregator | None = None,
    ):
        self.mapper = mapper or ChannelEventMapper()
        self.metrics_aggregator = metrics_aggregator or ChannelMetricsAggregator()

    def run(
        self,
        population: Iterable[ConsumerSocietyAgent],
        society_events: Iterable[Mapping[str, Any]],
        mode: str,
        enabled_channels: Sequence[str] | None,
        seed: int = 0,
    ) -> Dict[str, Any]:
        agents = list(population)
        events = list(society_events)
        channels = resolve_runtime_channels(enabled_channels, mode)
        policies = get_channel_policies(channels)
        assignments = self._assign_agents(agents, channels, seed)
        agent_to_channel = {
            agent_id: channel_id
            for channel_id, agent_ids in assignments.items()
            for agent_id in agent_ids
        }

        channel_events: List[Dict[str, Any]] = []
        for index, event in enumerate(events):
            actor_id = str(event.get("agent_id") or event.get("actor_id") or "")
            channel_id = agent_to_channel.get(actor_id) or channels[index % len(channels)]
            channel_events.append(
                self.mapper.map_event(
                    event=event,
                    channel_id=channel_id,
                    policy=policies[channel_id],
                    sequence=index,
                )
            )

        metrics = self.metrics_aggregator.aggregate(channel_events, channels, mode=mode)
        migrations = self._build_cross_channel_migrations(
            channel_events=channel_events,
            metrics=metrics,
            enabled_channels=channels,
            assignments=assignments,
        )
        if migrations["events"]:
            channel_events.extend(migrations["events"])
            metrics = self.metrics_aggregator.aggregate(channel_events, channels, mode=mode)

        return {
            "enabled_channels": channels,
            "assignments": assignments,
            "events": channel_events,
            "channel_metrics": metrics,
            "propagation_paths": migrations["paths"],
        }

    def _assign_agents(
        self,
        population: Sequence[ConsumerSocietyAgent],
        channels: Sequence[str],
        seed: int,
    ) -> Dict[str, List[str]]:
        rng = random.Random(seed)
        assignments: Dict[str, List[str]] = {channel_id: [] for channel_id in channels}
        for agent in population:
            ranked = sorted(
                channels,
                key=lambda channel_id: (
                    float(agent.channel_affinity.get(channel_id, 0.0)),
                    rng.random(),
                ),
                reverse=True,
            )
            assignments[ranked[0]].append(agent.agent_id)

        minimum = max(1, math.ceil(len(population) * 0.05)) if population else 0
        for channel_id in channels:
            while len(assignments[channel_id]) < minimum:
                donor = max(
                    (candidate for candidate in channels if candidate != channel_id),
                    key=lambda cid: len(assignments[cid]),
                )
                if len(assignments[donor]) <= minimum:
                    break
                assignments[channel_id].append(assignments[donor].pop())
        return assignments

    def _build_cross_channel_migrations(
        self,
        channel_events: Sequence[Mapping[str, Any]],
        metrics: Mapping[str, Any],
        enabled_channels: Sequence[str],
        assignments: Mapping[str, Sequence[str]],
    ) -> Dict[str, List[Dict[str, Any]]]:
        migration_events: List[Dict[str, Any]] = []
        paths: List[Dict[str, Any]] = []
        channel_metrics = metrics.get("channels", {})
        max_round = max((int(event.get("round_index", 0) or 0) for event in channel_events), default=0)

        for source, target, metric_key, threshold, migration_type in MIGRATION_RULES:
            if source not in enabled_channels or target not in enabled_channels:
                continue
            signal = self._migration_signal(source, metric_key, channel_events, channel_metrics)
            if signal <= threshold:
                continue
            source_events = [event for event in channel_events if event.get("channel_id") == source]
            if not source_events:
                continue
            first = source_events[0]
            target_ids = list(assignments.get(target, []))[:3]
            migration_event = ConsumerChannelEvent(
                event_id=f"migration:{source}:{target}:{len(migration_events)}",
                consumer_event_type=migration_type.value,
                channel_id=target,
                round_index=max_round + 1,
                actor_id=str(first.get("actor_id") or ""),
                target_ids=[str(item) for item in target_ids],
                claim_id=str(first.get("claim_id") or "claim-1"),
                finding_ids=[str(item) for item in first.get("finding_ids", [])],
                quote=f"{source} signal migrated to {target}",
                strength=signal,
                cross_channel=True,
                source_channel_id=source,
                target_channel_id=target,
            ).to_dict()
            migration_events.append(migration_event)
            paths.append(
                self._build_path(
                    source=source,
                    target=target,
                    metric_key=metric_key,
                    signal=signal,
                    source_events=source_events,
                    migration_event=migration_event,
                )
            )

        return {"events": migration_events, "paths": paths}

    def _migration_signal(
        self,
        source: str,
        metric_key: str,
        channel_events: Sequence[Mapping[str, Any]],
        channel_metrics: Mapping[str, Mapping[str, float]],
    ) -> float:
        metrics = channel_metrics.get(source, {})
        if metric_key in metrics:
            return float(metrics.get(metric_key, 0.0))
        source_events = [event for event in channel_events if event.get("channel_id") == source]
        total = max(len(source_events), 1)
        if metric_key == "trust_decay":
            count = sum(1 for event in source_events if event.get("consumer_event_type") == ConsumerEventType.TRUST_DECAY.value)
            return round(count / total, 4)
        if metric_key == "trial_objection_intensity":
            expected = {
                ConsumerEventType.ASK_PROOF.value,
                ConsumerEventType.BLOCK_PROPAGATION.value,
                ConsumerEventType.TRUST_DECAY.value,
            }
            count = sum(1 for event in source_events if event.get("consumer_event_type") in expected)
            return round(count / total, 4)
        return 0.0

    def _build_path(
        self,
        source: str,
        target: str,
        metric_key: str,
        signal: float,
        source_events: Sequence[Mapping[str, Any]],
        migration_event: Mapping[str, Any],
    ) -> Dict[str, Any]:
        affected_segments = sorted(
            {
                str(event.get("segment"))
                for event in source_events
                if event.get("segment")
            }
        )
        blocked_nodes = [
            str(event.get("actor_id") or "")
            for event in source_events
            if event.get("consumer_event_type") == ConsumerEventType.BLOCK_PROPAGATION.value
        ][:5]
        repair_nodes = [
            str(event.get("actor_id") or "")
            for event in source_events
            if event.get("consumer_event_type") == ConsumerEventType.TRUST_RECOVERY.value
        ][:5]
        if not affected_segments:
            affected_segments = [source, target]
        return {
            "path_id": f"path:{source}:{target}:{metric_key}",
            "first_actor_id": str(source_events[0].get("actor_id") or ""),
            "source_channel_id": source,
            "target_channel_id": target,
            "trigger_metric": metric_key,
            "trigger_value": round(signal, 4),
            "cross_segment_depth": len(affected_segments),
            "cross_channel_count": 1,
            "affected_segments": affected_segments,
            "blocked_nodes": blocked_nodes,
            "repair_nodes": repair_nodes,
            "event_id": migration_event.get("event_id", ""),
        }


__all__ = ["ConsumerChannelRuntime", "MIGRATION_RULES"]
