"""Comparison engine for consumer_test research snapshots."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from ...config import Config
from .intervention_manager import ConsumerInterventionManager
from .report_context import ConsumerReportContextBuilder
from .scoring import ConsumerScoringService


def _side_confidence_from_findings(findings: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Extract or compute confidence for a side from its findings."""
    if not findings:
        return {
            "confidence_label": "unknown",
            "confidence_score": 0.0,
            "confidence_reasons": ["no_findings"],
            "support_summary": "No findings available",
        }

    # Use existing confidence scores if present
    scores: List[float] = []
    labels: List[str] = []
    for f in findings:
        score = f.get("confidence")
        if isinstance(score, (int, float)) and score > 0:
            scores.append(float(score))
        label = f.get("confidence_label", "")
        if label:
            labels.append(label)

    if scores:
        avg_score = sum(scores) / len(scores)
        if avg_score >= 0.75:
            label = "high"
        elif avg_score >= 0.5:
            label = "medium"
        elif avg_score >= 0.25:
            label = "low"
        else:
            label = "unknown"
        return {
            "confidence_label": label,
            "confidence_score": round(avg_score, 4),
            "confidence_reasons": [f"derived_from_{len(scores)}_finding_scores"],
            "support_summary": f"Average confidence from {len(scores)} findings: {round(avg_score, 2)}",
        }

    # Fallback: try to compute from source_quality fields
    from .confidence_scoring import (
        compute_report_confidence,
        build_confidence_summary,
    )
    from .evidence_validator import validate_findings, build_evidence_validation_summary
    from .models import ResearchFinding

    typed_findings = []
    for f in findings:
        if isinstance(f, dict):
            typed_findings.append(ResearchFinding(**f))
        else:
            typed_findings.append(f)

    validations = validate_findings(typed_findings)
    report_conf = compute_report_confidence(typed_findings, validations, [])
    return build_confidence_summary(report_conf)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _comparisons_dir(upload_root: Optional[str] = None) -> Path:
    root = Path(upload_root) if upload_root else Path(Config.UPLOAD_FOLDER)
    return root / "research_assets" / "comparisons"


def _comparison_path(comparison_id: str, upload_root: Optional[str] = None) -> Path:
    return _comparisons_dir(upload_root) / f"{comparison_id}.json"


def _load_simulation_state(simulation_id: str, upload_root: Optional[str] = None) -> Optional[Dict[str, Any]]:
    root = Path(upload_root) if upload_root else Path(Config.UPLOAD_FOLDER)
    state_path = root / "simulations" / simulation_id / "state.json"
    if not state_path.exists():
        return None
    return json.loads(state_path.read_text(encoding="utf-8"))


def _load_rounds_events(simulation_id: str, branch_id: Optional[str] = None, upload_root: Optional[str] = None) -> List[Dict[str, Any]]:
    root = Path(upload_root) if upload_root else Path(Config.UPLOAD_FOLDER)
    if branch_id:
        rounds_path = root / "simulations" / simulation_id / "branches" / branch_id / "rounds.jsonl"
    else:
        rounds_path = root / "simulations" / simulation_id / "consumer_rounds.jsonl"
    builder = ConsumerReportContextBuilder()
    return builder.load_events(str(rounds_path))


def _summarize_side(
    simulation_id: str,
    branch_id: Optional[str] = None,
    label: Optional[str] = None,
    upload_root: Optional[str] = None,
) -> Dict[str, Any]:
    """Build a comparison side summary from simulation/branch rounds."""
    events = _load_rounds_events(simulation_id, branch_id, upload_root)
    if not events:
        return {
            "label": label or simulation_id,
            "kind": "branch" if branch_id else "run",
            "id": branch_id or simulation_id,
            "acceptance_positive": 0.0,
            "resonance_points": [],
            "risk_points": [],
        }

    builder = ConsumerReportContextBuilder()
    context = builder.build(events)
    summary = context["summary"]

    return {
        "label": label or (branch_id if branch_id else simulation_id),
        "kind": "branch" if branch_id else "run",
        "id": branch_id or simulation_id,
        "acceptance_positive": summary.get("post_propagation_acceptance", {}).get("positive", 0.0),
        "resonance_points": context.get("top_resonance_points", []),
        "risk_points": context.get("top_risk_points", []),
    }


