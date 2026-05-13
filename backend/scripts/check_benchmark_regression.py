"""Fail CI when pytest-benchmark mean latency regresses beyond the gate."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

MAX_REGRESSION_RATIO = 0.15


def _benchmark_key(item: dict[str, Any]) -> str:
    return str(item.get("name") or item.get("fullname") or item.get("group") or "")


def _load_means(path: Path) -> dict[str, float]:
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    means: dict[str, float] = {}
    for item in data.get("benchmarks", []):
        key = _benchmark_key(item)
        stats = item.get("stats", {})
        if key and "mean" in stats:
            means[key] = float(stats["mean"])
    return means


def check_regression(current_path: Path, baseline_path: Path, max_ratio: float = MAX_REGRESSION_RATIO) -> list[str]:
    current = _load_means(current_path)
    baseline = _load_means(baseline_path)
    failures: list[str] = []

    for key, current_mean in current.items():
        baseline_mean = baseline.get(key)
        if baseline_mean is None or baseline_mean <= 0:
            continue
        allowed = baseline_mean * (1.0 + max_ratio)
        if current_mean > allowed:
            failures.append(
                f"{key}: current mean {current_mean:.6f}s exceeds baseline {baseline_mean:.6f}s by > {max_ratio:.0%}"
            )
    return failures


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--current", required=True, type=Path)
    parser.add_argument("--baseline", required=True, type=Path)
    parser.add_argument("--max-regression", type=float, default=MAX_REGRESSION_RATIO)
    args = parser.parse_args(argv)

    failures = check_regression(args.current, args.baseline, args.max_regression)
    if failures:
        print("Performance regression gate failed:")
        for failure in failures:
            print(f"- {failure}")
        return 1

    print(f"Performance regression gate passed with max ratio {args.max_regression:.0%}")
    return 0


if __name__ == "__main__":
    sys.exit(main())


