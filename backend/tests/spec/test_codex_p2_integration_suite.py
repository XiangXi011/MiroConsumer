"""SPEC-P2-018 integration test suite contract."""

from __future__ import annotations

import ast
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[2]
REPO_ROOT = BACKEND_ROOT.parent
INTEGRATION_ROOT = BACKEND_ROOT / "tests" / "integration"


def _integration_files() -> list[Path]:
    if not INTEGRATION_ROOT.exists():
        return []
    return sorted(INTEGRATION_ROOT.rglob("test_*.py"))


def _integration_source() -> str:
    return "\n".join(path.read_text(encoding="utf-8") for path in _integration_files())


def _count_test_functions() -> int:
    total = 0
    for path in _integration_files():
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        total += sum(
            isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith("test_")
            for node in ast.walk(tree)
        )
    return total


def test_integration_suite_exists_with_at_least_twenty_tests():
    assert INTEGRATION_ROOT.is_dir()
    assert len(_integration_files()) >= 3
    assert _count_test_functions() >= 20


def test_integration_suite_covers_required_core_and_external_flows():
    source = _integration_source()
    required_terms = (
        "brief",
        "simulation",
        "round",
        "report",
        "llm",
        "fallback",
        "redis",
        "degradation",
        "minio",
        "upload",
        "download",
        "transaction",
        "rollback",
        "tenant",
        "isolation",
    )

    for term in required_terms:
        assert term in source.lower()


def test_test_compose_provisions_required_dependency_services():
    compose = REPO_ROOT / "docker-compose.test.yml"
    text = compose.read_text(encoding="utf-8")

    for service in ("postgres", "redis", "minio"):
        assert service in text
    assert "9000" in text
    assert "5432" in text


def test_ci_has_independent_integration_job():
    ci_text = (REPO_ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")

    assert "\n  integration:" in ci_text
    assert "Backend Integration Tests" in ci_text
    assert "pytest tests/integration" in ci_text
    assert "docker-compose.test.yml" in ci_text or "services:" in ci_text
