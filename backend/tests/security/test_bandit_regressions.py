from pathlib import Path

import pytest

from app.services.consumer.url_ingest import _default_fetch_url

ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "app"


def test_app_code_uses_bandit_clean_hash_primitives():
    offenders = []
    for path in APP.rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        if "hashlib.md5" in text or "hashlib.sha1" in text:
            offenders.append(str(path.relative_to(ROOT)))

    assert offenders == []


def test_default_fetch_url_rejects_non_http_scheme_before_open(monkeypatch):
    def fail_connection(*args, **kwargs):
        raise AssertionError("network connection should not be opened for unsupported schemes")

    monkeypatch.setattr("app.services.consumer.url_ingest.HTTPConnection", fail_connection)
    monkeypatch.setattr("app.services.consumer.url_ingest.HTTPSConnection", fail_connection)

    with pytest.raises(ValueError, match="Unsupported URL scheme"):
        _default_fetch_url("file:///etc/passwd")
