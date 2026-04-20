from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List


class GraphVisibility(str, Enum):
    Initial = "Initial"
    Propagation_Only = "Propagation_Only"
    Restricted = "Restricted"


@dataclass
class ConsumerBusinessBrief:
    task_type: str
    product_concept_assets: List[str]
    copy_material: List[str] = field(default_factory=list)
    claims: List[str] = field(default_factory=list)
    target_audience: List[str] = field(default_factory=list)
    usage_scene: List[str] = field(default_factory=list)
    research_goal: str = ""
    optional_background_materials: List[str] = field(default_factory=list)
    graph_visibility: GraphVisibility = GraphVisibility.Initial

    def to_summary(self) -> Dict[str, Any]:
        return {
            "task_type": self.task_type,
            "product_concept_assets": self.product_concept_assets,
            "copy_material": self.copy_material,
            "claims": self.claims,
            "target_audience": self.target_audience,
            "usage_scene": self.usage_scene,
            "research_goal": self.research_goal,
            "optional_background_materials": self.optional_background_materials,
            "graph_visibility": self.graph_visibility.value,
        }
