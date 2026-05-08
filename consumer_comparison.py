from flask import Blueprint, jsonify, request

from consumer_utils import _check_simulation_tenant, _status_from_value_error, _value_error_response
from services.comparison_service import (
    create_comparison_snapshot,
    list_comparison_snapshots,
    get_comparison_snapshot,
)

consumer_comparison_bp = Blueprint("consumer_comparison", __name__, url_prefix="/consumer")


@consumer_comparison_bp.route("/comparison-snapshots", methods=["POST"])
def create_comparison_snapshot_route():
    try:
        tenant = _check_simulation_tenant(request)
        return jsonify(create_comparison_snapshot(tenant, request.get_json(silent=True) or {}))
    except ValueError as exc:
        return _value_error_response(exc, _status_from_value_error(exc))


@consumer_comparison_bp.route("/comparison-snapshots", methods=["GET"])
def list_comparison_snapshots_route():
    try:
        tenant = _check_simulation_tenant(request)
        return jsonify(list_comparison_snapshots(tenant))
    except ValueError as exc:
        return _value_error_response(exc, _status_from_value_error(exc))


@consumer_comparison_bp.route("/comparison-snapshots/<snapshot_id>", methods=["GET"])
def get_comparison_snapshot_route(snapshot_id):
    try:
        tenant = _check_simulation_tenant(request)
        return jsonify(get_comparison_snapshot(tenant, snapshot_id))
    except ValueError as exc:
        return _value_error_response(exc, _status_from_value_error(exc))
