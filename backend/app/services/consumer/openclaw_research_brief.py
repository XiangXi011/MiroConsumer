"""President Lobster research planning and brief synthesis helpers."""

from __future__ import annotations

import re
from typing import Any, Dict, Iterable, List


RESEARCH_ANGLES = [
    ("product_fact", "产品事实、官方卖点和成分信息"),
    ("category_safety", "品类安全、儿童适用和口腔护理背景"),
    ("claim_risk", "功效宣称、安全误读和传播风险"),
    ("ecommerce_reviews", "电商评价、使用反馈和价格语境"),
    ("parent_objections", "家长顾虑、反对意见和决策阻力"),
    ("regulatory", "法规标准、儿童牙膏含氟和合规边界"),
]

_CHILD_TERMS = ("儿童", "孩子", "宝宝", "宝贝", "家长", "妈妈", "宝妈", "parent", "kid", "child")
_TOOTHPASTE_TERMS = ("牙膏", "口腔", "刷牙", "toothpaste", "oral", "dental")
_KNOWN_CLAIM_TERMS = (
    "魔法变色",
    "变色",
    "低氟",
    "含氟",
    "无氟",
    "色素",
    "泡沫",
    "草莓",
    "薄荷",
    "温和",
    "美白",
    "亮白",
    "以紫修黄",
    "冷光修白",
    "2分钟",
    "两分钟",
)


