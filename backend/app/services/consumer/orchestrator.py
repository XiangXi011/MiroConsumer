"""Consumer propagation orchestration helpers for Phase 1."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional

from .access_policy import resolve_visible_findings
from .event_engine import (
    build_propagation_event,
    classify_propagation_event,
    derive_speech_act_from_bucket,
    derive_trigger_from_findings,
)
from .intervention_manager import ConsumerIntervention
from .models import GraphVisibility, ResearchFinding
from .persona_pack import can_access_deep_graph, load_default_persona_pack
from .social_topology import (
    SocialTopology,
    build_social_topology,
    select_topology_aware_targets,
)


class ConsumerSimulationOrchestrator:
    """Build pinned prompts and persist consumer propagation snapshots."""

    def __init__(
        self,
        output_path: Optional[Path | str] = None,
        topology: Optional[SocialTopology] = None,
    ):
        self.output_path = Path(output_path) if output_path is not None else None
        self._topology = topology or build_social_topology()

    def build_round_prompt(
        self,
        round_num: int,
        agent_traits: Mapping[str, Any],
        brief_summary: str,
        visible_graph_nodes: Iterable[Mapping[str, Any]],
        research_findings: Optional[Iterable[ResearchFinding]] = None,
        interventions: Optional[Iterable[ConsumerIntervention]] = None,
    ) -> str:
        visible_nodes = self.filter_visible_graph_nodes(
            round_num=round_num,
            agent_traits=agent_traits,
            visible_graph_nodes=visible_graph_nodes,
        )
        visible_findings = resolve_visible_findings(
            persona=agent_traits,
            findings=research_findings or [],
            round_index=round_num,
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

        if visible_findings:
            lines.append("Visible research findings:")
            for finding in visible_findings:
                lines.append(f"- [{finding.finding_type}] {finding.summary}")

        # Inject active interventions for this round
        active_interventions = self._active_interventions_for_round(round_num, interventions)
        if active_interventions:
            lines.append("Interventions:")
            for intervention in active_interventions:
                payload_text = self._render_intervention_payload(intervention)
                if payload_text:
                    lines.append(f"- [{intervention.intervention_type}] {payload_text}")

        return "\n".join(lines)

    def _active_interventions_for_round(
        self,
        round_num: int,
        interventions: Optional[Iterable[ConsumerIntervention]],
    ) -> List[ConsumerIntervention]:
        if interventions is None:
            return []
        return [
            i for i in interventions
            if i.target_round is None or i.target_round == round_num
        ]

    def _render_intervention_payload(self, intervention: ConsumerIntervention) -> str:
        payload = intervention.payload
        if intervention.intervention_type == "clarification_injection":
            return str(payload.get("message", "")).strip()
        if intervention.intervention_type == "revised_claim_injection":
            return str(payload.get("claim", "")).strip()
        if intervention.intervention_type == "evidence_reveal":
            return str(payload.get("evidence", "")).strip()
        return str(payload) if payload else ""

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
        research_findings: Optional[Iterable[ResearchFinding]] = None,
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
            research_findings=research_findings,
        )
        visible_findings = resolve_visible_findings(
            persona=agent_traits,
            findings=research_findings or [],
            round_index=round_num,
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
            "visible_finding_ids": [f.finding_id for f in visible_findings],
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

    def build_propagation_events_for_transition(
        self,
        round_num: int,
        agent_id: str,
        previous_attitude: Optional[str],
        current_attitude: str,
        current_bucket: str,
        visible_finding_ids: List[str],
        quote: str,
        research_findings: Optional[Iterable[ResearchFinding]] = None,
    ) -> List[Dict[str, Any]]:
        """Build propagation events for a snapshot based on attitude transition."""
        if previous_attitude is None or previous_attitude == current_attitude:
            return []

        findings_list = list(research_findings or [])
        visible_findings_data: List[Dict[str, Any]] = []
        for finding in findings_list:
            if finding.finding_id in visible_finding_ids:
                visible_findings_data.append({
                    "finding_id": finding.finding_id,
                    "finding_type": finding.finding_type,
                })

        trigger = derive_trigger_from_findings(visible_findings_data)
        speech_act = derive_speech_act_from_bucket(current_bucket)
        event_type = classify_propagation_event(
            before_attitude=previous_attitude,
            after_attitude=current_attitude,
            trigger=trigger,
            speech_act=speech_act,
        )

        all_persona_ids = list(self._topology.persona_community.keys())
        target_ids = select_topology_aware_targets(
            actor_id=agent_id,
            event_type=event_type,
            topology=self._topology,
            all_persona_ids=all_persona_ids,
            round_index=round_num,
        )

        actor_community = self._topology.persona_community.get(agent_id, "")
        actor_role = self._topology.persona_role.get(agent_id, "")
        target_communities = [self._topology.persona_community.get(t, "") for t in target_ids]
        cross_community = actor_community != "" and any(
            tc != actor_community for tc in target_communities
        )

        event = build_propagation_event(
            actor_id=agent_id,
            target_ids=target_ids,
            event_type=event_type,
            trigger_finding_ids=list(visible_finding_ids),
            supporting_quote=quote,
            round_index=round_num,
            actor_community=actor_community,
            actor_role=actor_role,
            cross_community=cross_community,
            target_communities=target_communities,
        )
        return [event.model_dump()]

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
