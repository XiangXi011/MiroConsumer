import json

from app.security.audit_log import AuditLogger


def test_audit_logger_writes_jsonl_and_redacts_sensitive_values(tmp_path):
    path = tmp_path / "audit.jsonl"
    logger = AuditLogger(path)

    event = logger.record(
        event_type="auth.login_failed",
        actor_user_id="user_1",
        actor_tenant_id="tenant_a",
        target_type="auth",
        target_id="login",
        ip="127.0.0.1",
        user_agent="pytest",
        success=False,
        reason="invalid_credentials",
        details={
            "password": "StrongPassword123!",
            "token": "secret-token",
            "api_key": "mk_key.raw",
            "safe": "kept",
        },
    )

    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    assert rows == [event]
    serialized = json.dumps(rows[0])
    assert "StrongPassword123!" not in serialized
    assert "secret-token" not in serialized
    assert "mk_key.raw" not in serialized
    assert rows[0]["details"]["safe"] == "kept"
