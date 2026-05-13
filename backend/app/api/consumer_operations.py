"""Consumer operational routes for estimates, audit chains, and queue diagnostics."""

from flask import g, jsonify

from . import api_error_payload, consumer_bp
from .consumer_utils import _check_simulation_tenant, _value_error_response
from ..auth.middleware import require_permission
from ..services.application import queue_app_service
from ..services.application.audit_chain_service import AuditChainService
from ..services.application.simulation_app_service import SimulationAppService
from ..services.simulation_manager import SimulationManager
from ..utils.logger import get_logger
from ..utils.request_validator import safe_get_json

logger = get_logger("miroconsumer.api.consumer.operations")


# ============== Task Queue Dead Letters ==============

@consumer_bp.route("/simulations/<simulation_id>/run-estimate", methods=["POST"])
@require_permission("simulation.run")
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
@require_permission("audit.read")
def get_report_audit_chain(report_id: str):
    """Return Phase 7D report audit chain."""
    try:
        current_tenant = getattr(g, "current_tenant", None)
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


@consumer_bp.route("/reports/<report_id>/evidence-graph", methods=["GET"])
@require_permission("report.read")
def get_report_evidence_graph(report_id: str):
    """Return a finding-evidence-source graph for a consumer report."""
    try:
        current_tenant = getattr(g, "current_tenant", None)
        if current_tenant:
            from ..services.report_agent import ReportManager
            report = ReportManager.get_report(report_id)
            if report and report.simulation_id:
                sim = SimulationManager().get_simulation(report.simulation_id)
                if sim and sim.tenant_id and sim.tenant_id != current_tenant:
                    return jsonify({"success": False, "error": "FORBIDDEN", "message": "Access denied: tenant mismatch"}), 403
        result = AuditChainService().build_evidence_graph(report_id)
        return jsonify({"success": True, "data": result})
    except ValueError as e:
        return _value_error_response(e)
    except Exception as e:
        logger.error(f"获取报告证据图谱失败: {str(e)}")
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
