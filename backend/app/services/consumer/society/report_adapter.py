"""Adapt society runtime artifacts into consumer report context."""

from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Mapping

from .channel_report_adapter import ChannelReportAdapter
from .state_store import SocietyStateStore
from ..research_boundary import default_applicability_boundary


EMPTY_SOCIETY_CONTEXT = {
    "society_mode": "quick",
    "society_agents_count": 0,
    "society_rounds_completed": 0,
    "society_llm_budget_used": 0,
    "society_metrics": {},
    "representative_agents": [],
    "society_event_summary": {},
    "society_risk_summary": {},
    "society_purchase_intent_summary": {},
    "society_reasoning_summary": {
        "backend_counts": {},
        "llm_invoked_count": 0,
        "calibration_status": "golden_case_not_run",
        "production_readiness": "requires_golden_case_calibration",
    },
    "society_network_summary": {},
    "society_top_resonance_points": [],
    "society_top_risk_points": [],
    "society_top_misreads": [],
    "society_representative_voc_quotes": {
        "resonance": [],
        "risk": [],
        "misread": [],
    },
}


_RESONANCE_EVENT_TYPES = {
    "FIRST_IMPRESSION",
    "AMPLIFY_CLAIM",
    "SHARE_TO_CHANNEL",
    "PURCHASE_INTENT_UP",
    "TRUST_RECOVERY",
}
_RISK_EVENT_TYPES = {
    "ASK_PROOF",
    "COMPARE_COMPETITOR",
    "PRICE_RESISTANCE",
    "TRUST_DECAY",
    "BLOCK_PROPAGATION",
    "PURCHASE_INTENT_DOWN",
    "NEGATIVE_CASCADE",
}
_MISREAD_EVENT_TYPES = {"MISREAD_CLAIM"}

_EVENT_TYPE_PRIORITY = {
    "FIRST_IMPRESSION": 0,
    "PURCHASE_INTENT_UP": 1,
    "AMPLIFY_CLAIM": 2,
    "SHARE_TO_CHANNEL": 3,
    "TRUST_RECOVERY": 4,
    "ASK_PROOF": 0,
    "MISREAD_CLAIM": 1,
    "PRICE_RESISTANCE": 2,
    "COMPARE_COMPETITOR": 3,
    "TRUST_DECAY": 4,
    "BLOCK_PROPAGATION": 5,
    "PURCHASE_INTENT_DOWN": 6,
    "NEGATIVE_CASCADE": 7,
}


