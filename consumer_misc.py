from flask import Blueprint, jsonify, request

from consumer_utils import _check_simulation_tenant, _status_from_value_error, _value_error_response
from services.misc_service import (
    get_run_estimate,
    get_report_audit_chain,
    get_task_queue_dead_letters,
    export_personas,
    import_personas,
)

consumer_misc_bp = Blueprint("consumer_misc", __name__, url_prefix="/consumer")


@consumer_misc_bp.route("/run-estimate", methods=["GET"])
def run_estimate_route():
    try:
        tenant = _check_simulation_tenant(request)
        return jsonify(get_run_estimate(tenant))
    except ValueError as exc:
        return _value_error_response(exc, _status_from_value_error(exc))


@consumer_misc_bp.route("/report-audit-chain", methods=["GET"])
def report_audit_chain_route():
    try:
        tenant = _check_simulation_tenant(request)
        return jsonify(get_report_audit_chain(tenant))
    except ValueError as exc:
        return _value_error_response(exc, _status_from_value_error(exc))


@consumer_misc_bp.route("/task-queue/dead-letters", methods=["GET"])
def task_queue_dead_letters_route():
    try:
        tenant = _check_simulation_tenant(request)
        return jsonify(get_task_queue_dead_letters(tenant))
    except ValueError as exc:
        return _value_error_response(exc, _status_from_value_error(exc))


@consumer_misc_bp.route("/personas/export", methods=["POST"])
def export_personas_route():
    try:
        tenant = _check_simulation_tenant(request)
        return jsonify(export_personas(tenant, request.get_json(silent=True) or {}))
    except ValueError as exc:
        return _value_error_response(exc, _status_from_value_error(exc))


@consumer_misc_bp.route("/personas/import", methods=["POST"])
def import_personas_route():
    try:
        tenant = _check_simulation_tenant(request)
        return jsonify(import_personas(tenant, request.get_json(silent=True) or {}))
    except ValueError as exc:
        return _value_error_response(exc, _status_from_value_error(exc))
