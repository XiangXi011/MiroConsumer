"""Consumer comparison snapshot routes."""

from flask import jsonify, request

from . import api_error_payload, consumer_bp
from .consumer_utils import _status_from_value_error
from ..services.application.comparison_app_service import ComparisonAppService
from ..utils.logger import get_logger
from ..utils.request_validator import safe_get_json

logger = get_logger("miroconsumer.api.consumer.comparisons")


# ============== Comparison Snapshots ==============

@consumer_bp.route("/comparisons", methods=["POST"])
def create_comparison_snapshot():
    """Create a persisted comparison snapshot."""
    try:
        data = safe_get_json()
        if isinstance(data, tuple): return data
        snapshot = ComparisonAppService.create_comparison(data)
        return jsonify({"success": True, "data": snapshot})
    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), _status_from_value_error(e)
    except Exception as e:
        logger.error(f"创建对比快照失败: {str(e)}")
        return jsonify(api_error_payload(str(e))), 500


@consumer_bp.route("/comparisons", methods=["GET"])
def list_comparison_snapshots():
    """List comparison snapshots."""
    try:
        project_id = request.args.get("project_id")
        if not project_id:
            return jsonify({"success": False, "error": "project_id is required"}), 400
        items = ComparisonAppService.list_comparisons(project_id)
        return jsonify({"success": True, "data": {"items": items}})
    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), _status_from_value_error(e)
    except Exception as e:
        logger.error(f"列出对比快照失败: {str(e)}")
        return jsonify(api_error_payload(str(e))), 500


@consumer_bp.route("/comparisons/<comparison_id>", methods=["GET"])
def get_comparison_snapshot(comparison_id: str):
    """Get a single comparison snapshot."""
    try:
        snapshot = ComparisonAppService.get_comparison(comparison_id)
        return jsonify({"success": True, "data": snapshot})
    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), _status_from_value_error(e)
    except Exception as e:
        logger.error(f"获取对比快照失败: {str(e)}")
        return jsonify(api_error_payload(str(e))), 500
