"""Run a bounded mutation testing smoke sample for SPEC-P2-017."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
from pathlib import Path

MIN_MUTATION_SCORE = 0.70
MUTATION_TARGETS = [
    "app/utils/request_validator.py",
    "app/utils/llm_governor.py",
    "app/redis/health.py",
    "app/security/prompt_guard.py",
    "app/services/consumer/confidence_scoring.py",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the backend mutation smoke sample")
    parser.add_argument("--threshold", type=float, default=MIN_MUTATION_SCORE)
    parser.add_argument("--report", default="mutation-report.json", help="optional JSON report to validate")
    parser.add_argument("--run", action="store_true", help="invoke mutmut when it is installed")
    return parser.parse_args()


def validate_report(path: Path, threshold: float) -> float:
    data = json.loads(path.read_text(encoding="utf-8"))
    score = float(data.get("mutation_score", data.get("score", 0.0)))
    if score < threshold:
        raise SystemExit(f"mutation score {score:.2%} is below threshold {threshold:.2%}")
    return score


def run_mutmut() -> int:
    if shutil.which("mutmut") is None:
        raise SystemExit("mutmut is not installed; install it before running mutation smoke tests")
    command = ["mutmut", "run", "--paths-to-mutate", ",".join(MUTATION_TARGETS)]
    return subprocess.call(command)


def main() -> int:
    args = parse_args()
    if args.run:
        return run_mutmut()
    report = Path(args.report)
    if report.exists():
        score = validate_report(report, args.threshold)
        print(f"mutation score {score:.2%} meets threshold {args.threshold:.2%}")
        return 0
    print("No mutation report found; configured targets:")
    for target in MUTATION_TARGETS:
        print(f"- {target}")
    print(f"Required threshold: {args.threshold:.2%}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())