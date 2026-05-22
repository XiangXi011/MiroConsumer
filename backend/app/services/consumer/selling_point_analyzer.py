"""
卖点优先级分析模块
从仿真数据中提取每个 claim 的共鸣度、风险度、误读率、渠道适配度，
输出结构化的卖点决策表供报告使用。
"""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

# ---------------------------------------------------------------------------
# 事件类型常量 (与 ConsumerEventType 对齐但不引入依赖)
# ---------------------------------------------------------------------------
_EVENT_AMPLIFY = "AMPLIFY_CLAIM"
_EVENT_PURCHASE_UP = "PURCHASE_INTENT_UP"
_EVENT_PURCHASE_DOWN = "PURCHASE_INTENT_DOWN"
_EVENT_TRUST_DECAY = "TRUST_DECAY"
_EVENT_NEGATIVE_CASCADE = "NEGATIVE_CASCADE"
_EVENT_PRICE_RESISTANCE = "PRICE_RESISTANCE"
_EVENT_MISREAD = "MISREAD_CLAIM"
_EVENT_ASK_PROOF = "ASK_PROOF"

# 贡献正面共鸣的事件
_POSITIVE_EVENTS = {_EVENT_AMPLIFY, _EVENT_PURCHASE_UP}
# 贡献风险的事件
_RISK_EVENTS = {_EVENT_TRUST_DECAY, _EVENT_NEGATIVE_CASCADE, _EVENT_PRICE_RESISTANCE}

# 信任背书关键词
_TRUST_KEYWORDS = ("SGS", "临床", "认证", "持证", "验证", "检测", "专利", "背书")

# 场景关键词
_SCENE_KEYWORDS = (
    "清新", "口气", "通勤", "约会", "会议",
    "晨间", "睡前", "出差", "旅行", "运动",
)

# 适合场景化表达的渠道
_SCENE_CHANNELS = {"douyin", "livestream"}


# ---------------------------------------------------------------------------
# 数据结构
# ---------------------------------------------------------------------------
class SellingPointRole:
    """卖点角色分类（字符串常量，兼容序列化）。"""

    MAIN_SELLING_POINT = "主卖点"
    SUPPORTING_POINT = "辅助卖点"
    TRUST_BACKER = "信任背书"
    SCENARIO_POINT = "场景卖点"
    RISKY_CLAIM = "高风险卖点"
    NOT_RECOMMENDED = "不建议使用"


@dataclass
class SellingPointAnalysis:
    """单个卖点的分析结果。"""

    claim_text: str  # 原始卖点文案
    role: str  # 建议角色（SellingPointRole 常量）
    resonance_score: float  # 共鸣度 0-1
    risk_score: float  # 风险度 0-1
    misread_rate: float  # 误读率 0-1
    purchase_intent_delta: float  # 购买意向变化 -1 ~ 1
    channel_fit: Dict[str, float]  # 各渠道适配度
    best_channel: str  # 最佳渠道
    worst_channel: str  # 最差渠道
    evidence_demand: float  # 证据需求度 0-1
    representative_quotes: List[str]  # 代表性原声
    risk_quotes: List[str]  # 风险原声
    handling_suggestion: str  # 处理方式建议
    priority_rank: int  # 优先级排名 1=最高

    def to_dict(self) -> Dict[str, Any]:
        """转换为可序列化的字典。"""
        return {
            "claim_text": self.claim_text,
            "role": self.role,
            "resonance_score": round(self.resonance_score, 4),
            "risk_score": round(self.risk_score, 4),
            "misread_rate": round(self.misread_rate, 4),
            "purchase_intent_delta": round(self.purchase_intent_delta, 4),
            "channel_fit": {k: round(v, 4) for k, v in self.channel_fit.items()},
            "best_channel": self.best_channel,
            "worst_channel": self.worst_channel,
            "evidence_demand": round(self.evidence_demand, 4),
            "representative_quotes": self.representative_quotes,
            "risk_quotes": self.risk_quotes,
            "handling_suggestion": self.handling_suggestion,
            "priority_rank": self.priority_rank,
        }


