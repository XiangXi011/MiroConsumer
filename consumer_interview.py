from flask import Blueprint, jsonify, request

from consumer_utils import _check_simulation_tenant, _status_from_value_error, _value_error_response
from services.interview_service import (
    list_representative_agents,
    run_consumer_interview,
    run_focus_group,
    list_interview_history,
    list_focus_group_history,
)

consumer_interview_bp = Blueprint("consumer_interview", __name__, url_prefix="/consumer")


@consumer_interview_bp.route("/representative-agents", methods=["GET"])
def representative_agents_route():
    try:
        tenant = _check_simulation_tenant(request)
        return jsonify(list_representative_agents(tenant))
    except ValueError as exc:
        return _value_error_response(exc, _status_from_value_error(exc))


@consumer_interview_bp.route("/interviews/run", methods=["POST"])
def run_consumer_interview_route():
    try:
        tenant = _check_simulation_tenant(request)
        return jsonify(run_consumer_interview(tenant, request.get_json(silent=True) or {}))
    except ValueError as exc:
        return _value_error_response(exc, _status_from_value_error(exc))


@consumer_interview_bp.route("/focus-groups/run", methods=["POST"])
def run_focus_group_route():
    try:
        tenant = _check_simulation_tenant(request)
        return jsonify(run_focus_group(tenant, request.get_json(silent=True) or {}))
    except ValueError as exc:
        return _value_error_response(exc, _status_from_value_error(exc))


@consumer_interview_bp.route("/interview-history", methods=["GET"])
def interview_history_route():
    try:
        tenant = _check_simulation_tenant(request)
        return jsonify(list_interview_history(tenant))
    except ValueError as exc:
        return _value_error_response(exc, _status_from_value_error(exc))


@consumer_interview_bp.route("/focus-group-history", methods=["GET"])
def focus_group_history_route():
    try:
        tenant = _check_simulation_tenant(request)
        return jsonify(list_focus_group_history(tenant))
    except ValueError as exc:
        return _value_error_response(exc, _status_from_value_error(exc))
