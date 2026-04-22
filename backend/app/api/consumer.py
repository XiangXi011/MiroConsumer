"""
Consumer bounded-context API routes

Owns consumer-specific endpoints that were previously scattered across
simulation.py and report.py. Existing routes in those modules remain as
thin compatibility shims that delegate to the same consumer app service.

New canonical consumer URLs are prefixed with /api/consumer/.
"""

import traceback
from flask import jsonify

from . import consumer_bp
from ..services.application.consumer_app_service import ConsumerAppService
from ..utils.logger import get_logger

logger = get_logger("miroconsumer.api.consumer")


@consumer_bp.route("/simulation/<simulation_id>/consumer-summary", methods=["GET"])
def get_consumer_summary(simulation_id: str):
    """Build and return the consumer propagation summary for a simulation."""
    try:
        data = ConsumerAppService.get_consumer_summary(simulation_id)
        return jsonify({"success": True, "data": data})
    except ValueError as e:
        msg = str(e).lower()
        if "not found" in msg or "不存在" in msg:
            return jsonify({"success": False, "error": str(e)}), 404
        if "snapshots" in msg:
            return jsonify({"success": False, "error": str(e)}), 404
        return jsonify({"success": False, "error": str(e)}), 400
    except Exception as e:
        logger.error(f"获取消费者传播摘要失败: {str(e)}")
        return jsonify(
            {"success": False, "error": str(e), "traceback": traceback.format_exc()}
        ), 500
