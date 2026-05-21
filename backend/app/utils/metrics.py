"""Prometheus metrics endpoint and lightweight runtime SLO counters."""

from __future__ import annotations

import math
import time
from typing import Iterable

from flask import Blueprint, Response

metrics_bp = Blueprint("metrics", __name__)

_MAX_SAMPLES = 512
_response_durations_ms: list[float] = []
_llm_latencies_ms: list[float] = []

# In-memory metrics store. Process-local values are intentionally cheap and
# dependency-free; Prometheus/Sentry provide cross-process aggregation.
_metrics = {
    "requests_total": 0,
    "requests_by_status": {},
    "simulation_runs_total": 0,
    "llm_calls_total": 0,
    "llm_tokens_total": 0,
    "cache_hits_total": 0,
    "cache_misses_total": 0,
    "active_runs": 0,
    "start_time": time.time(),
}


def _append_sample(samples: list[float], value: float) -> None:
    samples.append(max(float(value), 0.0))
    if len(samples) > _MAX_SAMPLES:
        del samples[: len(samples) - _MAX_SAMPLES]


def _percentile(values: Iterable[float], percentile: float) -> float:
    ordered = sorted(float(value) for value in values)
    if not ordered:
        return 0.0
    index = max(0, math.ceil((percentile / 100.0) * len(ordered)) - 1)
    return round(ordered[index], 3)


def record_request(status_code, duration_ms: float | None = None):
    _metrics["requests_total"] += 1
    key = str(status_code)
    _metrics["requests_by_status"][key] = _metrics["requests_by_status"].get(key, 0) + 1
    if duration_ms is not None:
        _append_sample(_response_durations_ms, duration_ms)


def record_simulation_run():
    _metrics["simulation_runs_total"] += 1


def record_cache_hit(count: int = 1):
    _metrics["cache_hits_total"] += int(count)


def record_cache_miss(count: int = 1):
    _metrics["cache_misses_total"] += int(count)


def record_llm_call(tokens=0, latency_ms: float | None = None):
    _metrics["llm_calls_total"] += 1
    _metrics["llm_tokens_total"] += int(tokens or 0)
    if latency_ms is not None:
        _append_sample(_llm_latencies_ms, latency_ms)


def set_active_runs(count):
    _metrics["active_runs"] = count


def performance_snapshot() -> dict[str, float]:
    cache_total = _metrics["cache_hits_total"] + _metrics["cache_misses_total"]
    cache_hit_rate = _metrics["cache_hits_total"] / cache_total if cache_total else 0.0
    llm_avg_latency_ms = (
        sum(_llm_latencies_ms) / len(_llm_latencies_ms) if _llm_latencies_ms else 0.0
    )
    return {
        "p95_response_ms": _percentile(_response_durations_ms, 95),
        "cache_hit_rate": round(cache_hit_rate, 4),
        "llm_avg_latency_ms": round(llm_avg_latency_ms, 3),
    }


@metrics_bp.route("/metrics")
def prometheus_metrics():
    """Prometheus-compatible metrics endpoint.

    Returns application metrics in Prometheus text format with proper
    HELP and TYPE annotations for observability integration.
    """
    snapshot = performance_snapshot()
    uptime = time.time() - _metrics["start_time"]
    lines = [
        "# HELP miroconsumer_uptime_seconds Application uptime in seconds",
        "# TYPE miroconsumer_uptime_seconds gauge",
        f"miroconsumer_uptime_seconds {uptime}",
        "# HELP miroconsumer_simulation_runs_total Total simulations run",
        "# TYPE miroconsumer_simulation_runs_total counter",
        f"miroconsumer_simulation_runs_total {_metrics['simulation_runs_total']}",
        "# HELP miroconsumer_requests_total Total HTTP requests",
        "# TYPE miroconsumer_requests_total counter",
        f"miroconsumer_requests_total {_metrics['requests_total']}",
        "# HELP miroconsumer_llm_calls_total Total LLM API calls",
        "# TYPE miroconsumer_llm_calls_total counter",
        f"miroconsumer_llm_calls_total {_metrics['llm_calls_total']}",
        "# HELP miroconsumer_llm_tokens_total Total LLM tokens consumed",
        "# TYPE miroconsumer_llm_tokens_total counter",
        f"miroconsumer_llm_tokens_total {_metrics['llm_tokens_total']}",
        "# HELP miroconsumer_active_runs Current active simulation runs",
        "# TYPE miroconsumer_active_runs gauge",
        f"miroconsumer_active_runs {_metrics['active_runs']}",
        "# HELP miroconsumer_response_p95_ms P95 response time in ms",
        "# TYPE miroconsumer_response_p95_ms gauge",
        f"miroconsumer_response_p95_ms {snapshot['p95_response_ms']}",
        "# HELP miroconsumer_cache_hit_rate Cache hit rate (0-1)",
        "# TYPE miroconsumer_cache_hit_rate gauge",
        f"miroconsumer_cache_hit_rate {snapshot['cache_hit_rate']}",
        "# HELP miroconsumer_llm_avg_latency_ms Average LLM latency in ms",
        "# TYPE miroconsumer_llm_avg_latency_ms gauge",
        f"miroconsumer_llm_avg_latency_ms {snapshot['llm_avg_latency_ms']}",
    ]
    # Requests by status as labeled metrics
    for sub_key, sub_value in _metrics["requests_by_status"].items():
        lines.append(
            f'miroconsumer_requests_by_status{{status="{sub_key}"}} {sub_value}'
        )
    return Response("\n".join(lines) + "\n", mimetype="text/plain; version=0.0.4")
