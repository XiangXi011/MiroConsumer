from pathlib import Path
import sys


BACKEND_ROOT = Path(__file__).resolve().parents[2]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.services.consumer.models import ResearchFinding, ResearchSnapshot, GraphVisibility
from app.services.consumer.project_research_persistence import (
    artifacts_exist,
    load_persisted_findings,
    load_persisted_snapshot,
    persist_findings,
    persist_snapshot,
)


def test_persist_findings_writes_correct_file(tmp_path):
    root = str(tmp_path / "uploads")
    findings = [
        ResearchFinding(
            finding_id="f1",
            finding_type="risk_signal",
            summary="Sweetener concern",
            visibility=GraphVisibility.Restricted,
            source_label="brief_background",
        ),
        ResearchFinding(
            finding_id="f2",
            finding_type="category_context",
            summary="Target audience: busy commuters",
            visibility=GraphVisibility.Propagation_Only,
            source_label="auto_enrich",
        ),
    ]

    path = persist_findings("proj_test", findings, upload_root=root)

    assert path.exists()
    import json

    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["project_id"] == "proj_test"
    assert data["finding_count"] == 2
    assert len(data["findings"]) == 2
    assert data["findings"][0]["finding_id"] == "f1"
    assert data["findings"][1]["finding_id"] == "f2"
    assert "created_at" in data


def test_persist_snapshot_writes_correct_file(tmp_path):
    root = str(tmp_path / "uploads")
    snapshot = ResearchSnapshot(
        snapshot_id="rsnap_proj_test",
        project_id="proj_test",
        created_at="2026-04-21T10:00:00+00:00",
        sources=[],
        documents=[],
        chunks=[],
        findings=[
            ResearchFinding(
                finding_id="f1",
                finding_type="risk_signal",
                summary="Sweetener concern",
                visibility=GraphVisibility.Restricted,
            )
        ],
        retrieval_traces=[],
        summary="Test summary",
    )

    path = persist_snapshot("proj_test", snapshot, upload_root=root)

    assert path.exists()
    import json

    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["project_id"] == "proj_test"
    assert data["snapshot_id"] == "rsnap_proj_test"
    assert data["source_count"] == 0
    assert data["document_count"] == 0
    assert data["chunk_count"] == 0
    assert data["finding_count"] == 1
    assert data["retrieval_trace_count"] == 0
    assert data["snapshot"]["summary"] == "Test summary"


def test_load_persisted_findings_round_trips(tmp_path):
    root = str(tmp_path / "uploads")
    findings = [
        ResearchFinding(
            finding_id="f1",
            finding_type="risk_signal",
            summary="Sweetener concern",
            visibility=GraphVisibility.Restricted,
            source_label="brief_background",
        )
    ]
    persist_findings("proj_roundtrip", findings, upload_root=root)

    loaded = load_persisted_findings("proj_roundtrip", upload_root=root)

    assert loaded is not None
    assert len(loaded) == 1
    assert loaded[0].finding_id == "f1"
    assert loaded[0].finding_type == "risk_signal"
    assert loaded[0].summary == "Sweetener concern"
    assert loaded[0].visibility == GraphVisibility.Restricted
    assert loaded[0].source_label == "brief_background"


def test_load_persisted_snapshot_round_trips(tmp_path):
    root = str(tmp_path / "uploads")
    snapshot = ResearchSnapshot(
        snapshot_id="rsnap_roundtrip",
        project_id="proj_roundtrip",
        created_at="2026-04-21T10:00:00+00:00",
        sources=[],
        documents=[],
        chunks=[],
        findings=[
            ResearchFinding(
                finding_id="f1",
                finding_type="risk_signal",
                summary="Sweetener concern",
                visibility=GraphVisibility.Restricted,
            )
        ],
        retrieval_traces=[],
        summary="Roundtrip summary",
    )
    persist_snapshot("proj_roundtrip", snapshot, upload_root=root)

    loaded = load_persisted_snapshot("proj_roundtrip", upload_root=root)

    assert loaded is not None
    assert loaded.snapshot_id == "rsnap_roundtrip"
    assert loaded.project_id == "proj_roundtrip"
    assert loaded.summary == "Roundtrip summary"
    assert len(loaded.findings) == 1
    assert loaded.findings[0].finding_id == "f1"


def test_load_persisted_findings_returns_none_when_missing(tmp_path):
    root = str(tmp_path / "uploads")
    loaded = load_persisted_findings("proj_missing", upload_root=root)
    assert loaded is None


def test_load_persisted_snapshot_returns_none_when_missing(tmp_path):
    root = str(tmp_path / "uploads")
    loaded = load_persisted_snapshot("proj_missing", upload_root=root)
    assert loaded is None


def test_artifacts_exist_when_both_present(tmp_path):
    root = str(tmp_path / "uploads")
    persist_findings("proj_exists", [], upload_root=root)
    persist_snapshot(
        "proj_exists",
        ResearchSnapshot(snapshot_id="s1", project_id="proj_exists", created_at="2026-04-21T10:00:00+00:00"),
        upload_root=root,
    )

    assert artifacts_exist("proj_exists", upload_root=root) is True


def test_artifacts_exist_false_when_missing(tmp_path):
    root = str(tmp_path / "uploads")
    assert artifacts_exist("proj_none", upload_root=root) is False

    # Only findings present
    persist_findings("proj_partial", [], upload_root=root)
    assert artifacts_exist("proj_partial", upload_root=root) is False
