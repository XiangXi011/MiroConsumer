"""Consumer summary and channel routes."""

from flask import jsonify

from . import api_error_payload, consumer_bp
from .consumer_utils import _check_simulation_tenant, _status_from_value_error, _value_error_response
from ..services.application.consumer_app_service import ConsumerAppService
from ..utils.disclaimer import SIMULATION_DISCLAIMER
from ..utils.logger import get_logger

logger = get_logger("miroconsumer.api.consumer.summary")


# ============== Consumer Summary ==============

@consumer_bp.route("/simulation/<simulation_id>/consumer-summary", methods=["GET"])
def get_consumer_summary(simulation_id: str):
    """Build and return the consumer propagation summary for a simulation."""
    try:
        err = _check_simulation_tenant(simulation_id)
        if err:
            return err
        data = ConsumerAppService.get_consumer_summary(simulation_id)
        return jsonify({"success": True, "data": data, "disclaimer": SIMULATION_DISCLAIMER})
    except ValueError as e:
        msg = str(e).lower()
        if "not found" in msg or "不存在" in msg:
            return jsonify({"success": False, "error": str(e)}), 404
        if "snapshots" in msg:
            return jsonify({"success": False, "error": str(e)}), 404
        return jsonify({"success": False, "error": str(e)}), 400
    except Exception as e:
        logger.error(f"获取消费者传播摘要失败: {str(e)}")
        return jsonify(api_error_payload(str(e))), 500


@consumer_bp.route("/simulations/<simulation_id>/channel-summary", methods=["GET"])
def get_channel_summary(simulation_id: str):
    """Return Phase 6H channel metrics and report context fields."""
    try:
        err = _check_simulation_tenant(simulation_id)
        if err:
            return err
        data = ConsumerAppService.get_channel_summary(simulation_id)
        return jsonify({"success": True, "data": data, "disclaimer": SIMULATION_DISCLAIMER})
    except ValueError as e:
        return _value_error_response(e)
    except Exception as e:
        logger.error(f"鑾峰彇娓犻亾鎽樿澶辫触: {str(e)}")
        return jsonify(api_error_payload(str(e))), 500


@consumer_bp.route("/simulations/<simulation_id>/channel-events", methods=["GET"])
def get_channel_events(simulation_id: str):
    """Return Phase 6H channel event stream."""
    try:
        err = _check_simulation_tenant(simulation_id)
        if err:
            return err
        data = ConsumerAppService.get_channel_events(simulation_id)
        return jsonify({"success": True, "data": data, "disclaimer": SIMULATION_DISCLAIMER})
    except ValueError as e:
        return _value_error_response(e)
    except Exception as e:
        logger.error(f"鑾峰彇娓犻亾浜嬩欢澶辫触: {str(e)}")
        return jsonify(api_error_payload(str(e))), 500


@consumer_bp.route("/simulations/<simulation_id>/propagation-paths", methods=["GET"])
def get_propagation_paths(simulation_id: str):
    """Return Phase 6H cross-channel propagation paths."""
    try:
        err = _check_simulation_tenant(simulation_id)
        if err:
            return err
        data = ConsumerAppService.get_propagation_paths(simulation_id)
        return jsonify({"success": True, "data": data, "disclaimer": SIMULATION_DISCLAIMER})
    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), _status_from_value_error(e)
    except Exception as e:
        logger.error(f"鑾峰彇浼犳挱璺緞澶辫触: {str(e)}")
        return jsonify(api_error_payload(str(e))), 500
