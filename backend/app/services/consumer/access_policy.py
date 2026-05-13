"""Persona-aware knowledge access policy for consumer simulation rounds."""

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Mapping

from .models import GraphVisibility, ResearchFinding
from .persona_pack import can_access_deep_graph


def resolve_visible_findings(
    persona: Mapping[str, Any],
    findings: Iterable[ResearchFinding],
    round_index: int,
) -> List[ResearchFinding]:
    """Filter research findings based on persona traits and round.

    Rules:
    - GraphVisible findings are visible in every round.
    - Round 0: Initial visibility findings.
    - Round 1+: Propagation_Only visible to all consumer personas.
    - Restricted only visible to high-search + high-cognition personas.
    """
    visible: List[ResearchFinding] = []
    allow_propagation = round_index >= 1
    allow_restricted = allow_propagation and can_access_deep_graph(persona)

    for finding in findings:
        visibility = finding.visibility
        if visibility == GraphVisibility.GraphVisible:
            visible.append(finding)
            continue
        if visibility == GraphVisibility.Initial:
            visible.append(finding)
            continue
        if visibility == GraphVisibility.Propagation_Only and allow_propagation:
            visible.append(finding)
            continue
        if visibility == GraphVisibility.Restricted and allow_restricted:
            visible.append(finding)

    return visible


def _filter_visible_nodes(
    round_num: int,
    agent_traits: Mapping[str, Any],
    visible_graph_nodes: Iterable[Mapping[str, Any]],
) -> List[Dict[str, Any]]:
    """Local copy of graph-node visibility filtering (mirrors orchestrator logic)."""
    filtered: List[Dict[str, Any]] = []
    allow_propagation = round_num >= 1
    allow_restricted = allow_propagation and can_access_deep_graph(agent_traits)

    for node in visible_graph_nodes:
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

        normalized = {
            "type": str(node_type),
            "text": node_text,
            "visibility": visibility,
        }

        if visibility == GraphVisibility.GraphVisible:
            filtered.append(normalized)
            continue
        if visibility == GraphVisibility.Initial:
            filtered.append(normalized)
            continue
        if visibility == GraphVisibility.Propagation_Only and allow_propagation:
            filtered.append(normalized)
            continue
        if visibility == GraphVisibility.Restricted and allow_restricted:
            filtered.append(normalized)

    return filtered


def build_knowledge_view(
    persona: Mapping[str, Any],
    brief: Mapping[str, Any],
    graph_nodes: Iterable[Mapping[str, Any]],
    findings: Iterable[ResearchFinding],
    round_index: int,
) -> Dict[str, Any]:
    """Build a unified knowledge view for a persona at a given round.

    Returns a dict with visible graph nodes and visible research findings,
    plus metadata about what was filtered out.
    """
    visible_findings = resolve_visible_findings(persona, findings, round_index)
    visible_nodes = _filter_visible_nodes(
        round_num=round_index,
        agent_traits=persona,
        visible_graph_nodes=graph_nodes,
    )

    return {
        "round_index": round_index,
        "visible_nodes": visible_nodes,
        "visible_findings": [f.model_dump() for f in visible_findings],
        "visible_finding_ids": [f.finding_id for f in visible_findings],
        "hidden_count": len(list(findings)) - len(visible_findings),
    }
