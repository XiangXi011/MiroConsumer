"""仿真 API 输入校验"""

from pydantic import BaseModel, Field
from typing import Optional


class CreateSimulationRequest(BaseModel):
    project_id: str
    name: Optional[str] = Field(default=None, min_length=1, max_length=200)
    mode: str = Field(default="quick", pattern="^(quick|research|enterprise)$")
    max_agents: int = Field(default=10, ge=1, le=1000)
    max_rounds: int = Field(default=5, ge=1, le=100)
    random_seed: Optional[int] = None
    hypothesis: Optional[str] = None
    graph_type: str = Field(default="small_world", pattern="^(random|small_world|scale_free|community|custom)$")


class ExportRequest(BaseModel):
    format: str = Field(default="json", pattern="^(json|csv|manifest)$")


class PrepareSimulationRequest(BaseModel):
    simulation_id: str
    entity_types: Optional[list[str]] = None
    use_llm_for_profiles: bool = True
    parallel_profile_count: int = Field(default=5, ge=1, le=20)
    force_regenerate: bool = False


class StartSimulationRequest(BaseModel):
    simulation_id: str
    platform: str = Field(default="parallel", pattern="^(twitter|reddit|parallel)$")
    max_rounds: Optional[int] = Field(default=None, ge=1, le=1000)
    enable_graph_memory_update: bool = False
    force: bool = False
    dry_run: bool = False


class StopSimulationRequest(BaseModel):
    simulation_id: str
