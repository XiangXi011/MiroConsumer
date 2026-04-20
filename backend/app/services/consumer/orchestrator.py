"""Consumer propagation orchestration helpers for Phase 1."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional

from .models import GraphVisibility
from .persona_pack import can_access_deep_graph


class ConsumerSimulationOrchestrator:
    """Build pinned prompts and persist consumer propagation snapshots."""

    def __init__(self, output_path: Optional[Path | str] = None):
        self.output_path = Path(output_path) if output_path is not None else None

    def build_round_prompt(
        self,
        round_num: int,
        agent_traits: Mapping[str, Any],
        brief_summary: str,
        visible_graph_nodes: Iterable[Mapping[str, Any]],
    ) -> str:
        visible_nodes = self.filter_visible_graph_nodes(
            round_num=round_num,
            agent_traits=agent_traits,
            visible_graph_nodes=visible_graph_nodes,
        )
        round_stage = "initial reaction" if round_num == 0 else "propagation discussion"
        lines = [
            brief_summary.strip(),
            f"Current round: {round_num} ({round_stage})",
            "Focus only on the product concept, copy, and discussion context listed below.",
            "Visible graph context:",
        ]
        if visible_nodes:
            for node in visible_nodes:
                lines.append(f"- [{node['type']}] {node['text']}")
        else:
            lines.append("- No extra graph context is visible in this round.")
        return "\n".join(lines)

    def filter_visible_graph_nodes(
        self,
        round_num: int,
        agent_traits: Mapping[str, Any],
        visible_graph_nodes: Iterable[Mapping[str, Any]],
    ) -> List[Dict[str, str]]:
        filtered: List[Dict[str, str]] = []
        allow_propagation = round_num >= 1
        allow_restricted = allow_propagation and can_access_deep_graph(agent_traits)

        for node in visible_graph_nodes:
            normalized = self._normalize_graph_node(node)
            visibility = normalized["visibility"]
            if visibility == GraphVisibility.Initial:
                filtered.append(normalized)
                continue
            if visibility == GraphVisibility.Propagation_Only and allow_propagation:
                filtered.append(normalized)
                continue
            if visibility == GraphVisibility.Restricted and allow_restricted:
                filtered.append(normalized)

        return filtered

    def build_round_snapshot(
        self,
        round_num: int,
        agent_traits: Mapping[str, Any],
        brief_summary: str,
        visible_graph_nodes: Iterable[Mapping[str, Any]],
        agent_id: str,
        agent_name: str,
    ) -> Dict[str, Any]:
        normalized_nodes = self.filter_visible_graph_nodes(
            round_num=round_num,
            agent_traits=agent_traits,
            visible_graph_nodes=visible_graph_nodes,
        )
        prompt = self.build_round_prompt(
            round_num=round_num,
            agent_traits=agent_traits,
            brief_summary=brief_summary,
            visible_graph_nodes=visible_graph_nodes,
        )
        attitude_label, bucket, quote = self._generate_response(
            round_num=round_num,
            agent_traits=agent_traits,
            visible_nodes=normalized_nodes,
        )
        influence_weight = float(agent_traits.get("influence_weight", 0.5))
        engagement = max(1, min(10, int(round(3 + influence_weight * 7 + round_num))))
        return {
            "round_num": round_num,
            "agent_id": agent_id,
            "agent_name": agent_name,
            "prompt": prompt,
            "visible_nodes": normalized_nodes,
            "attitude_label": attitude_label,
            "bucket": bucket,
            "quote": quote,
            "engagement": engagement,
        }

    def persist_round_snapshot(self, snapshot: Mapping[str, Any]) -> None:
        if self.output_path is None:
            raise ValueError("output_path must be configured before persisting snapshots")

        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        with self.output_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(dict(snapshot), ensure_ascii=False))
            f.write("\n")

    def _normalize_graph_node(self, node: Mapping[str, Any]) -> Dict[str, Any]:
        node_text = str(node.get("text") or node.get("name") or node.get("summary") or "").strip()
        if not node_text:
            node_text = "Unnamed node"

        visibility_value = node.get("visibility")
        if visibility_value is None and isinstance(node.get("attributes"), Mapping):
            visibility_value = node["attributes"].get("visibility")
        visibility = GraphVisibility(str(visibility_value or GraphVisibility.Initial.value))

        node_type = node.get("type")
        if not node_type:
            labels = node.get("labels")
            if isinstance(labels, list):
                node_type = next((label for label in labels if label != "Entity"), labels[0] if labels else "Node")
            else:
                node_type = "Node"

        return {
            "type": str(node_type),
            "text": node_text,
            "visibility": visibility,
        }

    def _generate_response(
        self,
        round_num: int,
        agent_traits: Mapping[str, Any],
        visible_nodes: List[Mapping[str, Any]],
    ) -> tuple[str, str, str]:
        risk_nodes = [node for node in visible_nodes if node["type"] == "RiskPoint"]
        talking_nodes = [node for node in visible_nodes if node["type"] != "RiskPoint"]

        if risk_nodes:
            risk_text = risk_nodes[0]["text"]
            return (
                "negative",
                "risk",
                f"I keep thinking about {risk_text}, so the claim starts to feel less trustworthy.",
            )

        if round_num >= 1 and talking_nodes:
            topic_text = talking_nodes[0]["text"]
            herd_tendency = str(agent_traits.get("herd_tendency", "medium")).strip().lower()
            if herd_tendency == "high":
                return (
                    "positive",
                    "resonance",
                    f"People would probably keep sharing {topic_text}, and that makes the idea feel credible.",
                )
            return (
                "neutral",
                "question",
                f"I keep seeing {topic_text}, but I still want more proof before I fully buy in.",
            )

        if talking_nodes:
            topic_text = talking_nodes[0]["text"]
            return (
                "positive",
                "resonance",
                f"This actually sounds like a practical fix because of {topic_text}.",
            )

        return (
            "neutral",
            "question",
            "I understand the pitch, but I need more concrete proof before reacting strongly.",
        )


__all__ = ["ConsumerSimulationOrchestrator"]
