"""Consumer research action, interview, and focus-group routes."""

from flask import jsonify

from . import api_error_payload, consumer_bp
from .consumer_utils import _check_simulation_tenant, _status_from_value_error
from ..auth.middleware import require_permission
from ..services.application.consumer_app_service import ConsumerAppService
from ..services.application.consumer_research_action_service import ConsumerResearchActionService
from ..utils.disclaimer import SIMULATION_DISCLAIMER
from ..utils.logger import get_logger
from ..utils.request_validator import safe_get_json

logger = get_logger("miroconsumer.api.consumer.research")


# ============== Research Actions ==============

@consumer_bp.route("/simulations/<simulation_id>/research-actions", methods=["POST"])
@require_permission('simulation.run')
def run_consumer_research_action(simulation_id: str):
    """Execute a consumer research action on a simulation."""
    try:
        err = _check_simulation_tenant(simulation_id)
        if err:
            return err
        data = safe_get_json()
        if isinstance(data, tuple): return data
        result = ConsumerResearchActionService.run_action(
            simulation_id=simulation_id,
            payload=data,
        )
        return jsonify({"success": True, "data": result})
    except ValueError as e:
        msg = str(e).lower()
        if "not found" in msg or "不存在" in msg:
            return jsonify({"success": False, "error": str(e)}), 404
        if "already running" in msg:
            return jsonify({"success": False, "error": str(e)}), 409
        return jsonify({"success": False, "error": str(e)}), 400
    except Exception as e:
        logger.error(f"执行消费者研究动作失败: {str(e)}")
        return jsonify(api_error_payload(str(e))), 500


# ============== Phase 6I: Interview & Focus Group ==============

@consumer_bp.route("/simulations/<simulation_id>/representative-agents", methods=["GET"])
def list_representative_agents(simulation_id: str):
    """Return representative consumer cards for a simulation."""
    try:
        err = _check_simulation_tenant(simulation_id)
        if err:
            return err
        data = ConsumerAppService.list_representative_agents(simulation_id)
        return jsonify({"success": True, "data": data})
    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), _status_from_value_error(e)
    except Exception as e:
        logger.error(f"获取代表性消费者失败: {str(e)}")
        return jsonify(api_error_payload(str(e))), 500


@consumer_bp.route("/simulations/<simulation_id>/interviews", methods=["POST"])
def run_consumer_interview(simulation_id: str):
    """Run a single consumer interview."""
    try:
        err = _check_simulation_tenant(simulation_id)
        if err:
            return err
        data = safe_get_json()
        if isinstance(data, tuple): return data
        result = ConsumerAppService.run_consumer_interview(simulation_id, data)
        return jsonify({"success": True, "data": result, "disclaimer": SIMULATION_DISCLAIMER})
    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), _status_from_value_error(e)
    except Exception as e:
        logger.error(f"运行消费者访谈失败: {str(e)}")
        return jsonify(api_error_payload(str(e))), 500


@consumer_bp.route("/simulations/<simulation_id>/focus-groups", methods=["POST"])
def run_focus_group(simulation_id: str):
    """Run a virtual focus group session."""
    try:
        err = _check_simulation_tenant(simulation_id)
        if err:
            return err
        data = safe_get_json()
        if isinstance(data, tuple): return data
        result = ConsumerAppService.run_focus_group(simulation_id, data)
        return jsonify({"success": True, "data": result, "disclaimer": SIMULATION_DISCLAIMER})
    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), _status_from_value_error(e)
    except Exception as e:
        logger.error(f"运行焦点小组失败: {str(e)}")
        return jsonify(api_error_payload(str(e))), 500


@consumer_bp.route("/simulations/<simulation_id>/interviews/history", methods=["GET"])
def list_interview_history(simulation_id: str):
    """Return interview history for a simulation."""
    try:
        err = _check_simulation_tenant(simulation_id)
        if err:
            return err
        data = ConsumerAppService.list_interview_history(simulation_id)
        return jsonify({"success": True, "data": data})
    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), _status_from_value_error(e)
    except Exception as e:
        logger.error(f"获取访谈历史失败: {str(e)}")
        return jsonify(api_error_payload(str(e))), 500


@consumer_bp.route("/simulations/<simulation_id>/focus-groups/history", methods=["GET"])
def list_focus_group_history(simulation_id: str):
    """Return focus group history for a simulation."""
    try:
        err = _check_simulation_tenant(simulation_id)
        if err:
            return err
        data = ConsumerAppService.list_focus_group_history(simulation_id)
        return jsonify({"success": True, "data": data})
    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), _status_from_value_error(e)
    except Exception as e:
        logger.error(f"获取焦点小组历史失败: {str(e)}")
        return jsonify(api_error_payload(str(e))), 500
