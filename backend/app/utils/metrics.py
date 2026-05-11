"""Prometheus metrics endpoint."""
import time

from flask import Blueprint, Response

metrics_bp = Blueprint('metrics', __name__)

# In-memory metrics store
_metrics = {
    "requests_total": 0,
    "requests_by_status": {},
    "simulation_runs_total": 0,
    "llm_calls_total": 0,
    "llm_tokens_total": 0,
    "active_runs": 0,
    "start_time": time.time(),
}


def record_request(status_code):
    _metrics["requests_total"] += 1
    key = str(status_code)
    _metrics["requests_by_status"][key] = _metrics["requests_by_status"].get(key, 0) + 1


def record_simulation_run():
    _metrics["simulation_runs_total"] += 1


def record_llm_call(tokens=0):
    _metrics["llm_calls_total"] += 1
    _metrics["llm_tokens_total"] += tokens


def set_active_runs(count):
    _metrics["active_runs"] = count


@metrics_bp.route('/metrics')
def prometheus_metrics():
    """Prometheus format metrics."""
    lines = []
    for key, value in _metrics.items():
        if isinstance(value, dict):
            for sub_key, sub_value in value.items():
                lines.append(f'miroconsumer_{key}{{status="{sub_key}"}} {sub_value}')
        else:
            lines.append(f'miroconsumer_{key} {value}')
    lines.append(f'miroconsumer_uptime_seconds {time.time() - _metrics["start_time"]}')
    return Response('\n'.join(lines) + '\n', mimetype='text/plain')
