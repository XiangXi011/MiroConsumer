"""OpenClaw evidence filtering and quality scoring helpers."""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

BLOCKED_SOURCE_DOMAINS = {
    "espn.com": "blocked_domain:sports",
    "formula1.com": "blocked_domain:sports",
    "three.com.hk": "blocked_domain:telecom",
}

BLOCKED_SOURCE_KEYWORDS = {
    "dictionary": "blocked_domain:dictionary",
    "dict": "blocked_domain:dictionary",
    "zidian": "blocked_domain:dictionary",
    "scoreboard": "blocked_domain:sports",
    "grand prix": "blocked_domain:sports",
}

RELEVANCE_KEYWORDS = {
    "brand": ("舒客", "舒客宝贝", "shuke", "saky"),
    "category": ("牙膏", "儿童牙膏", "口腔", "刷牙", "toothpaste", "oral", "dental"),
    "audience": ("儿童", "孩子", "宝宝", "宝贝", "家长", "妈妈", "parent", "parents", "kid", "kids", "child", "children"),
    "claim": ("变色", "魔法变色", "低氟", "含氟", "色素", "泡沫", "安全", "美白", "亮白", "fluoride", "safety"),
}

EXPLORATION_STRATEGIES = {"retry_refined", "broaden_search", "uploaded_only"}

def _safe_top_k(value: Any) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        parsed = 3
    return max(1, min(parsed, 5))


def _safe_float(value: Any, default: float = 0.5) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        parsed = default
    return max(0.0, min(parsed, 1.0))


def _normalize_risk_tags(value: Any) -> List[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if item is not None]


def _normalized_finding_text(*values: Any) -> str:
    return " ".join(
        " ".join(str(value).strip().split())
        for value in values
        if value is not None and str(value).strip()
    ).strip()


def _host_from_url(url: str) -> str:
    try:
        return urlparse(url).netloc.lower().removeprefix("www.")
    except Exception:
        return ""


def _contains_any(text: str, keywords: tuple[str, ...]) -> bool:
    lower_text = text.lower()
    return any(keyword.lower() in lower_text for keyword in keywords)


def _classify_source_type(host: str, text: str, evidence_type: str) -> str:
    lower = f"{host} {text}".lower()
    if any(token in lower for token in ("jd.com", "tmall", "taobao", "amazon", "京东", "天猫", "评价")):
        return "ecommerce"
    if any(token in lower for token in ("gov", "国家标准", "法规", "监管", "标准")):
        return "regulatory"
    if any(token in lower for token in ("xiaohongshu", "小红书", "douyin", "抖音", "weibo", "知乎")):
        return "social"
    if evidence_type == "claim_risk":
        return "claim_risk"
    if evidence_type == "category_safety":
        return "category"
    if evidence_type == "product_fact":
        return "brand_or_product"
    return evidence_type or "external"


def _blocked_reason(host: str, text: str) -> str:
    for domain, reason in BLOCKED_SOURCE_DOMAINS.items():
        if host == domain or host.endswith(f".{domain}"):
            return reason
    lower = text.lower()
    for keyword, reason in BLOCKED_SOURCE_KEYWORDS.items():
        if keyword in lower:
            return reason
    return ""


def _score_result_relevance(
    *,
    user_goal: str,
    query: str,
    title: str,
    url: str,
    snippet: str,
    evidence_type: str,
    confidence: float,
) -> Dict[str, Any]:
    host = _host_from_url(url)
    result_text = _normalized_finding_text(title, snippet, host)
    query_text = _normalized_finding_text(query)
    text = _normalized_finding_text(result_text, query_text)
    blocked = _blocked_reason(host, text)
    if blocked:
        return {
            "accepted": False,
            "score": 0.0,
            "source_type": "rejected",
            "reject_reason": blocked,
        }

    brand_hit = _contains_any(result_text, RELEVANCE_KEYWORDS["brand"])
    category_hit = _contains_any(result_text, RELEVANCE_KEYWORDS["category"])
    audience_hit = _contains_any(result_text, RELEVANCE_KEYWORDS["audience"])
    claim_hit = _contains_any(result_text, RELEVANCE_KEYWORDS["claim"])
    domain_hit = brand_hit or category_hit or _contains_any(
        result_text,
        (
            "变色",
            "魔法变色",
            "低氟",
            "含氟",
            "fluoride",
            "色素",
            "泡沫",
            "防蛀",
        ),
    )

    score = 0.0
    if brand_hit:
        score += 0.3
    if category_hit:
        score += 0.3
    if audience_hit:
        score += 0.15
    if claim_hit:
        score += 0.15
    if domain_hit and not (brand_hit or category_hit):
        score += 0.18

    goal_tokens = [
        token
        for token in re.split(r"[\s,，。；;、/|]+", user_goal)
        if len(token) >= 2
    ]
    result_lower = result_text.lower()
    matched_goal_tokens = sum(1 for token in goal_tokens[:8] if token.lower() in result_lower)
    score += min(0.1, matched_goal_tokens * 0.025)
    score += confidence * 0.05
    score = min(score, 1.0)

    source_type = _classify_source_type(host, text, evidence_type)
    accepted = bool(domain_hit and score >= 0.35)
    return {
        "accepted": accepted,
        "score": round(score, 3),
        "source_type": source_type if accepted else "rejected",
        "reject_reason": "" if accepted else "low_relevance",
    }


def _evidence_quality_summary(
    findings: List[Dict[str, Any]],
    rejected: List[Dict[str, Any]],
    raw_count: int,
    strategy: str = "retry_refined",
) -> Dict[str, Any]:
    relevant_count = len(findings)
    source_types = sorted(
        {
            str(item.get("source_type") or item.get("evidence_type") or "external")
            for item in findings
            if item
        }
    )
    avg_relevance = (
        sum(float(item.get("relevance_score", 0.0) or 0.0) for item in findings)
        / relevant_count
        if relevant_count
        else 0.0
    )

    warnings: List[str] = []
    if relevant_count == 0:
        status = "insufficient"
        gate = "blocked"
        confidence_level = "very_low"
        warnings.append("未检索到足够相关的外部资料，不能静默创建正式项目。")
    elif relevant_count < 3 or len(source_types) < 2:
        status = "partial"
        gate = "review"
        confidence_level = "low"
        warnings.append("外部资料覆盖不足，建议重搜或补充材料后再创建项目。")
    else:
        status = "sufficient"
        gate = "pass"
        confidence_level = "medium"

    if rejected:
        warnings.append(f"已过滤 {len(rejected)} 条低相关或黑名单来源。")

    return {
        "status": status,
        "gate": gate,
        "confidence_level": confidence_level,
        "recoverable": True,
        "exploration_strategy": strategy,
        "raw_count": raw_count,
        "relevant_count": relevant_count,
        "rejected_count": len(rejected),
        "source_type_coverage": source_types,
        "average_relevance": round(avg_relevance, 3),
        "user_visible_warnings": warnings,
    }


def _confirmation_input_summary(payload: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    if not payload:
        return {}

    summary: Dict[str, Any] = {}
    if "approved" in payload:
        summary["approved"] = bool(payload.get("approved"))
    approved_queries = payload.get("approved_queries")
    if isinstance(approved_queries, list):
        summary["approved_query_count"] = len(approved_queries)
    return summary

