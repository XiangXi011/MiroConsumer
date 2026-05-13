from dataclasses import dataclass, field
from enum import Enum
from typing import Any, ClassVar, Dict, Iterable, List, Literal, Mapping, Optional

from pydantic import BaseModel, Field


class ConsumerTaskType(str, Enum):
    ConceptTest = "concept_test"
    CopyFeedback = "copy_feedback"
    PackagingTest = "packaging_test"
    ABTest = "ab_test"
    PriceTest = "price_test"


class GraphVisibility(str, Enum):
    Initial = "Initial"
    GraphVisible = "GraphVisible"
    Propagation_Only = "Propagation_Only"
    Restricted = "Restricted"


class ResearchSourceLane(str, Enum):
    LaneA = "lane_a"
    LaneB = "lane_b"


class ResearchSourceType(str, Enum):
    Upload = "upload"
    Url = "url"
    PublicWeb = "public_web"


class PersonaPackClass(str, Enum):
    Generic = "generic"
    Industry = "industry"
    Category = "category"
    Geography = "geography"
    Custom = "custom"


@dataclass
class PersonaPackSelection:
    """Lightweight persona pack selection carried inside a consumer brief."""

    pack_id: str = "default_persona_pack"
    pack_class: PersonaPackClass = PersonaPackClass.Generic
    custom_upload: bool = False

    def __post_init__(self) -> None:
        if isinstance(self.pack_class, str):
            try:
                self.pack_class = PersonaPackClass(self.pack_class.strip().lower())
            except ValueError:
                self.pack_class = PersonaPackClass.Generic
        if not isinstance(self.pack_class, PersonaPackClass):
            self.pack_class = PersonaPackClass.Generic

    def to_summary(self) -> Dict[str, Any]:
        return {
            "pack_id": self.pack_id,
            "pack_class": self.pack_class.value,
            "custom_upload": self.custom_upload,
        }


class ResearchSource(BaseModel):
    source_id: str
    lane: ResearchSourceLane
    source_type: ResearchSourceType
    label: str
    uri: str = ""
    metadata: Dict[str, Any] = Field(default_factory=dict)
    added_at: str = ""
    trust_tier: int = 1
    # Phase 4A source quality fields
    freshness_score: int = 0
    source_confidence: float = 0.0
    coverage_tags: List[str] = Field(default_factory=list)
    quality_reasons: List[str] = Field(default_factory=list)


class IngestedDocument(BaseModel):
    doc_id: str
    source_id: str
    title: str = ""
    raw_text: str = ""
    word_count: int = 0
    ingested_at: str = ""


class DocumentChunk(BaseModel):
    chunk_id: str
    doc_id: str
    source_id: str
    text: str
    index: int = 0
    char_start: int = 0
    char_end: int = 0
    created_at: str = ""


class RetrievalTrace(BaseModel):
    trace_id: str
    query: str
    lane: ResearchSourceLane
    chunk_ids: List[str] = Field(default_factory=list)
    scores: List[float] = Field(default_factory=list)
    retrieved_at: str = ""


class ResearchFinding(BaseModel):
    finding_id: str
    finding_type: Literal[
        "category_context",
        "competitor_signal",
        "risk_signal",
        "trend_signal",
        "propagation_signal",
    ]
    summary: str
    evidence_snippets: List[str] = Field(default_factory=list)
    source_label: str = "brief_background"
    visibility: GraphVisibility = GraphVisibility.Propagation_Only
    confidence: float = 0.5
    # Provenance fields for Phase 3A
    source_id: str = ""
    snippet_id: str = ""
    retrieval_trace_id: str = ""
    # Phase 4A confidence companion fields
    confidence_label: str = ""
    confidence_reasons: List[str] = Field(default_factory=list)
    support_summary: str = ""


class ResearchSnapshot(BaseModel):
    snapshot_id: str
    project_id: str
    created_at: str
    sources: List[ResearchSource] = Field(default_factory=list)
    documents: List[IngestedDocument] = Field(default_factory=list)
    chunks: List[DocumentChunk] = Field(default_factory=list)
    findings: List[ResearchFinding] = Field(default_factory=list)
    retrieval_traces: List[RetrievalTrace] = Field(default_factory=list)
    summary: str = ""


