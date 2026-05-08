from flask import Blueprint, jsonify, request

from consumer_utils import _check_simulation_tenant, _status_from_value_error, _value_error_response
from services.branch_service import (
    create_branch,
    list_branches,
    list_interventions_for_simulation,
    add_intervention,
    list_interventions_for_branch,
    get_branch_comparison,
    resume_branch,
    get_branch_run_status_route,
)

consumer_branch_bp = Blueprint("consumer_branch", __name__, url_prefix="/consumer")


@consumer_branch_bp.route("/branches", methods=["POST"])
def create_branch_route():
    try:
        tenant = _check_simulation_tenant(request)
        return jsonify(create_branch(tenant, request.get_json(silent=True) or {}))
    except ValueError as exc:
        return _value_error_response(exc, _status_from_value_error(exc))


@consumer_branch_bp.route("/branches", methods=["GET"])
def list_branches_route():
    try:
        tenant = _check_simulation_tenant(request)
        return jsonify(list_branches(tenant))
    except ValueError as exc:
        return _value_error_response(exc, _status_from_value_error(exc))


@consumer_branch_bp.route("/interventions", methods=["GET"])
def list_interventions_for_simulation_route():
    try:
        tenant = _check_simulation_tenant(request)
        return jsonify(list_interventions_for_simulation(tenant))
    except ValueError as exc:
        return _value_error_response(exc, _status_from_value_error(exc))


@consumer_branch_bp.route("/interventions", methods=["POST"])
def add_intervention_route():
    try:
        tenant = _check_simulation_tenant(request)
        return jsonify(add_intervention(tenant, request.get_json(silent=True) or {}))
    except ValueError as exc:
        return _value_error_response(exc, _status_from_value_error(exc))


@consumer_branch_bp.route("/branches/<branch_id>/interventions", methods=["GET"])
def list_interventions_for_branch_route(branch_id):
    try:
        tenant = _check_simulation_tenant(request)
        return jsonify(list_interventions_for_branch(tenant, branch_id))
    except ValueError as exc:
        return _value_error_response(exc, _status_from_value_error(exc))


@consumer_branch_bp.route("/branches/<branch_id>/comparison", methods=["GET"])
def branch_comparison_route(branch_id):
    try:
        tenant = _check_simulation_tenant(request)
        return jsonify(get_branch_comparison(tenant, branch_id))
    except ValueError as exc:
        return _value_error_response(exc, _status_from_value_error(exc))


@consumer_branch_bp.route("/branches/<branch_id>/resume", methods=["POST"])
def resume_branch_route(branch_id):
    try:
        tenant = _check_simulation_tenant(request)
        return jsonify(resume_branch(tenant, branch_id, request.get_json(silent=True) or {}))
    except ValueError as exc:
        return _value_error_response(exc, _status_from_value_error(exc))


@consumer_branch_bp.route("/branches/<branch_id>/run-status", methods=["GET"])
def branch_run_status_route(branch_id):
    try:
        tenant = _check_simulation_tenant(request)
        return jsonify(get_branch_run_status_route(tenant, branch_id))
    except ValueError as exc:
        return _value_error_response(exc, _status_from_value_error(exc))
