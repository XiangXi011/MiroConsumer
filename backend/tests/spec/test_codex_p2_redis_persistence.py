"""SPEC-P2-015 Redis persistence readiness contract."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from app import create_app
from app.config import Config
from app.redis.health import check_redis
from tests.ops.test_health_readiness import ReadyConfig

BACKEND_ROOT = Path(__file__).resolve().parents[2]
REPO_ROOT = BACKEND_ROOT.parent


def test_production_compose_enables_redis_aof_everysec():
    compose_text = (REPO_ROOT / "docker-compose.prod.yml").read_text(encoding="utf-8")

    assert 'command: ["redis-server", "--appendonly", "yes", "--appendfsync", "everysec"]' in compose_text
    assert "redis_data:/data" in compose_text


def test_config_exposes_redis_persistence_toggle(monkeypatch):
    monkeypatch.setenv("REDIS_PERSISTENCE_ENABLED", "true")
    assert Config.REDIS_PERSISTENCE_ENABLED is True

    monkeypatch.setenv("REDIS_PERSISTENCE_ENABLED", "false")
    assert Config.REDIS_PERSISTENCE_ENABLED is False


def test_redis_health_warns_when_required_persistence_is_disabled():
    redis_conn = MagicMock()
    redis_conn.config_get.side_effect = [
        {"appendonly": "no"},
        {"appendfsync": "everysec"},
    ]

    with patch("app.redis.health.redis.Redis.from_url", return_value=redis_conn):
        status, warning = check_redis("redis://localhost:6379/0", persistence_required=True)

    assert status == "warning"
    assert warning is not None
    assert "appendonly" in warning
    redis_conn.ping.assert_called_once()


def test_ready_endpoint_returns_warning_when_redis_persistence_is_disabled():
    class PersistentRedisConfig(ReadyConfig):
        REDIS_PERSISTENCE_ENABLED = True

    redis_conn = MagicMock()
    redis_conn.config_get.side_effect = [
        {"appendonly": "no"},
        {"appendfsync": "everysec"},
    ]

    with patch("app.redis.health.redis.Redis.from_url", return_value=redis_conn):
        app = create_app(PersistentRedisConfig)
        redis_conn.ping.reset_mock()
        response = app.test_client().get("/ready")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["status"] == "ready"
    assert payload["checks"]["redis"] == "warning"
    assert "redis" in payload["warnings"]
    assert "appendonly" in payload["warnings"]["redis"]


def test_redis_backup_restore_script_and_ops_doc_exist():
    script = BACKEND_ROOT / "scripts" / "redis_backup_restore.py"
    ops_doc = REPO_ROOT / "docs" / "operations" / "redis_persistence.md"

    script_text = script.read_text(encoding="utf-8")
    doc_text = ops_doc.read_text(encoding="utf-8")

    assert "--backup" in script_text
    assert "--restore" in script_text
    assert "dump.rdb" in script_text
    assert "appendonly.aof" in script_text
    assert "RDB" in doc_text
    assert "AOF" in doc_text
    assert "redis_backup_restore.py" in doc_text