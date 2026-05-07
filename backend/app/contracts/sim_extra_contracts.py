"""Simulation API 输入校验 — 补充 schemas

覆盖 simulation.py 中尚无 schema 的 POST 端点。
已有 schema 保留在 simulation_contracts.py 中：
  CreateSimulationRequest, StartSimulationRequest, StopSimulationRequest,
  PrepareSimulationRequest, ExportRequest
"""

from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional


class GetPrepareStatusRequest(BaseModel):
    task_id: Optional[str] = None
    simulation_id: Optional[str] = None


class GenerateProfilesRequest(BaseModel):
    graph_id: str
    entity_types: Optional[List[str]] = None
    use_llm: bool = True
    platform: str = Field(default="reddit", pattern="^(reddit|twitter)$")


class InterviewAgentRequest(BaseModel):
    simulation_id: str
    agent_id: int
    prompt: str = Field(min_length=1)
    platform: Optional[str] = Field(default=None, pattern="^(twitter|reddit)$")
    timeout: int = Field(default=60, ge=1, le=600)


class InterviewItem(BaseModel):
    agent_id: int
    prompt: str = Field(min_length=1)
    platform: Optional[str] = Field(default=None, pattern="^(twitter|reddit)$")


class InterviewBatchRequest(BaseModel):
    simulation_id: str
    interviews: List[InterviewItem]
    platform: Optional[str] = Field(default=None, pattern="^(twitter|reddit)$")
    timeout: int = Field(default=120, ge=1, le=600)


class InterviewAllRequest(BaseModel):
    simulation_id: str
    prompt: str = Field(min_length=1)
    platform: Optional[str] = Field(default=None, pattern="^(twitter|reddit)$")
    timeout: int = Field(default=180, ge=1, le=600)


class InterviewHistoryRequest(BaseModel):
    simulation_id: str
    platform: Optional[str] = None
    agent_id: Optional[int] = None
    limit: int = Field(default=100, ge=1, le=10000)


class EnvStatusRequest(BaseModel):
    simulation_id: str


class CloseEnvRequest(BaseModel):
    simulation_id: str
    timeout: int = Field(default=30, ge=1, le=300)


class SimCreateBranchRequest(BaseModel):
    name: str = ""
    fork_round: Optional[int] = None
    description: str = ""
    parent_branch_id: Optional[str] = None


class SimAddInterventionRequest(BaseModel):
    intervention_type: Optional[str] = None
    payload: Dict[str, Any] = Field(default_factory=dict)
    target_round: Optional[int] = None


class SimResumeBranchRequest(BaseModel):
    max_rounds: Optional[int] = Field(default=None, ge=1, le=1000)
