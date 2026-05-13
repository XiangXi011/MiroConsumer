"""SPEC-P2-026 pricing model and GTM documentation contract."""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]


def test_pricing_model_doc_covers_metering_tiers_and_resource_quotas():
    text = (ROOT / "docs" / "business" / "pricing-model.md").read_text(encoding="utf-8")

    required_terms = [
        "simulation run",
        "LLM cost",
        "16 consumers",
        "32 consumers",
        "64 consumers",
        "128 consumers",
        "Professional",
        "Enterprise",
        "short-term unified pricing",
        "long-term differentiated pricing",
        "resource quota",
        "custom Persona Pack",
        "external validity validation",
    ]
    for term in required_terms:
        assert term in text


def test_gtm_strategy_doc_covers_icp_channels_and_competitive_pricing():
    text = (ROOT / "docs" / "business" / "gtm-strategy.md").read_text(encoding="utf-8")

    required_terms = [
        "ideal customer profile",
        "sales channels",
        "competitive pricing",
        "consumer insights teams",
        "innovation agencies",
        "private deployment",
        "review owners",
    ]
    for term in required_terms:
        assert term in text
