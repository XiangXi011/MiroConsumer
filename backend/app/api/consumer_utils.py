"""Shared helpers for consumer API route modules."""

from flask import g, jsonify

from ..contracts.errors import ConcurrencyConflictError
from ..services.simulation_manager import SimulationManager


def _check_simulation_tenant(simulation_id: str):
    """Check tenant access for a simulation. Returns error response or None."""
    current_tenant = getattr(g, 'current_tenant', None)
    if not current_tenant:
        return None
    sim = SimulationManager().get_simulation(simulation_id)
    if sim and sim.tenant_id and sim.tenant_id != current_tenant:
        return jsonify({"success": False, "error": "FORBIDDEN", "message": "Access denied: tenant mismatch"}), 403
    return None


def _status_from_value_error(e: ValueError) -> int:
    """Map ValueError messages to HTTP status codes for backward compatibility."""
    if isinstance(e, ConcurrencyConflictError):
        return 409
    msg = str(e).lower()
    if "parent branch not found" in msg:
        return 400
    if "not found" in msg or "不存在" in msg:
        return 404
    if "already running" in msg:
        return 409
    if "live mode environment is not running" in msg:
        return 409
    return 400


def _value_error_response(e: ValueError):
    if isinstance(e, ConcurrencyConflictError):
        return jsonify(e.to_response()), 409
    payload = {"success": False, "error": str(e)}
    if hasattr(e, "details") and e.details:
        payload["details"] = e.details
        for key in ("error_code", "blocking_stage", "recoverable", "next_action", "suggested_action"):
            if key in e.details:
                payload[key] = e.details[key]
    return jsonify(payload), _status_from_value_error(e)