def _clean_text(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def _dedupe_terms(values: Iterable[str]) -> List[str]:
    seen = set()
    output: List[str] = []
    for value in values:
        text = _clean_text(value)
        if not text:
            continue
        key = text.lower()
        if key in seen:
            continue
        seen.add(key)
        output.append(text)
    return output


def _goal_keywords(goal: str) -> Dict[str, Any]:
    lower_goal = goal.lower()
    has_toothpaste = any(term.lower() in lower_goal for term in _TOOTHPASTE_TERMS)
    has_child_context = any(term.lower() in lower_goal for term in _CHILD_TERMS)
    claims = [term for term in _KNOWN_CLAIM_TERMS if term.lower() in lower_goal]

    brand_terms: List[str] = []
    if "舒客宝贝" in goal:
        brand_terms.append("舒客宝贝")
    elif "舒客" in goal:
        brand_terms.append("舒客")
    if re.search(r"\bshuke\b|\bsaky\b", lower_goal):
        brand_terms.append("Shuke")

    category = "儿童牙膏" if has_toothpaste and has_child_context else ""
    if not category and has_toothpaste:
        category = "牙膏"
    if not category and re.search(r"\btoothpaste\b", lower_goal):
        category = "kids toothpaste" if has_child_context else "toothpaste"

    product_terms = list(brand_terms)
    if "舒客宝贝" in goal and "魔法变色" in goal and "牙膏" in goal:
        product_terms.insert(0, "舒客宝贝魔法变色牙膏")
    elif brand_terms and claims and category:
        product_terms.insert(0, f"{brand_terms[0]}{claims[0]}{category}")
    elif brand_terms and category:
        product_terms.insert(0, f"{brand_terms[0]}{category}")
    elif category:
        product_terms.append(category)

    fallback_words = re.findall(r"[A-Za-z][A-Za-z0-9-]{2,}", goal)
    fallback_terms = [
        word
        for word in fallback_words
        if word.lower()
        not in {
            "the",
            "and",
            "for",
            "with",
            "openclaw",
            "research",
            "consumer",
            "evaluate",
        }
    ][:4]

    return {
        "product": _dedupe_terms(product_terms or fallback_terms or [goal[:32]]),
        "brand": _dedupe_terms(brand_terms),
        "category": category or "category",
        "claims": _dedupe_terms(claims),
        "audience": "家长 儿童" if has_child_context else "目标消费者",
    }


def _join_query_terms(*groups: Any) -> str:
    terms: List[str] = []
    for group in groups:
        if isinstance(group, (list, tuple)):
            terms.extend(str(item) for item in group)
        else:
            terms.append(str(group))
    return " ".join(_dedupe_terms(terms))


def build_exploration_plan(user_goal: str, query_budget: int = 6) -> List[Dict[str, Any]]:
    goal = _clean_text(user_goal)
    if not goal:
        raise ValueError("user_goal is required")
    terms = _goal_keywords(goal)
    product = terms["product"]
    category = terms["category"]
    claims = terms["claims"]
    audience = terms["audience"]
    primary_claim = claims[:2] or ["核心卖点"]

    query_specs = [
        (
            "product_fact",
            _join_query_terms(product[:2], category, "产品 成分 卖点"),
            "核对产品事实、官方信息和基础卖点，避免把用户任务原文当作唯一资料。",
        ),
        (
            "category_safety",
            _join_query_terms(category, "儿童口腔护理 低氟 含氟 安全", audience),
            "补齐品类安全、儿童适用和家长基础顾虑。",
        ),
        (
            "claim_risk",
            _join_query_terms(primary_claim, category, "色素 安全 误读 质疑"),
            "检查变色、低氟、功效等 claim 是否可能被误解或需要证据。",
        ),
        (
            "ecommerce_reviews",
            _join_query_terms(product[:2], category, "评价 京东 天猫 小红书 价格"),
            "寻找真实购买语境、评价语言和价格敏感点。",
        ),
        (
            "parent_objections",
            _join_query_terms(category, audience, "不爱刷牙 顾虑 反对意见 接受度"),
            "提取目标人群的反对意见、决策阻力和真实表达。",
        ),
        (
            "regulatory",
            _join_query_terms(category, "国家标准 儿童牙膏 含氟 法规 合规"),
            "识别儿童牙膏、含氟和安全表达的合规边界。",
        ),
    ]
    queries = [
        {
            "query": query,
            "evidence_type": evidence_type,
            "reason": reason,
            "max_results": 3,
        }
        for evidence_type, query, reason in query_specs[: max(1, query_budget)]
    ]
    return queries[:query_budget]


def build_research_brief(
    *,
    user_goal: str,
    external_findings: Iterable[Dict[str, Any]],
) -> Dict[str, Any]:
    findings = list(external_findings)
    source_lines = []
    risk_tags = set()
    for item in findings:
        evidence_type = _clean_text(item.get("evidence_type")) or "category_context"
        if evidence_type in {"claim_risk", "regulatory"}:
            risk_tags.add(evidence_type)
        source_lines.append(
            {
                "title": _clean_text(item.get("title")) or "Untitled source",
                "url": _clean_text(item.get("url")),
                "snippet": _clean_text(item.get("snippet")),
                "evidence_type": evidence_type,
                "confidence": float(item.get("confidence", 0.5) or 0.5),
                "query": _clean_text(item.get("query")),
                "retrieved_at": _clean_text(item.get("retrieved_at")),
            }
        )

    hypotheses = [
        {
            "text": "Use external findings as hypotheses to validate in simulation, not as consumer VOC.",
            "source": "agent_generated",
            "confidence": 0.5,
        }
    ]
    if risk_tags:
        hypotheses.append(
            {
                "text": "Claims with safety, efficacy, or regulatory implications need explicit proof and conservative wording.",
                "source": "agent_generated",
                "confidence": 0.55,
            }
        )

    return {
        "summary": f"Research brief for: {_clean_text(user_goal)}",
        "source_count": len(source_lines),
        "sources": source_lines,
        "hypotheses": hypotheses,
        "risk_tags": sorted(risk_tags),
    }


def build_consumer_brief_from_session(session_payload: Dict[str, Any]) -> Dict[str, Any]:
    goal = _clean_text(session_payload.get("user_goal"))
    if not goal:
        raise ValueError("user_goal is required")
    findings = list(session_payload.get("external_findings", []))
    risk_snippets = [
        _clean_text(item.get("snippet"))
        for item in findings
        if item.get("evidence_type") in {"claim_risk", "regulatory"}
        and _clean_text(item.get("snippet"))
    ]
    source_evidence_spans = []
    for item in findings:
        snippet = _clean_text(item.get("snippet"))
        if not snippet:
            continue
        source_evidence_spans.append(
            {
                "title": _clean_text(item.get("title")) or "Untitled source",
                "url": _clean_text(item.get("url")),
                "snippet": snippet,
                "evidence_type": _clean_text(item.get("evidence_type")) or "category_context",
                "confidence": float(item.get("confidence", 0.5) or 0.5),
                "query": _clean_text(item.get("query")),
            }
        )

    audience = "target parent buyers and category-interested consumers"
    if re.search(r"\bmoms?\b|宝妈|妈妈|parents?", goal, re.IGNORECASE):
        audience = "moms and parent buyers evaluating children's oral care"

    return {
        "schema_version": "1.0.0",
        "task_type": "concept_test",
        "product_concept_assets": [goal],
        "copy_material": [],
        "claims": risk_snippets[:6],
        "target_audience": [audience],
        "usage_scene": ["daily use and purchase decision context"],
        "research_goal": goal,
        "optional_background_materials": [],
        "research_mode": "auto_enrich",
        "enable_lane_b": True,
        "source_evidence_spans": source_evidence_spans,
        "source_quality_summary": session_payload.get("evidence_quality", {}),
        "risk_flags": session_payload.get("research_brief", {}).get("risk_tags", []),
    }