@dataclass
class SellingPointReport:
    """卖点分析报告。"""

    analyses: List[SellingPointAnalysis]  # 按优先级排序的卖点分析
    main_recommendation: str  # 主卖点建议
    trust_backers: List[str]  # 信任背书卖点列表
    scenario_points: List[str]  # 场景卖点列表
    risky_claims: List[str]  # 高风险卖点列表
    not_recommended: List[str]  # 不建议使用的卖点

    def to_dict(self) -> Dict[str, Any]:
        """转换为可序列化的字典。"""
        return {
            "analyses": [a.to_dict() for a in self.analyses],
            "main_recommendation": self.main_recommendation,
            "trust_backers": self.trust_backers,
            "scenario_points": self.scenario_points,
            "risky_claims": self.risky_claims,
            "not_recommended": self.not_recommended,
        }


# ---------------------------------------------------------------------------
# 渠道适配度计算
# ---------------------------------------------------------------------------
def _compute_channel_fit(
    channel_metrics: Dict[str, Dict[str, float]],
    resonance_score: float,
    misread_rate: float,
    evidence_demand: float,
) -> Dict[str, float]:
    """为每个渠道计算综合适配度。

    公式: fit = resonance * 0.4 + (1 - misread_risk) * 0.25
            + (1 - evidence_demand) * 0.2 + fit_score * 0.15

    Args:
        channel_metrics: 渠道指标字典，key=渠道名，value=指标字典。
        resonance_score: 该卖点的整体共鸣度。
        misread_rate: 该卖点的整体误读率。
        evidence_demand: 该卖点的证据需求度。

    Returns:
        渠道名 -> 适配度分数 (0-1) 的映射。
    """
    result: Dict[str, float] = {}
    for channel, metrics in channel_metrics.items():
        ch_resonance = metrics.get("resonance", resonance_score)
        ch_misread = metrics.get("misread_risk", misread_rate)
        ch_evidence = metrics.get("evidence_demand", evidence_demand)
        ch_fit = metrics.get("fit_score", 0.5)
        score = (
            ch_resonance * 0.4
            + (1.0 - ch_misread) * 0.25
            + (1.0 - ch_evidence) * 0.2
            + ch_fit * 0.15
        )
        result[channel] = max(0.0, min(1.0, score))
    return result


# ---------------------------------------------------------------------------
# 角色判定
# ---------------------------------------------------------------------------
_TRUST_KEYWORDS_LOWER = tuple(k.lower() for k in _TRUST_KEYWORDS)
_SCENE_KEYWORDS_LOWER = tuple(k.lower() for k in _SCENE_KEYWORDS)


def _assign_role(
    resonance_score: float,
    risk_score: float,
    misread_rate: float,
    evidence_demand: float,
    claim_text: str,
    best_channel: str,
) -> str:
    """根据指标判定卖点角色。

    优先级从高到低:
    1. NOT_RECOMMENDED  — 风险极高
    2. MAIN_SELLING_POINT — 高共鸣低风险
    3. TRUST_BACKER — 高证据需求或含信任关键词
    4. SCENARIO_POINT — 含场景关键词或最佳渠道为短视频/直播
    5. RISKY_CLAIM — 共鸣尚可但风险偏高
    6. SUPPORTING_POINT — 兜底
    """
    claim_lower = claim_text.lower()

    # 1. 不建议使用：风险远大于收益
    if risk_score >= 0.5 or misread_rate >= 0.4:
        return SellingPointRole.NOT_RECOMMENDED

    # 2. 主卖点：高共鸣、低风险、低误读
    if resonance_score >= 0.5 and risk_score < 0.2 and misread_rate < 0.15:
        return SellingPointRole.MAIN_SELLING_POINT

    # 3. 信任背书：证据需求高或含信任关键词
    if evidence_demand >= 0.4:
        return SellingPointRole.TRUST_BACKER
    if any(kw in claim_lower for kw in _TRUST_KEYWORDS_LOWER):
        return SellingPointRole.TRUST_BACKER

    # 4. 场景卖点：含场景关键词或最佳渠道适配短视频/直播
    if any(kw in claim_lower for kw in _SCENE_KEYWORDS_LOWER):
        return SellingPointRole.SCENARIO_POINT
    if best_channel in _SCENE_CHANNELS:
        return SellingPointRole.SCENARIO_POINT

    # 5. 高风险卖点：有共鸣但风险偏高
    if resonance_score >= 0.3 and (risk_score >= 0.3 or misread_rate >= 0.2):
        return SellingPointRole.RISKY_CLAIM

    # 6. 辅助卖点
    if resonance_score >= 0.3 and risk_score < 0.3:
        return SellingPointRole.SUPPORTING_POINT

    # 默认辅助
    return SellingPointRole.SUPPORTING_POINT


