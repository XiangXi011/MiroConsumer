"""Consumer branch, intervention, and branch run routes."""

from flask import jsonify, request

from . import api_error_payload, consumer_bp
from .consumer_utils import _check_simulation_tenant, _status_from_value_error, _value_error_response
from ..auth.middleware import require_permission
from ..services.application.branch_app_service import BranchAppService
from ..utils.logger import get_logger
from ..utils.request_validator import safe_get_json

logger = get_logger("miroconsumer.api.consumer.branches")


# ============== Branches ==============

@consumer_bp.route("/simulations/<simulation_id>/branches", methods=["POST"])
@require_permission('simulation.run')
def create_branch(simulation_id: str):
    """Create a new branch for a consumer simulation."""
    try:
        err = _check_simulation_tenant(simulation_id)
        if err:
            return err
        data = safe_get_json()
        if isinstance(data, tuple): return data
        result = BranchAppService.create_branch(
            simulation_id=simulation_id,
            name=data.get("name", ""),
            fork_round=data.get("fork_round"),
            description=data.get("description", ""),
            parent_branch_id=data.get("parent_branch_id"),
        )
        return jsonify({"success": True, "data": result}), 201
    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), _status_from_value_error(e)
    except Exception as e:
        logger.error(f"创建分支失败: {str(e)}")
        return jsonify(api_error_payload(str(e))), 500


@consumer_bp.route("/simulations/<simulation_id>/branches", methods=["GET"])
def list_branches(simulation_id: str):
    """List all branches for a simulation."""
    try:
        err = _check_simulation_tenant(simulation_id)
        if err:
            return err
        result = BranchAppService.list_branches(simulation_id)
        return jsonify({"success": True, "data": {"branches": result}})
    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), _status_from_value_error(e)
    except Exception as e:
        logger.error(f"列出分支失败: {str(e)}")
        return jsonify(api_error_payload(str(e))), 500


# ============== Interventions ==============

@consumer_bp.route("/simulations/<simulation_id>/interventions", methods=["GET"])
@require_permission('project.read')
def list_interventions_for_simulation(simulation_id: str):
    """List interventions for a simulation (across all branches or filtered by branch_id)."""
    try:
        err = _check_simulation_tenant(simulation_id)
        if err:
            return err
        branch_id = request.args.get("branch_id") or None
        result = BranchAppService.list_interventions(simulation_id, branch_id=branch_id)
        return jsonify({"success": True, "data": {"interventions": result}})
    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), _status_from_value_error(e)
    except Exception as e:
        logger.error(f"列出干预失败: {str(e)}")
        return jsonify(api_error_payload(str(e))), 500


@consumer_bp.route("/simulations/<simulation_id>/branches/<branch_id>/interventions", methods=["POST"])
@require_permission('simulation.run')
def add_intervention(simulation_id: str, branch_id: str):
    """Add an intervention to a branch."""
    try:
        err = _check_simulation_tenant(simulation_id)
        if err:
            return err
        data = safe_get_json()
        if isinstance(data, tuple): return data
        result = BranchAppService.add_intervention(
            simulation_id=simulation_id,
            branch_id=branch_id,
            intervention_type=data.get("intervention_type"),
            payload=data.get("payload", {}),
            target_round=data.get("target_round"),
        )
        return jsonify({"success": True, "data": result}), 201
    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), _status_from_value_error(e)
    except Exception as e:
        logger.error(f"添加干预失败: {str(e)}")
        return jsonify(api_error_payload(str(e))), 500


@consumer_bp.route("/simulations/<simulation_id>/branches/<branch_id>/interventions", methods=["GET"])
def list_interventions_for_branch(simulation_id: str, branch_id: str):
    """List interventions for a specific branch."""
    try:
        err = _check_simulation_tenant(simulation_id)
        if err:
            return err
        result = BranchAppService.list_interventions(simulation_id, branch_id=branch_id)
        return jsonify({"success": True, "data": {"interventions": result}})
    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), _status_from_value_error(e)
    except Exception as e:
        logger.error(f"列出分支干预失败: {str(e)}")
        return jsonify(api_error_payload(str(e))), 500


# ============== Branch Comparison ==============

@consumer_bp.route("/simulations/<simulation_id>/branches/<branch_id>/comparison", methods=["GET"])
def get_branch_comparison(simulation_id: str, branch_id: str):
    """Fetch branch comparison context with base-vs-branch summaries."""
    try:
        err = _check_simulation_tenant(simulation_id)
        if err:
            return err
        result = BranchAppService.get_branch_comparison(simulation_id, branch_id)
        return jsonify({"success": True, "data": result})
    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), _status_from_value_error(e)
    except Exception as e:
        logger.error(f"获取分支对比失败: {str(e)}")
        return jsonify(api_error_payload(str(e))), 500


# ============== Branch Resume / Status ==============

@consumer_bp.route("/simulations/<simulation_id>/branches/<branch_id>/resume", methods=["POST"])
@require_permission('simulation.run')
def resume_branch(simulation_id: str, branch_id: str):
    """Run or resume a branch simulation (consumer_test only)."""
    try:
        err = _check_simulation_tenant(simulation_id)
        if err:
            return err
        data = safe_get_json(required=False)
        result = BranchAppService.resume_branch(
            simulation_id=simulation_id,
            branch_id=branch_id,
            max_rounds=data.get("max_rounds"),
        )
        return jsonify({"success": True, "data": result})
    except ValueError as e:
        return _value_error_response(e)
    except Exception as e:
        logger.error(f"启动分支模拟失败: {str(e)}")
        return jsonify(api_error_payload(str(e))), 500


@consumer_bp.route("/simulations/<simulation_id>/branches/<branch_id>/status", methods=["GET"])
def get_branch_run_status_route(simulation_id: str, branch_id: str):
    """Get branch simulation run status."""
    try:
        err = _check_simulation_tenant(simulation_id)
        if err:
            return err
        result = BranchAppService.get_branch_run_status(simulation_id, branch_id)
        return jsonify({"success": True, "data": result})
    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), _status_from_value_error(e)
    except Exception as e:
        logger.error(f"获取分支状态失败: {str(e)}")
        return jsonify(api_error_payload(str(e))), 500
