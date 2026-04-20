"""Consumer report context assembly for Phase 1."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping

from .scoring import ConsumerScoringService


class ConsumerReportContextBuilder:
    """Build structured report context from consumer round snapshots."""

    def __init__(self, scoring_service: ConsumerScoringService | None = None):
        self.scoring_service = scoring_service or ConsumerScoringService()

    def load_events(self, file_path: str | Path) -> List[Dict[str, Any]]:
        path = Path(file_path)
        if not path.exists():
            return []

        events: List[Dict[str, Any]] = []
        for line in path.read_text(encoding="utf-8").splitlines():
            text = line.strip()
            if not text:
                continue
            events.append(json.loads(text))
        return events

    def build(self, events: Iterable[Mapping[str, Any]]) -> Dict[str, Any]:
        normalized = [self._normalize_event(event) for event in events]
        normalized.sort(key=lambda item: (item["round_num"], str(item["agent_id"])))

        initial_labels = [event["attitude_label"] for event in normalized if event["round_num"] == 0]
        final_labels = list(self._latest_labels(normalized).values())
        summary = self.scoring_service.summarize(initial_labels, final_labels)
        evidence = self.scoring_service.build_evidence_bundle(normalized)

        return {
            "summary": summary.to_dict(),
            "initial_acceptance": summary.initial_acceptance,
            "post_propagation_acceptance": summary.post_propagation_acceptance,
            "attitude_shift_rate": summary.attitude_shift_rate,
            "top_resonance_points": self._top_points(normalized, {"resonance"}),
            "top_risk_points": self._top_points(normalized, {"risk"}),
            "top_misreads": self._top_points(normalized, {"misread", "question"}),
            "representative_voc_quotes": {
                "resonance": evidence.top_resonance_quotes,
                "risk": evidence.top_risk_quotes,
                "misread": evidence.top_misread_quotes,
            },
            "evidence_bundle": evidence.to_dict(),
            "events_count": len(normalized),
        }

    def _normalize_event(self, event: Mapping[str, Any]) -> Dict[str, Any]:
        visible_nodes = event.get("visible_nodes", [])
        if not isinstance(visible_nodes, list):
            visible_nodes = []
        return {
            "round_num": int(event.get("round_num", 0) or 0),
            "agent_id": str(event.get("agent_id", "")).strip(),
            "attitude_label": str(event.get("attitude_label", "neutral")).strip().lower() or "neutral",
            "bucket": str(event.get("bucket", "question")).strip().lower() or "question",
            "engagement": int(event.get("engagement", 0) or 0),
            "quote": str(event.get("quote", "")).strip(),
            "visible_nodes": visible_nodes,
        }

    def _latest_labels(self, events: Iterable[Mapping[str, Any]]) -> Dict[str, str]:
        latest: Dict[str, tuple[int, str]] = {}
        for event in events:
            agent_id = str(event.get("agent_id", "")).strip()
            if not agent_id:
                continue
            round_num = int(event.get("round_num", 0) or 0)
            attitude_label = str(event.get("attitude_label", "neutral")).strip().lower() or "neutral"
            previous = latest.get(agent_id)
            if previous is None or round_num >= previous[0]:
                latest[agent_id] = (round_num, attitude_label)
        return {agent_id: label for agent_id, (_, label) in latest.items()}

    def _top_points(self, events: Iterable[Mapping[str, Any]], buckets: set[str], limit: int = 3) -> List[str]:
        counter = Counter()
        first_seen: Dict[str, int] = {}

        for index, event in enumerate(events):
            if event["bucket"] not in buckets:
                continue
            point = self._extract_point(event)
            if not point:
                continue
            counter[point] += 1
            first_seen.setdefault(point, index)

        ranked = sorted(counter.items(), key=lambda item: (-item[1], first_seen[item[0]], item[0].casefold()))
        return [point for point, _ in ranked[:limit]]

    def _extract_point(self, event: Mapping[str, Any]) -> str:
        visible_nodes = event.get("visible_nodes", [])
        bucket = str(event.get("bucket", "question")).strip().lower()

        preferred_type = "RiskPoint" if bucket == "risk" else None
        if preferred_type:
            for node in visible_nodes:
                if node.get("type") == preferred_type and node.get("text"):
                    return str(node["text"]).strip()

        for node in visible_nodes:
            text = str(node.get("text", "")).strip()
            if text:
                return text

        return str(event.get("quote", "")).strip()


__all__ = ["ConsumerReportContextBuilder"]