# ---------------------------------------------------------------------------
# 处理建议
# ---------------------------------------------------------------------------
_HANDLING_SUGGESTIONS: Dict[str, str] = {
    SellingPointRole.MAIN_SELLING_POINT: "建议作为核心卖点，可直接用于主标题和首屏",
    SellingPointRole.SUPPORTING_POINT: "建议作为辅助卖点，配合主卖点使用",
    SellingPointRole.TRUST_BACKER: "建议用于增强可信度，配合功效解释",
    SellingPointRole.SCENARIO_POINT: "建议绑定具体使用场景，适合短视频和直播间",
    SellingPointRole.RISKY_CLAIM: "需要加限定语和证据支撑，避免裸表达",
    SellingPointRole.NOT_RECOMMENDED: "风险过高，建议重新措辞或放弃使用",
}


# ---------------------------------------------------------------------------
# 主入口
# ---------------------------------------------------------------------------
def analyze_selling_points(
    claims: List[str],
    events: List[Dict[str, Any]],
    voc_quotes: Dict[str, List[Dict[str, Any]]],
    channel_metrics: Optional[Dict[str, Dict[str, float]]] = None,
    event_counts: Optional[Dict[str, int]] = None,
) -> SellingPointReport:
    """分析卖点并生成结构化决策表。

    Args:
        claims: 业务简报中的卖点列表。
        events: 传播事件列表，每个事件包含 ``event_type``、``claim`` 等字段。
        voc_quotes: 分组后的 VOC 原声，结构为
            ``{"resonance": [...], "risk": [...], "misread": [...]}``，
            每条记录包含 ``quote``、``claim``、``engagement``、``segment``。
        channel_metrics: 各渠道指标字典，key=渠道名，value=指标字典
            （含 ``fit_score``、``resonance``、``misread_risk``、
            ``evidence_demand``、``price_resistance``）。
        event_counts: 全局事件计数字典（可选，当前未直接使用，
            预留给外部聚合场景）。

    Returns:
        :class:`SellingPointReport`，按优先级排序的卖点分析报告。
    """
    if channel_metrics is None:
        channel_metrics = {}

    # 按 claim 聚合事件
    claim_events: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for ev in events:
        claim = ev.get("claim", "")
        if claim:
            claim_events[claim].append(ev)

    # 按 claim 聚合 VOC 原声
    claim_resonance_quotes: Dict[str, List[str]] = defaultdict(list)
    claim_risk_quotes: Dict[str, List[str]] = defaultdict(list)
    claim_misread_quotes: Dict[str, List[str]] = defaultdict(list)

    for entry in voc_quotes.get("resonance", []):
        q = entry.get("quote", "")
        c = entry.get("claim", "")
        if q and c:
            claim_resonance_quotes[c].append(q)

    for entry in voc_quotes.get("risk", []):
        q = entry.get("quote", "")
        c = entry.get("claim", "")
        if q and c:
            claim_risk_quotes[c].append(q)

    for entry in voc_quotes.get("misread", []):
        q = entry.get("quote", "")
        c = entry.get("claim", "")
        if q and c:
            claim_misread_quotes[c].append(q)

    analyses: List[SellingPointAnalysis] = []

    for claim in claims:
        evs = claim_events.get(claim, [])
        total = len(evs)

        # 按事件类型计数
        type_counts: Counter[str] = Counter()
        for ev in evs:
            type_counts[str(ev.get("event_type", ""))] += 1

        # 1. 共鸣度
        positive_count = sum(type_counts[t] for t in _POSITIVE_EVENTS)
        resonance_score = positive_count / total if total > 0 else 0.0

        # 2. 风险度
        risk_count = sum(type_counts[t] for t in _RISK_EVENTS)
        risk_score = risk_count / total if total > 0 else 0.0

        # 3. 误读率
        misread_count = type_counts.get(_EVENT_MISREAD, 0)
        misread_rate = misread_count / total if total > 0 else 0.0

        # 4. 购买意向变化
        pi_up = type_counts.get(_EVENT_PURCHASE_UP, 0)
        pi_down = type_counts.get(_EVENT_PURCHASE_DOWN, 0)
        denom = max(total, 1)
        purchase_intent_delta = max(-1.0, min(1.0, (pi_up - pi_down) / denom))

        # 5. 证据需求度
        ask_proof = type_counts.get(_EVENT_ASK_PROOF, 0)
        evidence_demand = ask_proof / total if total > 0 else 0.0

        # 6. 渠道适配度
        if channel_metrics:
            channel_fit = _compute_channel_fit(
                channel_metrics, resonance_score, misread_rate, evidence_demand,
            )
        else:
            channel_fit = {}

        if channel_fit:
            best_channel = max(channel_fit, key=channel_fit.get)  # type: ignore[arg-type]
            worst_channel = min(channel_fit, key=channel_fit.get)  # type: ignore[arg-type]
        else:
            best_channel = ""
            worst_channel = ""

        # 7. 角色判定
        role = _assign_role(
            resonance_score,
            risk_score,
            misread_rate,
            evidence_demand,
            claim,
            best_channel,
        )

        # 8. 代表性原声（共鸣原声 + 风险原声，各取前 3 条）
        representative = claim_resonance_quotes.get(claim, [])[:3]
        risk_quotes = claim_risk_quotes.get(claim, [])[:3]

        # 9. 处理建议
        handling_suggestion = _HANDLING_SUGGESTIONS.get(role, "")

        analysis = SellingPointAnalysis(
            claim_text=claim,
            role=role,
            resonance_score=resonance_score,
            risk_score=risk_score,
            misread_rate=misread_rate,
            purchase_intent_delta=purchase_intent_delta,
            channel_fit=channel_fit,
            best_channel=best_channel,
            worst_channel=worst_channel,
            evidence_demand=evidence_demand,
            representative_quotes=representative,
            risk_quotes=risk_quotes,
            handling_suggestion=handling_suggestion,
            priority_rank=0,  # 排序后赋值
        )
        analyses.append(analysis)

    # 10. 优先级排序：共鸣 * 0.4 + (1 - 风险) * 0.3 + 购买意向 * 0.3
    analyses.sort(
        key=lambda a: (
            a.resonance_score * 0.4
            + (1.0 - a.risk_score) * 0.3
            + a.purchase_intent_delta * 0.3
        ),
        reverse=True,
    )

    # 赋予排名
    for idx, a in enumerate(analyses, start=1):
        a.priority_rank = idx

    # 11. 汇总分类
    main_candidates = [
        a for a in analyses if a.role == SellingPointRole.MAIN_SELLING_POINT
    ]
    main_recommendation = (
        main_candidates[0].claim_text
        if main_candidates
        else "无明确主卖点，建议组合使用辅助卖点"
    )

    trust_backers = [
        a.claim_text for a in analyses if a.role == SellingPointRole.TRUST_BACKER
    ]
    scenario_points = [
        a.claim_text for a in analyses if a.role == SellingPointRole.SCENARIO_POINT
    ]
    risky_claims = [
        a.claim_text for a in analyses if a.role == SellingPointRole.RISKY_CLAIM
    ]
    not_recommended = [
        a.claim_text for a in analyses if a.role == SellingPointRole.NOT_RECOMMENDED
    ]

    return SellingPointReport(
        analyses=analyses,
        main_recommendation=main_recommendation,
        trust_backers=trust_backers,
        scenario_points=scenario_points,
        risky_claims=risky_claims,
        not_recommended=not_recommended,
    )