def _extract_signals_from_findings(findings: List[Dict[str, Any]]) -> Dict[str, List[str]]:
    """Map finding summaries to source labels for divergence analysis."""
    signals: Dict[str, List[str]] = {}
    for f in findings:
        summary = f.get("summary", "").strip()
        if summary:
            signals.setdefault(summary, []).append(f.get("source_label", "unknown"))
    return signals


def _compute_evidence_backed_divergences(
    left_findings: List[Dict[str, Any]],
    right_findings: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Find signals present in one side but not the other, with source attribution."""
    left_signals = _extract_signals_from_findings(left_findings)
    right_signals = _extract_signals_from_findings(right_findings)

    all_signals = set(left_signals.keys()) | set(right_signals.keys())
    divergences: List[Dict[str, Any]] = []
    for signal in sorted(all_signals):
        left_presence = signal in left_signals
        right_presence = signal in right_signals
        if left_presence != right_presence or (left_presence and right_presence and left_signals[signal] != right_signals[signal]):
            divergences.append({
                "signal": signal,
                "left_presence": left_presence,
                "right_presence": right_presence,
                "left_sources": list(set(left_signals.get(signal, []))),
                "right_sources": list(set(right_signals.get(signal, []))),
            })
    return divergences


def _load_findings(simulation_id: str, upload_root: Optional[str] = None) -> List[Dict[str, Any]]:
    """Load research findings for a simulation from consumer_config."""
    root = Path(upload_root) if upload_root else Path(Config.UPLOAD_FOLDER)
    config_path = root / "simulations" / simulation_id / "consumer_config.json"
    if not config_path.exists():
        return []
    data = json.loads(config_path.read_text(encoding="utf-8"))
    return data.get("research_findings", [])


def _load_branch_findings(simulation_id: str, branch_id: str, upload_root: Optional[str] = None) -> List[Dict[str, Any]]:
    """Load research findings for a branch; falls back to simulation consumer_config."""
    # Branches inherit findings from the parent simulation config
    return _load_findings(simulation_id, upload_root)


def _compute_source_overlap_count(
    left_findings: List[Dict[str, Any]],
    right_findings: List[Dict[str, Any]],
) -> int:
    """Count overlapping source labels between two finding sets."""
    left_sources: Set[str] = set()
    right_sources: Set[str] = set()
    for f in left_findings:
        src = f.get("source_label", "")
        if src:
            left_sources.add(src)
    for f in right_findings:
        src = f.get("source_label", "")
        if src:
            right_sources.add(src)
    return len(left_sources & right_sources)


def compare_run_vs_run(
    left_simulation_id: str,
    right_simulation_id: str,
    upload_root: Optional[str] = None,
) -> Dict[str, Any]:
    """Compare two simulation runs."""
    left = _summarize_side(left_simulation_id, upload_root=upload_root)
    right = _summarize_side(right_simulation_id, upload_root=upload_root)

    left["label"] = left_simulation_id
    right["label"] = right_simulation_id

    left_findings = _load_findings(left_simulation_id, upload_root)
    right_findings = _load_findings(right_simulation_id, upload_root)

    resonance_overlap = list(set(left["resonance_points"]) & set(right["resonance_points"]))
    recurring_risk_signals = list(set(left["risk_points"]) & set(right["risk_points"]))
    divergences = _compute_evidence_backed_divergences(left_findings, right_findings)
    acceptance_delta_pp = round((right["acceptance_positive"] - left["acceptance_positive"]) * 100, 4)
    source_overlap_count = _compute_source_overlap_count(left_findings, right_findings)

    left_state = _load_simulation_state(left_simulation_id, upload_root)
    right_state = _load_simulation_state(right_simulation_id, upload_root)
    project_ids = []
    if left_state and left_state.get("project_id"):
        project_ids.append(left_state["project_id"])
    if right_state and right_state.get("project_id") and right_state["project_id"] not in project_ids:
        project_ids.append(right_state["project_id"])

    left_confidence = _side_confidence_from_findings(left_findings)
    right_confidence = _side_confidence_from_findings(right_findings)
    from .confidence_scoring import compute_comparison_confidence

    return {
        "comparison_id": f"cmp_{uuid.uuid4().hex[:12]}",
        "mode": "run_vs_run",
        "created_at": _now_iso(),
        "project_ids": project_ids,
        "left": left,
        "right": right,
        "resonance_overlap": resonance_overlap,
        "recurring_risk_signals": recurring_risk_signals,
        "evidence_backed_divergences": divergences,
        "acceptance_delta_pp": acceptance_delta_pp,
        "source_overlap_count": source_overlap_count,
        "left_confidence": left_confidence,
        "right_confidence": right_confidence,
        "comparison_confidence": compute_comparison_confidence(left_confidence, right_confidence),
    }


def compare_branch_vs_base(
    simulation_id: str,
    branch_id: str,
    upload_root: Optional[str] = None,
) -> Dict[str, Any]:
    """Compare a branch against its base using ConsumerInterventionManager."""
    branches_dir = (Path(upload_root) / "simulations" / simulation_id / "branches") if upload_root else None
    mgr = ConsumerInterventionManager(branches_dir=str(branches_dir) if branches_dir else None)
    comparison_ctx = mgr.build_comparison_context(simulation_id, branch_id)

    branch = mgr.get_branch(simulation_id, branch_id)
    base_branch_id = branch.parent_branch_id if branch else None

    base_summary = comparison_ctx.get("base_summary", {})
    branch_summary = comparison_ctx.get("branch_summary", {})

    left = {
        "label": base_branch_id or "base",
        "kind": "branch" if base_branch_id else "run",
        "id": base_branch_id or simulation_id,
        "acceptance_positive": base_summary.get("post_propagation_acceptance", {}).get("positive", 0.0),
        "resonance_points": [],
        "risk_points": [],
    }
    right = {
        "label": branch.name if branch else branch_id,
        "kind": "branch",
        "id": branch_id,
        "acceptance_positive": branch_summary.get("post_propagation_acceptance", {}).get("positive", 0.0),
        "resonance_points": [],
        "risk_points": [],
    }

    # Enrich resonance/risk points from actual events when available
    if base_summary.get("has_data"):
        base_events = _load_rounds_events(simulation_id, base_branch_id, upload_root)
        if base_events:
            builder = ConsumerReportContextBuilder()
            base_ctx = builder.build(base_events)
            left["resonance_points"] = base_ctx.get("top_resonance_points", [])
            left["risk_points"] = base_ctx.get("top_risk_points", [])

    if branch_summary.get("has_data"):
        branch_events = _load_rounds_events(simulation_id, branch_id, upload_root)
        if branch_events:
            builder = ConsumerReportContextBuilder()
            branch_ctx = builder.build(branch_events)
            right["resonance_points"] = branch_ctx.get("top_resonance_points", [])
            right["risk_points"] = branch_ctx.get("top_risk_points", [])

    left_findings = _load_branch_findings(simulation_id, base_branch_id or branch_id, upload_root)
    right_findings = _load_branch_findings(simulation_id, branch_id, upload_root)

    resonance_overlap = list(set(left["resonance_points"]) & set(right["resonance_points"]))
    recurring_risk_signals = list(set(left["risk_points"]) & set(right["risk_points"]))
    divergences = _compute_evidence_backed_divergences(left_findings, right_findings)
    acceptance_delta_pp = round((right["acceptance_positive"] - left["acceptance_positive"]) * 100, 4)
    source_overlap_count = _compute_source_overlap_count(left_findings, right_findings)

    state = _load_simulation_state(simulation_id, upload_root)
    project_ids = []
    if state and state.get("project_id"):
        project_ids.append(state["project_id"])

    left_confidence = _side_confidence_from_findings(left_findings)
    right_confidence = _side_confidence_from_findings(right_findings)
    from .confidence_scoring import compute_comparison_confidence

    return {
        "comparison_id": f"cmp_{uuid.uuid4().hex[:12]}",
        "mode": "branch_vs_base",
        "created_at": _now_iso(),
        "project_ids": project_ids,
        "left": left,
        "right": right,
        "resonance_overlap": resonance_overlap,
        "recurring_risk_signals": recurring_risk_signals,
        "evidence_backed_divergences": divergences,
        "acceptance_delta_pp": acceptance_delta_pp,
        "source_overlap_count": source_overlap_count,
        "left_confidence": left_confidence,
        "right_confidence": right_confidence,
        "comparison_confidence": compute_comparison_confidence(left_confidence, right_confidence),
    }


def compare_project_vs_project(
    left_project_id: str,
    right_project_id: str,
    upload_root: Optional[str] = None,
) -> Dict[str, Any]:
    """Compare two projects using their latest simulation data if available."""
    # Projects don't have direct simulation data here; we load findings from their research workspace
    from .project_research_persistence import load_persisted_findings

    left_findings_raw = load_persisted_findings(left_project_id, upload_root=upload_root)
    right_findings_raw = load_persisted_findings(right_project_id, upload_root=upload_root)

    left_findings = [f.model_dump() for f in left_findings_raw] if left_findings_raw else []
    right_findings = [f.model_dump() for f in right_findings_raw] if right_findings_raw else []

    left = {
        "label": left_project_id,
        "kind": "project",
        "id": left_project_id,
        "acceptance_positive": 0.0,
        "resonance_points": [],
        "risk_points": [],
    }
    right = {
        "label": right_project_id,
        "kind": "project",
        "id": right_project_id,
        "acceptance_positive": 0.0,
        "resonance_points": [],
        "risk_points": [],
    }

    divergences = _compute_evidence_backed_divergences(left_findings, right_findings)
    source_overlap_count = _compute_source_overlap_count(left_findings, right_findings)

    left_confidence = _side_confidence_from_findings(left_findings)
    right_confidence = _side_confidence_from_findings(right_findings)
    from .confidence_scoring import compute_comparison_confidence

    return {
        "comparison_id": f"cmp_{uuid.uuid4().hex[:12]}",
        "mode": "project_vs_project",
        "created_at": _now_iso(),
        "project_ids": [left_project_id, right_project_id],
        "left": left,
        "right": right,
        "resonance_overlap": [],
        "recurring_risk_signals": [],
        "evidence_backed_divergences": divergences,
        "acceptance_delta_pp": 0.0,
        "source_overlap_count": source_overlap_count,
        "left_confidence": left_confidence,
        "right_confidence": right_confidence,
        "comparison_confidence": compute_comparison_confidence(left_confidence, right_confidence),
    }


def create_comparison(
    mode: str,
    left_simulation_id: Optional[str] = None,
    right_simulation_id: Optional[str] = None,
    simulation_id: Optional[str] = None,
    branch_id: Optional[str] = None,
    left_project_id: Optional[str] = None,
    right_project_id: Optional[str] = None,
    upload_root: Optional[str] = None,
) -> Dict[str, Any]:
    """Create and persist a comparison snapshot."""
    if mode == "run_vs_run":
        if not left_simulation_id or not right_simulation_id:
            raise ValueError("run_vs_run requires left_simulation_id and right_simulation_id")
        snapshot = compare_run_vs_run(left_simulation_id, right_simulation_id, upload_root)
    elif mode == "branch_vs_base":
        if not simulation_id or not branch_id:
            raise ValueError("branch_vs_base requires simulation_id and branch_id")
        snapshot = compare_branch_vs_base(simulation_id, branch_id, upload_root)
    elif mode == "project_vs_project":
        if not left_project_id or not right_project_id:
            raise ValueError("project_vs_project requires left_project_id and right_project_id")
        snapshot = compare_project_vs_project(left_project_id, right_project_id, upload_root)
    else:
        raise ValueError(f"Unsupported comparison mode: {mode}")

    path = _comparison_path(snapshot["comparison_id"], upload_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2), encoding="utf-8")
    return snapshot


def list_comparisons(project_id: str, upload_root: Optional[str] = None) -> List[Dict[str, Any]]:
    """List comparison snapshots that involve the given project."""
    comp_dir = _comparisons_dir(upload_root)
    if not comp_dir.exists():
        return []

    items: List[Dict[str, Any]] = []
    for path in comp_dir.glob("cmp_*.json"):
        data = json.loads(path.read_text(encoding="utf-8"))
        project_ids = data.get("project_ids", [])
        if project_id in project_ids:
            items.append(data)
    items.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    return items


def get_comparison(comparison_id: str, upload_root: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Get a single comparison snapshot by ID."""
    path = _comparison_path(comparison_id, upload_root)
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def delete_comparison(comparison_id: str, upload_root: Optional[str] = None) -> bool:
    """Delete a comparison snapshot by ID."""
    path = _comparison_path(comparison_id, upload_root)
    if not path.exists():
        return False
    path.unlink()
    return True


__all__ = [
    "create_comparison",
    "list_comparisons",
    "get_comparison",
    "delete_comparison",
    "compare_run_vs_run",
    "compare_branch_vs_base",
    "compare_project_vs_project",
]
