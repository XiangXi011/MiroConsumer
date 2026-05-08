"""Consumer research asset and persona import/export routes."""

import json
import secrets
from pathlib import Path

from flask import jsonify, request

from . import api_error_payload, consumer_bp
from .consumer_utils import _check_simulation_tenant, _status_from_value_error
from ..auth.middleware import require_permission
from ..config import Config
from ..middleware.rate_limiter import export_rate_limit
from ..services.application.research_asset_app_service import ResearchAssetAppService
from ..utils.logger import get_logger
from ..utils.request_validator import safe_get_json

logger = get_logger("miroconsumer.api.consumer.assets")


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
