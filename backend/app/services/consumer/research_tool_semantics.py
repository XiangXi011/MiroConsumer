"""Consumer research tool semantic labels and purposes for Phase 6F."""

from __future__ import annotations

from typing import Dict

CONSUMER_TOOL_SEMANTICS: Dict[str, Dict[str, str]] = {
    "insight_forge": {
        "zh": "消费者洞察深挖",
        "en": "Consumer Insight Deep Dive",
        "purpose": "Explains the reasons behind conclusion formation by decomposing questions and performing multi-dimensional retrieval of consumer facts and relationships.",
    },
    "panorama_search": {
        "zh": "传播路径解释器",
        "en": "Propagation Path Explainer",
        "purpose": "Explains information diffusion paths, blocking points, misreading amplification, and trust-repair trajectories across the consumer network.",
    },
    "quick_search": {
        "zh": "报告结论证据校验",
        "en": "Evidence Verifier",
        "purpose": "Validates whether available evidence supports report conclusions by performing lightweight verification of specific consumer claims or evidence snippets.",
    },
    "interview_agents": {
        "zh": "虚拟消费者深访",
        "en": "Virtual Consumer Interview",
        "purpose": "Provides Phase 6I interview execution capability for first-person perspectives from simulated consumer agents.",
    },
    "get_all_nodes": {
        "zh": "消费者认知图谱节点",
        "en": "Consumer Cognition Graph Nodes",
        "purpose": "",
    },
    "get_all_edges": {
        "zh": "消费者认知图谱关系",
        "en": "Consumer Cognition Graph Edges",
        "purpose": "",
    },
}


def get_consumer_tool_label(tool_name: str, locale: str = "zh") -> str:
    """Return a human-readable label for a consumer research tool.

    Unknown tools return the raw tool name without raising.
    """
    entry = CONSUMER_TOOL_SEMANTICS.get(tool_name)
    if entry is None:
        return str(tool_name)
    label = entry.get(locale)
    if label is None:
        label = entry.get("en", str(tool_name))
    return label


def get_consumer_tool_purpose(tool_name: str) -> str:
    """Return the purpose description for a consumer research tool.

    Unknown tools return an empty string.
    """
    entry = CONSUMER_TOOL_SEMANTICS.get(tool_name)
    if entry is None:
        return ""
    return entry.get("purpose", "")


__all__ = [
    "CONSUMER_TOOL_SEMANTICS",
    "get_consumer_tool_label",
    "get_consumer_tool_purpose",
]
