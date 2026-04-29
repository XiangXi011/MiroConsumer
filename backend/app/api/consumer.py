"""
Consumer bounded-context API routes

Owns consumer-specific endpoints that were previously scattered across
simulation.py and report.py. Existing routes in those modules remain as
thin compatibility shims that delegate to the same consumer app service.

New canonical consumer URLs are prefixed with /api/consumer/.
"""

import traceback
from flask import jsonify, request

from . import consumer_bp
from ..services.application.consumer_app_service import ConsumerAppService
from ..services.application.branch_app_service import BranchAppService
from ..services.application.comparison_app_service import ComparisonAppService
from ..services.application.consumer_research_action_service import (
    ConsumerResearchActionService,
)
from ..services.application.research_asset_app_service import ResearchAssetAppService
from ..utils.logger import get_logger

logger = get_logger("miroconsumer.api.consumer")


def _status_from_value_error(e: ValueError) -> int:
    """Map ValueError messages to HTTP status codes for backward compatibility."""
    msg = str(e).lower()
    if "parent branch not found" in msg:
        return 400
    if "not found" in msg or "不存在" in msg:
        return 404
    if "already running" in msg:
        return 409
    if "live mode environment is not running" in msg:
        return 409
    return 400


# ============== Consumer Summary ==============

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


@consumer_bp.route("/simulations/<simulation_id>/channel-summary", methods=["GET"])
def get_channel_summary(simulation_id: str):
    """Return Phase 6H channel metrics and report context fields."""
    try:
        data = ConsumerAppService.get_channel_summary(simulation_id)
        return jsonify({"success": True, "data": data})
    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), _status_from_value_error(e)
    except Exception as e:
        logger.error(f"鑾峰彇娓犻亾鎽樿澶辫触: {str(e)}")
        return jsonify({"success": False, "error": str(e), "traceback": traceback.format_exc()}), 500


@consumer_bp.route("/simulations/<simulation_id>/channel-events", methods=["GET"])
def get_channel_events(simulation_id: str):
    """Return Phase 6H channel event stream."""
    try:
        data = ConsumerAppService.get_channel_events(simulation_id)
        return jsonify({"success": True, "data": data})
    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), _status_from_value_error(e)
    except Exception as e:
        logger.error(f"鑾峰彇娓犻亾浜嬩欢澶辫触: {str(e)}")
        return jsonify({"success": False, "error": str(e), "traceback": traceback.format_exc()}), 500


@consumer_bp.route("/simulations/<simulation_id>/propagation-paths", methods=["GET"])
def get_propagation_paths(simulation_id: str):
    """Return Phase 6H cross-channel propagation paths."""
    try:
        data = ConsumerAppService.get_propagation_paths(simulation_id)
        return jsonify({"success": True, "data": data})
    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), _status_from_value_error(e)
    except Exception as e:
        logger.error(f"鑾峰彇浼犳挱璺緞澶辫触: {str(e)}")
        return jsonify({"success": False, "error": str(e), "traceback": traceback.format_exc()}), 500


# ============== Branches ==============

@consumer_bp.route("/simulations/<simulation_id>/branches", methods=["POST"])
def create_branch(simulation_id: str):
    """Create a new branch for a consumer simulation."""
    try:
        data = request.get_json() or {}
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
        return jsonify({"success": False, "error": str(e), "traceback": traceback.format_exc()}), 500


@consumer_bp.route("/simulations/<simulation_id>/branches", methods=["GET"])
def list_branches(simulation_id: str):
    """List all branches for a simulation."""
    try:
        result = BranchAppService.list_branches(simulation_id)
        return jsonify({"success": True, "data": {"branches": result}})
    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), _status_from_value_error(e)
    except Exception as e:
        logger.error(f"列出分支失败: {str(e)}")
        return jsonify({"success": False, "error": str(e), "traceback": traceback.format_exc()}), 500


# ============== Interventions ==============

@consumer_bp.route("/simulations/<simulation_id>/interventions", methods=["GET"])
def list_interventions_for_simulation(simulation_id: str):
    """List interventions for a simulation (across all branches or filtered by branch_id)."""
    try:
        branch_id = request.args.get("branch_id") or None
        result = BranchAppService.list_interventions(simulation_id, branch_id=branch_id)
        return jsonify({"success": True, "data": {"interventions": result}})
    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), _status_from_value_error(e)
    except Exception as e:
        logger.error(f"列出干预失败: {str(e)}")
        return jsonify({"success": False, "error": str(e), "traceback": traceback.format_exc()}), 500