class PropagationEvent(BaseModel):
    event_id: str
    event_type: Literal[
        "positive_relay",
        "skeptical_challenge",
        "misread_amplification",
        "risk_discovery",
        "clarification_recovery",
    ]
    actor_id: str
    target_ids: List[str] = Field(default_factory=list)
    trigger_finding_ids: List[str] = Field(default_factory=list)
    supporting_quote: str = ""
    round_index: int
    actor_community: str = ""
    actor_role: str = ""
    cross_community: bool = False
    target_communities: List[str] = Field(default_factory=list)

    @property
    def consumer_event_type(self) -> str:
        """Derived consumer ontology value from the legacy event_type."""
        from .event_ontology import map_legacy_event_type_to_consumer

        return map_legacy_event_type_to_consumer(self.event_type)

    def model_dump(self, **kwargs: Any) -> Dict[str, Any]:
        data = super().model_dump(**kwargs)
        data["consumer_event_type"] = self.consumer_event_type
        return data


def _normalize_string_list(value: Any, field_name: str) -> List[str]:
    if value is None:
        return []

    if isinstance(value, str):
        items: Iterable[str] = [value]
    elif isinstance(value, (list, tuple)):
        items = value
    else:
        raise ValueError(f"{field_name} must be a string or list of strings")

    cleaned: List[str] = []
    for item in items:
        if not isinstance(item, str):
            raise ValueError(f"{field_name} must contain only strings")
        text = item.strip()
        if text:
            cleaned.append(text)
    return cleaned


def _normalize_required_text(value: Any, field_name: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"Missing required field: {field_name}")

    text = value.strip()
    if not text:
        raise ValueError(f"Missing required field: {field_name}")
    return text


def _normalize_task_type(value: Any) -> ConsumerTaskType:
    if isinstance(value, ConsumerTaskType):
        return value
    if isinstance(value, str):
        try:
            return ConsumerTaskType(value.strip())
        except ValueError as exc:
            raise ValueError(f"Unsupported task_type: {value}") from exc
    raise ValueError("Missing required field: task_type")


def _normalize_graph_visibility(value: Any) -> GraphVisibility:
    if value is None:
        return GraphVisibility.Initial
    if isinstance(value, GraphVisibility):
        return value
    if isinstance(value, str):
        try:
            return GraphVisibility(value.strip())
        except ValueError as exc:
            raise ValueError(f"Unsupported graph_visibility: {value}") from exc
    raise ValueError("graph_visibility must be a string or GraphVisibility")


def _normalize_research_mode(value: Any) -> str:
    if value is None:
        return "manual_only"
    if isinstance(value, str):
        text = value.strip().lower()
        if text in {"manual_only", "auto_enrich"}:
            return text
    return "manual_only"


def _normalize_enable_lane_b(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"true", "1", "yes"}
    if isinstance(value, (int, float)):
        return bool(value)
    return False


@dataclass
class TestVariant:
    """Structured A/B test variant with rich concept fields."""

    variant_id: str
    label: str
    concept_assets: List[str] = field(default_factory=list)
    copy_material: List[str] = field(default_factory=list)
    claims: List[str] = field(default_factory=list)
    packaging_assets: Optional[List[str]] = None
    price_points: Optional[List[str]] = None

    def to_summary(self) -> Dict[str, Any]:
        result: Dict[str, Any] = {
            "variant_id": self.variant_id,
            "label": self.label,
            "concept_assets": self.concept_assets,
            "copy_material": self.copy_material,
            "claims": self.claims,
        }
        if self.packaging_assets is not None:
            result["packaging_assets"] = self.packaging_assets
        if self.price_points is not None:
            result["price_points"] = self.price_points
        return result


