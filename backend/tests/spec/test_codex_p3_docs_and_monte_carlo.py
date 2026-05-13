"""Spec contracts for P3 documentation and Monte Carlo tuning."""

from __future__ import annotations

from pathlib import Path

from app.services.consumer.validation.monte_carlo import MonteCarloValidator


ROOT = Path(__file__).resolve().parents[3]


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_p3_001_architecture_roadmap_is_documented_and_linked_from_readme():
    architecture = _read("docs/architecture.md")
    readme = _read("README.md")

    assert "技术栈演进路线图" in architecture
    for phase in range(1, 8):
        assert f"Phase {phase}" in architecture
    for required in ["OASIS", "LiteLLM", "Pydantic v2", "未来6个月"]:
        assert required in architecture

    assert "docs/architecture.md#技术栈演进路线图" in readme


def test_p3_002_competitive_landscape_matrix_exists_and_is_linked():
    doc = _read("docs/product/competitive-landscape.md")
    readme = _read("README.md")

    for competitor in ["Remesh", "Zappi", "Aytm", "NetLogo", "AgentPy"]:
        assert competitor in doc
    for dimension in ["agent simulation", "动态传播", "可解释证据链"]:
        assert dimension in doc
    assert "学术agent simulation工具" in doc
    assert "商业消费者洞察工具" in doc

    assert "docs/product/competitive-landscape.md" in readme


def test_p3_004_monte_carlo_tuning_document_and_docstring_cover_parameters():
    tuning_doc = _read("docs/research/monte-carlo-tuning.md")

    for term in [
        "random_walk_std",
        "baseline_floor",
        "baseline_relative_noise",
        "参数敏感性",
        "真实社交平台传播数据",
        "统计功效",
    ]:
        assert term in tuning_doc

    assert "docs/research/monte-carlo-tuning.md" in (MonteCarloValidator.__doc__ or "")


def test_p3_004_monte_carlo_random_walk_parameters_are_configurable():
    validator = MonteCarloValidator(seed=42, random_walk_std=0.25, baseline_floor=4.0)

    assert validator.random_walk_std == 0.25
    assert validator.baseline_floor == 4.0

    distribution = validator.null_under_random_walk(
        baseline_value=1.0,
        n_simulations=25,
    )

    assert len(distribution) == 25
    assert max(abs(value - 1.0) for value in distribution) < 3.0