class SocietyReportAdapter:
    """Build and merge society context for ReportAgent."""

    def __init__(self, base_dir: str | Path | None = None):
        self.store = SocietyStateStore(base_dir=base_dir)

    def build_report_context(self, simulation_id: str) -> Dict[str, Any]:
        config = self.store.read_config(simulation_id)
        metrics = self.store.read_metrics(simulation_id)
        population = self.store.read_population(simulation_id)
        rounds = self.store.read_rounds(simulation_id)
        network_topology = self.store.read_network_topology(simulation_id)
        research_boundary = self.store.read_research_boundary(simulation_id) or default_applicability_boundary()
        channel_context = ChannelReportAdapter(base_dir=self.store.base_dir).build_report_context(simulation_id)
        if not config and not metrics and not population:
            return {
                **dict(EMPTY_SOCIETY_CONTEXT),
                "applicability_boundary": research_boundary,
                **channel_context,
            }

        event_summary: Dict[str, int] = {}
        backend_counts: Dict[str, int] = dict(config.get("reasoning_backend_counts", {}) or {})
        llm_invoked_count = int(config.get("llm_invoked_count", 0) or 0)
        should_count_backends_from_rounds = not backend_counts
        should_count_llm_invocations_from_rounds = "llm_invoked_count" not in config
        for snapshot in rounds:
            for event in snapshot.get("events", []):
                event_type = event.get("consumer_event_type", "")
                if event_type:
                    event_summary[event_type] = event_summary.get(event_type, 0) + 1
                if should_count_backends_from_rounds:
                    backend = str(event.get("reasoning_backend", "unknown") or "unknown")
                    backend_counts[backend] = backend_counts.get(backend, 0) + 1
                if should_count_llm_invocations_from_rounds and event.get("llm_invoked"):
                    llm_invoked_count += 1
        events = self._flatten_round_events(rounds)

        calibration_status = str(config.get("reasoning_calibration_status", "golden_case_not_run"))
        production_readiness = (
            "ready_for_calibrated_reporting"
            if calibration_status == "golden_case_passed"
            else "requires_golden_case_calibration"
        )

        context = {
            "society_mode": config.get("mode", "quick"),
            "society_agents_count": len(population),
            "society_rounds_completed": len(rounds),
            "society_llm_budget_used": config.get("llm_budget_used", 0),
            "society_metrics": metrics,
            "representative_agents": self._representative_agents(population),
            "society_event_summary": event_summary,
            "society_risk_summary": {
                "misread_rate": metrics.get("misread_rate", 0.0),
                "negative_cascade_probability": metrics.get("negative_cascade_probability", 0.0),
                "trust_decay_rate": metrics.get("trust_decay_rate", 0.0),
            },
            "society_purchase_intent_summary": {
                "purchase_intent_delta": metrics.get("purchase_intent_delta", 0.0),
                "price_resistance_index": metrics.get("price_resistance_index", 0.0),
            },
            "society_reasoning_summary": {
                "backend_counts": backend_counts,
                "llm_invoked_count": llm_invoked_count,
                "calibration_status": calibration_status,
                "production_readiness": production_readiness,
            },
            "society_network_summary": {
                "topology_version": network_topology.get("topology_version", ""),
                "node_count": network_topology.get("node_count", 0),
                "edge_count": network_topology.get("edge_count", 0),
                "graphs": {
                    key: len(value)
                    for key, value in dict(network_topology.get("graphs", {}) or {}).items()
                },
            },
            "society_top_resonance_points": self._top_points(events, "resonance"),
            "society_top_risk_points": self._top_points(events, "risk"),
            "society_top_misreads": self._top_points(events, "misread"),
            "society_representative_voc_quotes": self._representative_voc_quotes(events),
            "applicability_boundary": research_boundary,
        }
        context.update(channel_context)
        return context

    def merge_into_context(
        self,
        context: Mapping[str, Any],
        society_context: Mapping[str, Any],
    ) -> Dict[str, Any]:
        merged = dict(context)
        merged.update(dict(society_context))
        return merged

    def _representative_agents(self, population: list[dict]) -> list[str]:
        return [str(agent.get("agent_id", "")) for agent in population[:8] if agent.get("agent_id")]

    def _flatten_round_events(self, rounds: List[Mapping[str, Any]]) -> List[Dict[str, Any]]:
        events: List[Dict[str, Any]] = []
        for snapshot in rounds:
            round_index = snapshot.get("round_index", 0)
            for event in snapshot.get("events", []) or []:
                if not isinstance(event, Mapping):
                    continue
                item = dict(event)
                item.setdefault("round_index", round_index)
                events.append(item)
        return events

    def _representative_voc_quotes(self, events: List[Mapping[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        return {
            "resonance": self._top_quotes(events, "resonance"),
            "risk": self._top_quotes(events, "risk"),
            "misread": self._top_quotes(events, "misread"),
        }

    def _top_quotes(
        self,
        events: List[Mapping[str, Any]],
        bucket: str,
        limit: int = 3,
    ) -> List[Dict[str, Any]]:
        candidates: List[tuple[int, Dict[str, Any]]] = []
        seen_quotes: set[str] = set()
        for index, event in enumerate(events):
            event_type = self._event_type(event)
            if bucket not in self._buckets_for_event_type(event_type):
                continue
            quote = self._quote_text(event)
            if not quote:
                continue
            quote_key = quote.casefold()
            if quote_key in seen_quotes:
                continue
            seen_quotes.add(quote_key)
            candidates.append((index, self._quote_item(event, event_type, quote)))

        def sort_key(item: tuple[int, Dict[str, Any]]) -> tuple[int, int, int, int]:
            index, quote_item = item
            metadata = quote_item.get("quote_metadata") or {}
            is_llm = isinstance(metadata, Mapping) and metadata.get("template_generated") is False
            event_type = str(quote_item.get("consumer_event_type", "") or "")
            return (
                _EVENT_TYPE_PRIORITY.get(event_type, 99),
                0 if is_llm else 1,
                -int(quote_item.get("engagement", 0) or 0),
                index,
            )

        return [quote for _, quote in sorted(candidates, key=sort_key)[:limit]]

    def _quote_item(
        self,
        event: Mapping[str, Any],
        event_type: str,
        quote: str,
    ) -> Dict[str, Any]:
        metadata = event.get("quote_metadata")
        if not isinstance(metadata, Mapping):
            metadata = self._metadata_from_event(event)
        return {
            "quote": quote,
            "engagement": self._engagement_score(event),
            "agent_id": str(event.get("agent_id", "") or ""),
            "segment": str(event.get("segment", "") or event.get("role", "") or ""),
            "consumer_event_type": event_type,
            "claim": str(event.get("claim", "") or ""),
            "round_num": int(event.get("round_index", 0) or 0),
            "quote_metadata": dict(metadata),
        }

    def _top_points(
        self,
        events: List[Mapping[str, Any]],
        bucket: str,
        limit: int = 3,
    ) -> List[str]:
        counter: Counter[str] = Counter()
        first_seen: Dict[str, int] = {}
        for index, event in enumerate(events):
            event_type = self._event_type(event)
            if bucket not in self._buckets_for_event_type(event_type):
                continue
            point = self._point_for_event(event_type, str(event.get("claim", "") or ""))
            if not point:
                continue
            counter[point] += 1
            first_seen.setdefault(point, index)
        ranked = sorted(
            counter.items(),
            key=lambda item: (-item[1], first_seen[item[0]], item[0].casefold()),
        )
        return [point for point, _ in ranked[:limit]]

    @staticmethod
    def _event_type(event: Mapping[str, Any]) -> str:
        return str(event.get("consumer_event_type") or event.get("event_type") or "").strip()

    @staticmethod
    def _buckets_for_event_type(event_type: str) -> set[str]:
        buckets: set[str] = set()
        if event_type in _RESONANCE_EVENT_TYPES:
            buckets.add("resonance")
        if event_type in _RISK_EVENT_TYPES or event_type in _MISREAD_EVENT_TYPES:
            buckets.add("risk")
        if event_type in _MISREAD_EVENT_TYPES:
            buckets.add("misread")
        return buckets

    @staticmethod
    def _quote_text(event: Mapping[str, Any]) -> str:
        for key in ("quote", "quote_text", "paraphrase_text"):
            text = str(event.get(key, "") or "").strip()
            if text:
                return text
        return ""

    @staticmethod
    def _metadata_from_event(event: Mapping[str, Any]) -> Dict[str, Any]:
        source = str(event.get("generated_by") or event.get("reasoning_backend") or "template")
        llm_invoked = bool(event.get("llm_invoked"))
        return {
            "source": source,
            "template_generated": not (source == "llm" or llm_invoked),
        }

    @staticmethod
    def _engagement_score(event: Mapping[str, Any]) -> int:
        candidates = []
        for key in (
            "engagement",
            "strength",
            "propagation_strength",
            "purchase_intent",
            "trust",
            "confidence",
            "price_sensitivity",
        ):
            try:
                candidates.append(float(event.get(key, 0) or 0))
            except (TypeError, ValueError):
                continue
        if not candidates:
            return 0
        score = max(candidates)
        if score <= 1:
            score *= 100
        return int(round(score))

    @staticmethod
    def _point_for_event(event_type: str, claim: str) -> str:
        subject = claim.strip() or "核心宣称"
        labels = {
            "FIRST_IMPRESSION": f"{subject}有第一眼记忆点，但需要真实场景支撑",
            "AMPLIFY_CLAIM": f"{subject}具备被转述和扩散的表达潜力",
            "SHARE_TO_CHANNEL": f"{subject}适合在社群和内容渠道继续放大",
            "PURCHASE_INTENT_UP": f"{subject}能激发尝试意愿",
            "TRUST_RECOVERY": f"{subject}在补充证据后有信任修复空间",
            "ASK_PROOF": f"{subject}需要检测证明、备案信息或真实反馈支撑",
            "MISREAD_CLAIM": f"{subject}容易被误读为全场景承诺或短期强承诺",
            "COMPARE_COMPETITOR": f"{subject}会被拿来和竞品功效/价格直接比较",
            "PRICE_RESISTANCE": f"{subject}需要解释价格与竞品价值差异",
            "TRUST_DECAY": f"{subject}在证据不足时可能触发信任下降",
            "BLOCK_PROPAGATION": f"{subject}在疑问未澄清前可能阻断口碑扩散",
            "PURCHASE_INTENT_DOWN": f"{subject}可能拉低试用意愿",
            "NEGATIVE_CASCADE": f"{subject}存在负面讨论放大的风险",
        }
        return labels.get(event_type, "")


__all__ = ["EMPTY_SOCIETY_CONTEXT", "SocietyReportAdapter"]
