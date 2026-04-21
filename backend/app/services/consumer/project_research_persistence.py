"""Project-level research workspace persistence for findings and snapshots.

Persists and loads formal research artifacts under the project research
workspace so downstream consumers (report, simulation) can use them
instead of relying solely on ad hoc embedded copies.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from .models import ResearchFinding, ResearchSnapshot


RESEARCH_DIR_NAME = "research"
FINDINGS_FILE_NAME = "findings.json"
SNAPSHOT_FILE_NAME = "research_snapshot.json"


def _get_research_dir(project_id: str, upload_root: Optional[str] = None) -> Path:
    root = Path(upload_root) if upload_root else Path(__file__).resolve().parents[3] / "uploads"
    return root / "projects" / project_id / RESEARCH_DIR_NAME


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def persist_findings(
    project_id: str,
    findings: List[ResearchFinding],
    upload_root: Optional[str] = None,
) -> Path:
    """Persist findings to the project research workspace.

    Returns the path to the written file.
    """
    research_dir = _get_research_dir(project_id, upload_root)
    research_dir.mkdir(parents=True, exist_ok=True)

    payload: Dict[str, Any] = {
        "project_id": project_id,
        "created_at": _now_iso(),
        "finding_count": len(findings),
        "findings": [f.model_dump() for f in findings],
    }

    findings_path = research_dir / FINDINGS_FILE_NAME
    with findings_path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    return findings_path


def persist_snapshot(
    project_id: str,
    snapshot: ResearchSnapshot,
    upload_root: Optional[str] = None,
) -> Path:
    """Persist a research snapshot to the project research workspace.

    Returns the path to the written file.
    """
    research_dir = _get_research_dir(project_id, upload_root)
    research_dir.mkdir(parents=True, exist_ok=True)

    payload: Dict[str, Any] = {
        "project_id": project_id,
        "snapshot_id": snapshot.snapshot_id,
        "created_at": snapshot.created_at,
        "source_count": len(snapshot.sources),
        "document_count": len(snapshot.documents),
        "chunk_count": len(snapshot.chunks),
        "finding_count": len(snapshot.findings),
        "retrieval_trace_count": len(snapshot.retrieval_traces),
        "snapshot": snapshot.model_dump(),
    }

    snapshot_path = research_dir / SNAPSHOT_FILE_NAME
    with snapshot_path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    return snapshot_path


def load_persisted_findings(
    project_id: str,
    upload_root: Optional[str] = None,
) -> Optional[List[ResearchFinding]]:
    """Load persisted findings from the project research workspace.

    Returns None if the findings file does not exist.
    """
    findings_path = _get_research_dir(project_id, upload_root) / FINDINGS_FILE_NAME
    if not findings_path.exists():
        return None

    with findings_path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    findings_data = data.get("findings", [])
    return [ResearchFinding(**item) for item in findings_data]


def load_persisted_snapshot(
    project_id: str,
    upload_root: Optional[str] = None,
) -> Optional[ResearchSnapshot]:
    """Load a persisted research snapshot from the project research workspace.

    Returns None if the snapshot file does not exist.
    """
    snapshot_path = _get_research_dir(project_id, upload_root) / SNAPSHOT_FILE_NAME
    if not snapshot_path.exists():
        return None

    with snapshot_path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    snapshot_data = data.get("snapshot")
    if snapshot_data is None:
        return None

    return ResearchSnapshot(**snapshot_data)


def load_persisted_retrieval_traces(
    project_id: str,
    upload_root: Optional[str] = None,
) -> Optional[List[Dict[str, Any]]]:
    """Load retrieval traces from the persisted snapshot wrapper.

    Returns None if the snapshot file does not exist.
    """
    snapshot_path = _get_research_dir(project_id, upload_root) / SNAPSHOT_FILE_NAME
    if not snapshot_path.exists():
        return None

    with snapshot_path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    snapshot_data = data.get("snapshot")
    if snapshot_data is None:
        return None

    traces = snapshot_data.get("retrieval_traces", [])
    return traces if traces else None


def artifacts_exist(
    project_id: str,
    upload_root: Optional[str] = None,
) -> bool:
    """Return True if both findings and snapshot artifacts exist."""
    research_dir = _get_research_dir(project_id, upload_root)
    findings_path = research_dir / FINDINGS_FILE_NAME
    snapshot_path = research_dir / SNAPSHOT_FILE_NAME
    return findings_path.exists() and snapshot_path.exists()
