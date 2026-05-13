"""Codex P1 release contract checks."""

from pathlib import Path
import json
import re
import tomllib

ROOT = Path(__file__).resolve().parents[3]
EXPECTED_VERSION = "0.7.1"


def _json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_project_versions_match_changelog_release():
    backend = tomllib.loads((ROOT / "backend" / "pyproject.toml").read_text(encoding="utf-8"))
    root_pkg = _json(ROOT / "package.json")
    frontend_pkg = _json(ROOT / "frontend" / "package.json")
    root_lock = _json(ROOT / "package-lock.json")
    frontend_lock = _json(ROOT / "frontend" / "package-lock.json")
    changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")

    assert backend["project"]["version"] == EXPECTED_VERSION
    assert root_pkg["version"] == EXPECTED_VERSION
    assert frontend_pkg["version"] == EXPECTED_VERSION
    assert root_lock["version"] == EXPECTED_VERSION
    assert root_lock["packages"][""]["version"] == EXPECTED_VERSION
    assert frontend_lock["version"] == EXPECTED_VERSION
    assert frontend_lock["packages"][""]["version"] == EXPECTED_VERSION
    assert re.search(r"^## \[0\.7\.1\]", changelog, re.MULTILINE)

def test_root_security_and_deployment_docs_are_standalone():
    security = (ROOT / "SECURITY.md").read_text(encoding="utf-8")
    deployment = (ROOT / "DEPLOYMENT.md").read_text(encoding="utf-8")

    for expected in [
        "Security Policy",
        "Reporting a Vulnerability",
        "Response SLA",
        "Supported Versions",
        "AGPL-3.0",
    ]:
        assert expected in security
    assert len(security.splitlines()) >= 40

    for expected in [
        "Deployment Guide",
        "Required Environment Variables",
        "Health Checks",
        "/metrics",
        "Rollback",
        "Backup",
        "Troubleshooting",
        "Scaling",
    ]:
        assert expected in deployment
    assert len(deployment.splitlines()) >= 60

def test_consumer_api_logs_are_readable_utf8_and_ci_blocks_garbled_text():
    files = [
        ROOT / "backend" / "app" / "api" / "consumer_operations.py",
        ROOT / "backend" / "app" / "api" / "consumer_summary.py",
    ]
    combined = "\n".join(path.read_text(encoding="utf-8") for path in files)

    for expected in [
        "获取运行成本估算失败",
        "获取报告审计链失败",
        "获取报告证据图谱失败",
        "获取死信列表失败",
        "消费者传播摘要获取失败",
        "渠道摘要获取失败",
        "渠道事件获取失败",
        "传播路径获取失败",
    ]:
        assert expected in combined

    for garbled in ["鑾峰彇", "鎶ュ憡", "璇佹嵁", "鍥捐氨", "澶辫触", "閼惧嘲", "涓嶅瓨鍦"]:
        assert garbled not in combined

    ci = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    assert "Check Python file encoding" in ci
    assert "Check for garbled Chinese characters" in ci
    assert "open(path, 'r', encoding='utf-8').read()" in ci
