import json

import pytest

from app.services.application.openclaw_models import (
    OpenClawActionLogEntry,
    OpenClawResearchSession,
)
from app.services.application.openclaw_session_store import OpenClawSessionStore


def test_openclaw_session_store_round_trips_session(tmp_path):
    store = OpenClawSessionStore(upload_root=str(tmp_path / "uploads"))
    session = OpenClawResearchSession.create(user_goal="测试儿童变色牙膏")
    session.updated_at = "2000-01-01T00:00:00+00:00"
    session.exploration_plan.append(
        {
            "query": "color changing kids toothpaste parent concerns",
            "evidence_type": "consumer_discussion",
            "reason": "Find parent objections",
        }
    )
    session.action_log.append(
        OpenClawActionLogEntry.create(
            action_type="confirm_research_plan",
            actor="user",
            tool_name="research.plan",
            input_summary={"query_count": 1},
            result_status="confirmed",
        )
    )

    store.save(session)
    restored = store.get(session.research_session_id)
    saved_text = (
        tmp_path
        / "uploads"
        / "openclaw_sessions"
        / f"{session.research_session_id}.json"
    ).read_text(encoding="utf-8")

    assert restored is not None
    assert restored.research_session_id == session.research_session_id
    assert restored.status == "planning"
    assert restored.user_goal == "测试儿童变色牙膏"
    assert restored.exploration_plan[0]["evidence_type"] == "consumer_discussion"
    assert restored.action_log[0].result_status == "confirmed"
    assert "\\u6d4b" not in saved_text
    assert json.loads(saved_text)["user_goal"] == "测试儿童变色牙膏"
    assert restored.updated_at != "2000-01-01T00:00:00+00:00"


def test_openclaw_session_store_returns_none_for_missing_session(tmp_path):
    store = OpenClawSessionStore(upload_root=str(tmp_path / "uploads"))

    assert store.get("rsess_000000000000") is None


def test_openclaw_session_store_round_trips_owner_metadata(tmp_path):
    store = OpenClawSessionStore(upload_root=str(tmp_path / "uploads"))
    session = OpenClawResearchSession.create(
        user_goal="Owner metadata",
        user_id=" user_a ",
        tenant_id=" tenant_a ",
    )

    store.save(session)
    restored = store.get(session.research_session_id)

    assert restored is not None
    assert restored.user_id == "user_a"
    assert restored.tenant_id == "tenant_a"


def test_openclaw_session_from_dict_keeps_legacy_owner_fields_blank():
    session = OpenClawResearchSession.from_dict(
        {
            "research_session_id": "rsess_123456789abc",
            "status": "planning",
            "user_goal": "Legacy session",
            "created_at": "2000-01-01T00:00:00+00:00",
            "updated_at": "2000-01-01T00:00:00+00:00",
        }
    )

    assert session.user_id == ""
    assert session.tenant_id == ""


@pytest.mark.parametrize(
    "research_session_id",
    [
        "../escape",
        "rsess_../../escape",
        "rsess_123456789abc/escape",
        "C:/tmp/escape",
        "rsess_123456789abg",
    ],
)
def test_openclaw_session_store_rejects_invalid_session_ids(
    tmp_path, research_session_id
):
    store = OpenClawSessionStore(upload_root=str(tmp_path / "uploads"))
    session = OpenClawResearchSession.create(user_goal="Test path safety")
    session.research_session_id = research_session_id

    assert store.get(research_session_id) is None
    with pytest.raises(ValueError, match="Invalid OpenClaw research session id"):
        store.save(session)
