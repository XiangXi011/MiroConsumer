"""JSON-backed session store for President Lobster research sessions."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Optional

from ...config import Config
from .openclaw_models import OpenClawResearchSession

_SESSION_ID_PATTERN = re.compile(r"^rsess_[0-9a-f]{12}$")


class OpenClawSessionStore:
    def __init__(self, upload_root: Optional[str] = None):
        root = Path(upload_root or Config.UPLOAD_FOLDER)
        self._dir = root / "openclaw_sessions"
        self._dir.mkdir(parents=True, exist_ok=True)

    def _path(self, research_session_id: str) -> Path:
        if not _SESSION_ID_PATTERN.fullmatch(research_session_id):
            raise ValueError(
                f"Invalid OpenClaw research session id: {research_session_id}"
            )
        return self._dir / f"{research_session_id}.json"

    def save(self, session: OpenClawResearchSession) -> None:
        session.touch()
        path = self._path(session.research_session_id)
        tmp_path = path.with_suffix(".json.tmp")
        tmp_path.write_text(
            json.dumps(session.to_dict(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        tmp_path.replace(path)

    def get(self, research_session_id: str) -> Optional[OpenClawResearchSession]:
        if not _SESSION_ID_PATTERN.fullmatch(research_session_id):
            return None
        path = self._path(research_session_id)
        if not path.exists():
            return None
        return OpenClawResearchSession.from_dict(
            json.loads(path.read_text(encoding="utf-8"))
        )

    def list_recent(
        self,
        limit: int = 10,
        tenant_id: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> list[OpenClawResearchSession]:
        try:
            parsed_limit = int(limit)
        except (TypeError, ValueError):
            parsed_limit = 10
        parsed_limit = max(1, min(parsed_limit, 50))
        tenant_filter = str(tenant_id or "").strip()
        user_filter = str(user_id or "").strip()

        sessions: list[OpenClawResearchSession] = []
        for path in self._dir.glob("*.json"):
            try:
                session = OpenClawResearchSession.from_dict(
                    json.loads(path.read_text(encoding="utf-8"))
                )
            except (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError):
                continue
            if tenant_filter and session.tenant_id != tenant_filter:
                continue
            if user_filter and session.user_id != user_filter:
                continue
            sessions.append(session)

        sessions.sort(
            key=lambda item: item.updated_at or item.created_at or "",
            reverse=True,
        )
        return sessions[:parsed_limit]
