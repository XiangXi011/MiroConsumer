"""Research source registry: project-scoped source governance for dual-lane RAG."""

from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from .models import ResearchSource, ResearchSourceLane, ResearchSourceType


RESEARCH_DIR_NAME = "research"
SOURCES_FILE_NAME = "sources.json"


def _get_research_dir(project_id: str, upload_root: Optional[str] = None) -> Path:
    root = Path(upload_root) if upload_root else Path(__file__).resolve().parents[3] / "uploads"
    return root / "projects" / project_id / RESEARCH_DIR_NAME


def _get_sources_path(project_id: str, upload_root: Optional[str] = None) -> Path:
    return _get_research_dir(project_id, upload_root) / SOURCES_FILE_NAME


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class SourceRegistry:
    """Manage research sources for a project with repo-local persistence."""

    def __init__(self, project_id: str, upload_root: Optional[str] = None):
        self.project_id = project_id
        self._dir = _get_research_dir(project_id, upload_root)
        self._sources_path = self._dir / SOURCES_FILE_NAME
        self._ensure_dir()

    def _ensure_dir(self) -> None:
        self._dir.mkdir(parents=True, exist_ok=True)

    def _load(self) -> List[ResearchSource]:
        if not self._sources_path.exists():
            return []
        with self._sources_path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        return [ResearchSource(**item) for item in data.get("sources", [])]

    def _save(self, sources: List[ResearchSource]) -> None:
        payload = {
            "project_id": self.project_id,
            "updated_at": _now_iso(),
            "sources": [s.model_dump() for s in sources],
        }
        with self._sources_path.open("w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)

    def list_sources(self, lane: Optional[ResearchSourceLane] = None) -> List[ResearchSource]:
        sources = self._load()
        if lane is None:
            return sources
        return [s for s in sources if s.lane == lane]

    def get_source(self, source_id: str) -> Optional[ResearchSource]:
        for s in self._load():
            if s.source_id == source_id:
                return s
        return None

    def register_source(
        self,
        lane: ResearchSourceLane,
        source_type: ResearchSourceType,
        label: str,
        uri: str = "",
        metadata: Optional[Dict[str, Any]] = None,
        source_id: Optional[str] = None,
    ) -> ResearchSource:
        sources = self._load()
        new_id = source_id or f"src_{uuid.uuid4().hex[:12]}"
        trust_tier = 1 if lane == ResearchSourceLane.LaneA else 2
        source = ResearchSource(
            source_id=new_id,
            lane=lane,
            source_type=source_type,
            label=label,
            uri=uri,
            metadata=metadata or {},
            added_at=_now_iso(),
            trust_tier=trust_tier,
        )
        sources.append(source)
        self._save(sources)
        return source

    def remove_source(self, source_id: str) -> bool:
        sources = self._load()
        filtered = [s for s in sources if s.source_id != source_id]
        if len(filtered) == len(sources):
            return False
        self._save(filtered)
        return True

    def clear_lane(self, lane: ResearchSourceLane) -> int:
        sources = self._load()
        kept = [s for s in sources if s.lane != lane]
        removed = len(sources) - len(kept)
        self._save(kept)
        return removed

    def get_or_register_source(
        self,
        lane: ResearchSourceLane,
        source_type: ResearchSourceType,
        label: str,
        uri: str = "",
        metadata: Optional[Dict[str, Any]] = None,
        source_id: Optional[str] = None,
    ) -> ResearchSource:
        """Return existing source matching URI+lane, or register a new one."""
        sources = self._load()
        if uri:
            for s in sources:
                if s.uri == uri and s.lane == lane:
                    return s
        if source_id:
            for s in sources:
                if s.source_id == source_id:
                    return s
        return self.register_source(
            lane=lane,
            source_type=source_type,
            label=label,
            uri=uri,
            metadata=metadata,
            source_id=source_id,
        )

    def update_source(self, source: ResearchSource) -> bool:
        """Replace an existing source by source_id. Returns True if found and updated."""
        sources = self._load()
        replaced = False
        new_list: List[ResearchSource] = []
        for s in sources:
            if s.source_id == source.source_id:
                new_list.append(source)
                replaced = True
            else:
                new_list.append(s)
        if replaced:
            self._save(new_list)
        return replaced

    def source_count(self, lane: Optional[ResearchSourceLane] = None) -> int:
        return len(self.list_sources(lane=lane))

    def to_dict(self) -> Dict[str, Any]:
        sources = self._load()
        return {
            "project_id": self.project_id,
            "source_count": len(sources),
            "lane_a_count": sum(1 for s in sources if s.lane == ResearchSourceLane.LaneA),
            "lane_b_count": sum(1 for s in sources if s.lane == ResearchSourceLane.LaneB),
            "sources": [s.model_dump() for s in sources],
        }
