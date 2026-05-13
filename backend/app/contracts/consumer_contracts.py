"""消费者 API 与应用层合约模型"""

from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional


# ── API 请求合约 ──────────────────────────────────────────

class CreateBriefRequest(BaseModel):
    product_name: str = Field(min_length=1, max_length=200)
    category: str = Field(min_length=1, max_length=100)
    target_audience: Optional[str] = Field(default=None, max_length=500)
    price_point: Optional[float] = Field(default=None, ge=0)
    claims: List[str] = Field(default_factory=list)
    concept_description: Optional[str] = Field(default=None, max_length=2000)
    persona_pack_id: Optional[str] = None


class BusinessBriefRequest(BaseModel):
    """Versioned BusinessBrief API contract with split retry budgets."""

    task_type: str = Field(default="concept_test", description="Consumer test type.")
    product_concept_assets: List[str] = Field(default_factory=list, description="Concept assets or text inputs.")
    copy_material: List[str] = Field(default_factory=list, description="Copy claims to evaluate.")
    target_audience: List[str] = Field(default_factory=list, description="Audience segments.")
    usage_scene: List[str] = Field(default_factory=list, description="Usage contexts.")
    research_goal: str = Field(default="", description="Research question for this run.")
    retry_budget: Optional[int] = Field(
        default=None,
        ge=0,
        description="Deprecated legacy retry budget mapped to llm_retry_budget.",
    )
    llm_retry_budget: int = Field(
        default=2,
        ge=0,
        le=5,
        description="Retry attempts for one LLM call; intended for second-level transient failures.",
    )
    task_retry_budget: int = Field(
        default=1,
        ge=0,
        le=3,
        description="Retry attempts for a background task such as a Celery/RQ job; intended for minute-level failures.",
    )
    simulation_retry_budget: int = Field(
        default=0,
        ge=0,
        le=2,
        description="Retry attempts for the whole simulation workflow; default is zero because it is cost-sensitive.",
    )


class RunInterviewRequest(BaseModel):
    simulation_id: str = Field(min_length=1)
    agent_ids: Optional[List[str]] = None
    questions: Optional[List[str]] = None
    interview_depth: str = Field(default="standard", pattern="^(quick|standard|deep)$")


class RunFocusGroupRequest(BaseModel):
    simulation_id: str = Field(min_length=1)
    topic: str = Field(min_length=1, max_length=500)
    group_size: int = Field(default=6, ge=2, le=20)
    moderator_style: str = Field(default="neutral", pattern="^(neutral|provocative|supportive)$")


class CompareConceptsRequest(BaseModel):
    simulation_id: str = Field(min_length=1)
    concept_a: Dict[str, Any]
    concept_b: Dict[str, Any]
    metrics: Optional[List[str]] = None


class CreateGraphRequest(BaseModel):
    graph_type: str = Field(default="small_world", pattern="^(random|small_world|scale_free|community|influencer_follower|channel_separated|custom)$")
    num_agents: int = Field(default=50, ge=2, le=1000)
    params: Dict[str, Any] = Field(default_factory=dict)


class UpdateGraphRequest(BaseModel):
    add_edges: Optional[List[Dict[str, Any]]] = None
    remove_edges: Optional[List[Dict[str, Any]]] = None
    params: Optional[Dict[str, Any]] = None


class CompareGraphsRequest(BaseModel):
    graph_a_id: str = Field(min_length=1)
    graph_b_id: str = Field(min_length=1)
    metrics: Optional[List[str]] = None


class ImportGraphRequest(BaseModel):
    adjacency_list: Dict[str, List[str]]
    graph_type: str = Field(default="custom")


# ── 应用层合约 ──────────────────────────────────────────

class SourceQualitySummary(BaseModel):
    """来源质量汇总"""
    source_count: int = 0
    lane_a_count: int = 0
    lane_b_count: int = 0
    average_source_confidence: float = 0.0
    average_freshness_score: float = 0.0
    trust_tier_distribution: Dict[str, int] = Field(default_factory=dict)
    coverage_tag_distribution: Dict[str, int] = Field(default_factory=dict)


class FindingConfidenceSummary(BaseModel):
    """单条发现的置信度摘要"""
    finding_id: str = ""
    confidence_label: str = "unknown"
    confidence_score: float = 0.0


class ConfidenceSummary(BaseModel):
    """置信度汇总"""
    confidence_label: str = "unknown"
    confidence_score: float = 0.0
    confidence_reasons: List[str] = Field(default_factory=list)
    support_summary: str = ""
    replay_alignment: str = "not_replayed"
    finding_confidence_summary: List[FindingConfidenceSummary] = Field(default_factory=list)


class ComparisonConfidence(BaseModel):
    """对比置信度"""
    comparison_label: str = "unknown"
    comparison_score: float = 0.0


class ComparisonSide(BaseModel):
    """对比单侧"""
    label: str = ""
    kind: str = ""
    id: str = ""
    confidence: Optional[ConfidenceSummary] = None


class ComparisonSnapshot(BaseModel):
    """对比快照"""
    comparison_id: str = ""
    mode: str = ""
    left: ComparisonSide = Field(default_factory=ComparisonSide)
    right: ComparisonSide = Field(default_factory=ComparisonSide)
    left_confidence: ConfidenceSummary = Field(default_factory=ConfidenceSummary)
    right_confidence: ConfidenceSummary = Field(default_factory=ConfidenceSummary)
    comparison_confidence: Optional[Dict[str, Any]] = None
    metrics: Dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict) -> "ComparisonSnapshot":
        """从原始字典构建，自动补齐缺失的置信度字段。"""
        left_conf = data.get("left_confidence", {})
        right_conf = data.get("right_confidence", {})
        snap = cls(
            comparison_id=data.get("comparison_id", ""),
            mode=data.get("mode", ""),
            left=ComparisonSide(**data.get("left", {})),
            right=ComparisonSide(**data.get("right", {})),
            left_confidence=ConfidenceSummary(**left_conf) if left_conf else ConfidenceSummary(),
            right_confidence=ConfidenceSummary(**right_conf) if right_conf else ConfidenceSummary(),
            comparison_confidence=data.get("comparison_confidence"),
            metrics=data.get("metrics", {}),
        )
        return snap


class BenchmarkReplayResult(BaseModel):
    """Benchmark 回放结果"""
    replay_id: str = ""
    benchmark_id: str = ""
    alignment_status: str = ""
    overall_score: float = 0.0
    expected_signals: Dict[str, Any] = Field(default_factory=dict)
    actual_signals: Dict[str, Any] = Field(default_factory=dict)
    metric_deltas: Dict[str, Any] = Field(default_factory=dict)
    drift_signals: List[Any] = Field(default_factory=list)
    evidence_gatekeeping_summary: Dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict) -> "BenchmarkReplayResult":
        """从原始字典构建。"""
        return cls(
            replay_id=data.get("replay_id", ""),
            benchmark_id=data.get("benchmark_id", ""),
            alignment_status=data.get("alignment_status", ""),
            overall_score=data.get("overall_score", 0.0),
            expected_signals=data.get("expected_signals", {}),
            actual_signals=data.get("actual_signals", {}),
            metric_deltas=data.get("metric_deltas", {}),
            drift_signals=data.get("drift_signals", []),
            evidence_gatekeeping_summary=data.get("evidence_gatekeeping_summary", {}),
        )
