"""Graph API 输入校验 schemas"""

from pydantic import BaseModel, Field
from typing import Optional


class BuildGraphRequest(BaseModel):
    project_id: str
    graph_name: Optional[str] = None
    chunk_size: Optional[int] = Field(default=None, ge=50, le=5000)
    chunk_overlap: Optional[int] = Field(default=None, ge=0, le=1000)
    force: bool = False
