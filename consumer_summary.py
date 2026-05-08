from flask import Blueprint, jsonify, request

from consumer_utils import _check_simulation_tenant, _status_from_value_error, _value_error_response
from services.consumer_service import (
    get_consumer_summary,
    get_channel_summary,
    get_channel_events,
    get_propagation_paths,
)

consumer_summary_bp = Blueprint("consumer_summary", __name__, url_prefix="/consumer")


@consumer_summary_bp.route("/summary", methods=["GET"])
def consumer_summary_route():
    try:
        tenant = _check_simulation_tenant(request)
        return jsonify(get_consumer_summary(tenant))
    except ValueError as exc:
        return _value_error_response(exc, _status_from_value_error(exc))


@consumer_summary_bp.route("/channel-summary", methods=["GET"])
def channel_summary_route():
    try:
        tenant = _check_simulation_tenant(request)
        return jsonify(get_channel_summary(tenant))
    except ValueError as exc:
        return _value_error_response(exc, _status_from_value_error(exc))


@consumer_summary_bp.route("/channel-events", methods=["GET"])
def channel_events_route():
    try:
        tenant = _check_simulation_tenant(request)
        return jsonify(get_channel_events(tenant))
    except ValueError as exc:
        return _value_error_response(exc, _status_from_value_error(exc))


@consumer_summary_bp.route("/propagation-paths", methods=["GET"])
def propagation_paths_route():
    try:
        tenant = _check_simulation_tenant(request)
        return jsonify(get_propagation_paths(tenant))
    except ValueError as exc:
        return _value_error_response(exc, _status_from_value_error(exc))