def _normalize_test_variants(value: Any, field_name: str = "test_variants") -> List[TestVariant]:
    """Normalize test_variants from objects or legacy string list."""
    if value is None:
        return []

    if isinstance(value, str):
        # Single string -> single variant with auto-generated id
        return [TestVariant(variant_id="v1", label=value)]

    if isinstance(value, (list, tuple)):
        variants: List[TestVariant] = []
        for idx, item in enumerate(value):
            if isinstance(item, TestVariant):
                variants.append(item)
            elif isinstance(item, str):
                # Legacy string variant -> normalize to TestVariant
                variants.append(TestVariant(variant_id=f"v{idx + 1}", label=item))
            elif isinstance(item, Mapping):
                # Dict-style variant from payload
                vid = str(item.get("variant_id", f"v{idx + 1}")).strip()
                label = str(item.get("label", "")).strip()
                if not label:
                    raise ValueError(f"{field_name} item missing required 'label'")
                variants.append(
                    TestVariant(
                        variant_id=vid,
                        label=label,
                        concept_assets=_normalize_string_list(
                            item.get("concept_assets"), "concept_assets"
                        ),
                        copy_material=_normalize_string_list(
                            item.get("copy_material"), "copy_material"
                        ),
                        claims=_normalize_string_list(item.get("claims"), "claims"),
                        packaging_assets=_normalize_string_list(
                            item.get("packaging_assets"), "packaging_assets"
                        ) or None,
                        price_points=_normalize_string_list(
                            item.get("price_points"), "price_points"
                        ) or None,
                    )
                )
            else:
                raise ValueError(f"{field_name} items must be TestVariant, dict, or str")
        return variants

    raise ValueError(f"{field_name} must be a list of variant objects or strings")


def _normalize_price_context(value: Any) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, str):
        text = value.strip()
        return text if text else None
    return None


def _normalize_retry_budget(value: Any, default: int, field_name: str, upper_bound: int) -> int:
    if value is None:
        return default
    try:
        budget = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field_name} must be an integer") from exc
    if budget < 0 or budget > upper_bound:
        raise ValueError(f"{field_name} must be between 0 and {upper_bound}")
    return budget


def _normalize_persona_pack_selection(value: Any) -> PersonaPackSelection:
    if value is None:
        return PersonaPackSelection()
    if isinstance(value, PersonaPackSelection):
        return value
    if isinstance(value, Mapping):
        pack_id = str(value.get("pack_id", "default_persona_pack")).strip()
        pack_class_raw = str(value.get("pack_class", "generic")).strip().lower()
        try:
            pack_class = PersonaPackClass(pack_class_raw)
        except ValueError:
            pack_class = PersonaPackClass.Generic
        custom_upload = bool(value.get("custom_upload", False))
        return PersonaPackSelection(
            pack_id=pack_id,
            pack_class=pack_class,
            custom_upload=custom_upload,
        )
    return PersonaPackSelection()


