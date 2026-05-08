from flask import Blueprint, jsonify, request

from consumer_utils import _check_simulation_tenant, _status_from_value_error, _value_error_response
from services.research_asset_service import (
    export_research_asset,
    list_research_assets,
    get_research_asset,
    run_consumer_research_action,
)

consumer_asset_bp = Blueprint("consumer_asset", __name__, url_prefix="/consumer")


@consumer_asset_bp.route("/research-assets/export", methods=["POST"])
def export_research_asset_route():
    try:
        tenant = _check_simulation_tenant(request)
        return jsonify(export_research_asset(tenant, request.get_json(silent=True) or {}))
    except ValueError as exc:
        return _value_error_response(exc, _status_from_value_error(exc))


@consumer_asset_bp.route("/research-assets", methods=["GET"])
def list_research_assets_route():
    try:
        tenant = _check_simulation_tenant(request)
        return jsonify(list_research_assets(tenant))
    except ValueError as exc:
        return _value_error_response(exc, _status_from_value_error(exc))


@consumer_asset_bp.route("/research-assets/<asset_id>", methods=["GET"])
def get_research_asset_route(asset_id):
    try:
        tenant = _check_simulation_tenant(request)
        return jsonify(get_research_asset(tenant, asset_id))
    except ValueError as exc:
        return _value_error_response(exc, _status_from_value_error(exc))


@consumer_asset_bp.route("/research-actions", methods=["POST"])
def run_consumer_research_action_route():
    try:
        tenant = _check_simulation_tenant(request)
        return jsonify(run_consumer_research_action(tenant, request.get_json(silent=True) or {}))
    except ValueError as exc:
        return _value_error_response(exc, _status_from_value_error(exc))