@consumer_bp.route("/simulations/<simulation_id>/branches/<branch_id>/interventions", methods=["POST"])
def add_intervention(simulation_id: str, branch_id: str):
    """Add an intervention to a branch."""
    try:
        data = request.get_json() or {}
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
        return jsonify({"success": False, "error": str(e), "traceback": traceback.format_exc()}), 500


@consumer_bp.route("/simulations/<simulation_id>/branches/<branch_id>/interventions", methods=["GET"])
def list_interventions_for_branch(simulation_id: str, branch_id: str):
    """List interventions for a specific branch."""
    try:
        result = BranchAppService.list_interventions(simulation_id, branch_id=branch_id)
        return jsonify({"success": True, "data": {"interventions": result}})
    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), _status_from_value_error(e)
    except Exception as e:
        logger.error(f"列出分支干预失败: {str(e)}")
        return jsonify({"success": False, "error": str(e), "traceback": traceback.format_exc()}), 500


# ============== Branch Comparison ==============

@consumer_bp.route("/simulations/<simulation_id>/branches/<branch_id>/comparison", methods=["GET"])
def get_branch_comparison(simulation_id: str, branch_id: str):
    """Fetch branch comparison context with base-vs-branch summaries."""
    try:
        result = BranchAppService.get_branch_comparison(simulation_id, branch_id)
        return jsonify({"success": True, "data": result})
    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), _status_from_value_error(e)
    except Exception as e:
        logger.error(f"获取分支对比失败: {str(e)}")
        return jsonify({"success": False, "error": str(e), "traceback": traceback.format_exc()}), 500


# ============== Branch Resume / Status ==============

@consumer_bp.route("/simulations/<simulation_id>/branches/<branch_id>/resume", methods=["POST"])
def resume_branch(simulation_id: str, branch_id: str):
    """Run or resume a branch simulation (consumer_test only)."""
    try:
        data = request.get_json(silent=True) or {}
        result = BranchAppService.resume_branch(
            simulation_id=simulation_id,
            branch_id=branch_id,
            max_rounds=data.get("max_rounds"),
        )
        return jsonify({"success": True, "data": result})
    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), _status_from_value_error(e)
    except Exception as e:
        logger.error(f"启动分支模拟失败: {str(e)}")
        return jsonify({"success": False, "error": str(e), "traceback": traceback.format_exc()}), 500


@consumer_bp.route("/simulations/<simulation_id>/branches/<branch_id>/status", methods=["GET"])
def get_branch_run_status_route(simulation_id: str, branch_id: str):
    """Get branch simulation run status."""
    try:
        result = BranchAppService.get_branch_run_status(simulation_id, branch_id)
        return jsonify({"success": True, "data": result})
    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), _status_from_value_error(e)
    except Exception as e:
        logger.error(f"获取分支状态失败: {str(e)}")
        return jsonify({"success": False, "error": str(e), "traceback": traceback.format_exc()}), 500


# ============== Comparison Snapshots ==============

@consumer_bp.route("/comparisons", methods=["POST"])
def create_comparison_snapshot():
    """Create a persisted comparison snapshot."""
    try:
        data = request.get_json() or {}
        snapshot = ComparisonAppService.create_comparison(data)
        return jsonify({"success": True, "data": snapshot})
    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), _status_from_value_error(e)
    except Exception as e:
        logger.error(f"创建对比快照失败: {str(e)}")
        return jsonify({"success": False, "error": str(e), "traceback": traceback.format_exc()}), 500


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
        return jsonify({"success": False, "error": str(e), "traceback": traceback.format_exc()}), 500


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
        return jsonify({"success": False, "error": str(e), "traceback": traceback.format_exc()}), 500


# ============== Research Assets ==============

@consumer_bp.route("/research-assets/export", methods=["POST"])
def export_research_asset():
    """Export a research asset pack from a consumer simulation."""
    try:
        data = request.get_json() or {}
        project_id = data.get("project_id")
        simulation_id = data.get("simulation_id")
        branch_id = data.get("branch_id")
        name = data.get("name")

        if not project_id:
            return jsonify({"success": False, "error": "project_id is required"}), 400
        if not simulation_id:
            return jsonify({"success": False, "error": "simulation_id is required"}), 400

        asset_pack = ResearchAssetAppService.export_research_asset(
            project_id=project_id,
            simulation_id=simulation_id,
            branch_id=branch_id,
            name=name,
        )
        return jsonify({"success": True, "data": asset_pack})
    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), _status_from_value_error(e)
    except Exception as e:
        logger.error(f"导出研究资产失败: {str(e)}")
        return jsonify({"success": False, "error": str(e), "traceback": traceback.format_exc()}), 500


