"""报告 API 输入校验"""

from pydantic import BaseModel, Field
from typing import Optional, List


class CreateReportRequest(BaseModel):
    simulation_id: str = Field(min_length=1)
    report_type: str = Field(default="full", pattern="^(full|summary|executive)$")
    include_voc: bool = True
    include_evidence: bool = True


class UpdateReportRequest(BaseModel):
    title: Optional[str] = Field(default=None, max_length=500)
    notes: Optional[str] = Field(default=None, max_length=5000)
    status: Optional[str] = Field(default=None, pattern="^(draft|final|archived)$")


class ExportReportRequest(BaseModel):
    format: str = Field(default="json", pattern="^(json|csv|pdf|docx|pptx)$")
    include_methodology: bool = True
    include_raw_data: bool = False


class ListReportsRequest(BaseModel):
    simulation_id: Optional[str] = None
    status: Optional[str] = None
    page: int = Field(default=1, ge=1)
    per_page: int = Field(default=20, ge=1, le=100)
