"""Pydantic contracts for consumer report outputs."""

from __future__ import annotations

from typing import Any, Dict, Literal

from pydantic import BaseModel, Field


class ConsumerOutputContract(BaseModel):
    """Minimum compliance envelope required for consumer report responses."""

    report_id: str
    simulation_id: str
    status: str = ""
    methodology_limits: Dict[str, Any] = Field(default_factory=dict)
    methodology_page: str = Field(min_length=1)
    disclaimer: str = Field(min_length=1)
    output_type: Literal["json", "markdown", "pdf", "word"] = "json"


__all__ = ["ConsumerOutputContract"]
