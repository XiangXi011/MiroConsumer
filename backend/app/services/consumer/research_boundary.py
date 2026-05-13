"""Research boundary checks for consumer simulation runs."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping

from ...contracts.errors import ValidationError
from ...security.audit_log import audit_event


HIGH_RISK_DOMAINS: dict[str, tuple[str, ...]] = {
    "medical_advice": (
        "medical advice",
        "diagnosis",
        "clinical diagnosis",
        "treatment plan",
        "prescription",
        "医疗建议",
        "诊断",
        "处方",
    ),
    "financial_advice": (
        "investment advice",
        "guaranteed returns",
        "securities recommendation",
        "stock pick",
        "trading signal",
        "financial advice",
        "投资建议",
        "保本收益",
        "证券推荐",
    ),
    "legal_advice": (
        "legal advice",
        "lawsuit strategy",
        "contract legal opinion",
        "法律建议",
        "诉讼策略",
    ),
}

DEFAULT_NOT_RECOMMENDED = [
    "medical advice",
    "investment advice",
    "legal advice",
    "clinical diagnosis",
    "regulated financial recommendations",
]


@dataclass
class ResearchBoundaryAssessment:
    applicable_categories: list[str] = field(default_factory=list)
    applicable_markets: list[str] = field(default_factory=list)
    confidence_level: str = "medium"
    not_recommended_scenarios: list[str] = field(default_factory=lambda: list(DEFAULT_NOT_RECOMMENDED))
    warnings: list[str] = field(default_factory=list)
    blocked_domain: str = ""

    def to_dict(self) -> dict[str, Any]:
        payload = {
            "applicable_categories": self.applicable_categories or ["consumer research simulation"],
            "applicable_markets": self.applicable_markets or ["synthetic consumer segments"],
            "confidence_level": self.confidence_level,
            "not_recommended_scenarios": self.not_recommended_scenarios,
            "warnings": self.warnings,
        }
        if self.blocked_domain:
            payload["blocked_domain"] = self.blocked_domain
        return payload


class ResearchBoundaryViolation(ValidationError):
    """Raised when a brief asks the simulator to operate outside allowed research boundaries."""

    def __init__(self, message: str, assessment: ResearchBoundaryAssessment):
        details = assessment.to_dict()
        details["error_code"] = "BOUNDARY_VIOLATION"
        super().__init__(message, details=details)


def enforce_research_boundary(
    *,
    simulation_id: str,
    brief_context: Mapping[str, Any] | None,
    persona_pack: Iterable[Mapping[str, Any]] | None,
) -> dict[str, Any]:
    """Evaluate and enforce research boundaries before a society run starts."""
    personas = list(persona_pack or [])
    assessment = evaluate_research_boundary(brief_context or {}, personas)
    if assessment.blocked_domain:
        audit_event(
            event_type="boundary_violation",
            target_type="simulation",
            target_id=simulation_id,
            success=False,
            reason=assessment.blocked_domain,
            details=assessment.to_dict(),
        )
        raise ResearchBoundaryViolation(
            "Research boundary violation: high-risk advice domains are not supported.",
            assessment,
        )

    for warning in assessment.warnings:
        audit_event(
            event_type="boundary_warning",
            target_type="simulation",
            target_id=simulation_id,
            success=True,
            reason=warning,
            details=assessment.to_dict(),
        )

    return assessment.to_dict()


def evaluate_research_boundary(
    brief_context: Mapping[str, Any],
    persona_pack: Iterable[Mapping[str, Any]],
) -> ResearchBoundaryAssessment:
    brief_text = _flatten_text(brief_context).lower()
    blocked_domain = _blocked_domain(brief_text)
    persona_categories = _persona_categories(persona_pack)
    brief_category = _brief_category(brief_context)
    applicable_markets = _applicable_markets(brief_context, persona_pack)
    not_recommended = list(DEFAULT_NOT_RECOMMENDED)
    warnings: list[str] = []

    if blocked_domain:
        return ResearchBoundaryAssessment(
            applicable_categories=persona_categories or ["consumer research simulation"],
            applicable_markets=applicable_markets,
            confidence_level="blocked",
            not_recommended_scenarios=not_recommended,
            warnings=["high_risk_domain_blocked"],
            blocked_domain=blocked_domain,
        )

    if brief_category and persona_categories and not _category_matches(brief_category, persona_categories):
        warnings.append("category_mismatch")
        if brief_category not in not_recommended:
            not_recommended.insert(0, brief_category)

    return ResearchBoundaryAssessment(
        applicable_categories=persona_categories or ["consumer research simulation"],
        applicable_markets=applicable_markets,
        confidence_level="low" if warnings else "medium",
        not_recommended_scenarios=not_recommended,
        warnings=warnings,
    )


def default_applicability_boundary() -> dict[str, Any]:
    return ResearchBoundaryAssessment().to_dict()


def _blocked_domain(text: str) -> str:
    for domain, keywords in HIGH_RISK_DOMAINS.items():
        if any(keyword.lower() in text for keyword in keywords):
            return domain
    return ""


def _brief_category(brief_context: Mapping[str, Any]) -> str:
    for key in ("product_category", "category", "industry", "domain"):
        value = str(brief_context.get(key) or "").strip()
        if value:
            return value
    return ""


def _persona_categories(persona_pack: Iterable[Mapping[str, Any]]) -> list[str]:
    categories: list[str] = []
    for persona in persona_pack:
        text = _flatten_text(persona).lower()
        if any(token in text for token in ("fmcg", "consumer packaged", "shopper", "nutrition")):
            _append_unique(categories, "FMCG")
        if any(token in text for token in ("saas", "enterprise", "b2b", "software")):
            _append_unique(categories, "enterprise SaaS")
        explicit = persona.get("category_scope") or persona.get("applicable_categories")
        if isinstance(explicit, list):
            for item in explicit:
                _append_unique(categories, str(item))
        elif explicit:
            _append_unique(categories, str(explicit))
    return categories


def _applicable_markets(
    brief_context: Mapping[str, Any],
    persona_pack: Iterable[Mapping[str, Any]],
) -> list[str]:
    markets: list[str] = []
    target_market = str(brief_context.get("target_market") or "").strip()
    if target_market:
        _append_unique(markets, target_market)
    for persona in persona_pack:
        source_basis = persona.get("source_basis")
        if isinstance(source_basis, Mapping):
            sample = source_basis.get("sample_characteristics")
            if isinstance(sample, Mapping):
                region = str(sample.get("region") or "").strip()
                if region:
                    _append_unique(markets, region)
    return markets or ["synthetic consumer segments"]


def _category_matches(brief_category: str, persona_categories: list[str]) -> bool:
    normalized_brief = _normalize_category(brief_category)
    return any(_normalize_category(category) == normalized_brief for category in persona_categories)


def _normalize_category(value: str) -> str:
    text = value.strip().lower()
    if any(token in text for token in ("fmcg", "consumer packaged", "cpg", "food", "beverage")):
        return "fmcg"
    if any(token in text for token in ("enterprise", "saas", "b2b", "software")):
        return "enterprise_saas"
    return text


def _flatten_text(value: Any) -> str:
    if isinstance(value, Mapping):
        return " ".join(_flatten_text(item) for item in value.values())
    if isinstance(value, (list, tuple, set)):
        return " ".join(_flatten_text(item) for item in value)
    return str(value or "")


def _append_unique(items: list[str], value: str) -> None:
    text = value.strip()
    if text and text not in items:
        items.append(text)


__all__ = [
    "ResearchBoundaryAssessment",
    "ResearchBoundaryViolation",
    "default_applicability_boundary",
    "enforce_research_boundary",
    "evaluate_research_boundary",
]
