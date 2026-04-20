from dataclasses import dataclass, field
from enum import Enum
from typing import Any, ClassVar, Dict, Iterable, List


class ConsumerTaskType(str, Enum):
    ConceptTest = "concept_test"
    CopyFeedback = "copy_feedback"


class GraphVisibility(str, Enum):
    Initial = "Initial"
    Propagation_Only = "Propagation_Only"
    Restricted = "Restricted"


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


@dataclass
class ConsumerBusinessBrief:
    task_type: ConsumerTaskType
    product_concept_assets: List[str]
    copy_material: List[str] = field(default_factory=list)
    claims: List[str] = field(default_factory=list)
    target_audience: List[str] = field(default_factory=list)
    usage_scene: List[str] = field(default_factory=list)
    research_goal: str = ""
    optional_background_materials: List[str] = field(default_factory=list)
    graph_visibility: GraphVisibility = GraphVisibility.Initial
    supported_task_types: ClassVar[set[ConsumerTaskType]] = {
        ConsumerTaskType.ConceptTest,
        ConsumerTaskType.CopyFeedback,
    }

    def __post_init__(self) -> None:
        self.task_type = _normalize_task_type(self.task_type)
        if self.task_type not in self.supported_task_types:
            raise ValueError(f"Unsupported task_type: {self.task_type.value}")

        self.product_concept_assets = _normalize_string_list(
            self.product_concept_assets, "product_concept_assets"
        )
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

    def to_summary(self) -> Dict[str, Any]:
        return {
            "task_type": self.task_type.value,
            "product_concept_assets": self.product_concept_assets,
            "copy_material": self.copy_material,
            "claims": self.claims,
            "target_audience": self.target_audience,
            "usage_scene": self.usage_scene,
            "research_goal": self.research_goal,
            "optional_background_materials": self.optional_background_materials,
            "graph_visibility": self.graph_visibility.value,
        }
