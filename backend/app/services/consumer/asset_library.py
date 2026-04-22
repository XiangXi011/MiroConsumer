"""Research asset export and persistence for consumer_test simulations."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from ...config import Config
from .report_context import ConsumerReportContextBuilder
from .scoring import ConsumerScoringService, build_consumer_summary
from .project_research_persistence import (
    artifacts_exist,
    load_persisted_findings,
    load_persisted_snapshot,
)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _assets_dir(upload_root: Optional[str] = None) -> Path:
    root = Path(upload_root) if upload_root else Path(Config.UPLOAD_FOLDER)
    return root / "research_assets"


def _asset_path(asset_id: str, upload_root: Optional[str] = None) -> Path:
    return _assets_dir(upload_root) / f"{asset_id}.json"


def _load_simulation_state(simulation_id: str, upload_root: Optional[str] = None) -> Optional[Dict[str, Any]]:
    state_path = Path(upload_root) / "simulations" / simulation_id / "state.json" if upload_root else Path(Config.UPLOAD_FOLDER) / "simulations" / simulation_id / "state.json"
    if not state_path.exists():
        return None
    return json.loads(state_path.read_text(encoding="utf-8"))


def _load_consumer_config(simulation_id: str, upload_root: Optional[str] = None) -> Dict[str, Any]:
    config_path = Path(upload_root) / "simulations" / simulation_id / "consumer_config.json" if upload_root else Path(Config.UPLOAD_FOLDER) / "simulations" / simulation_id / "consumer_config.json"
    if not config_path.exists():
        return {}
    return json.loads(config_path.read_text(encoding="utf-8"))


def _load_rounds_events(simulation_id: str, branch_id: Optional[str] = None, upload_root: Optional[str] = None) -> List[Dict[str, Any]]:
    root = Path(upload_root) if upload_root else Path(Config.UPLOAD_FOLDER)
    if branch_id:
        rounds_path = root / "simulations" / simulation_id / "branches" / branch_id / "rounds.jsonl"
    else:
        rounds_path = root / "simulations" / simulation_id / "consumer_rounds.jsonl"
    builder = ConsumerReportContextBuilder()
    return builder.load_events(str(rounds_path))


def _resolve_project_id(simulation_id: str, upload_root: Optional[str] = None) -> Optional[str]:
    state = _load_simulation_state(simulation_id, upload_root)
    if state:
        return state.get("project_id")
    return None


def _build_asset_pack(
    project_id: str,
    simulation_id: str,
    branch_id: Optional[str] = None,
    name: Optional[str] = None,
    upload_root: Optional[str] = None,
) -> Dict[str, Any]:
    """Build a research asset pack from simulation/branch data."""
    events = _load_rounds_events(simulation_id, branch_id, upload_root)
    if not events:
        raise ValueError(f"No round events found for simulation {simulation_id}{f' branch {branch_id}' if branch_id else ''}")

    builder = ConsumerReportContextBuilder()
    context = builder.build(events)

    # Extract propagation events
    all_events = []
    for snap in events:
        for event_data in snap.get("propagation_events", []):
            all_events.append(event_data)

    # Load research findings and snapshot (prefer project-level artifacts)
    research_findings: List[Any] = []
    retrieval_traces: List[Any] = []
    research_snapshot: Dict[str, Any] = {}
    source_catalog: List[Dict[str, Any]] = []

    loaded_from_project = False
    if artifacts_exist(project_id, upload_root=upload_root or Config.UPLOAD_FOLDER):
        persisted_findings = load_persisted_findings(project_id, upload_root=upload_root or Config.UPLOAD_FOLDER)
        persisted_snapshot = load_persisted_snapshot(project_id, upload_root=upload_root or Config.UPLOAD_FOLDER)
        if persisted_findings is not None and persisted_snapshot is not None:
            research_findings = [f.model_dump() for f in persisted_findings]
            research_snapshot = {
                "snapshot_id": persisted_snapshot.snapshot_id,
                "source_count": len(persisted_snapshot.sources),
                "document_count": len(persisted_snapshot.documents),
                "chunk_count": len(persisted_snapshot.chunks),
                "finding_count": len(persisted_snapshot.findings),
                "retrieval_trace_count": len(persisted_snapshot.retrieval_traces),
            }
            retrieval_traces = [t.model_dump() for t in persisted_snapshot.retrieval_traces]
            loaded_from_project = True
            from .report_context import _build_source_catalog
            source_catalog = _build_source_catalog(persisted_snapshot)

    if not loaded_from_project:
        consumer_config = _load_consumer_config(simulation_id, upload_root)
        research_findings = consumer_config.get("research_findings", [])
        retrieval_traces = consumer_config.get("retrieval_traces", [])
        research_snapshot = consumer_config.get("research_snapshot", {})

    # Merge Phase 2 fields when propagation events exist
    evidence_bundle = context.get("evidence_bundle", {})
    if all_events:
        initial_labels = [s.get("attitude_label", "neutral") for s in events if s.get("round_num") == 0]
        latest_attitudes: Dict[str, str] = {}
        for s in events:
            agent_id = s.get("agent_id", "")
            if agent_id:
                latest_attitudes[agent_id] = s.get("attitude_label", "neutral")
        final_labels = list(latest_attitudes.values())

        phase2_summary = build_consumer_summary(
            events=all_events,
            findings=research_findings,
            initial_labels=initial_labels,
            final_labels=final_labels,
        )
        from .report_context import build_consumer_report_context
        phase2_context = build_consumer_report_context(
            summary=phase2_summary,
            findings=research_findings,
            events=all_events,
            traces=retrieval_traces,
            snapshot=persisted_snapshot if loaded_from_project else None,
        )
        evidence_bundle = phase2_summary.evidence_bundle.to_dict()
        if not source_catalog and "source_catalog" in phase2_context:
            source_catalog = phase2_context["source_catalog"]

    summary = context["summary"]
    asset_name = name or f"Research Pack {simulation_id}{f' ({branch_id})' if branch_id else ''}"

    return {
        "asset_id": f"asset_{uuid.uuid4().hex[:12]}",
        "asset_type": "consumer_research_pack",
        "project_id": project_id,
        "simulation_id": simulation_id,
        "branch_id": branch_id,
        "name": asset_name,
        "created_at": _now_iso(),
        "summary": {
            "source_count": research_snapshot.get("source_count", 0),
            "finding_count": len(research_findings),
            "resonance_points": len(context.get("top_resonance_points", [])),
            "risk_points": len(context.get("top_risk_points", [])),
            "misreads": len(context.get("top_misreads", [])),
            "acceptance_positive": summary.get("post_propagation_acceptance", {}).get("positive", 0.0),
        },
        "source_catalog": source_catalog,
        "research_snapshot": research_snapshot,
        "research_findings": research_findings,
        "representative_voc_quotes": context.get("representative_voc_quotes", {}),
        "evidence_bundle": evidence_bundle,
    }


def export_asset(
    project_id: str,
    simulation_id: Optional[str] = None,
    branch_id: Optional[str] = None,
    name: Optional[str] = None,
    upload_root: Optional[str] = None,
) -> Dict[str, Any]:
    """Export and persist a research asset pack."""
    if not simulation_id:
        # Try to find a simulation for this project
        raise ValueError("simulation_id is required")

    pack = _build_asset_pack(
        project_id=project_id,
        simulation_id=simulation_id,
        branch_id=branch_id,
        name=name,
        upload_root=upload_root,
    )

    path = _asset_path(pack["asset_id"], upload_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(pack, ensure_ascii=False, indent=2), encoding="utf-8")
    return pack


def list_assets(project_id: str, upload_root: Optional[str] = None) -> List[Dict[str, Any]]:
    """List all research asset packs for a project."""
    assets_dir = _assets_dir(upload_root)
    if not assets_dir.exists():
        return []

    items: List[Dict[str, Any]] = []
    for path in assets_dir.glob("asset_*.json"):
        data = json.loads(path.read_text(encoding="utf-8"))
        if data.get("project_id") == project_id:
            items.append(data)
    items.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    return items


def get_asset(asset_id: str, upload_root: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Get a single research asset pack by ID."""
    path = _asset_path(asset_id, upload_root)
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def delete_asset(asset_id: str, upload_root: Optional[str] = None) -> bool:
    """Delete a research asset pack by ID."""
    path = _asset_path(asset_id, upload_root)
    if not path.exists():
        return False
    path.unlink()
    return True


__all__ = [
    "export_asset",
    "list_assets",
    "get_asset",
    "delete_asset",
]