@consumer_bp.route("/research-assets", methods=["GET"])
def list_research_assets():
    """List research asset packs for a project."""
    try:
        project_id = request.args.get("project_id")
        if not project_id:
            return jsonify({"success": False, "error": "project_id is required"}), 400

        items = ResearchAssetAppService.list_research_assets(project_id)
        return jsonify({"success": True, "data": {"items": items}})
    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), _status_from_value_error(e)
    except Exception as e:
        logger.error(f"列出研究资产失败: {str(e)}")
        return jsonify({"success": False, "error": str(e), "traceback": traceback.format_exc()}), 500


@consumer_bp.route("/research-assets/<asset_id>", methods=["GET"])
def get_research_asset(asset_id: str):
    """Get a single research asset pack."""
    try:
        asset_pack = ResearchAssetAppService.get_research_asset(asset_id)
        return jsonify({"success": True, "data": asset_pack})
    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), _status_from_value_error(e)
    except Exception as e:
        logger.error(f"获取研究资产失败: {str(e)}")
        return jsonify({"success": False, "error": str(e), "traceback": traceback.format_exc()}), 500


# ============== Research Actions ==============

@consumer_bp.route("/simulations/<simulation_id>/research-actions", methods=["POST"])
def run_consumer_research_action(simulation_id: str):
    """Execute a consumer research action on a simulation."""
    try:
        data = request.get_json() or {}
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
        return jsonify({"success": False, "error": str(e), "traceback": traceback.format_exc()}), 500


# ============== Phase 6I: Interview & Focus Group ==============

@consumer_bp.route("/simulations/<simulation_id>/representative-agents", methods=["GET"])
def list_representative_agents(simulation_id: str):
    """Return representative consumer cards for a simulation."""
    try:
        data = ConsumerAppService.list_representative_agents(simulation_id)
        return jsonify({"success": True, "data": data})
    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), _status_from_value_error(e)
    except Exception as e:
        logger.error(f"获取代表性消费者失败: {str(e)}")
        return jsonify({"success": False, "error": str(e), "traceback": traceback.format_exc()}), 500


@consumer_bp.route("/simulations/<simulation_id>/interviews", methods=["POST"])
def run_consumer_interview(simulation_id: str):
    """Run a single consumer interview."""
    try:
        data = request.get_json() or {}
        result = ConsumerAppService.run_consumer_interview(simulation_id, data)
        return jsonify({"success": True, "data": result})
    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), _status_from_value_error(e)
    except Exception as e:
        logger.error(f"运行消费者访谈失败: {str(e)}")
        return jsonify({"success": False, "error": str(e), "traceback": traceback.format_exc()}), 500


@consumer_bp.route("/simulations/<simulation_id>/focus-groups", methods=["POST"])
def run_focus_group(simulation_id: str):
    """Run a virtual focus group session."""
    try:
        data = request.get_json() or {}
        result = ConsumerAppService.run_focus_group(simulation_id, data)
        return jsonify({"success": True, "data": result})
    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), _status_from_value_error(e)
    except Exception as e:
        logger.error(f"运行焦点小组失败: {str(e)}")
        return jsonify({"success": False, "error": str(e), "traceback": traceback.format_exc()}), 500


@consumer_bp.route("/simulations/<simulation_id>/interviews/history", methods=["GET"])
def list_interview_history(simulation_id: str):
    """Return interview history for a simulation."""
    try:
        data = ConsumerAppService.list_interview_history(simulation_id)
        return jsonify({"success": True, "data": data})
    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), _status_from_value_error(e)
    except Exception as e:
        logger.error(f"获取访谈历史失败: {str(e)}")
        return jsonify({"success": False, "error": str(e), "traceback": traceback.format_exc()}), 500


@consumer_bp.route("/simulations/<simulation_id>/focus-groups/history", methods=["GET"])
def list_focus_group_history(simulation_id: str):
    """Return focus group history for a simulation."""
    try:
        data = ConsumerAppService.list_focus_group_history(simulation_id)
        return jsonify({"success": True, "data": data})
    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), _status_from_value_error(e)
    except Exception as e:
        logger.error(f"获取焦点小组历史失败: {str(e)}")
        return jsonify({"success": False, "error": str(e), "traceback": traceback.format_exc()}), 500
