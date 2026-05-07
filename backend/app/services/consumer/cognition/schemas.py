"""认知引擎输出 Pydantic Schema"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict


class PerceptionOutput(BaseModel):
    perceived_benefits: List[str] = Field(default_factory=list)
    perceived_risks: List[str] = Field(default_factory=list)
    confusion_points: List[str] = Field(default_factory=list)
    trust_signals: List[str] = Field(default_factory=list)
    relevance_score: float = Field(ge=0, le=1, default=0.5)
    emotional_reaction: str = "neutral"


class DecisionOutput(BaseModel):
    choice: str  # accept/reject/hesitate/share/challenge/ignore
    reason_codes: List[str] = Field(default_factory=list)
    confidence: float = Field(ge=0, le=1, default=0.5)
    purchase_intent_score: float = Field(ge=0, le=1, default=0.5)
    credibility_score: float = Field(ge=0, le=1, default=0.5)
    risk_level: str = "medium"


class ExpressionOutput(BaseModel):
    quote: str = ""
    paraphrase: str = ""
    sentiment: str = "neutral"
    channel: str = "general"
    generated_by: str = "llm"  # llm / fallback / template
    misread_variant: Optional[str] = None  # 误解变体
    first_person_voice: str = ""  # 第一人称表述
    channel_style: str = "neutral"  # 渠道风格


class CognitionResult(BaseModel):
    agent_id: str
    round_id: int
    perception: PerceptionOutput
    decision: DecisionOutput
    expression: ExpressionOutput
    reasoning_trace: Dict = Field(default_factory=dict)
    dimension_scores: Dict[str, float] = Field(default_factory=dict)
    persona_id: Optional[str] = None
    input_span: Optional[str] = None  # 输入来源标识
    memory_state: Optional[Dict] = None  # 记忆状态快照
