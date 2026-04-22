"""Benchmark registry for repo-local benchmark storage.

Stores benchmark cases under backend/uploads/benchmarks/ with:
- benchmark_manifest.json
- expected_signals.json
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from ...config import Config


def _benchmarks_dir(upload_root: Optional[str] = None) -> Path:
    root = Path(upload_root) if upload_root else Path(Config.UPLOAD_FOLDER)
    return root / "benchmarks"


def _benchmark_folder(benchmark_id: str, upload_root: Optional[str] = None) -> Path:
    return _benchmarks_dir(upload_root) / benchmark_id


def _manifest_path(benchmark_id: str, upload_root: Optional[str] = None) -> Path:
    return _benchmark_folder(benchmark_id, upload_root) / "benchmark_manifest.json"


def _expected_signals_path(benchmark_id: str, upload_root: Optional[str] = None) -> Path:
    return _benchmark_folder(benchmark_id, upload_root) / "expected_signals.json"


def register_benchmark(
    name: str,
    source_pack_lineage: str,
    expected_signals: Dict[str, Any],
    simulation_context: Optional[Dict[str, Any]] = None,
    upload_root: Optional[str] = None,
) -> Dict[str, Any]:
    """Register a new benchmark case.

    Args:
        name: Human-readable benchmark name.
        source_pack_lineage: Identifier for the source pack this benchmark derives from.
        expected_signals: Dict of stable derived signals (acceptance_band, top_resonance_labels, etc.).
        simulation_context: Optional context about the simulation that generated this benchmark.
        upload_root: Optional upload root override.

    Returns:
        Benchmark metadata dict including benchmark_id and created_at.
    """
    benchmark_id = f"bench_{uuid.uuid4().hex[:12]}"
    created_at = datetime.now(timezone.utc).isoformat()

    folder = _benchmark_folder(benchmark_id, upload_root)
    folder.mkdir(parents=True, exist_ok=True)

    manifest = {
        "benchmark_id": benchmark_id,
        "name": name,
        "source_pack_lineage": source_pack_lineage,
        "created_at": created_at,
        "simulation_context": simulation_context or {},
    }

    manifest_path = _manifest_path(benchmark_id, upload_root)
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    signals_path = _expected_signals_path(benchmark_id, upload_root)
    signals_path.write_text(json.dumps(expected_signals, ensure_ascii=False, indent=2), encoding="utf-8")

    return {
        **manifest,
        "expected_signals": expected_signals,
    }


def list_benchmarks(upload_root: Optional[str] = None) -> List[Dict[str, Any]]:
    """List all registered benchmarks."""
    bench_dir = _benchmarks_dir(upload_root)
    if not bench_dir.exists():
        return []

    items: List[Dict[str, Any]] = []
    for folder in bench_dir.iterdir():
        if not folder.is_dir():
            continue
        benchmark_id = folder.name
        manifest_path = _manifest_path(benchmark_id, upload_root)
        signals_path = _expected_signals_path(benchmark_id, upload_root)
        if not manifest_path.exists():
            continue

        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        expected_signals = {}
        if signals_path.exists():
            expected_signals = json.loads(signals_path.read_text(encoding="utf-8"))

        items.append({**manifest, "expected_signals": expected_signals})

    items.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    return items


def get_benchmark(benchmark_id: str, upload_root: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Get a single benchmark by ID."""
    manifest_path = _manifest_path(benchmark_id, upload_root)
    if not manifest_path.exists():
        return None

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    signals_path = _expected_signals_path(benchmark_id, upload_root)
    expected_signals = {}
    if signals_path.exists():
        expected_signals = json.loads(signals_path.read_text(encoding="utf-8"))

    return {**manifest, "expected_signals": expected_signals}


def delete_benchmark(benchmark_id: str, upload_root: Optional[str] = None) -> bool:
    """Delete a benchmark and its artifacts."""
    import shutil

    folder = _benchmark_folder(benchmark_id, upload_root)
    if not folder.exists():
        return False

    shutil.rmtree(folder)
    return True


__all__ = [
    "register_benchmark",
    "list_benchmarks",
    "get_benchmark",
    "delete_benchmark",
    "_benchmarks_dir",
]
