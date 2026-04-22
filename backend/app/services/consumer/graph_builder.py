"""Phase 1 consumer graph builder."""

from __future__ import annotations

import re
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Mapping, Optional

from .models import ConsumerBusinessBrief, ConsumerTaskType, GraphVisibility, ResearchFinding
from .persona_pack import load_default_persona_pack, map_persona_to_agent_traits


class ConsumerGraphBuilder:
    """Build a repo-local graph payload for consumer_test projects."""

    def build(
        self,
        brief: ConsumerBusinessBrief,
        background_text: Optional[str] = None,
        persona_pack: Optional[Iterable[Mapping[str, Any]]] = None,
        graph_id: Optional[str] = None,
        research_findings: Optional[List[ResearchFinding]] = None,
    ) -> Dict[str, Any]:
        created_at = datetime.now(timezone.utc).isoformat()
        graph_id = graph_id or f"consumer_{uuid.uuid4().hex[:12]}"
        personas = list(persona_pack) if persona_pack is not None else load_default_persona_pack()

        nodes: List[Dict[str, Any]] = []
        edges: List[Dict[str, Any]] = []
        node_index: Dict[tuple[str, str], str] = {}

        brief_node_id = self._add_node(
            nodes,
            node_index,
            label="ConsumerBrief",
            name=brief.research_goal,
            summary="Consumer-facing brief used to seed the simulation graph.",
            visibility=GraphVisibility.Initial,
            attributes={
                "task_type": brief.task_type.value,
                "source": "consumer_brief",
                "round0_visible": True,
            },
            created_at=created_at,
        )

        self._add_items(
            nodes=nodes,
            edges=edges,
            node_index=node_index,
            root_node_id=brief_node_id,
            items=brief.product_concept_assets,
            label="ProductConcept",
            edge_type="HAS_PRODUCT_CONCEPT",
            summary_prefix="Consumer-facing concept asset",
            visibility=GraphVisibility.Initial,
            created_at=created_at,
            extra_attributes={"source": "consumer_brief", "round0_visible": True},
        )
        self._add_items(
            nodes=nodes,
            edges=edges,
            node_index=node_index,
            root_node_id=brief_node_id,
            items=brief.copy_material,
            label="CopyPoint",
            edge_type="HAS_COPY_POINT",
            summary_prefix="Direct copy or messaging point from the brief",
            visibility=GraphVisibility.Initial,
            created_at=created_at,
            extra_attributes={"source": "consumer_brief", "round0_visible": True},
        )
        self._add_items(
            nodes=nodes,
            edges=edges,
            node_index=node_index,
            root_node_id=brief_node_id,
            items=brief.claims,
            label="Claim",
            edge_type="HAS_CLAIM",
            summary_prefix="Claim directly presented in the brief",
            visibility=GraphVisibility.Initial,
            created_at=created_at,
            extra_attributes={"source": "consumer_brief", "round0_visible": True},
        )
        self._add_items(
            nodes=nodes,
            edges=edges,
            node_index=node_index,
            root_node_id=brief_node_id,
            items=brief.usage_scene,
            label="SceneFact",
            edge_type="HAS_SCENE_FACT",
            summary_prefix="Basic usage or scene fact shown in round 0",
            visibility=GraphVisibility.Initial,
            created_at=created_at,
            extra_attributes={"source": "consumer_brief", "round0_visible": True},
        )
        self._add_items(
            nodes=nodes,
            edges=edges,
            node_index=node_index,
            root_node_id=brief_node_id,
            items=brief.target_audience,
            label="AudienceSegment",
            edge_type="TARGETS_AUDIENCE",
            summary_prefix="Explicit target audience named in the brief",
            visibility=GraphVisibility.Initial,
            created_at=created_at,
            extra_attributes={"source": "consumer_brief", "round0_visible": True},
        )

        if brief.task_type == ConsumerTaskType.PackagingTest:
            self._add_items(
                nodes=nodes,
                edges=edges,
                node_index=node_index,
                root_node_id=brief_node_id,
                items=brief.packaging_assets,
                label="PackagingCue",
                edge_type="HAS_PACKAGING_CUE",
                summary_prefix="Packaging asset shown in round 0",
                visibility=GraphVisibility.Initial,
                created_at=created_at,
                extra_attributes={"source": "consumer_brief", "round0_visible": True},
            )
        elif brief.task_type == ConsumerTaskType.ABTest:
            variant_labels = [v.label for v in brief.test_variants]
            self._add_items(
                nodes=nodes,
                edges=edges,
                node_index=node_index,
                root_node_id=brief_node_id,
                items=variant_labels,
                label="Variant",
                edge_type="HAS_VARIANT",
                summary_prefix="A/B variant shown in round 0",
                visibility=GraphVisibility.Initial,
                created_at=created_at,
                extra_attributes={"source": "consumer_brief", "round0_visible": True},
            )
        elif brief.task_type == ConsumerTaskType.PriceTest:
            self._add_items(
                nodes=nodes,
                edges=edges,
                node_index=node_index,
                root_node_id=brief_node_id,
                items=brief.price_points,
                label="PricePoint",
                edge_type="HAS_PRICE_POINT",
                summary_prefix="Price point shown in round 0",
                visibility=GraphVisibility.Initial,
                created_at=created_at,
                extra_attributes={"source": "consumer_brief", "round0_visible": True},
            )

        self._add_persona_segments(
            nodes=nodes,
            edges=edges,
            node_index=node_index,
            root_node_id=brief_node_id,
            personas=personas,
            created_at=created_at,
        )
        self._add_secondary_topics(
            nodes=nodes,
            edges=edges,
            node_index=node_index,
            root_node_id=brief_node_id,
            brief=brief,
            created_at=created_at,
        )
        self._add_background_risks(
            nodes=nodes,
            edges=edges,
            node_index=node_index,
            root_node_id=brief_node_id,
            background_text=background_text,
            brief=brief,
            created_at=created_at,
        )
        self._add_research_findings(
            nodes=nodes,
            edges=edges,
            node_index=node_index,
            root_node_id=brief_node_id,
            research_findings=research_findings or [],
            created_at=created_at,
        )

        return {
            "graph_id": graph_id,
            "graph_type": "consumer_test",
            "nodes": nodes,
            "edges": edges,
            "node_count": len(nodes),
            "edge_count": len(edges),
            "metadata": {
                "visibility_levels": [visibility.value for visibility in GraphVisibility],
                "task_type": brief.task_type.value,
            },
        }

    def _add_persona_segments(
        self,
        nodes: List[Dict[str, Any]],
        edges: List[Dict[str, Any]],
        node_index: Dict[tuple[str, str], str],
        root_node_id: str,
        personas: Iterable[Mapping[str, Any]],
        created_at: str,
    ) -> None:
        for persona in personas:
            agent_traits = map_persona_to_agent_traits(persona)
            label = agent_traits["label"]

            persona_id = self._add_node(
                nodes,
                node_index,
                label="AudienceSegment",
                name=label,
                summary="Default persona segment used to anchor downstream simulation cohorts.",
                visibility=GraphVisibility.Propagation_Only,
                attributes={
                    "persona_id": agent_traits["persona_id"],
                    "attention_drivers": list(agent_traits.get("attention_drivers", [])),
                    "risk_sensitivities": list(agent_traits.get("risk_sensitivities", [])),
                    "source": "default_persona_pack",
                    "round0_visible": False,
                },
                created_at=created_at,
            )
            self._add_edge(
                edges,
                root_node_id,
                persona_id,
                fact_type="MAY_RESONATE_WITH",
                fact=f"Persona cohort likely to discuss or react to {label}.",
                visibility=GraphVisibility.Propagation_Only,
                created_at=created_at,
                attributes={"source": "default_persona_pack"},
            )

    def _add_secondary_topics(
        self,
        nodes: List[Dict[str, Any]],
        edges: List[Dict[str, Any]],
        node_index: Dict[tuple[str, str], str],
        root_node_id: str,
        brief: ConsumerBusinessBrief,
        created_at: str,
    ) -> None:
        seen_topics = set()
        seed_texts = [*brief.copy_material, *brief.claims]
        if brief.task_type == ConsumerTaskType.PackagingTest:
            seed_texts.extend(brief.packaging_assets)
        elif brief.task_type == ConsumerTaskType.ABTest:
            seed_texts.extend(v.label for v in brief.test_variants)
        elif brief.task_type == ConsumerTaskType.PriceTest:
            seed_texts.extend(brief.price_points)
        for text in seed_texts:
            cleaned = text.strip()
            if not cleaned:
                continue
            topic = f"Word-of-mouth: {cleaned}"
            if topic in seen_topics:
                continue
            seen_topics.add(topic)
            topic_id = self._add_node(
                nodes,
                node_index,
                label="TalkingPoint",
                name=topic,
                summary="Likely spread topic derived from direct concept or copy inputs.",
                visibility=GraphVisibility.Propagation_Only,
                attributes={"source": "consumer_brief", "round0_visible": False},
                created_at=created_at,
            )
            self._add_edge(
                edges,
                root_node_id,
                topic_id,
                fact_type="MAY_PROPAGATE_AS",
                fact=f"Consumers may repeat this message beyond the initial brief: {cleaned}",
                visibility=GraphVisibility.Propagation_Only,
                created_at=created_at,
                attributes={"source": "consumer_brief"},
            )

    def _add_background_risks(
        self,
        nodes: List[Dict[str, Any]],
        edges: List[Dict[str, Any]],
        node_index: Dict[tuple[str, str], str],
        root_node_id: str,
        background_text: Optional[str],
        brief: ConsumerBusinessBrief,
        created_at: str,
    ) -> None:
        sources = list(brief.optional_background_materials)
        if background_text:
            sources.append(background_text)

        seen_risks = set()
        for source in sources:
            for sentence in self._split_sentences(source):
                visibility = self._classify_risk_visibility(sentence)
                if visibility is None:
                    continue
                risk_key = sentence.casefold()
                if risk_key in seen_risks:
                    continue
                seen_risks.add(risk_key)
                risk_id = self._add_node(
                    nodes,
                    node_index,
                    label="RiskPoint",
                    name=sentence,
                    summary="Background risk or controversy that should not be surfaced as an initial brief fact.",
                    visibility=visibility,
                    attributes={
                        "source": "background_material",
                        "round0_visible": False,
                        "risk_depth": "restricted" if visibility == GraphVisibility.Restricted else "spread",
                    },
                    created_at=created_at,
                )
                self._add_edge(
                    edges,
                    root_node_id,
                    risk_id,
                    fact_type="HAS_RISK_CONTEXT",
                    fact=sentence,
                    visibility=visibility,
                    created_at=created_at,
                    attributes={"source": "background_material"},
                )

    def _add_research_findings(
        self,
        nodes: List[Dict[str, Any]],
        edges: List[Dict[str, Any]],
        node_index: Dict[tuple[str, str], str],
        root_node_id: str,
        research_findings: List[ResearchFinding],
        created_at: str,
    ) -> None:
        for finding in research_findings:
            finding_id = self._add_node(
                nodes,
                node_index,
                label="ResearchFinding",
                name=finding.summary,
                summary=f"[{finding.finding_type}] {finding.summary}",
                visibility=finding.visibility,
                attributes={
                    "source": "research_finding",
                    "round0_visible": finding.visibility == GraphVisibility.Initial,
                    "provenance": {
                        "finding_id": finding.finding_id,
                        "finding_type": finding.finding_type,
                        "source_label": finding.source_label,
                        "confidence": finding.confidence,
                    },
                    "evidence_snippets": list(finding.evidence_snippets),
                },
                created_at=created_at,
            )
            self._add_edge(
                edges,
                root_node_id,
                finding_id,
                fact_type="HAS_RESEARCH_FINDING",
                fact=finding.summary,
                visibility=finding.visibility,
                created_at=created_at,
                attributes={
                    "source": "research_finding",
                    "provenance": {
                        "finding_id": finding.finding_id,
                        "finding_type": finding.finding_type,
                        "source_label": finding.source_label,
                    },
                },
            )

    def _add_items(
        self,
        nodes: List[Dict[str, Any]],
        edges: List[Dict[str, Any]],
        node_index: Dict[tuple[str, str], str],
        root_node_id: str,
        items: Iterable[str],
        label: str,
        edge_type: str,
        summary_prefix: str,
        visibility: GraphVisibility,
        created_at: str,
        extra_attributes: Optional[Dict[str, Any]] = None,
    ) -> None:
        for item in items:
            text = item.strip()
            if not text:
                continue
            node_id = self._add_node(
                nodes,
                node_index,
                label=label,
                name=text,
                summary=f"{summary_prefix}: {text}",
                visibility=visibility,
                attributes=extra_attributes or {},
                created_at=created_at,
            )
            self._add_edge(
                edges,
                root_node_id,
                node_id,
                fact_type=edge_type,
                fact=text,
                visibility=visibility,
                created_at=created_at,
                attributes=extra_attributes or {},
            )

    def _add_node(
        self,
        nodes: List[Dict[str, Any]],
        node_index: Dict[tuple[str, str], str],
        label: str,
        name: str,
        summary: str,
        visibility: GraphVisibility,
        attributes: Optional[Dict[str, Any]],
        created_at: str,
    ) -> str:
        key = (label, name.strip().casefold())
        if key in node_index:
            return node_index[key]

        node_id = f"node_{uuid.uuid4().hex[:12]}"
        node_attributes = dict(attributes or {})
        node_attributes["visibility"] = visibility.value
        node = {
            "uuid": node_id,
            "name": name.strip(),
            "labels": ["Entity", label],
            "summary": summary,
            "attributes": node_attributes,
            "visibility": visibility.value,
            "created_at": created_at,
        }
        nodes.append(node)
        node_index[key] = node_id
        return node_id

    def _add_edge(
        self,
        edges: List[Dict[str, Any]],
        source_node_uuid: str,
        target_node_uuid: str,
        fact_type: str,
        fact: str,
        visibility: GraphVisibility,
        created_at: str,
        attributes: Optional[Dict[str, Any]] = None,
    ) -> None:
        edge_attributes = dict(attributes or {})
        edge_attributes["visibility"] = visibility.value
        edges.append(
            {
                "uuid": f"edge_{uuid.uuid4().hex[:12]}",
                "name": fact_type,
                "fact": fact,
                "fact_type": fact_type,
                "source_node_uuid": source_node_uuid,
                "target_node_uuid": target_node_uuid,
                "attributes": edge_attributes,
                "visibility": visibility.value,
                "created_at": created_at,
                "episodes": [],
            }
        )

    def _split_sentences(self, text: str) -> List[str]:
        chunks = re.split(r"[\n\r.!?;]+", text)
        return [chunk.strip() for chunk in chunks if chunk and chunk.strip()]

    def _classify_risk_visibility(self, text: str) -> Optional[GraphVisibility]:
        lowered = text.casefold()

        restricted_markers = (
            "controvers",
            "technical",
            "manufactur",
            "defect",
            "contamination",
            "safety",
            "lawsuit",
            "recall",
            "privacy",
            "regulator",
            "competitor",
            "negative",
            "risk",
        )
        propagation_markers = (
            "spread",
            "rumor",
            "buzz",
            "creator",
            "group chat",
            "word of mouth",
            "talking point",
            "repeat",
            "discuss",
        )

        if any(marker in lowered for marker in restricted_markers):
            return GraphVisibility.Restricted
        if any(marker in lowered for marker in propagation_markers):
            return GraphVisibility.Propagation_Only
        return None
