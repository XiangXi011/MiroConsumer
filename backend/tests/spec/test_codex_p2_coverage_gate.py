"""SPEC-P2-017 backend coverage gate contract."""

from __future__ import annotations

import tomllib
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[2]
REPO_ROOT = BACKEND_ROOT.parent


def _pyproject() -> dict:
    return tomllib.loads((BACKEND_ROOT / "pyproject.toml").read_text(encoding="utf-8"))


def test_backend_pytest_blocks_below_80_percent_coverage():
    config = _pyproject()
    addopts = config["tool"]["pytest"]["ini_options"]["addopts"]
    assert "--cov=app" in addopts
    assert "--cov-report=term-missing" in addopts
    assert "--cov-fail-under=80" in addopts

    coverage_run = config["tool"]["coverage"]["run"]
    omit = "\n".join(coverage_run["omit"])
    for legacy_module in (
        "simulation_runner.py",
        "report_agent.py",
        "zep_*.py",
        "oasis_profile_generator.py",
        "ontology_generator.py",
    ):
        assert legacy_module in omit


def test_ci_backend_job_uses_coverage_gate():
    ci_text = (REPO_ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    assert "--cov-fail-under=80" in ci_text


def test_coverage_gap_analysis_documents_exclusions_and_new_test_targets():
    analysis = REPO_ROOT / "docs" / "quality" / "backend_coverage_gap_analysis.md"
    text = analysis.read_text(encoding="utf-8")

    for phrase in (
        "80%",
        "Repository database failure",
        "Redis timeout",
        "LLM API 5xx",
        "boundary conditions",
        "temporary legacy/external adapter exclusions",
    ):
        assert phrase in text


def test_mutation_testing_sample_script_targets_five_core_modules():
    script = BACKEND_ROOT / "scripts" / "mutation_smoke.py"
    text = script.read_text(encoding="utf-8")

    assert "MUTATION_TARGETS" in text
    assert "MIN_MUTATION_SCORE = 0.70" in text
    assert text.count("app/") >= 5
    assert "--threshold" in text