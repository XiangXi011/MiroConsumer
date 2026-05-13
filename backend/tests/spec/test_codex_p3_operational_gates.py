from __future__ import annotations

import ast
import re
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[3]


def read_text(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def load_yaml(relative: str) -> dict:
    return yaml.safe_load(read_text(relative))


def test_p3_012_comment_coverage_gate_and_required_docstrings() -> None:
    for relative in [
        "backend/app/contracts/__init__.py",
        "backend/app/services/consumer/confidence_scoring.py",
        "backend/app/services/consumer/phase6j_calibration.py",
        "backend/app/services/consumer/society/run_controller.py",
    ]:
        tree = ast.parse(read_text(relative))
        assert ast.get_docstring(tree), f"{relative} needs a module docstring"
        assert "from __future__ import annotations" in read_text(relative)

    pyproject = read_text("backend/pyproject.toml")
    assert "[tool.interrogate]" in pyproject
    assert "fail-under = 80" in pyproject

    ci = read_text(".github/workflows/ci.yml")
    assert "interrogate" in ci
    assert "Check Python docstring coverage" in ci


def test_p3_013_architecture_adrs_and_known_deviations_are_documented() -> None:
    architecture = read_text("docs/architecture.md")
    assert architecture.count("### ADR-") >= 3
    assert "Service Locator" in architecture
    assert "@classmethod" in architecture
    assert "create_app()" in architecture
    assert "Repository+Manager" in architecture
    assert "red" in architecture.lower() or "#ff" in architecture.lower()

    readme = read_text("README.md")
    assert "architecture deviations" in readme.lower()
    assert "Service Locator" in readme


def test_p3_014_api_deprecation_headers_policy_and_permissions() -> None:
    app_init = read_text("backend/app/__init__.py")
    assert "Deprecation" in app_init
    assert "Sunset" in app_init
    assert "01 Nov 2026" in app_init
    assert "01 Dec 2026" in app_init

    policy = read_text("docs/API_VERSIONING_POLICY.md")
    assert "/api/*" in policy and "deprecated" in policy.lower()
    assert "/api/v1/*" in policy and "recommended" in policy.lower()

    openapi = read_text("backend/app/__init__.py")
    assert 'operation["deprecated"] = True' in openapi or '"deprecated": True' in openapi

    for endpoint in ["get_run_estimate", "get_report_audit_chain", "get_report_evidence_graph"]:
        matches = re.findall(r"@require_permission\([^)]+\)\s*\n\s*def " + endpoint, app_init + read_text("backend/app/api/consumer_operations.py") + read_text("backend/app/api/consumer_summary.py"))
        assert matches, f"{endpoint} must be protected by @require_permission"


def test_p3_015_cors_is_explicit_and_strict() -> None:
    config = read_text("backend/app/config.py")
    app_init = read_text("backend/app/__init__.py")
    assert "CORS_ALLOW_ORIGINS" in config
    assert "CORS_ALLOWED_ORIGINS" in config
    assert "must be explicitly set" in app_init
    assert "wildcard '*' is not allowed in production" in app_init


def test_p3_016_autoscaling_resources_health_and_docs() -> None:
    compose = load_yaml("docker-compose.prod.yml")
    worker = compose["services"]["worker"]
    deploy = worker["deploy"]
    assert deploy["mode"] == "replicated"
    assert deploy["replicas"] >= 2
    assert "cpus" in deploy["resources"]["limits"]
    assert "memory" in deploy["resources"]["reservations"]
    assert "healthcheck" in worker

    deployment = read_text("docs/deployment.md")
    assert "HorizontalPodAutoscaler" in deployment
    assert "queue depth" in deployment.lower()
    assert "worker" in deployment.lower()


def test_p3_017_migration_smoke_job_and_revision_comments() -> None:
    ci = read_text(".github/workflows/ci.yml")
    assert "Migration Smoke Test" in ci
    assert "alembic downgrade -1" in ci
    assert "alembic upgrade +1" in ci

    migrations = sorted((ROOT / "backend/alembic/versions").glob("*.py"))
    assert migrations
    for path in migrations:
        text = path.read_text(encoding="utf-8")
        if path.name.startswith("__"):
            continue
        assert "Revision rationale:" in text, f"{path.name} missing migration rationale"


def test_p3_018_alert_rules_and_docs_exist() -> None:
    rules = read_text("alerts/prometheus-rules.yml")
    for alert in [
        "SimulationQueueHigh",
        "LLMErrorRateHigh",
        "DatabaseConnectionPoolLow",
        "WorkerDown",
    ]:
        assert alert in rules

    deployment = read_text("docs/deployment.md")
    assert "AlertManager" in deployment
    assert "Slack" in deployment
    assert "PagerDuty" in deployment


def test_p3_019_frontend_coverage_gate_and_artifact() -> None:
    vitest = read_text("frontend/vitest.config.js")
    assert "coverage" in vitest
    assert "thresholds" in vitest
    assert "60" in vitest

    ci = read_text(".github/workflows/ci.yml")
    assert "npm run test:coverage" in ci
    assert "frontend-coverage" in ci
    assert "actions/upload-artifact" in ci


def test_p3_020_branch_protection_settings() -> None:
    settings = load_yaml(".github/settings.yml")
    main = next(branch for branch in settings["branches"] if branch["name"] == "main")
    protection = main["protection"]
    assert protection["required_pull_request_reviews"]["required_approving_review_count"] >= 1
    assert protection["required_status_checks"]["strict"] is True
    assert "Backend Tests" in protection["required_status_checks"]["contexts"]
    assert protection["enforce_admins"] is True
    assert protection.get("allow_force_pushes") is False


def test_p3_021_version_consistency_and_changelog_norms() -> None:
    pyproject = read_text("backend/pyproject.toml")
    version = re.search(r'^version = "([^"]+)"', pyproject, re.MULTILINE).group(1)
    changelog = read_text("CHANGELOG.md")
    assert f"## [{version}]" in changelog

    contributing = read_text("CONTRIBUTING.md")
    assert "Keep a Changelog" in contributing
    assert "SemVer" in contributing
    assert "YYYY-MM-DD" in contributing

    ci = read_text(".github/workflows/ci.yml")
    assert "Check version consistency" in ci
    assert "scripts/check_version_consistency.py" in ci


def test_p3_022_to_p3_024_security_dependabot_sbom_and_license_gates() -> None:
    dependabot = load_yaml(".github/dependabot.yml")
    ecosystems = {entry["package-ecosystem"] for entry in dependabot["updates"]}
    assert {"pip", "npm"}.issubset(ecosystems)

    pyproject = read_text("backend/pyproject.toml")
    override_block = pyproject.split("override-dependencies = [", 1)[1].split("]", 1)[0]
    for line in override_block.splitlines():
        if '"' in line:
            assert "CVE-" in line and "remove after" in line

    security = read_text(".github/workflows/security.yml")
    assert "pip-audit" in security
    assert "npm audit" in security
    assert "pip-licenses" in security
    assert "licenses.json" in security

    docker = read_text(".github/workflows/docker-image.yml")
    assert "SBOM" in docker
    assert "upload-artifact" in docker

    compliance = read_text("docs/compliance.md")
    assert "SBOM" in compliance
    assert "AGPL" in compliance
    assert "license" in compliance.lower()

    app_vue = read_text("frontend/src/App.vue")
    assert "Source" in app_vue and "github.com" in app_vue


def test_p3_025_benchmark_regression_gate_and_slo_docs() -> None:
    ci = read_text(".github/workflows/ci.yml")
    assert "pytest tests/benchmark" in ci
    assert "--benchmark-only" in ci
    assert "check_benchmark_regression.py" in ci
    assert "--max-regression 0.20" in ci

    operations = read_text("docs/operations.md")
    assert "P99" in operations
    assert "500ms" in operations
    assert "30s" in operations
    assert "2s" in operations


def test_p3_033_contributor_docs_and_internal_agent_rules() -> None:
    contributing_lines = read_text("CONTRIBUTING.md").splitlines()
    deployment_lines = read_text("docs/deployment.md").splitlines()
    assert len(contributing_lines) >= 100
    assert len(deployment_lines) >= 80
    assert not (ROOT / "AGENTS.md").exists()
    assert (ROOT / "docs/internal/AGENTS.md").exists()
    internal_agents = read_text("docs/internal/AGENTS.md")
    assert "Agent Operating Rules" in internal_agents
    assert "Testing" in internal_agents
