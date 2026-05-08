"""
Consumer bounded-context API routes

Owns consumer-specific endpoints that were previously scattered across
simulation.py and report.py. Existing routes in those modules remain as
thin compatibility shims that delegate to the same consumer app service.

New canonical consumer URLs are prefixed with /api/consumer/.
"""

import json
import secrets
from pathlib import Path
from flask import jsonify, request, g

from . import consumer_bp, api_error_payload
from ..services.application.consumer_app_service import ConsumerAppService
from ..services.application.branch_app_service import BranchAppService
from ..services.application.comparison_app_service import ComparisonAppService
from ..services.application.consumer_research_action_service import (
    ConsumerResearchActionService,
)
from ..services.application.research_asset_app_service import ResearchAssetAppService
from ..services.application import queue_app_service
from ..services.application.audit_chain_service import AuditChainService
from ..services.application.simulation_app_service import SimulationAppService
from .consumer_utils import _check_simulation_tenant, _status_from_value_error, _value_error_response
from ..contracts.errors import ConcurrencyConflictError
from ..utils.logger import get_logger
from ..utils.disclaimer import SIMULATION_DISCLAIMER
from ..auth.middleware import require_permission
from ..middleware.rate_limiter import export_rate_limit
from ..services.simulation_manager import SimulationManager

logger = get_logger("miroconsumer.api.consumer")


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


# ============== Research Assets ==============

@consumer_bp.route("/research-assets/export", methods=["POST"])
@require_permission('asset.export')
@export_rate_limit
def export_research_asset():
    """Export a research asset pack from a consumer simulation."""
    try:
        data = safe_get_json()
        if isinstance(data, tuple): return data
        project_id = data.get("project_id")
        simulation_id = data.get("simulation_id")
        branch_id = data.get("branch_id")
        name = data.get("name")

        if not project_id:
            return jsonify({"success": False, "error": "project_id is required"}), 400
        if not simulation_id:
            return jsonify({"success": False, "error": "simulation_id is required"}), 400

        err = _check_simulation_tenant(simulation_id)
        if err:
            return err

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
        return jsonify(api_error_payload(str(e))), 500


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
        return jsonify(api_error_payload(str(e))), 500


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
        return jsonify(api_error_payload(str(e))), 500


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


# ============== Task Queue Dead Letters ==============

@consumer_bp.route("/simulations/<simulation_id>/run-estimate", methods=["POST"])
def get_run_estimate(simulation_id: str):
    """Return Phase 7D pre-run LLM budget estimate."""
    try:
        err = _check_simulation_tenant(simulation_id)
        if err:
            return err
        data = safe_get_json(required=False)
        data["simulation_id"] = simulation_id
        result = SimulationAppService.estimate_run(data)
        return jsonify({"success": True, "data": result})
    except ValueError as e:
        return _value_error_response(e)
    except Exception as e:
        logger.error(f"获取运行成本估算失败: {str(e)}")
        return jsonify(api_error_payload(str(e))), 500


@consumer_bp.route("/reports/<report_id>/audit-chain", methods=["GET"])
def get_report_audit_chain(report_id: str):
    """Return Phase 7D report audit chain."""
    try:
        # 租户隔离检查（通过 report -> simulation -> tenant 链路）
        current_tenant = getattr(g, 'current_tenant', None)
        if current_tenant:
            from ..services.report_agent import ReportManager
            report = ReportManager.get_report(report_id)
            if report and report.simulation_id:
                sim = SimulationManager().get_simulation(report.simulation_id)
                if sim and sim.tenant_id and sim.tenant_id != current_tenant:
                    return jsonify({"success": False, "error": "FORBIDDEN", "message": "Access denied: tenant mismatch"}), 403
        result = AuditChainService().build_report_chain(report_id)
        return jsonify({"success": True, "data": result})
    except ValueError as e:
        return _value_error_response(e)
    except Exception as e:
        logger.error(f"获取报告审计链失败: {str(e)}")
        return jsonify(api_error_payload(str(e))), 500

@consumer_bp.route("/task-queue/dead-letters", methods=["GET"])
def get_task_queue_dead_letters():
    """List dead letters for the current queue backend."""
    try:
        result = queue_app_service.list_dead_letters()
        return jsonify({"success": True, "data": result})
    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), 400
    except Exception as e:
        logger.error(f"获取死信列表失败: {str(e)}")
        return jsonify(api_error_payload(str(e))), 500


# ── P1-2.4: 画像导入/导出 API ──────────────────────────

@consumer_bp.route("/personas/export", methods=["POST"])
def export_personas():
    """导出画像为 JSON。"""
    try:
        data = safe_get_json(required=False)
        if isinstance(data, tuple):
            return data
        simulation_id = data.get("simulation_id")
        if not simulation_id:
            return jsonify({"success": False, "error": "VALIDATION_ERROR", "message": "simulation_id required"}), 400
        from ..services.consumer.demographics.population import PopulationGenerator
        store_path = Path(Config.PROJECT_STORE_PATH) / simulation_id / "personas"
        if not store_path.exists():
            return jsonify({"success": False, "error": "NOT_FOUND", "message": "No personas found"}), 404
        personas = []
        for f in sorted(store_path.glob("*.json")):
            with open(f, "r", encoding="utf-8") as fh:
                personas.append(json.load(fh))
        return jsonify({"success": True, "data": {"personas": personas, "count": len(personas)}})
    except Exception as e:
        logger.error(f"导出画像失败: {str(e)}")
        return jsonify(api_error_payload(str(e))), 500


@consumer_bp.route("/personas/import", methods=["POST"])
def import_personas():
    """导入画像 JSON。"""
    try:
        data = safe_get_json()
        if isinstance(data, tuple):
            return data
        simulation_id = data.get("simulation_id")
        personas = data.get("personas", [])
        if not simulation_id:
            return jsonify({"success": False, "error": "VALIDATION_ERROR", "message": "simulation_id required"}), 400
        if not personas:
            return jsonify({"success": False, "error": "VALIDATION_ERROR", "message": "personas list required"}), 400
        store_path = Path(Config.PROJECT_STORE_PATH) / simulation_id / "personas"
        store_path.mkdir(parents=True, exist_ok=True)
        imported = 0
        for p in personas:
            pid = p.get("persona_id", f"imported_{secrets.token_hex(4)}")
            p["persona_id"] = pid
            p["source_basis"] = p.get("source_basis", "imported")
            with open(store_path / f"{pid}.json", "w", encoding="utf-8") as fh:
                json.dump(p, fh, ensure_ascii=False, indent=2)
            imported += 1
        return jsonify({"success": True, "data": {"imported": imported}})
    except Exception as e:
        logger.error(f"导入画像失败: {str(e)}")
        return jsonify(api_error_payload(str(e))), 500
