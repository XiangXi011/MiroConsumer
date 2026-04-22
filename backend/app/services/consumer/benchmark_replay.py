"""Benchmark replay for consumer_test simulations.

Replays a saved benchmark case against current simulation output and compares
stable derived signals. Persists replay results under:
- backend/uploads/benchmarks/replay_runs/{replay_id}.json
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from ...config import Config
from .benchmark_registry import get_benchmark


def _replay_runs_dir(upload_root: Optional[str] = None) -> Path:
    root = Path(upload_root) if upload_root else Path(Config.UPLOAD_FOLDER)
    return root / "benchmarks" / "replay_runs"


def _replay_path(replay_id: str, upload_root: Optional[str] = None) -> Path:
    return _replay_runs_dir(upload_root) / f"{replay_id}.json"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _acceptance_band_from_acceptance(acceptance: Dict[str, float]) -> str:
    """Map acceptance ratios to a band label."""
    positive = acceptance.get("positive", 0.0)
    negative = acceptance.get("negative", 0.0)
    if positive >= 0.55:
        return "positive_lean"
    if negative >= 0.55:
        return "negative_lean"
    return "mixed"


def _cascade_band_from_metrics(cascade_metrics: Dict[str, Any]) -> str:
    """Map cascade metrics to a cascade band label."""
    narrative_takeover = cascade_metrics.get("narrative_takeover_score", 0.0) or 0.0
    cross_community = cascade_metrics.get("cross_community_event_count", 0) or 0
    if narrative_takeover >= 0.7:
        return "takeover"
    if cross_community >= 3:
        return "spreading"
    return "contained"


def extract_stable_signals(report_context: Dict[str, Any]) -> Dict[str, Any]:
    """Extract stable derived signals from a report context.

    Stable signals (per Phase 4A spec):
    - acceptance_band: positive_lean | mixed | negative_lean
    - top_resonance_labels: normalized labels from top resonance findings
    - top_risk_labels: normalized labels from top risk findings
    - misread_present: whether meaningful misread amplification occurred
    - clarification_recovery_present: whether clarification recovery occurred
    - cascade_band: contained | spreading | takeover
    """
    summary = report_context.get("summary", {})
    acceptance = summary.get("post_propagation_acceptance", {}) if isinstance(summary, dict) else {}
    if not isinstance(acceptance, dict):
        acceptance = {}

    top_resonance = report_context.get("top_resonance_points", []) or []
    top_risk = report_context.get("top_risk_points", []) or []
    top_misreads = report_context.get("top_misreads", []) or []
    top_clarifications = report_context.get("top_clarification_opportunities", []) or []
    cascade_metrics = report_context.get("cascade_metrics", {}) or {}

    signals: Dict[str, Any] = {
        "acceptance_band": _acceptance_band_from_acceptance(acceptance),
        "top_resonance_labels": list(top_resonance)[:5],
        "top_risk_labels": list(top_risk)[:5],
        "misread_present": len(top_misreads) > 0,
        "clarification_recovery_present": len(top_clarifications) > 0,
        "cascade_band": _cascade_band_from_metrics(cascade_metrics),
    }

    # Phase 5C: surface evidence quality from gatekeeping summary when available
    gatekeeping_summary = report_context.get("evidence_gatekeeping_summary")
    if gatekeeping_summary is not None:
        blocked_count = gatekeeping_summary.get("blocked_count", 0)
        downgraded_count = gatekeeping_summary.get("downgraded_count", 0)
        if blocked_count > 0:
            signals["evidence_quality_flag"] = "blocked_findings"
        elif downgraded_count > 0:
            signals["evidence_quality_flag"] = "downgraded_findings"
        else:
            signals["evidence_quality_flag"] = "clean"
        signals["evidence_gatekeeping_summary"] = gatekeeping_summary

    return signals


def _jaccard_similarity(a: List[str], b: List[str]) -> float:
    """Compute Jaccard similarity between two string lists."""
    set_a: Set[str] = set(str(x).strip().lower() for x in a if str(x).strip())
    set_b: Set[str] = set(str(x).strip().lower() for x in b if str(x).strip())
    if not set_a and not set_b:
        return 1.0
    intersection = set_a & set_b
    union = set_a | set_b
    if not union:
        return 1.0
    return len(intersection) / len(union)


def compare_replay_result(
    expected: Dict[str, Any],
    actual: Dict[str, Any],
) -> Dict[str, Any]:
    """Compare expected vs actual stable signals and compute alignment.

    Returns:
        Dict with alignment_status, metric_deltas, drift_signals, summary.
    """
    drift_signals: List[str] = []
    metric_deltas: Dict[str, float] = {}

    # Acceptance band match
    acceptance_match = 1.0 if expected.get("acceptance_band") == actual.get("acceptance_band") else 0.0
    metric_deltas["acceptance_band_match"] = acceptance_match
    if acceptance_match == 0.0:
        drift_signals.append(
            f"acceptance_band changed from {expected.get('acceptance_band')} to {actual.get('acceptance_band')}"
        )

    # Resonance overlap
    resonance_sim = _jaccard_similarity(
        expected.get("top_resonance_labels", []),
        actual.get("top_resonance_labels", []),
    )
    metric_deltas["resonance_overlap"] = round(resonance_sim, 4)
    if resonance_sim < 0.5:
        drift_signals.append(
            f"top_resonance_labels overlap dropped to {round(resonance_sim * 100)}%"
        )

    # Risk overlap
    risk_sim = _jaccard_similarity(
        expected.get("top_risk_labels", []),
        actual.get("top_risk_labels", []),
    )
    metric_deltas["risk_overlap"] = round(risk_sim, 4)
    if risk_sim < 0.5:
        drift_signals.append(
            f"top_risk_labels overlap dropped to {round(risk_sim * 100)}%"
        )

    # Misread presence match
    misread_match = 1.0 if expected.get("misread_present") == actual.get("misread_present") else 0.0
    metric_deltas["misread_match"] = misread_match
    if misread_match == 0.0:
        drift_signals.append(
            f"misread_present changed from {expected.get('misread_present')} to {actual.get('misread_present')}"
        )

    # Clarification recovery match
    clarification_match = 1.0 if expected.get("clarification_recovery_present") == actual.get("clarification_recovery_present") else 0.0
    metric_deltas["clarification_recovery_match"] = clarification_match
    if clarification_match == 0.0:
        drift_signals.append(
            f"clarification_recovery_present changed from {expected.get('clarification_recovery_present')} to {actual.get('clarification_recovery_present')}"
        )

    # Cascade band match
    cascade_match = 1.0 if expected.get("cascade_band") == actual.get("cascade_band") else 0.0
    metric_deltas["cascade_band_match"] = cascade_match
    if cascade_match == 0.0:
        drift_signals.append(
            f"cascade_band changed from {expected.get('cascade_band')} to {actual.get('cascade_band')}"
        )

    # Overall alignment
    overall_score = (
        acceptance_match
        + resonance_sim
        + risk_sim
        + misread_match
        + clarification_match
        + cascade_match
    ) / 6.0

    if overall_score >= 0.85 and len(drift_signals) == 0:
        alignment_status = "aligned"
    elif overall_score >= 0.5:
        alignment_status = "partial"
    else:
        alignment_status = "drift"

    summary = (
        f"Replay alignment: {alignment_status} "
        f"(score={round(overall_score, 2)}; "
        f"acceptance={expected.get('acceptance_band')}/{actual.get('acceptance_band')}; "
        f"resonance_overlap={round(resonance_sim, 2)}; "
        f"risk_overlap={round(risk_sim, 2)}; "
        f"cascade={expected.get('cascade_band')}/{actual.get('cascade_band')})"
    )

    return {
        "alignment_status": alignment_status,
        "metric_deltas": metric_deltas,
        "drift_signals": drift_signals,
        "overall_score": round(overall_score, 4),
        "summary": summary,
    }


def replay_benchmark(
    benchmark_id: str,
    report_context: Dict[str, Any],
    project_id: Optional[str] = None,
    simulation_id: Optional[str] = None,
    upload_root: Optional[str] = None,
) -> Dict[str, Any]:
    """Replay a benchmark against the current report context.

    Phase 5C: Down-weights or fails weak evidence by checking the report context's
    evidence_gatekeeping_summary. If findings are blocked, drift signals are added
    and the overall score is penalized.

    Args:
        benchmark_id: The benchmark to replay.
        report_context: Current simulation report context.
        project_id: Optional project ID.
        simulation_id: Optional simulation ID.
        upload_root: Optional upload root override.

    Returns:
        Replay result dict with replay_id, alignment_status, drift_signals, etc.
    """
    benchmark = get_benchmark(benchmark_id, upload_root=upload_root)
    if benchmark is None:
        raise ValueError(f"Benchmark not found: {benchmark_id}")

    expected_signals = benchmark.get("expected_signals", {})
    actual_signals = extract_stable_signals(report_context)
    comparison = compare_replay_result(expected_signals, actual_signals)

    # Phase 5C: Apply evidence gatekeeping penalties
    drift_signals = list(comparison["drift_signals"])
    overall_score = comparison["overall_score"]

    gatekeeping_summary = report_context.get("evidence_gatekeeping_summary")
    if gatekeeping_summary is not None:
        blocked_count = gatekeeping_summary.get("blocked_count", 0)
        downgraded_count = gatekeeping_summary.get("downgraded_count", 0)
        total_count = gatekeeping_summary.get("finding_count", 0)

        if blocked_count > 0 and total_count > 0:
            ratio = blocked_count / total_count
            drift_signals.append(
                f"evidence_gatekeeping_blocked:{blocked_count}/{total_count} findings blocked"
            )
            # Penalize overall score: up to -0.3 for all blocked
            penalty = min(0.3, 0.15 * ratio)
            overall_score = max(0.0, overall_score - penalty)

        if downgraded_count > 0 and total_count > 0:
            ratio = downgraded_count / total_count
            drift_signals.append(
                f"evidence_gatekeeping_downgraded:{downgraded_count}/{total_count} findings downgraded"
            )
            penalty = min(0.15, 0.075 * ratio)
            overall_score = max(0.0, overall_score - penalty)

        # Re-evaluate alignment status after penalties
        if overall_score >= 0.85 and len(drift_signals) == 0:
            alignment_status = "aligned"
        elif overall_score >= 0.5:
            alignment_status = "partial"
        else:
            alignment_status = "drift"

        summary = (
            f"Replay alignment: {alignment_status} "
            f"(score={round(overall_score, 2)}; "
            f"acceptance={expected_signals.get('acceptance_band')}/{actual_signals.get('acceptance_band')}; "
            f"resonance_overlap={round(comparison['metric_deltas'].get('resonance_overlap', 0.0), 2)}; "
            f"risk_overlap={round(comparison['metric_deltas'].get('risk_overlap', 0.0), 2)}; "
            f"cascade={expected_signals.get('cascade_band')}/{actual_signals.get('cascade_band')})"
        )
    else:
        alignment_status = comparison["alignment_status"]
        summary = comparison["summary"]

    replay_id = f"replay_{uuid.uuid4().hex[:12]}"
    replay_result = {
        "replay_id": replay_id,
        "benchmark_id": benchmark_id,
        "project_id": project_id,
        "simulation_id": simulation_id,
        "replayed_at": _now_iso(),
        "expected_signals": expected_signals,
        "actual_signals": actual_signals,
        "alignment_status": alignment_status,
        "metric_deltas": comparison["metric_deltas"],
        "drift_signals": drift_signals,
        "overall_score": round(overall_score, 4),
        "replay_summary": summary,
    }

    # Phase 5C: include gatekeeping summary when available
    if gatekeeping_summary is not None:
        replay_result["evidence_gatekeeping_summary"] = gatekeeping_summary

    # Persist replay result
    replay_dir = _replay_runs_dir(upload_root)
    replay_dir.mkdir(parents=True, exist_ok=True)
    replay_path = _replay_path(replay_id, upload_root)
    replay_path.write_text(json.dumps(replay_result, ensure_ascii=False, indent=2), encoding="utf-8")

    return replay_result


def get_replay_result(replay_id: str, upload_root: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Get a single replay result by ID."""
    path = _replay_path(replay_id, upload_root)
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def list_replay_results(benchmark_id: str, upload_root: Optional[str] = None) -> List[Dict[str, Any]]:
    """List replay results for a benchmark."""
    replay_dir = _replay_runs_dir(upload_root)
    if not replay_dir.exists():
        return []

    items: List[Dict[str, Any]] = []
    for path in replay_dir.glob("replay_*.json"):
        data = json.loads(path.read_text(encoding="utf-8"))
        if data.get("benchmark_id") == benchmark_id:
            items.append(data)

    items.sort(key=lambda x: x.get("replayed_at", ""), reverse=True)
    return items


__all__ = [
    "extract_stable_signals",
    "compare_replay_result",
    "replay_benchmark",
    "get_replay_result",
    "list_replay_results",
    "_replay_runs_dir",
]
