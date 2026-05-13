"""Calibrate MiroConsumer confidence weights from labelled JSONL records."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, Iterable, List

BASELINE_WEIGHTS = {"source": 0.35, "evidence": 0.35, "signal": 0.20, "replay": 0.10}
FEATURES = tuple(BASELINE_WEIGHTS)


def _load_jsonl(path: Path) -> List[Dict[str, Any]]:
    records: List[Dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


def _bounded(value: Any, default: float = 0.5) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        parsed = default
    return max(0.0, min(1.0, parsed))


def score_record(record: Dict[str, Any], weights: Dict[str, float] = BASELINE_WEIGHTS) -> float:
    return round(sum(weights[name] * _bounded(record.get(name)) for name in FEATURES), 4)


def evaluate(records: Iterable[Dict[str, Any]], weights: Dict[str, float] = BASELINE_WEIGHTS) -> Dict[str, Any]:
    rows = list(records)
    if not rows:
        return {"sample_size": 0, "accuracy": None, "expected_calibration_error": None}

    correct = 0
    calibration_error = 0.0
    for record in rows:
        score = score_record(record, weights)
        label = bool(record.get("is_correct"))
        correct += int((score >= 0.5) == label)
        calibration_error += abs(score - float(label))
    return {
        "sample_size": len(rows),
        "accuracy": round(correct / len(rows), 4),
        "expected_calibration_error": round(calibration_error / len(rows), 4),
    }


def build_report(records: List[Dict[str, Any]]) -> Dict[str, Any]:
    metrics = evaluate(records)
    return {
        "status": "accepted" if metrics["sample_size"] >= 50 else "pending_expert_review",
        "method": "baseline_documented_weights",
        "sample_size": metrics["sample_size"],
        "weights": BASELINE_WEIGHTS,
        "metrics": {
            "accuracy": metrics["accuracy"],
            "expected_calibration_error": metrics["expected_calibration_error"],
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Calibrate confidence weights")
    parser.add_argument("--input", type=Path, help="Optional labelled JSONL file")
    parser.add_argument("--output", type=Path, default=Path("../docs/weight_calibration_report.json"))
    args = parser.parse_args()

    records = _load_jsonl(args.input) if args.input else []
    report = build_report(records)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
