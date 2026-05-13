"""Spec contracts for P3 personalized consumer report generation."""

from __future__ import annotations

import inspect

from app.services.consumer.finding_distiller import (
    _classify_finding_type,
    _classify_visibility,
)
from app.services.consumer.models import GraphVisibility
from app.services.report_agent import ReportAgent


def _context(task_type: str) -> dict:
    return {
        "task_type": task_type,
        "industry": "food_beverage",
        "target_audience": ["working moms"],
        "summary": {
            "initial_acceptance": {"positive": 0.4, "neutral": 0.4, "negative": 0.2},
            "post_propagation_acceptance": {"positive": 0.55, "neutral": 0.3, "negative": 0.15},
            "attitude_shift_rate": 0.22,
        },
    }


def test_p3_011_finding_distiller_separates_propagation_signal_and_graph_visible_default():
    assert _classify_finding_type("group chat creators repeat this talking point") == "propagation_signal"
    assert _classify_visibility("ordinary category context") == GraphVisibility.GraphVisible


def test_p3_011_consumer_outline_changes_by_test_type():
    agent = ReportAgent(graph_id="g", simulation_id="s", simulation_requirement="brief")

    price_titles = [section.title for section in agent._build_consumer_outline(_context("price_test")).sections]
    packaging_titles = [section.title for section in agent._build_consumer_outline(_context("packaging_test")).sections]
    ab_titles = [section.title for section in agent._build_consumer_outline(_context("ab_test")).sections]

    assert any("价格敏感度" in title for title in price_titles)
    assert any("WTP" in title for title in price_titles)
    assert any("视觉认知" in title for title in packaging_titles)
    assert any("货架吸引力" in title for title in packaging_titles)
    assert any("偏好对比" in title for title in ab_titles)
    assert any("统计显著性" in title for title in ab_titles)


def test_p3_011_react_context_prompt_includes_industry_audience_and_task_type():
    source = inspect.getsource(ReportAgent._build_consumer_report_context)
    assert "industry" in source
    assert "target_audience" in source
    assert "task_type" in source