@dataclass
class ConsumerBusinessBrief:
    schema_version: str = "1.0.0"
    brief_id: str = ""
    task_type: ConsumerTaskType = ConsumerTaskType.ConceptTest
    product_concept_assets: List[str] = field(default_factory=list)
    copy_material: List[str] = field(default_factory=list)
    claims: List[str] = field(default_factory=list)
    target_audience: List[str] = field(default_factory=list)
    usage_scene: List[str] = field(default_factory=list)
    research_goal: str = ""
    optional_background_materials: List[str] = field(default_factory=list)
    graph_visibility: GraphVisibility = GraphVisibility.Initial
    research_mode: str = "manual_only"
    enable_lane_b: bool = False
    packaging_assets: List[str] = field(default_factory=list)
    variants: List[str] = field(default_factory=list)
    price_points: List[str] = field(default_factory=list)
    test_variants: List[TestVariant] = field(default_factory=list)
    price_context: Optional[str] = None
    persona_pack_selection: PersonaPackSelection = field(default_factory=PersonaPackSelection)
    llm_retry_budget: int = 2
    task_retry_budget: int = 1
    simulation_retry_budget: int = 0
    source_evidence_spans: List[str] = field(default_factory=list)
    risk_flags: List[str] = field(default_factory=list)
    supported_task_types: ClassVar[set[ConsumerTaskType]] = {
        ConsumerTaskType.ConceptTest,
        ConsumerTaskType.CopyFeedback,
        ConsumerTaskType.PackagingTest,
        ConsumerTaskType.ABTest,
        ConsumerTaskType.PriceTest,
    }

    def __post_init__(self) -> None:
        self.task_type = _normalize_task_type(self.task_type)
        if self.task_type not in self.supported_task_types:
            raise ValueError(f"Unsupported task_type: {self.task_type.value}")

        self.product_concept_assets = _normalize_string_list(
            self.product_concept_assets, "product_concept_assets"
        )
        self.packaging_assets = _normalize_string_list(self.packaging_assets, "packaging_assets")
        self.variants = _normalize_string_list(self.variants, "variants")
        self.price_points = _normalize_string_list(self.price_points, "price_points")
        self.test_variants = _normalize_test_variants(self.test_variants, "test_variants")
        self.price_context = _normalize_price_context(self.price_context)

        # Backward compatibility: normalize old-style string variants into test_variants
        if self.variants and not self.test_variants:
            self.test_variants = [
                TestVariant(variant_id=f"v{idx + 1}", label=v) for idx, v in enumerate(self.variants)
            ]

        # Task-specific required field validation
        if self.task_type == ConsumerTaskType.PackagingTest:
            if not self.packaging_assets:
                raise ValueError("Missing required field: packaging_assets")
        elif self.task_type == ConsumerTaskType.ABTest:
            if len(self.test_variants) < 2:
                raise ValueError("ab_test requires at least 2 variants")
        elif self.task_type == ConsumerTaskType.PriceTest:
            if not self.price_points:
                raise ValueError("Missing required field: price_points")
        else:
            # concept_test and copy_feedback require product_concept_assets
            if not self.product_concept_assets:
                raise ValueError("Missing required field: product_concept_assets")

        self.copy_material = _normalize_string_list(self.copy_material, "copy_material")
        self.claims = _normalize_string_list(self.claims, "claims")
        self.target_audience = _normalize_string_list(self.target_audience, "target_audience")
        self.usage_scene = _normalize_string_list(self.usage_scene, "usage_scene")
        self.optional_background_materials = _normalize_string_list(
            self.optional_background_materials, "optional_background_materials"
        )
        self.research_goal = _normalize_required_text(self.research_goal, "research_goal")
        self.graph_visibility = _normalize_graph_visibility(self.graph_visibility)
        self.research_mode = _normalize_research_mode(self.research_mode)
        self.enable_lane_b = _normalize_enable_lane_b(self.enable_lane_b)
        self.persona_pack_selection = _normalize_persona_pack_selection(self.persona_pack_selection)
        self.llm_retry_budget = _normalize_retry_budget(
            self.llm_retry_budget, 2, "llm_retry_budget", 5
        )
        self.task_retry_budget = _normalize_retry_budget(
            self.task_retry_budget, 1, "task_retry_budget", 3
        )
        self.simulation_retry_budget = _normalize_retry_budget(
            self.simulation_retry_budget, 0, "simulation_retry_budget", 2
        )

    def to_summary(self) -> Dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "brief_id": self.brief_id,
            "task_type": self.task_type.value,
            "product_concept_assets": self.product_concept_assets,
            "copy_material": self.copy_material,
            "claims": self.claims,
            "target_audience": self.target_audience,
            "usage_scene": self.usage_scene,
            "research_goal": self.research_goal,
            "optional_background_materials": self.optional_background_materials,
            "graph_visibility": self.graph_visibility.value,
            "research_mode": self.research_mode,
            "enable_lane_b": self.enable_lane_b,
            "packaging_assets": self.packaging_assets,
            "variants": self.variants,
            "price_points": self.price_points,
            "test_variants": [v.to_summary() for v in self.test_variants],
            "price_context": self.price_context,
            "persona_pack_selection": self.persona_pack_selection.to_summary(),
            "llm_retry_budget": self.llm_retry_budget,
            "task_retry_budget": self.task_retry_budget,
            "simulation_retry_budget": self.simulation_retry_budget,
            "source_evidence_spans": self.source_evidence_spans,
            "risk_flags": self.risk_flags,
        }
