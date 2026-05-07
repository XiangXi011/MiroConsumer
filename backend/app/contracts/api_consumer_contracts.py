"""Consumer API 输入校验 schemas"""

from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional


class CreateBranchRequest(BaseModel):
    name: str = ""
    fork_round: Optional[int] = None
    description: str = ""
    parent_branch_id: Optional[str] = None


class AddInterventionRequest(BaseModel):
    intervention_type: Optional[str] = None
    payload: Dict[str, Any] = Field(default_factory=dict)
    target_round: Optional[int] = None


class ResumeBranchRequest(BaseModel):
    max_rounds: Optional[int] = Field(default=None, ge=1, le=1000)


class CreateConsumerComparisonRequest(BaseModel):
    mode: str = Field(pattern="^(run_vs_run|branch_vs_base|project_vs_project)$")
    left_simulation_id: Optional[str] = None
    right_simulation_id: Optional[str] = None
    simulation_id: Optional[str] = None
    branch_id: Optional[str] = None
    left_project_id: Optional[str] = None
    right_project_id: Optional[str] = None


class ExportConsumerResearchAssetRequest(BaseModel):
    project_id: str
    simulation_id: str
    branch_id: Optional[str] = None
    name: Optional[str] = None


class RunResearchActionRequest(BaseModel):
    """Generic payload for consumer research actions; extra fields allowed."""
    action_type: Optional[str] = None

    class Config:
        extra = "allow"


class RunInterviewRequest(BaseModel):
    """Consumer interview request."""
    agent_id: Optional[str] = None
    question: Optional[str] = None
    prompt: Optional[str] = None

    class Config:
        extra = "allow"


class RunFocusGroupRequest(BaseModel):
    """Consumer focus group request."""
    topic: Optional[str] = None
    agent_ids: Optional[List[str]] = None

    class Config:
        extra = "allow"


class RunEstimateRequest(BaseModel):
    """Run cost estimate request."""
    simulation_id: Optional[str] = None

    class Config:
        extra = "allow"
