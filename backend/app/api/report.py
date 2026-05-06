"""
Report API路由
提供模拟报告生成、获取、对话等接口
"""

import os
import tempfile
import traceback
from flask import request, jsonify, send_file

from . import report_bp
from ..config import Config
from ..services.report_agent import ReportManager
from ..utils.logger import get_logger
from ..utils.locale import t
from ..services.application.report_app_service import ReportAppService
from ..services.application.benchmark_app_service import BenchmarkAppService
from ..services.application.research_asset_app_service import ResearchAssetAppService
from ..services.application.comparison_app_service import ComparisonAppService
from ..contracts.errors import ConcurrencyConflictError

logger = get_logger('miroconsumer.api.report')


def _status_from_value_error(e: ValueError) -> int:
    """Map ValueError messages to HTTP status codes for backward compatibility."""
    if isinstance(e, ConcurrencyConflictError):
        return 409
    msg = str(e).lower()
    if "not found" in msg or "不存在" in msg:
        return 404
    return 400


def _value_error_response(e: ValueError):
    if isinstance(e, ConcurrencyConflictError):
        return jsonify(e.to_response()), 409
    return jsonify({
        "success": False,
        "error": str(e)
    }), _status_from_value_error(e)


# ============== 报告生成接口 ==============

@report_bp.route('/generate', methods=['POST'])
def generate_report():
    """
    生成模拟分析报告（异步任务）

    这是一个耗时操作，接口会立即返回task_id，
    使用 GET /api/report/generate/status 查询进度

    请求（JSON）：
        {
            "simulation_id": "sim_xxxx",    // 必填，模拟ID
            "force_regenerate": false        // 可选，强制重新生成
        }

    返回：
        {
            "success": true,
            "data": {
                "simulation_id": "sim_xxxx",
                "task_id": "task_xxxx",
                "status": "generating",
                "message": "报告生成任务已启动"
            }
        }
    """
    try:
        data = request.get_json() or {}

        simulation_id = data.get('simulation_id')
        if not simulation_id:
            return jsonify({
                "success": False,
                "error": t('api.requireSimulationId')
            }), 400

        force_regenerate = data.get('force_regenerate', False)
        result = ReportAppService.generate_report(simulation_id, force_regenerate=force_regenerate)
        return jsonify({
            "success": True,
            "data": result
        })

    except ValueError as e:
        return _value_error_response(e)

    except Exception as e:
        logger.error(f"启动报告生成任务失败: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500


@report_bp.route('/generate/status', methods=['POST'])
def get_generate_status():
    """
    查询报告生成任务进度

    请求（JSON）：
        {
            "task_id": "task_xxxx",         // 可选，generate返回的task_id
            "simulation_id": "sim_xxxx"     // 可选，模拟ID
        }

    返回：
        {
            "success": true,
            "data": {
                "task_id": "task_xxxx",
                "status": "processing|completed|failed",
                "progress": 45,
                "message": "..."
            }
        }
    """
    try:
        data = request.get_json() or {}

        task_id = data.get('task_id')
        simulation_id = data.get('simulation_id')

        result = ReportAppService.get_generate_status(
            simulation_id=simulation_id,
            task_id=task_id,
        )
        return jsonify({
            "success": True,
            "data": result
        })

    except ValueError as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), _status_from_value_error(e)

    except Exception as e:
        logger.error(f"查询任务状态失败: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


# ============== 报告获取接口 ==============

@report_bp.route('/<report_id>', methods=['GET'])
def get_report(report_id: str):
    """
    获取报告详情

    返回：
        {
            "success": true,
            "data": {
                "report_id": "report_xxxx",
                "simulation_id": "sim_xxxx",
                "status": "completed",
                "outline": {...},
                "markdown_content": "...",
                "created_at": "...",
                "completed_at": "..."
            }
        }
    """
    try:
        report = ReportManager.get_report(report_id)

        if not report:
            return jsonify({
                "success": False,
                "error": t('api.reportNotFound', id=report_id)
            }), 404

        return jsonify({
            "success": True,
            "data": report.to_dict()
        })

    except Exception as e:
        logger.error(f"获取报告失败: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500


@report_bp.route('/by-simulation/<simulation_id>', methods=['GET'])
def get_report_by_simulation(simulation_id: str):
    """
    根据模拟ID获取报告

    返回：
        {
            "success": true,
            "data": {
                "report_id": "report_xxxx",
                ...
            }
        }
    """
    try:
        report = ReportManager.get_report_by_simulation(simulation_id)

        if not report:
            return jsonify({
                "success": False,
                "error": t('api.noReportForSim', id=simulation_id),
                "has_report": False
            }), 404

        return jsonify({
            "success": True,
            "data": report.to_dict(),
            "has_report": True
        })

    except Exception as e:
        logger.error(f"获取报告失败: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500


@report_bp.route('/list', methods=['GET'])
def list_reports():
    """
    列出所有报告

    Query参数：
        simulation_id: 按模拟ID过滤（可选）
        limit: 返回数量限制（默认50）

    返回：
        {
            "success": true,
            "data": [...],
            "count": 10
        }
    """
    try:
        simulation_id = request.args.get('simulation_id')
        limit = request.args.get('limit', 50, type=int)

        reports = ReportManager.list_reports(
            simulation_id=simulation_id,
            limit=limit
        )

        return jsonify({
            "success": True,
            "data": [r.to_dict() for r in reports],
            "count": len(reports)
        })

    except Exception as e:
        logger.error(f"列出报告失败: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500


@report_bp.route('/<report_id>/download', methods=['GET'])
def download_report(report_id: str):
    """
    下载报告（Markdown格式）

    返回Markdown文件
    """
    try:
        info = ReportAppService.get_report_download_info(report_id)

        if info["is_temp"]:
            with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
                f.write(info["content"])
                temp_path = f.name

            return send_file(
                temp_path,
                as_attachment=True,
                download_name=info["download_name"]
            )

        return send_file(
            info["path"],
            as_attachment=True,
            download_name=info["download_name"]
        )

    except ValueError as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), _status_from_value_error(e)

    except Exception as e:
        logger.error(f"下载报告失败: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500


@report_bp.route('/<report_id>', methods=['DELETE'])
def delete_report(report_id: str):
    """删除报告"""
    try:
        success = ReportManager.delete_report(report_id)

        if not success:
            return jsonify({
                "success": False,
                "error": t('api.reportNotFound', id=report_id)
            }), 404

        return jsonify({
            "success": True,
            "message": t('api.reportDeleted', id=report_id)
        })

    except Exception as e:
        logger.error(f"删除报告失败: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500


# ============== Report Agent对话接口 ==============

@report_bp.route('/chat', methods=['POST'])
def chat_with_report_agent():
    """
    与Report Agent对话

    Report Agent可以在对话中自主调用检索工具来回答问题

    请求（JSON）：
        {
            "simulation_id": "sim_xxxx",        // 必填，模拟ID
            "message": "请解释一下舆情走向",    // 必填，用户消息
            "chat_history": [                   // 可选，对话历史
                {"role": "user", "content": "..."},
                {"role": "assistant", "content": "..."}
            ]
        }

    返回：
        {
            "success": true,
            "data": {
                "response": "Agent回复...",
                "tool_calls": [调用的工具列表],
                "sources": [信息来源]
            }
        }
    """
    try:
        data = request.get_json() or {}

        simulation_id = data.get('simulation_id')
        message = data.get('message')
        chat_history = data.get('chat_history', [])

        if not simulation_id:
            return jsonify({
                "success": False,
                "error": t('api.requireSimulationId')
            }), 400

        if not message:
            return jsonify({
                "success": False,
                "error": t('api.requireMessage')
            }), 400

        result = ReportAppService.chat_with_report_agent(
            simulation_id=simulation_id,
            message=message,
            chat_history=chat_history,
        )

        return jsonify({
            "success": True,
            "data": result
        })

    except ValueError as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), _status_from_value_error(e)

    except Exception as e:
        logger.error(f"对话失败: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500


# ============== 报告进度与分章节接口 ==============

@report_bp.route('/<report_id>/progress', methods=['GET'])
def get_report_progress(report_id: str):
    """
    获取报告生成进度（实时）

    返回：
        {
            "success": true,
            "data": {
                "status": "generating",
                "progress": 45,
                "message": "正在生成章节: 关键发现",
                "current_section": "关键发现",
                "completed_sections": ["执行摘要", "模拟背景"],
                "updated_at": "2025-12-09T..."
            }
        }
    """
    try:
        progress = ReportManager.get_progress(report_id)

        if not progress:
            return jsonify({
                "success": False,
                "error": t('api.reportProgressNotAvail', id=report_id)
            }), 404

        return jsonify({
            "success": True,
            "data": progress
        })

    except Exception as e:
        logger.error(f"获取报告进度失败: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500


@report_bp.route('/<report_id>/sections', methods=['GET'])
def get_report_sections(report_id: str):
    """
    获取已生成的章节列表（分章节输出）

    前端可以轮询此接口获取已生成的章节内容，无需等待整个报告完成

    返回：
        {
            "success": true,
            "data": {
                "report_id": "report_xxxx",
                "sections": [
                    {
                        "filename": "section_01.md",
                        "section_index": 1,
                        "content": "## 执行摘要\\n\\n..."
                    },
                    ...
                ],
                "total_sections": 3,
                "is_complete": false
            }
        }
    """
    try:
        result = ReportAppService.get_report_sections(report_id)

        return jsonify({
            "success": True,
            "data": result
        })

    except Exception as e:
        logger.error(f"获取章节列表失败: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500


@report_bp.route('/<report_id>/section/<int:section_index>', methods=['GET'])
def get_single_section(report_id: str, section_index: int):
    """
    获取单个章节内容

    返回：
        {
            "success": true,
            "data": {
                "filename": "section_01.md",
                "content": "## 执行摘要\\n\\n..."
            }
        }
    """
    try:
        section_path = ReportManager._get_section_path(report_id, section_index)

        if not os.path.exists(section_path):
            return jsonify({
                "success": False,
                "error": t('api.sectionNotFound', index=f"{section_index:02d}")
            }), 404

        with open(section_path, 'r', encoding='utf-8') as f:
            content = f.read()

        return jsonify({
            "success": True,
            "data": {
                "filename": f"section_{section_index:02d}.md",
                "section_index": section_index,
                "content": content
            }
        })

    except Exception as e:
        logger.error(f"获取章节内容失败: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500


# ============== 报告状态检查接口 ==============

@report_bp.route('/check/<simulation_id>', methods=['GET'])
def check_report_status(simulation_id: str):
    """
    检查模拟是否有报告，以及报告状态

    用于前端判断是否解锁Interview功能

    返回：
        {
            "success": true,
            "data": {
                "simulation_id": "sim_xxxx",
                "has_report": true,
                "report_status": "completed",
                "report_id": "report_xxxx",
                "interview_unlocked": true
            }
        }
    """
    try:
        result = ReportAppService.check_report_status(simulation_id)

        return jsonify({
            "success": True,
            "data": result
        })

    except Exception as e:
        logger.error(f"检查报告状态失败: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500


# ============== Agent 日志接口 ==============

@report_bp.route('/<report_id>/agent-log', methods=['GET'])
def get_agent_log(report_id: str):
    """
    获取 Report Agent 的详细执行日志

    实时获取报告生成过程中的每一步动作，包括：
    - 报告开始、规划开始/完成
    - 每个章节的开始、工具调用、LLM响应、完成
    - 报告完成或失败

    Query参数：
        from_line: 从第几行开始读取（可选，默认0，用于增量获取）

    返回：
        {
            "success": true,
            "data": {
                "logs": [
                    {
                        "timestamp": "2025-12-13T...",
                        "elapsed_seconds": 12.5,
                        "report_id": "report_xxxx",
                        "action": "tool_call",
                        "stage": "generating",
                        "section_title": "执行摘要",
                        "section_index": 1,
                        "details": {
                            "tool_name": "insight_forge",
                            "parameters": {...},
                            ...
                        }
                    },
                    ...
                ],
                "total_lines": 25,
                "from_line": 0,
                "has_more": false
            }
        }
    """
    try:
        from_line = request.args.get('from_line', 0, type=int)

        log_data = ReportManager.get_agent_log(report_id, from_line=from_line)

        return jsonify({
            "success": True,
            "data": log_data
        })

    except Exception as e:
        logger.error(f"获取Agent日志失败: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500


@report_bp.route('/<report_id>/agent-log/stream', methods=['GET'])
def stream_agent_log(report_id: str):
    """
    获取完整的 Agent 日志（一次性获取全部）

    返回：
        {
            "success": true,
            "data": {
                "logs": [...],
                "count": 25
            }
        }
    """
    try:
        logs = ReportManager.get_agent_log_stream(report_id)

        return jsonify({
            "success": True,
            "data": {
                "logs": logs,
                "count": len(logs)
            }
        })

    except Exception as e:
        logger.error(f"获取Agent日志失败: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500


# ============== 控制台日志接口 ==============

@report_bp.route('/<report_id>/console-log', methods=['GET'])
def get_console_log(report_id: str):
    """
    获取 Report Agent 的控制台输出日志

    实时获取报告生成过程中的控制台输出（INFO、WARNING等），
    这与 agent-log 接口返回的结构化 JSON 日志不同，
    是纯文本格式的控制台风格日志。

    Query参数：
        from_line: 从第几行开始读取（可选，默认0，用于增量获取）

    返回：
        {
            "success": true,
            "data": {
                "logs": [
                    "[19:46:14] INFO: 搜索完成: 找到 15 条相关事实",
                    "[19:46:14] INFO: 图谱搜索: graph_id=xxx, query=...",
                    ...
                ],
                "total_lines": 100,
                "from_line": 0,
                "has_more": false
            }
        }
    """
    try:
        from_line = request.args.get('from_line', 0, type=int)

        log_data = ReportManager.get_console_log(report_id, from_line=from_line)

        return jsonify({
            "success": True,
            "data": log_data
        })

    except Exception as e:
        logger.error(f"获取控制台日志失败: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500


@report_bp.route('/<report_id>/console-log/stream', methods=['GET'])
def stream_console_log(report_id: str):
    """
    获取完整的控制台日志（一次性获取全部）

    返回：
        {
            "success": true,
            "data": {
                "logs": [...],
                "count": 100
            }
        }
    """
    try:
        logs = ReportManager.get_console_log_stream(report_id)

        return jsonify({
            "success": True,
            "data": {
                "logs": logs,
                "count": len(logs)
            }
        })

    except Exception as e:
        logger.error(f"获取控制台日志失败: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500


# ============== 工具调用接口（供调试使用）==============

@report_bp.route('/tools/search', methods=['POST'])
def search_graph_tool():
    """
    图谱搜索工具接口（供调试使用）

    请求（JSON）：
        {
            "graph_id": "miroconsumer_xxxx",
            "query": "搜索查询",
            "limit": 10
        }
    """
    try:
        data = request.get_json() or {}

        graph_id = data.get('graph_id')
        query = data.get('query')
        limit = data.get('limit', 10)

        if not graph_id or not query:
            return jsonify({
                "success": False,
                "error": t('api.requireGraphIdAndQuery')
            }), 400

        from ..services.zep_tools import ZepToolsService

        tools = ZepToolsService()
        result = tools.search_graph(
            graph_id=graph_id,
            query=query,
            limit=limit
        )

        return jsonify({
            "success": True,
            "data": result.to_dict()
        })

    except Exception as e:
        logger.error(f"图谱搜索失败: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500


@report_bp.route('/tools/statistics', methods=['POST'])
def get_graph_statistics_tool():
    """
    图谱统计工具接口（供调试使用）

    请求（JSON）：
        {
            "graph_id": "miroconsumer_xxxx"
        }
    """
    try:
        data = request.get_json() or {}

        graph_id = data.get('graph_id')

        if not graph_id:
            return jsonify({
                "success": False,
                "error": t('api.requireGraphId')
            }), 400

        from ..services.zep_tools import ZepToolsService

        tools = ZepToolsService()
        result = tools.get_graph_statistics(graph_id)

        return jsonify({
            "success": True,
            "data": result
        })

    except Exception as e:
        logger.error(f"获取图谱统计失败: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500


# ============== 研究资产接口 ==============

@report_bp.route('/research-assets/export', methods=['POST'])
def export_research_asset():
    """
    Export a research asset pack from a consumer simulation.

    请求（JSON）:
        {
            "project_id": "proj_xxxx",
            "simulation_id": "sim_xxxx",
            "branch_id"?: "branch_xxxx",
            "name"?: "My Asset"
        }

    返回:
        { "success": true, "data": assetPack }
    """
    try:
        data = request.get_json() or {}
        project_id = data.get('project_id')
        simulation_id = data.get('simulation_id')
        branch_id = data.get('branch_id')
        name = data.get('name')

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


@report_bp.route('/research-assets', methods=['GET'])
def list_research_assets():
    """
    List research asset packs for a project.

    Query参数:
        project_id: 项目ID（必填）

    返回:
        { "success": true, "data": { "items": assetPack[] } }
    """
    try:
        project_id = request.args.get('project_id')
        if not project_id:
            return jsonify({"success": False, "error": "project_id is required"}), 400

        items = ResearchAssetAppService.list_research_assets(project_id)
        return jsonify({"success": True, "data": {"items": items}})

    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), _status_from_value_error(e)
    except Exception as e:
        logger.error(f"列出研究资产失败: {str(e)}")
        return jsonify({"success": False, "error": str(e), "traceback": traceback.format_exc()}), 500


@report_bp.route('/research-assets/<asset_id>', methods=['GET'])
def get_research_asset(asset_id: str):
    """
    Get a single research asset pack.

    返回:
        { "success": true, "data": assetPack }
    """
    try:
        asset_pack = ResearchAssetAppService.get_research_asset(asset_id)
        return jsonify({"success": True, "data": asset_pack})

    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), _status_from_value_error(e)
    except Exception as e:
        logger.error(f"获取研究资产失败: {str(e)}")
        return jsonify({"success": False, "error": str(e), "traceback": traceback.format_exc()}), 500


# ============== 对比快照接口 ==============

@report_bp.route('/compare', methods=['POST'])
def create_comparison_snapshot():
    """
    Create a persisted comparison snapshot.

    Supports three modes:
    a) run_vs_run: { mode, left_simulation_id, right_simulation_id }
    b) branch_vs_base: { mode, simulation_id, branch_id }
    c) project_vs_project: { mode, left_project_id, right_project_id }

    返回:
        { "success": true, "data": comparisonSnapshot }
    """
    try:
        data = request.get_json() or {}
        snapshot = ComparisonAppService.create_comparison(data)
        return jsonify({"success": True, "data": snapshot})

    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), _status_from_value_error(e)
    except Exception as e:
        logger.error(f"创建对比快照失败: {str(e)}")
        return jsonify({"success": False, "error": str(e), "traceback": traceback.format_exc()}), 500


@report_bp.route('/comparisons', methods=['GET'])
def list_comparison_snapshots():
    """
    List comparison snapshots.

    Query参数:
        project_id: 项目ID（必填）

    返回:
        { "success": true, "data": { "items": comparisonSnapshot[] } }
    """
    try:
        project_id = request.args.get('project_id')
        if not project_id:
            return jsonify({"success": False, "error": "project_id is required"}), 400

        items = ComparisonAppService.list_comparisons(project_id)
        return jsonify({"success": True, "data": {"items": items}})

    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), _status_from_value_error(e)
    except Exception as e:
        logger.error(f"列出对比快照失败: {str(e)}")
        return jsonify({"success": False, "error": str(e), "traceback": traceback.format_exc()}), 500


@report_bp.route('/comparisons/<comparison_id>', methods=['GET'])
def get_comparison_snapshot(comparison_id: str):
    """
    Get a single comparison snapshot.

    返回:
        { "success": true, "data": comparisonSnapshot }
    """
    try:
        snapshot = ComparisonAppService.get_comparison(comparison_id)
        return jsonify({"success": True, "data": snapshot})

    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), _status_from_value_error(e)
    except Exception as e:
        logger.error(f"获取对比快照失败: {str(e)}")
        return jsonify({"success": False, "error": str(e), "traceback": traceback.format_exc()}), 500


# ============== 基准测试接口 ==============

@report_bp.route('/benchmarks/register', methods=['POST'])
def register_benchmark_route():
    """
    Register a new benchmark case.

    请求 (JSON):
        {
            "name": "Benchmark name",
            "source_pack_lineage": "asset_pack_xxx",
            "expected_signals": { ... },
            "simulation_context": { ... }  // optional
        }

    返回:
        { "success": true, "data": benchmark }
    """
    try:
        data = request.get_json() or {}
        result = BenchmarkAppService.register_benchmark(
            name=data.get("name"),
            source_pack_lineage=data.get("source_pack_lineage"),
            expected_signals=data.get("expected_signals"),
            simulation_context=data.get("simulation_context"),
        )
        return jsonify({"success": True, "data": result})
    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), _status_from_value_error(e)
    except Exception as e:
        logger.error(f"注册基准测试失败: {str(e)}")
        return jsonify({"success": False, "error": str(e), "traceback": traceback.format_exc()}), 500


@report_bp.route('/benchmarks', methods=['GET'])
def list_benchmarks_route():
    """
    List all registered benchmarks.

    返回:
        { "success": true, "data": { "items": benchmark[] } }
    """
    try:
        items = BenchmarkAppService.list_benchmarks()
        return jsonify({"success": True, "data": {"items": items}})
    except Exception as e:
        logger.error(f"列出基准测试失败: {str(e)}")
        return jsonify({"success": False, "error": str(e), "traceback": traceback.format_exc()}), 500


@report_bp.route('/benchmarks/<benchmark_id>', methods=['GET'])
def get_benchmark_route(benchmark_id: str):
    """
    Get a single benchmark by ID.

    返回:
        { "success": true, "data": benchmark }
    """
    try:
        benchmark = BenchmarkAppService.get_benchmark(benchmark_id)
        if not benchmark:
            return jsonify({"success": False, "error": f"Benchmark not found: {benchmark_id}"}), 404
        return jsonify({"success": True, "data": benchmark})
    except Exception as e:
        logger.error(f"获取基准测试失败: {str(e)}")
        return jsonify({"success": False, "error": str(e), "traceback": traceback.format_exc()}), 500


@report_bp.route('/benchmarks/<benchmark_id>/replay', methods=['POST'])
def replay_benchmark_route(benchmark_id: str):
    """
    Replay a benchmark against the current simulation report context.

    请求 (JSON):
        {
            "report_context": { ... },
            "project_id": "proj_xxx",      // optional
            "simulation_id": "sim_xxx"     // optional
        }

    返回:
        { "success": true, "data": replayResult }
    """
    try:
        data = request.get_json() or {}
        report_context = data.get("report_context")
        if not report_context:
            return jsonify({"success": False, "error": "report_context is required"}), 400

        result = BenchmarkAppService.replay_benchmark(
            benchmark_id=benchmark_id,
            report_context=report_context,
            project_id=data.get("project_id"),
            simulation_id=data.get("simulation_id"),
        )
        return jsonify({"success": True, "data": result})
    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), _status_from_value_error(e)
    except Exception as e:
        logger.error(f"回放基准测试失败: {str(e)}")
        return jsonify({"success": False, "error": str(e), "traceback": traceback.format_exc()}), 500


@report_bp.route('/benchmark-replays/<replay_id>', methods=['GET'])
def get_replay_result_route(replay_id: str):
    """
    Get a single replay result by ID.

    返回:
        { "success": true, "data": replayResult }
    """
    try:
        replay = BenchmarkAppService.get_replay_result(replay_id)
        return jsonify({"success": True, "data": replay})
    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), _status_from_value_error(e)
    except Exception as e:
        logger.error(f"获取回放结果失败: {str(e)}")
        return jsonify({"success": False, "error": str(e), "traceback": traceback.format_exc()}), 500
