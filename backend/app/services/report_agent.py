"""
Report Agent服务
使用LangChain + Zep实现ReACT模式的模拟报告生成

功能：
1. 根据模拟需求和Zep图谱信息生成报告
2. 先规划目录结构，然后分段生成
3. 每段采用ReACT多轮思考与反思模式
4. 支持与用户对话，在对话中自主调用检索工具
"""

import os
import json
import time
import re
from collections import Counter
from typing import Dict, Any, List, Optional, Callable
from dataclasses import asdict
from datetime import datetime

from ..config import Config
from ..models.project import ProjectManager
from ..utils.llm_client import LLMClient
from ..utils.logger import get_logger
from ..utils.locale import get_language_instruction, t
from .consumer.report_context import ConsumerReportContextBuilder
from .consumer.project_research_persistence import (
    artifacts_exist,
    load_persisted_findings,
    load_persisted_snapshot,
)
from .zep_tools import (
    ZepToolsService, 
    SearchResult, 
    InsightForgeResult, 
    PanoramaResult,
    InterviewResult
)
from .report_models import Report, ReportOutline, ReportSection, ReportStatus
from .report_manager import ReportManager
from .report_prompts import (
    CHAT_OBSERVATION_SUFFIX,
    CHAT_SYSTEM_PROMPT_TEMPLATE,
    CONSUMER_CHAT_SYSTEM_PROMPT_TEMPLATE,
    CONSUMER_PLAN_SYSTEM_PROMPT,
    CONSUMER_PLAN_USER_PROMPT_TEMPLATE,
    CONSUMER_SECTION_SYSTEM_PROMPT_TEMPLATE,
    CONSUMER_SECTION_USER_PROMPT_TEMPLATE,
    PLAN_SYSTEM_PROMPT,
    PLAN_USER_PROMPT_TEMPLATE,
    REACT_FORCE_FINAL_MSG,
    REACT_INSUFFICIENT_TOOLS_MSG,
    REACT_INSUFFICIENT_TOOLS_MSG_ALT,
    REACT_OBSERVATION_TEMPLATE,
    REACT_TOOL_LIMIT_MSG,
    REACT_UNUSED_TOOLS_HINT,
    SECTION_SYSTEM_PROMPT_TEMPLATE,
    SECTION_USER_PROMPT_TEMPLATE,
    TOOL_DESC_INSIGHT_FORGE,
    TOOL_DESC_INTERVIEW_AGENTS,
    TOOL_DESC_PANORAMA_SEARCH,
    TOOL_DESC_QUICK_SEARCH,
)

try:
    from .consumer.selling_point_analyzer import analyze_selling_points, SellingPointRole
except ImportError:
    analyze_selling_points = None  # type: ignore[assignment]
    SellingPointRole = None  # type: ignore[assignment,misc]

try:
    from .consumer.compliance_checker import check_compliance
except ImportError:
    check_compliance = None  # type: ignore[assignment]

logger = get_logger('miroconsumer.report_agent')


class ReportLogger:
    """
    Report Agent 详细日志记录器
    
    在报告文件夹中生成 agent_log.jsonl 文件，记录每一步详细动作。
    每行是一个完整的 JSON 对象，包含时间戳、动作类型、详细内容等。
    """
    
    def __init__(self, report_id: str):
        """
        初始化日志记录器
        
        Args:
            report_id: 报告ID，用于确定日志文件路径
        """
        self.report_id = report_id
        self.log_file_path = os.path.join(
            Config.UPLOAD_FOLDER, 'reports', report_id, 'agent_log.jsonl'
        )
        self.start_time = datetime.now()
        self._ensure_log_file()
    
    def _ensure_log_file(self):
        """确保日志文件所在目录存在"""
        log_dir = os.path.dirname(self.log_file_path)
        os.makedirs(log_dir, exist_ok=True)
    
    def _get_elapsed_time(self) -> float:
        """获取从开始到现在的耗时（秒）"""
        return (datetime.now() - self.start_time).total_seconds()
    
    def log(
        self, 
        action: str, 
        stage: str,
        details: Dict[str, Any],
        section_title: str = None,
        section_index: int = None
    ):
        """
        记录一条日志
        
        Args:
            action: 动作类型，如 'start', 'tool_call', 'llm_response', 'section_complete' 等
            stage: 当前阶段，如 'planning', 'generating', 'completed'
            details: 详细内容字典，不截断
            section_title: 当前章节标题（可选）
            section_index: 当前章节索引（可选）
        """
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "elapsed_seconds": round(self._get_elapsed_time(), 2),
            "report_id": self.report_id,
            "action": action,
            "stage": stage,
            "section_title": section_title,
            "section_index": section_index,
            "details": details
        }
        
        # 追加写入 JSONL 文件
        with open(self.log_file_path, 'a', encoding='utf-8') as f:
            f.write(json.dumps(log_entry, ensure_ascii=False) + '\n')
    
    def log_start(self, simulation_id: str, graph_id: str, simulation_requirement: str):
        """记录报告生成开始"""
        self.log(
            action="report_start",
            stage="pending",
            details={
                "simulation_id": simulation_id,
                "graph_id": graph_id,
                "simulation_requirement": simulation_requirement,
                "message": t('report.taskStarted')
            }
        )
    
    def log_planning_start(self):
        """记录大纲规划开始"""
        self.log(
            action="planning_start",
            stage="planning",
            details={"message": t('report.planningStart')}
        )
    
    def log_planning_context(self, context: Dict[str, Any]):
        """记录规划时获取的上下文信息"""
        self.log(
            action="planning_context",
            stage="planning",
            details={
                "message": t('report.fetchSimContext'),
                "context": context
            }
        )
    
    def log_planning_complete(self, outline_dict: Dict[str, Any]):
        """记录大纲规划完成"""
        self.log(
            action="planning_complete",
            stage="planning",
            details={
                "message": t('report.planningComplete'),
                "outline": outline_dict
            }
        )
    
    def log_section_start(self, section_title: str, section_index: int):
        """记录章节生成开始"""
        self.log(
            action="section_start",
            stage="generating",
            section_title=section_title,
            section_index=section_index,
            details={"message": t('report.sectionStart', title=section_title)}
        )
    
    def log_react_thought(self, section_title: str, section_index: int, iteration: int, thought: str):
        """记录 ReACT 思考过程"""
        self.log(
            action="react_thought",
            stage="generating",
            section_title=section_title,
            section_index=section_index,
            details={
                "iteration": iteration,
                "thought": thought,
                "message": t('report.reactThought', iteration=iteration)
            }
        )
    
    def log_tool_call(
        self, 
        section_title: str, 
        section_index: int,
        tool_name: str, 
        parameters: Dict[str, Any],
        iteration: int
    ):
        """记录工具调用"""
        self.log(
            action="tool_call",
            stage="generating",
            section_title=section_title,
            section_index=section_index,
            details={
                "iteration": iteration,
                "tool_name": tool_name,
                "parameters": parameters,
                "message": t('report.toolCall', toolName=tool_name)
            }
        )
    
    def log_tool_result(
        self,
        section_title: str,
        section_index: int,
        tool_name: str,
        result: str,
        iteration: int
    ):
        """记录工具调用结果（完整内容，不截断）"""
        self.log(
            action="tool_result",
            stage="generating",
            section_title=section_title,
            section_index=section_index,
            details={
                "iteration": iteration,
                "tool_name": tool_name,
                "result": result,  # 完整结果，不截断
                "result_length": len(result),
                "message": t('report.toolResult', toolName=tool_name)
            }
        )
    
    def log_llm_response(
        self,
        section_title: str,
        section_index: int,
        response: str,
        iteration: int,
        has_tool_calls: bool,
        has_final_answer: bool
    ):
        """记录 LLM 响应（完整内容，不截断）"""
        self.log(
            action="llm_response",
            stage="generating",
            section_title=section_title,
            section_index=section_index,
            details={
                "iteration": iteration,
                "response": response,  # 完整响应，不截断
                "response_length": len(response),
                "has_tool_calls": has_tool_calls,
                "has_final_answer": has_final_answer,
                "message": t('report.llmResponse', hasToolCalls=has_tool_calls, hasFinalAnswer=has_final_answer)
            }
        )
    
    def log_section_content(
        self,
        section_title: str,
        section_index: int,
        content: str,
        tool_calls_count: int
    ):
        """记录章节内容生成完成（仅记录内容，不代表整个章节完成）"""
        self.log(
            action="section_content",
            stage="generating",
            section_title=section_title,
            section_index=section_index,
            details={
                "content": content,  # 完整内容，不截断
                "content_length": len(content),
                "tool_calls_count": tool_calls_count,
                "message": t('report.sectionContentDone', title=section_title)
            }
        )
    
    def log_section_full_complete(
        self,
        section_title: str,
        section_index: int,
        full_content: str
    ):
        """
        记录章节生成完成

        前端应监听此日志来判断一个章节是否真正完成，并获取完整内容
        """
        self.log(
            action="section_complete",
            stage="generating",
            section_title=section_title,
            section_index=section_index,
            details={
                "content": full_content,
                "content_length": len(full_content),
                "message": t('report.sectionComplete', title=section_title)
            }
        )
    
    def log_report_complete(self, total_sections: int, total_time_seconds: float):
        """记录报告生成完成"""
        self.log(
            action="report_complete",
            stage="completed",
            details={
                "total_sections": total_sections,
                "total_time_seconds": round(total_time_seconds, 2),
                "message": t('report.reportComplete')
            }
        )
    
    def log_error(self, error_message: str, stage: str, section_title: str = None):
        """记录错误"""
        self.log(
            action="error",
            stage=stage,
            section_title=section_title,
            section_index=None,
            details={
                "error": error_message,
                "message": t('report.errorOccurred', error=error_message)
            }
        )


class ReportConsoleLogger:
    """
    Report Agent 控制台日志记录器
    
    将控制台风格的日志（INFO、WARNING等）写入报告文件夹中的 console_log.txt 文件。
    这些日志与 agent_log.jsonl 不同，是纯文本格式的控制台输出。
    """
    
    def __init__(self, report_id: str):
        """
        初始化控制台日志记录器
        
        Args:
            report_id: 报告ID，用于确定日志文件路径
        """
        self.report_id = report_id
        self.log_file_path = os.path.join(
            Config.UPLOAD_FOLDER, 'reports', report_id, 'console_log.txt'
        )
        self._ensure_log_file()
        self._file_handler = None
        self._setup_file_handler()
    
    def _ensure_log_file(self):
        """确保日志文件所在目录存在"""
        log_dir = os.path.dirname(self.log_file_path)
        os.makedirs(log_dir, exist_ok=True)
    
    def _setup_file_handler(self):
        """设置文件处理器，将日志同时写入文件"""
        import logging
        
        # 创建文件处理器
        self._file_handler = logging.FileHandler(
            self.log_file_path,
            mode='a',
            encoding='utf-8'
        )
        self._file_handler.setLevel(logging.INFO)
        
        # 使用与控制台相同的简洁格式
        formatter = logging.Formatter(
            '[%(asctime)s] %(levelname)s: %(message)s',
            datefmt='%H:%M:%S'
        )
        self._file_handler.setFormatter(formatter)
        
        # 添加到 report_agent 相关的 logger
        loggers_to_attach = [
            'miroconsumer.report_agent',
            'miroconsumer.zep_tools',
        ]
        
        for logger_name in loggers_to_attach:
            target_logger = logging.getLogger(logger_name)
            # 避免重复添加
            if self._file_handler not in target_logger.handlers:
                target_logger.addHandler(self._file_handler)
    
    def close(self):
        """关闭文件处理器并从 logger 中移除"""
        import logging
        
        if self._file_handler:
            loggers_to_detach = [
                'miroconsumer.report_agent',
                'miroconsumer.zep_tools',
            ]
            
            for logger_name in loggers_to_detach:
                target_logger = logging.getLogger(logger_name)
                if self._file_handler in target_logger.handlers:
                    target_logger.removeHandler(self._file_handler)
            
            self._file_handler.close()
            self._file_handler = None
    
    def __del__(self):
        """析构时确保关闭文件处理器"""
        self.close()


# ═══════════════════════════════════════════════════════════════
# ReportAgent 主类
# ═══════════════════════════════════════════════════════════════


class ReportAgent:
    """
    Report Agent - 模拟报告生成Agent

    采用ReACT（Reasoning + Acting）模式：
    1. 规划阶段：分析模拟需求，规划报告目录结构
    2. 生成阶段：逐章节生成内容，每章节可多次调用工具获取信息
    3. 反思阶段：检查内容完整性和准确性
    """
    
    # 最大工具调用次数（每个章节）
    MAX_TOOL_CALLS_PER_SECTION = 5
    
    # 最大反思轮数
    MAX_REFLECTION_ROUNDS = 3
    
    # 对话中的最大工具调用次数
    MAX_TOOL_CALLS_PER_CHAT = 2
    
    def __init__(
        self, 
        graph_id: str,
        simulation_id: str,
        simulation_requirement: str,
        llm_client: Optional[LLMClient] = None,
        zep_tools: Optional[ZepToolsService] = None,
        project_type: str = "default",
        project_id: Optional[str] = None,
    ):
        """
        初始化Report Agent
        
        Args:
            graph_id: 图谱ID
            simulation_id: 模拟ID
            simulation_requirement: 模拟需求描述
            llm_client: LLM客户端（可选）
            zep_tools: Zep工具服务（可选）
        """
        self.graph_id = graph_id
        self.simulation_id = simulation_id
        self.simulation_requirement = simulation_requirement
        self.project_type = project_type or "default"
        self.project_id = project_id
        
        self.llm = llm_client or LLMClient()
        self.zep_tools = zep_tools or ZepToolsService()
        
        # 工具定义
        self.tools = self._define_tools()
        
        # 日志记录器（在 generate_report 中初始化）
        self.report_logger: Optional[ReportLogger] = None
        # 控制台日志记录器（在 generate_report 中初始化）
        self.console_logger: Optional[ReportConsoleLogger] = None
        
        logger.info(t('report.agentInitDone', graphId=graph_id, simulationId=simulation_id))
    
    def _define_tools(self) -> Dict[str, Dict[str, Any]]:
        """定义可用工具"""
        return {
            "insight_forge": {
                "name": "insight_forge",
                "description": TOOL_DESC_INSIGHT_FORGE,
                "parameters": {
                    "query": "你想深入分析的问题或话题",
                    "report_context": "当前报告章节的上下文（可选，有助于生成更精准的子问题）"
                }
            },
            "panorama_search": {
                "name": "panorama_search",
                "description": TOOL_DESC_PANORAMA_SEARCH,
                "parameters": {
                    "query": "搜索查询，用于相关性排序",
                    "include_expired": "是否包含过期/历史内容（默认True）"
                }
            },
            "quick_search": {
                "name": "quick_search",
                "description": TOOL_DESC_QUICK_SEARCH,
                "parameters": {
                    "query": "搜索查询字符串",
                    "limit": "返回结果数量（可选，默认10）"
                }
            },
            "interview_agents": {
                "name": "interview_agents",
                "description": TOOL_DESC_INTERVIEW_AGENTS,
                "parameters": {
                    "interview_topic": "采访主题或需求描述（如：'了解学生对宿舍甲醛事件的看法'）",
                    "max_agents": "最多采访的Agent数量（可选，默认5，最大10）"
                }
            }
        }
    
    def _execute_tool(self, tool_name: str, parameters: Dict[str, Any], report_context: str = "") -> str:
        """
        执行工具调用
        
        Args:
            tool_name: 工具名称
            parameters: 工具参数
            report_context: 报告上下文（用于InsightForge）
            
        Returns:
            工具执行结果（文本格式）
        """
        logger.info(t('report.executingTool', toolName=tool_name, params=parameters))
        
        try:
            if tool_name == "insight_forge":
                query = parameters.get("query", "")
                ctx = parameters.get("report_context", "") or report_context
                result = self.zep_tools.insight_forge(
                    graph_id=self.graph_id,
                    query=query,
                    simulation_requirement=self.simulation_requirement,
                    report_context=ctx
                )
                return result.to_text()
            
            elif tool_name == "panorama_search":
                # 广度搜索 - 获取全貌
                query = parameters.get("query", "")
                include_expired = parameters.get("include_expired", True)
                if isinstance(include_expired, str):
                    include_expired = include_expired.lower() in ['true', '1', 'yes']
                result = self.zep_tools.panorama_search(
                    graph_id=self.graph_id,
                    query=query,
                    include_expired=include_expired
                )
                return result.to_text()
            
            elif tool_name == "quick_search":
                # 简单搜索 - 快速检索
                query = parameters.get("query", "")
                limit = parameters.get("limit", 10)
                if isinstance(limit, str):
                    limit = int(limit)
                result = self.zep_tools.quick_search(
                    graph_id=self.graph_id,
                    query=query,
                    limit=limit
                )
                return result.to_text()
            
            elif tool_name == "interview_agents":
                # 深度采访 - 调用真实的OASIS采访API获取模拟Agent的回答（双平台）
                interview_topic = parameters.get("interview_topic", parameters.get("query", ""))
                max_agents = parameters.get("max_agents", 5)
                if isinstance(max_agents, str):
                    max_agents = int(max_agents)
                max_agents = min(max_agents, 10)
                result = self.zep_tools.interview_agents(
                    simulation_id=self.simulation_id,
                    interview_requirement=interview_topic,
                    simulation_requirement=self.simulation_requirement,
                    max_agents=max_agents
                )
                return result.to_text()
            
            # ========== 向后兼容的旧工具（内部重定向到新工具） ==========
            
            elif tool_name == "search_graph":
                # 重定向到 quick_search
                logger.info(t('report.redirectToQuickSearch'))
                return self._execute_tool("quick_search", parameters, report_context)
            
            elif tool_name == "get_graph_statistics":
                result = self.zep_tools.get_graph_statistics(self.graph_id)
                return json.dumps(result, ensure_ascii=False, indent=2)
            
            elif tool_name == "get_entity_summary":
                entity_name = parameters.get("entity_name", "")
                result = self.zep_tools.get_entity_summary(
                    graph_id=self.graph_id,
                    entity_name=entity_name
                )
                return json.dumps(result, ensure_ascii=False, indent=2)
            
            elif tool_name == "get_simulation_context":
                # 重定向到 insight_forge，因为它更强大
                logger.info(t('report.redirectToInsightForge'))
                query = parameters.get("query", self.simulation_requirement)
                return self._execute_tool("insight_forge", {"query": query}, report_context)
            
            elif tool_name == "get_entities_by_type":
                entity_type = parameters.get("entity_type", "")
                nodes = self.zep_tools.get_entities_by_type(
                    graph_id=self.graph_id,
                    entity_type=entity_type
                )
                result = [n.to_dict() for n in nodes]
                return json.dumps(result, ensure_ascii=False, indent=2)
            
            else:
                return f"未知工具: {tool_name}。请使用以下工具之一: insight_forge, panorama_search, quick_search"
                
        except Exception as e:
            logger.error(t('report.toolExecFailed', toolName=tool_name, error=str(e)))
            return f"工具执行失败: {str(e)}"
    
    # 合法的工具名称集合，用于裸 JSON 兜底解析时校验
    VALID_TOOL_NAMES = {"insight_forge", "panorama_search", "quick_search", "interview_agents"}

    def _parse_tool_calls(self, response: str) -> List[Dict[str, Any]]:
        """
        从LLM响应中解析工具调用

        支持的格式（按优先级）：
        1. <tool_call>{"name": "tool_name", "parameters": {...}}</tool_call>
        2. 裸 JSON（响应整体或单行就是一个工具调用 JSON）
        """
        tool_calls = []

        # 格式1: XML风格（标准格式）
        xml_pattern = r'<tool_call>\s*(\{.*?\})\s*</tool_call>'
        for match in re.finditer(xml_pattern, response, re.DOTALL):
            try:
                call_data = json.loads(match.group(1))
                tool_calls.append(call_data)
            except json.JSONDecodeError:
                pass

        if tool_calls:
            return tool_calls

        # 格式2: 兜底 - LLM 直接输出裸 JSON（没包 <tool_call> 标签）
        # 只在格式1未匹配时尝试，避免误匹配正文中的 JSON
        stripped = response.strip()
        if stripped.startswith('{') and stripped.endswith('}'):
            try:
                call_data = json.loads(stripped)
                if self._is_valid_tool_call(call_data):
                    tool_calls.append(call_data)
                    return tool_calls
            except json.JSONDecodeError:
                pass

        # 响应可能包含思考文字 + 裸 JSON，尝试提取最后一个 JSON 对象
        json_pattern = r'(\{"(?:name|tool)"\s*:.*?\})\s*$'
        match = re.search(json_pattern, stripped, re.DOTALL)
        if match:
            try:
                call_data = json.loads(match.group(1))
                if self._is_valid_tool_call(call_data):
                    tool_calls.append(call_data)
            except json.JSONDecodeError:
                pass

        return tool_calls

    def _is_valid_tool_call(self, data: dict) -> bool:
        """校验解析出的 JSON 是否是合法的工具调用"""
        # 支持 {"name": ..., "parameters": ...} 和 {"tool": ..., "params": ...} 两种键名
        tool_name = data.get("name") or data.get("tool")
        if tool_name and tool_name in self.VALID_TOOL_NAMES:
            # 统一键名为 name / parameters
            if "tool" in data:
                data["name"] = data.pop("tool")
            if "params" in data and "parameters" not in data:
                data["parameters"] = data.pop("params")
            return True
        return False
    
    def _get_tools_description(self) -> str:
        """生成工具描述文本"""
        desc_parts = ["可用工具："]
        for name, tool in self.tools.items():
            params_desc = ", ".join([f"{k}: {v}" for k, v in tool["parameters"].items()])
            desc_parts.append(f"- {name}: {tool['description']}")
            if params_desc:
                desc_parts.append(f"  参数: {params_desc}")
        return "\n".join(desc_parts)
    
    def plan_outline(
        self, 
        progress_callback: Optional[Callable] = None
    ) -> ReportOutline:
        """
        规划报告大纲
        
        使用LLM分析模拟需求，规划报告的目录结构
        
        Args:
            progress_callback: 进度回调函数
            
        Returns:
            ReportOutline: 报告大纲
        """
        logger.info(t('report.startPlanningOutline'))
        
        if progress_callback:
            progress_callback("planning", 0, t('progress.analyzingRequirements'))
        
        # 首先获取模拟上下文
        context = self.zep_tools.get_simulation_context(
            graph_id=self.graph_id,
            simulation_requirement=self.simulation_requirement
        )
        
        if progress_callback:
            progress_callback("planning", 30, t('progress.generatingOutline'))
        
        if self.project_type == "consumer_test":
            system_prompt = f"{CONSUMER_PLAN_SYSTEM_PROMPT}\n\n{get_language_instruction()}"
            user_prompt = CONSUMER_PLAN_USER_PROMPT_TEMPLATE.format(
                simulation_requirement=self.simulation_requirement,
                total_nodes=context.get('graph_statistics', {}).get('total_nodes', 0),
                total_edges=context.get('graph_statistics', {}).get('total_edges', 0),
                entity_types=list(context.get('graph_statistics', {}).get('entity_types', {}).keys()),
                total_entities=context.get('total_entities', 0),
                related_facts_json=json.dumps(context.get('related_facts', [])[:10], ensure_ascii=False, indent=2),
            )
        else:
            system_prompt = f"{PLAN_SYSTEM_PROMPT}\n\n{get_language_instruction()}"
            user_prompt = PLAN_USER_PROMPT_TEMPLATE.format(
                simulation_requirement=self.simulation_requirement,
                total_nodes=context.get('graph_statistics', {}).get('total_nodes', 0),
                total_edges=context.get('graph_statistics', {}).get('total_edges', 0),
                entity_types=list(context.get('graph_statistics', {}).get('entity_types', {}).keys()),
                total_entities=context.get('total_entities', 0),
                related_facts_json=json.dumps(context.get('related_facts', [])[:10], ensure_ascii=False, indent=2),
            )

        try:
            response = self.llm.chat_json(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.3
            )
            
            if progress_callback:
                progress_callback("planning", 80, t('progress.parsingOutline'))
            
            # 解析大纲
            sections = []
            for section_data in response.get("sections", []):
                sections.append(ReportSection(
                    title=section_data.get("title", ""),
                    content=""
                ))
            
            outline = ReportOutline(
                title=response.get("title", "模拟分析报告"),
                summary=response.get("summary", ""),
                sections=sections
            )
            
            if progress_callback:
                progress_callback("planning", 100, t('progress.outlinePlanComplete'))
            
            logger.info(t('report.outlinePlanDone', count=len(sections)))
            return outline
            
        except Exception as e:
            logger.error(t('report.outlinePlanFailed', error=str(e)))
            # 返回默认大纲（3个章节，作为fallback）
            return ReportOutline(
                title="未来预测报告",
                summary="基于模拟预测的未来趋势与风险分析",
                sections=[
                    ReportSection(title="预测场景与核心发现"),
                    ReportSection(title="人群行为预测分析"),
                    ReportSection(title="趋势展望与风险提示")
                ]
            )
    
    def _generate_section_react(
        self, 
        section: ReportSection,
        outline: ReportOutline,
        previous_sections: List[str],
        progress_callback: Optional[Callable] = None,
        section_index: int = 0
    ) -> str:
        """
        使用ReACT模式生成单个章节内容
        
        ReACT循环：
        1. Thought（思考）- 分析需要什么信息
        2. Action（行动）- 调用工具获取信息
        3. Observation（观察）- 分析工具返回结果
        4. 重复直到信息足够或达到最大次数
        5. Final Answer（最终回答）- 生成章节内容
        
        Args:
            section: 要生成的章节
            outline: 完整大纲
            previous_sections: 之前章节的内容（用于保持连贯性）
            progress_callback: 进度回调
            section_index: 章节索引（用于日志记录）
            
        Returns:
            章节内容（Markdown格式）
        """
        logger.info(t('report.reactGenerateSection', title=section.title))
        
        # 记录章节开始日志
        if self.report_logger:
            self.report_logger.log_section_start(section.title, section_index)
        
        # 构建用户prompt - 每个已完成章节各传入最大4000字
        if previous_sections:
            previous_parts = []
            for sec in previous_sections:
                # 每个章节最多4000字
                truncated = sec[:4000] + "..." if len(sec) > 4000 else sec
                previous_parts.append(truncated)
            previous_content = "\n\n---\n\n".join(previous_parts)
        else:
            previous_content = "（这是第一个章节）"

        if self.project_type == "consumer_test":
            system_prompt = CONSUMER_SECTION_SYSTEM_PROMPT_TEMPLATE.format(
                report_title=outline.title,
                report_summary=outline.summary,
                simulation_requirement=self.simulation_requirement,
                section_title=section.title,
                tools_description=self._get_tools_description(),
            )
            user_prompt = CONSUMER_SECTION_USER_PROMPT_TEMPLATE.format(
                previous_content=previous_content,
                section_title=section.title,
            )
        else:
            system_prompt = SECTION_SYSTEM_PROMPT_TEMPLATE.format(
                report_title=outline.title,
                report_summary=outline.summary,
                simulation_requirement=self.simulation_requirement,
                section_title=section.title,
                tools_description=self._get_tools_description(),
            )
            user_prompt = SECTION_USER_PROMPT_TEMPLATE.format(
                previous_content=previous_content,
                section_title=section.title,
            )
        system_prompt = f"{system_prompt}\n\n{get_language_instruction()}"

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        # ReACT循环
        tool_calls_count = 0
        max_iterations = 5  # 最大迭代轮数
        min_tool_calls = 3  # 最少工具调用次数
        conflict_retries = 0  # 工具调用与Final Answer同时出现的连续冲突次数
        used_tools = set()  # 记录已调用过的工具名
        all_tools = {"insight_forge", "panorama_search", "quick_search", "interview_agents"}

        # 报告上下文，用于InsightForge的子问题生成
        report_context = f"章节标题: {section.title}\n模拟需求: {self.simulation_requirement}"
        
        for iteration in range(max_iterations):
            if progress_callback:
                progress_callback(
                    "generating", 
                    int((iteration / max_iterations) * 100),
                    t('progress.deepSearchAndWrite', current=tool_calls_count, max=self.MAX_TOOL_CALLS_PER_SECTION)
                )
            
            # 调用LLM
            response = self.llm.chat(
                messages=messages,
                temperature=0.5,
                max_tokens=4096
            )

            # 检查 LLM 返回是否为 None（API 异常或内容为空）
            if response is None:
                logger.warning(t('report.sectionIterNone', title=section.title, iteration=iteration + 1))
                # 如果还有迭代次数，添加消息并重试
                if iteration < max_iterations - 1:
                    messages.append({"role": "assistant", "content": "（响应为空）"})
                    messages.append({"role": "user", "content": "请继续生成内容。"})
                    continue
                # 最后一次迭代也返回 None，跳出循环进入强制收尾
                break

            logger.debug(f"LLM响应: {response[:200]}...")

            # 解析一次，复用结果
            tool_calls = self._parse_tool_calls(response)
            has_tool_calls = bool(tool_calls)
            has_final_answer = "Final Answer:" in response

            # ── 冲突处理：LLM 同时输出了工具调用和 Final Answer ──
            if has_tool_calls and has_final_answer:
                conflict_retries += 1
                logger.warning(
                    t('report.sectionConflict', title=section.title, iteration=iteration+1, conflictCount=conflict_retries)
                )

                if conflict_retries <= 2:
                    # 前两次：丢弃本次响应，要求 LLM 重新回复
                    messages.append({"role": "assistant", "content": response})
                    messages.append({
                        "role": "user",
                        "content": (
                            "【格式错误】你在一次回复中同时包含了工具调用和 Final Answer，这是不允许的。\n"
                            "每次回复只能做以下两件事之一：\n"
                            "- 调用一个工具（输出一个 <tool_call> 块，不要写 Final Answer）\n"
                            "- 输出最终内容（以 'Final Answer:' 开头，不要包含 <tool_call>）\n"
                            "请重新回复，只做其中一件事。"
                        ),
                    })
                    continue
                else:
                    # 第三次：降级处理，截断到第一个工具调用，强制执行
                    logger.warning(
                        t('report.sectionConflictDowngrade', title=section.title, conflictCount=conflict_retries)
                    )
                    first_tool_end = response.find('</tool_call>')
                    if first_tool_end != -1:
                        response = response[:first_tool_end + len('</tool_call>')]
                        tool_calls = self._parse_tool_calls(response)
                        has_tool_calls = bool(tool_calls)
                    has_final_answer = False
                    conflict_retries = 0

            # 记录 LLM 响应日志
            if self.report_logger:
                self.report_logger.log_llm_response(
                    section_title=section.title,
                    section_index=section_index,
                    response=response,
                    iteration=iteration + 1,
                    has_tool_calls=has_tool_calls,
                    has_final_answer=has_final_answer
                )

            # ── 情况1：LLM 输出了 Final Answer ──
            if has_final_answer:
                # 工具调用次数不足，拒绝并要求继续调工具
                if tool_calls_count < min_tool_calls:
                    messages.append({"role": "assistant", "content": response})
                    unused_tools = all_tools - used_tools
                    unused_hint = f"（这些工具还未使用，推荐用一下他们: {', '.join(unused_tools)}）" if unused_tools else ""
                    messages.append({
                        "role": "user",
                        "content": REACT_INSUFFICIENT_TOOLS_MSG.format(
                            tool_calls_count=tool_calls_count,
                            min_tool_calls=min_tool_calls,
                            unused_hint=unused_hint,
                        ),
                    })
                    continue

                # 正常结束
                final_answer = response.split("Final Answer:")[-1].strip()
                logger.info(t('report.sectionGenDone', title=section.title, count=tool_calls_count))

                if self.report_logger:
                    self.report_logger.log_section_content(
                        section_title=section.title,
                        section_index=section_index,
                        content=final_answer,
                        tool_calls_count=tool_calls_count
                    )
                return final_answer

            # ── 情况2：LLM 尝试调用工具 ──
            if has_tool_calls:
                # 工具额度已耗尽 → 明确告知，要求输出 Final Answer
                if tool_calls_count >= self.MAX_TOOL_CALLS_PER_SECTION:
                    messages.append({"role": "assistant", "content": response})
                    messages.append({
                        "role": "user",
                        "content": REACT_TOOL_LIMIT_MSG.format(
                            tool_calls_count=tool_calls_count,
                            max_tool_calls=self.MAX_TOOL_CALLS_PER_SECTION,
                        ),
                    })
                    continue

                # 只执行第一个工具调用
                call = tool_calls[0]
                if len(tool_calls) > 1:
                    logger.info(t('report.multiToolOnlyFirst', total=len(tool_calls), toolName=call['name']))

                if self.report_logger:
                    self.report_logger.log_tool_call(
                        section_title=section.title,
                        section_index=section_index,
                        tool_name=call["name"],
                        parameters=call.get("parameters", {}),
                        iteration=iteration + 1
                    )

                result = self._execute_tool(
                    call["name"],
                    call.get("parameters", {}),
                    report_context=report_context
                )

                if self.report_logger:
                    self.report_logger.log_tool_result(
                        section_title=section.title,
                        section_index=section_index,
                        tool_name=call["name"],
                        result=result,
                        iteration=iteration + 1
                    )

                tool_calls_count += 1
                used_tools.add(call['name'])

                # 构建未使用工具提示
                unused_tools = all_tools - used_tools
                unused_hint = ""
                if unused_tools and tool_calls_count < self.MAX_TOOL_CALLS_PER_SECTION:
                    unused_hint = REACT_UNUSED_TOOLS_HINT.format(unused_list="、".join(unused_tools))

                messages.append({"role": "assistant", "content": response})
                messages.append({
                    "role": "user",
                    "content": REACT_OBSERVATION_TEMPLATE.format(
                        tool_name=call["name"],
                        result=result,
                        tool_calls_count=tool_calls_count,
                        max_tool_calls=self.MAX_TOOL_CALLS_PER_SECTION,
                        used_tools_str=", ".join(used_tools),
                        unused_hint=unused_hint,
                    ),
                })
                continue

            # ── 情况3：既没有工具调用，也没有 Final Answer ──
            messages.append({"role": "assistant", "content": response})

            if tool_calls_count < min_tool_calls:
                # 工具调用次数不足，推荐未用过的工具
                unused_tools = all_tools - used_tools
                unused_hint = f"（这些工具还未使用，推荐用一下他们: {', '.join(unused_tools)}）" if unused_tools else ""

                messages.append({
                    "role": "user",
                    "content": REACT_INSUFFICIENT_TOOLS_MSG_ALT.format(
                        tool_calls_count=tool_calls_count,
                        min_tool_calls=min_tool_calls,
                        unused_hint=unused_hint,
                    ),
                })
                continue

            # 工具调用已足够，LLM 输出了内容但没带 "Final Answer:" 前缀
            # 直接将这段内容作为最终答案，不再空转
            logger.info(t('report.sectionNoPrefix', title=section.title, count=tool_calls_count))
            final_answer = response.strip()

            if self.report_logger:
                self.report_logger.log_section_content(
                    section_title=section.title,
                    section_index=section_index,
                    content=final_answer,
                    tool_calls_count=tool_calls_count
                )
            return final_answer
        
        # 达到最大迭代次数，强制生成内容
        logger.warning(t('report.sectionMaxIter', title=section.title))
        messages.append({"role": "user", "content": REACT_FORCE_FINAL_MSG})
        
        response = self.llm.chat(
            messages=messages,
            temperature=0.5,
            max_tokens=4096
        )

        # 检查强制收尾时 LLM 返回是否为 None
        if response is None:
            logger.error(t('report.sectionForceFailed', title=section.title))
            final_answer = t('report.sectionGenFailedContent')
        elif "Final Answer:" in response:
            final_answer = response.split("Final Answer:")[-1].strip()
        else:
            final_answer = response
        
        # 记录章节内容生成完成日志
        if self.report_logger:
            self.report_logger.log_section_content(
                section_title=section.title,
                section_index=section_index,
                content=final_answer,
                tool_calls_count=tool_calls_count
            )
        
        return final_answer
    
    def generate_report(
        self, 
        progress_callback: Optional[Callable[[str, int, str], None]] = None,
        report_id: Optional[str] = None
    ) -> Report:
        """
        生成完整报告（分章节实时输出）
        
        每个章节生成完成后立即保存到文件夹，不需要等待整个报告完成。
        文件结构：
        reports/{report_id}/
            meta.json       - 报告元信息
            outline.json    - 报告大纲
            progress.json   - 生成进度
            section_01.md   - 第1章节
            section_02.md   - 第2章节
            ...
            full_report.md  - 完整报告
        
        Args:
            progress_callback: 进度回调函数 (stage, progress, message)
            report_id: 报告ID（可选，如果不传则自动生成）
            
        Returns:
            Report: 完整报告
        """
        import uuid
        
        # 如果没有传入 report_id，则自动生成
        if not report_id:
            report_id = f"report_{uuid.uuid4().hex[:12]}"
        start_time = datetime.now()
        
        report = Report(
            report_id=report_id,
            simulation_id=self.simulation_id,
            graph_id=self.graph_id,
            simulation_requirement=self.simulation_requirement,
            status=ReportStatus.PENDING,
            project_type=self.project_type,
            created_at=datetime.now().isoformat()
        )
        
        # 已完成的章节标题列表（用于进度追踪）
        completed_section_titles = []
        
        try:
            # 初始化：创建报告文件夹并保存初始状态
            ReportManager._ensure_report_folder(report_id)
            
            # 初始化日志记录器（结构化日志 agent_log.jsonl）
            self.report_logger = ReportLogger(report_id)
            self.report_logger.log_start(
                simulation_id=self.simulation_id,
                graph_id=self.graph_id,
                simulation_requirement=self.simulation_requirement
            )
            
            # 初始化控制台日志记录器（console_log.txt）
            self.console_logger = ReportConsoleLogger(report_id)
            
            ReportManager.update_progress(
                report_id, "pending", 0, t('progress.initReport'),
                completed_sections=[]
            )
            ReportManager.save_report(report)

            if self.project_type == "consumer_test":
                return self._generate_consumer_report(
                    report=report,
                    report_id=report_id,
                    start_time=start_time,
                    completed_section_titles=completed_section_titles,
                    progress_callback=progress_callback,
                )
            
            # 阶段1: 规划大纲
            report.status = ReportStatus.PLANNING
            ReportManager.update_progress(
                report_id, "planning", 5, t('progress.startPlanningOutline'),
                completed_sections=[]
            )
            
            # 记录规划开始日志
            self.report_logger.log_planning_start()
            
            if progress_callback:
                progress_callback("planning", 0, t('progress.startPlanningOutline'))
            
            outline = self.plan_outline(
                progress_callback=lambda stage, prog, msg: 
                    progress_callback(stage, prog // 5, msg) if progress_callback else None
            )
            report.outline = outline
            
            # 记录规划完成日志
            self.report_logger.log_planning_complete(outline.to_dict())
            
            # 保存大纲到文件
            ReportManager.save_outline(report_id, outline)
            ReportManager.update_progress(
                report_id, "planning", 15, t('progress.outlineDone', count=len(outline.sections)),
                completed_sections=[]
            )
            ReportManager.save_report(report)
            
            logger.info(t('report.outlineSavedToFile', reportId=report_id))
            
            # 阶段2: 逐章节生成（分章节保存）
            report.status = ReportStatus.GENERATING
            
            total_sections = len(outline.sections)
            generated_sections = []  # 保存内容用于上下文
            
            for i, section in enumerate(outline.sections):
                section_num = i + 1
                base_progress = 20 + int((i / total_sections) * 70)
                
                # 更新进度
                ReportManager.update_progress(
                    report_id, "generating", base_progress,
                    t('progress.generatingSection', title=section.title, current=section_num, total=total_sections),
                    current_section=section.title,
                    completed_sections=completed_section_titles
                )

                if progress_callback:
                    progress_callback(
                        "generating",
                        base_progress,
                        t('progress.generatingSection', title=section.title, current=section_num, total=total_sections)
                    )
                
                # 生成主章节内容
                section_content = self._generate_section_react(
                    section=section,
                    outline=outline,
                    previous_sections=generated_sections,
                    progress_callback=lambda stage, prog, msg:
                        progress_callback(
                            stage, 
                            base_progress + int(prog * 0.7 / total_sections),
                            msg
                        ) if progress_callback else None,
                    section_index=section_num
                )
                
                section.content = section_content
                generated_sections.append(f"## {section.title}\n\n{section_content}")

                # 保存章节
                ReportManager.save_section(report_id, section_num, section)
                completed_section_titles.append(section.title)

                # 记录章节完成日志
                full_section_content = f"## {section.title}\n\n{section_content}"

                if self.report_logger:
                    self.report_logger.log_section_full_complete(
                        section_title=section.title,
                        section_index=section_num,
                        full_content=full_section_content.strip()
                    )

                logger.info(t('report.sectionSaved', reportId=report_id, sectionNum=f"{section_num:02d}"))
                
                # 更新进度
                ReportManager.update_progress(
                    report_id, "generating", 
                    base_progress + int(70 / total_sections),
                    t('progress.sectionDone', title=section.title),
                    current_section=None,
                    completed_sections=completed_section_titles
                )
            
            # 阶段3: 组装完整报告
            if progress_callback:
                progress_callback("generating", 95, t('progress.assemblingReport'))
            
            ReportManager.update_progress(
                report_id, "generating", 95, t('progress.assemblingReport'),
                completed_sections=completed_section_titles
            )
            
            # 使用ReportManager组装完整报告
            report.markdown_content = ReportManager.assemble_full_report(report_id, outline)
            report.status = ReportStatus.COMPLETED
            report.completed_at = datetime.now().isoformat()
            
            # 计算总耗时
            total_time_seconds = (datetime.now() - start_time).total_seconds()
            
            # 记录报告完成日志
            if self.report_logger:
                self.report_logger.log_report_complete(
                    total_sections=total_sections,
                    total_time_seconds=total_time_seconds
                )
            
            # 保存最终报告
            ReportManager.save_report(report)
            ReportManager.update_progress(
                report_id, "completed", 100, t('progress.reportComplete'),
                completed_sections=completed_section_titles
            )
            
            if progress_callback:
                progress_callback("completed", 100, t('progress.reportComplete'))
            
            logger.info(t('report.reportGenDone', reportId=report_id))
            
            # 关闭控制台日志记录器
            if self.console_logger:
                self.console_logger.close()
                self.console_logger = None
            
            return report
            
        except Exception as e:
            logger.error(t('report.reportGenFailed', error=str(e)))
            report.status = ReportStatus.FAILED
            report.error = str(e)
            
            # 记录错误日志
            if self.report_logger:
                self.report_logger.log_error(str(e), "failed")
            
            # 保存失败状态
            try:
                ReportManager.save_report(report)
                ReportManager.update_progress(
                    report_id, "failed", -1, t('progress.reportFailed', error=str(e)),
                    completed_sections=completed_section_titles
                )
            except Exception:
                pass  # 忽略保存失败的错误
            
            # 关闭控制台日志记录器
            if self.console_logger:
                self.console_logger.close()
                self.console_logger = None
            
            return report

    def _generate_consumer_report(
        self,
        report: Report,
        report_id: str,
        start_time: datetime,
        completed_section_titles: List[str],
        progress_callback: Optional[Callable[[str, int, str], None]] = None,
    ) -> Report:
        if self.report_logger:
            self.report_logger.log_planning_start()

        ReportManager.update_progress(
            report_id, "planning", 10, "正在整理消费者传播证据",
            completed_sections=completed_section_titles,
        )
        if progress_callback:
            progress_callback("planning", 10, "正在整理消费者传播证据")

        context = self._build_consumer_report_context()
        report.report_context = context
        outline = self._build_consumer_outline(context)
        report.outline = outline
        report.status = ReportStatus.GENERATING
        ReportManager.save_outline(report_id, outline)
        ReportManager.save_report(report)

        if self.report_logger:
            self.report_logger.log_planning_complete(outline.to_dict())

        total_sections = len(outline.sections)
        generated_section_contents: List[str] = []
        for index, section in enumerate(outline.sections, start=1):
            progress = 20 + int(((index - 1) / max(total_sections, 1)) * 70)
            ReportManager.update_progress(
                report_id,
                "generating",
                progress,
                f"正在生成章节：{section.title}",
                current_section=section.title,
                completed_sections=completed_section_titles,
            )
            if progress_callback:
                progress_callback("generating", progress, f"正在生成章节：{section.title}")

            section.content = self._render_consumer_section_with_optional_llm(
                section=section,
                outline=outline,
                context=context,
                previous_sections=generated_section_contents,
            )
            ReportManager.save_section(report_id, index, section)
            completed_section_titles.append(section.title)
            generated_section_contents.append(f"## {section.title}\n\n{section.content}".strip())

            if self.report_logger:
                self.report_logger.log_section_full_complete(
                    section_title=section.title,
                    section_index=index,
                    full_content=f"## {section.title}\n\n{section.content}".strip(),
                )

        report.markdown_content = ReportManager.assemble_full_report(report_id, outline)
        report.status = ReportStatus.COMPLETED
        report.completed_at = datetime.now().isoformat()

        total_time_seconds = (datetime.now() - start_time).total_seconds()
        if self.report_logger:
            self.report_logger.log_report_complete(
                total_sections=total_sections,
                total_time_seconds=total_time_seconds,
            )

        ReportManager.save_report(report)
        ReportManager.update_progress(
            report_id, "completed", 100, t('progress.reportComplete'),
            completed_sections=completed_section_titles,
        )
        if progress_callback:
            progress_callback("completed", 100, t('progress.reportComplete'))

        if self.console_logger:
            self.console_logger.close()
            self.console_logger = None

        return report

    def _consumer_report_llm_enabled(self) -> bool:
        return os.environ.get("CONSUMER_REPORT_LLM_ENABLED", "").strip().lower() in {
            "1",
            "true",
            "yes",
            "on",
        }

    def _render_consumer_section_with_optional_llm(
        self,
        *,
        section: ReportSection,
        outline: ReportOutline,
        context: Dict[str, Any],
        previous_sections: List[str],
    ) -> str:
        if not self._consumer_report_llm_enabled():
            return self._render_consumer_section(section.title, context)

        stats = getattr(
            self,
            "consumer_report_llm_stats",
            {"attempted": 0, "succeeded": 0, "failed": 0, "latencies": []},
        )
        stats["attempted"] += 1
        started_at = time.time()
        try:
            context_preview = json.dumps(context, ensure_ascii=False, default=str)[:4000]
            llm_previous_sections = [
                f"consumer_report_context:\n{context_preview}",
                *previous_sections,
            ]
            content = self._generate_section_react(section, outline, llm_previous_sections)
            stats["succeeded"] += 1
            stats["latencies"].append(round(time.time() - started_at, 4))
            self.consumer_report_llm_stats = stats
            return content
        except Exception as exc:
            stats["failed"] += 1
            stats["latencies"].append(round(time.time() - started_at, 4))
            self.consumer_report_llm_stats = stats
            logger.warning("Consumer report LLM section failed; falling back to template: %s", exc)
            return self._render_consumer_section(section.title, context)
    def _build_consumer_report_context(self) -> Dict[str, Any]:
        rounds_path = os.path.join(
            Config.UPLOAD_FOLDER,
            "simulations",
            self.simulation_id,
            "consumer_rounds.jsonl",
        )
        builder = ConsumerReportContextBuilder()
        snapshots = builder.load_events(rounds_path)
        context: Dict[str, Any]
        if not snapshots:
            from .consumer.society.report_adapter import SocietyReportAdapter

            society_context = SocietyReportAdapter().build_report_context(self.simulation_id)
            if society_context.get("society_agents_count", 0) > 0:
                context = self._build_consumer_context_from_society_context(society_context)
            else:
                raise ValueError(f"消费者传播快照不存在: {self.simulation_id}")
        else:
            # Phase 1 baseline context
            context = builder.build(snapshots)

        # Extract propagation events for Phase 2 enrichment
        all_events = []
        for snap in snapshots:
            for event_data in snap.get("propagation_events", []):
                all_events.append(event_data)

        # Load research findings and snapshot
        # Prefer project-level persisted artifacts when available
        research_findings: List[Any] = []
        retrieval_traces: List[Any] = []
        research_snapshot: Dict[str, Any] = {}

        project_id = self.project_id
        if project_id is None:
            # Fall back to reading project_id from simulation state
            state_path = os.path.join(
                Config.UPLOAD_FOLDER, "simulations", self.simulation_id, "state.json"
            )
            if os.path.exists(state_path):
                with open(state_path, "r", encoding="utf-8") as f:
                    state_data = json.load(f)
                project_id = state_data.get("project_id")

        loaded_from_project = False
        if project_id and artifacts_exist(project_id, upload_root=Config.UPLOAD_FOLDER):
            persisted_findings = load_persisted_findings(
                project_id, upload_root=Config.UPLOAD_FOLDER
            )
            persisted_snapshot = load_persisted_snapshot(
                project_id, upload_root=Config.UPLOAD_FOLDER
            )
            if persisted_findings is not None and persisted_snapshot is not None:
                research_findings = [f.model_dump() for f in persisted_findings]
                research_snapshot = {
                    "snapshot_id": persisted_snapshot.snapshot_id,
                    "source_count": len(persisted_snapshot.sources),
                    "document_count": len(persisted_snapshot.documents),
                    "chunk_count": len(persisted_snapshot.chunks),
                    "finding_count": len(persisted_snapshot.findings),
                    "retrieval_trace_count": len(persisted_snapshot.retrieval_traces),
                }
                retrieval_traces = [
                    t.model_dump() for t in persisted_snapshot.retrieval_traces
                ]
                loaded_from_project = True

        consumer_config: Dict[str, Any] = {}
        consumer_config_path = os.path.join(
            Config.UPLOAD_FOLDER, "simulations", self.simulation_id, "consumer_config.json"
        )
        if os.path.exists(consumer_config_path):
            with open(consumer_config_path, "r", encoding="utf-8") as f:
                consumer_config = json.load(f)
        if not loaded_from_project:
            research_findings = consumer_config.get("research_findings", [])
            retrieval_traces = consumer_config.get("retrieval_traces", [])
            research_snapshot = consumer_config.get("research_snapshot", {})
        # When loaded_from_project is True, project-level artifacts are authoritative
        # for research_findings/retrieval_traces/research_snapshot. consumer_config is
        # still read above for consumer_brief/task_type extraction below.
        # However, if propagation events reference finding_ids not present in project
        # findings, append matching consumer_config findings/traces as supplemental.
        supplemental_merged = False
        if loaded_from_project and consumer_config and all_events:
            event_finding_ids = set()
            for event in all_events:
                for fid in event.get("trigger_finding_ids", []):
                    if fid:
                        event_finding_ids.add(fid)
            project_finding_ids = {
                f.get("finding_id") for f in research_findings if f.get("finding_id")
            }
            missing_ids = event_finding_ids - project_finding_ids
            if missing_ids:
                cc_findings = consumer_config.get("research_findings", [])
                cc_traces = consumer_config.get("retrieval_traces", [])
                existing_trace_ids = {
                    t.get("trace_id") for t in retrieval_traces if t.get("trace_id")
                }
                for finding in cc_findings:
                    if finding.get("finding_id") in missing_ids:
                        research_findings.append(finding)
                        supplemental_merged = True
                        trace_id = finding.get("retrieval_trace_id")
                        if trace_id:
                            for t in cc_traces:
                                if t.get("trace_id") == trace_id and trace_id not in existing_trace_ids:
                                    retrieval_traces.append(t)
                                    existing_trace_ids.add(trace_id)
                                    break

        # Extract task_type from consumer brief when available
        task_type: Optional[str] = None
        brief = None
        consumer_brief_summary = consumer_config.get("consumer_brief", {})
        if isinstance(consumer_brief_summary, dict) and consumer_brief_summary.get("task_type"):
            task_type = consumer_brief_summary.get("task_type")
            from ..services.consumer.brief_adapter import ConsumerBriefAdapter
            brief = ConsumerBriefAdapter.from_payload(consumer_brief_summary)
        elif self.project_id:
            project = ProjectManager.get_project(self.project_id)
            if project and getattr(project, "consumer_brief", None):
                from ..services.consumer.brief_adapter import ConsumerBriefAdapter
                brief = ConsumerBriefAdapter.from_payload(project.consumer_brief)
                task_type = brief.task_type.value

        # Include research snapshot and findings in report context
        context["research_snapshot"] = research_snapshot
        context["research_findings"] = research_findings
        context["retrieval_traces"] = retrieval_traces
        context["task_type"] = task_type or "concept_test"
        brief_summary = consumer_brief_summary if isinstance(consumer_brief_summary, dict) else {}
        context["industry"] = brief_summary.get("category") or (
            getattr(brief, "category", "")
            if brief is not None
            else ""
        ) or brief_summary.get("industry", "")
        context["target_audience"] = (
            brief.target_audience if brief is not None and getattr(brief, "target_audience", None) else brief_summary.get("target_audience", [])
        )

        # Merge Phase 2 fields when we have propagation events or research findings.
        if all_events or research_findings:
            from ..services.consumer.scoring import build_consumer_summary
            from ..services.consumer.report_context import build_consumer_report_context

            initial_labels = [s.get("attitude_label", "neutral") for s in snapshots if s.get("round_num") == 0]
            latest_attitudes: Dict[str, str] = {}
            for s in snapshots:
                agent_id = s.get("agent_id", "")
                if agent_id:
                    latest_attitudes[agent_id] = s.get("attitude_label", "neutral")
            final_labels = list(latest_attitudes.values())

            phase2_summary = build_consumer_summary(
                events=all_events,
                findings=research_findings,
                initial_labels=initial_labels,
                final_labels=final_labels,
                traces=retrieval_traces,
                task_type=task_type,
                brief=brief,
            )
            # Avoid revalidating against an empty snapshot; phase2_summary already
            # carries the gatekeeping result built from consumer_config traces.
            report_snapshot = persisted_snapshot if loaded_from_project else None
            if report_snapshot is not None and not getattr(report_snapshot, "chunks", None) and not getattr(report_snapshot, "sources", None):
                report_snapshot = None
            # If supplemental simulation-level evidence was merged, do not re-run
            # gatekeeping against an incomplete project snapshot; let phase2_summary
            # supply the gatekeeping result. Snapshot enrichment is still applied.
            if supplemental_merged and report_snapshot is not None:
                phase2_context = build_consumer_report_context(
                    summary=phase2_summary,
                    findings=research_findings,
                    events=all_events,
                    traces=retrieval_traces,
                    snapshot=None,
                )
                from ..services.consumer.report_context import enrich_report_context_with_snapshot
                enrich_report_context_with_snapshot(
                    phase2_context, research_findings, retrieval_traces, report_snapshot
                )
            else:
                phase2_context = build_consumer_report_context(
                    summary=phase2_summary,
                    findings=research_findings,
                    events=all_events,
                    traces=retrieval_traces,
                    snapshot=report_snapshot,
                )

            if all_events:
                context["event_counts"] = phase2_summary.event_counts
                context["top_risk_findings"] = phase2_summary.top_risk_findings
                context["causal_chains"] = phase2_context["causal_chains"]
                context["event_led_reversals"] = phase2_context["event_led_reversals"]

            context["retrieval_provenance"] = phase2_context.get("retrieval_provenance")
            context["source_catalog"] = phase2_context.get("source_catalog")
            context["enriched_findings"] = phase2_context.get("enriched_findings")
            context["enriched_traces"] = phase2_context.get("enriched_traces")
            context["finding_evidence_atoms"] = phase2_context.get(
                "finding_evidence_atoms",
                context.get("finding_evidence_atoms", []),
            )
            context["evidence_atom_count"] = phase2_context.get(
                "evidence_atom_count",
                context.get("evidence_atom_count", 0),
            )
            context["evidence_gatekeeping_summary"] = (
                phase2_summary.evidence_gatekeeping_summary
                if supplemental_merged
                else (
                    phase2_context.get("evidence_gatekeeping_summary")
                    or phase2_summary.evidence_gatekeeping_summary
                )
            )

            # Inject task-aware fields from Phase 2 summary into context
            context["top_packaging_hooks"] = phase2_summary.top_packaging_hooks or context.get("top_packaging_hooks", [])
            context["top_trust_objections"] = phase2_summary.top_trust_objections or context.get("top_trust_objections", [])
            context["top_confusion_triggers"] = phase2_summary.top_confusion_triggers or context.get("top_confusion_triggers", [])
            context["winning_variant"] = phase2_summary.winning_variant or context.get("winning_variant", "")
            context["top_variant_deltas"] = phase2_summary.top_variant_deltas or context.get("top_variant_deltas", [])
            context["top_persona_divergences"] = phase2_summary.top_persona_divergences or context.get("top_persona_divergences", [])
            context["acceptable_price_points"] = phase2_summary.acceptable_price_points or context.get("acceptable_price_points", [])
            context["resisted_price_points"] = phase2_summary.resisted_price_points or context.get("resisted_price_points", [])
            context["top_price_objections"] = phase2_summary.top_price_objections or context.get("top_price_objections", [])
            context["price_context"] = phase2_summary.price_context or context.get("price_context", "")

        context.update(self._build_research_synthesis(context))

        # Phase 4A: include latest replay alignment for this simulation if available
        context["replay_alignment"] = self._load_latest_replay_alignment()

        # Phase 5: Selling point analysis & compliance check
        context['all_events'] = all_events
        claims = self._extract_claims_from_context(context)
        try:
            if analyze_selling_points is not None and claims:
                sp_report = analyze_selling_points(
                    claims=claims,
                    events=context.get('all_events', []),
                    voc_quotes=context.get('representative_voc_quotes', {}),
                    channel_metrics=context.get('channel_metrics'),
                    event_counts=context.get('consumer_event_counts', {}),
                )
                # Ensure JSON-serializable storage in context
                if hasattr(sp_report, 'to_dict'):
                    context['selling_point_report'] = sp_report.to_dict()
                elif hasattr(sp_report, '__dataclass_fields__'):
                    context['selling_point_report'] = asdict(sp_report)
                else:
                    context['selling_point_report'] = sp_report
        except Exception as e:
            logger.warning("Selling point analysis failed: %s", e)

        try:
            if check_compliance is not None and claims:
                comp_report = check_compliance(
                    claims=claims,
                    misread_quotes=context.get('representative_voc_quotes', {}).get('misread', []),
                    risk_quotes=context.get('representative_voc_quotes', {}).get('risk', []),
                )
                # Ensure JSON-serializable storage in context
                comp_dict = asdict(comp_report) if hasattr(comp_report, '__dataclass_fields__') else comp_report
                # findings is a property on ComplianceReport, not a field — add manually
                if isinstance(comp_dict, dict) and 'findings' not in comp_dict:
                    try:
                        comp_dict['findings'] = [
                            {
                                'expression': f.expression,
                                'risk_reason': f.risk_reason,
                                'suggested_alternative': f.suggested_alternative,
                            }
                            for f in comp_report.findings
                        ]
                    except Exception:
                        comp_dict['findings'] = []
                context['compliance_report'] = comp_dict
        except Exception as e:
            logger.warning("Compliance check failed: %s", e)

        from .consumer.society.report_adapter import SocietyReportAdapter

        society_adapter = SocietyReportAdapter()
        return society_adapter.merge_into_context(
            context,
            society_adapter.build_report_context(self.simulation_id),
        )

    def _build_consumer_context_from_society_context(
        self, society_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        context = dict(society_context)
        event_counts = {
            str(key): int(value or 0)
            for key, value in dict(context.get("society_event_summary") or {}).items()
        }
        total_events = sum(event_counts.values())

        positive_events = {
            "ADVOCACY",
            "FIRST_IMPRESSION",
            "PURCHASE_SIGNAL",
            "TRUST_RECOVERY",
        }
        negative_events = {
            "ASK_PROOF",
            "MISREAD_CLAIM",
            "PRICE_RESISTANCE",
            "TRUST_OBJECTION",
        }

        positive_count = sum(event_counts.get(name, 0) for name in positive_events)
        negative_count = sum(event_counts.get(name, 0) for name in negative_events)
        neutral_count = max(total_events - positive_count - negative_count, 0)

        if total_events > 0:
            post_acceptance = {
                "positive": positive_count / total_events,
                "neutral": neutral_count / total_events,
                "negative": negative_count / total_events,
            }
        else:
            post_acceptance = {"positive": 0.0, "neutral": 1.0, "negative": 0.0}

        initial_acceptance = {"positive": 0.0, "neutral": 1.0, "negative": 0.0}
        summary = {
            "initial_acceptance": initial_acceptance,
            "post_propagation_acceptance": post_acceptance,
            "attitude_shift_rate": abs(post_acceptance["positive"] - initial_acceptance["positive"]),
        }

        metrics = dict(context.get("society_metrics") or {})
        risk_points = self._string_list(context.get("society_top_risk_points"))
        if not risk_points:
            if metrics.get("misread_rate", 0) > 0:
                risk_points.append("功效边界和光学修色容易触发误读")
            if metrics.get("price_resistance_index", 0) > 0:
                risk_points.append("价格需要与同类产品形成清晰价值解释")
            if metrics.get("evidence_demand_rate", 0) > 0:
                risk_points.append("需要补充检测证明、备案信息和真实用户反馈")

        resonance_points = self._string_list(context.get("society_top_resonance_points"))
        if not resonance_points and positive_count:
            resonance_points = ["核心宣称有第一眼记忆点，但需要真实场景支撑"]

        misread_points = self._string_list(context.get("society_top_misreads"))
        if not misread_points and event_counts.get("MISREAD_CLAIM", 0):
            misread_points = ["核心宣称容易被误读为全场景承诺或短期强承诺"]

        representative_voc_quotes = self._voc_quote_groups(
            context.get("representative_voc_quotes")
        )
        if not any(representative_voc_quotes.values()):
            representative_voc_quotes = self._voc_quote_groups(
                context.get("society_representative_voc_quotes")
            )

        context.update(
            {
                "summary": summary,
                "initial_acceptance": initial_acceptance,
                "post_propagation_acceptance": post_acceptance,
                "attitude_shift_rate": summary["attitude_shift_rate"],
                "events_count": total_events,
                "event_counts": event_counts,
                "consumer_event_counts": event_counts,
                "top_resonance_points": resonance_points,
                "top_risk_points": risk_points,
                "top_misreads": misread_points,
                "representative_voc_quotes": representative_voc_quotes,
                "evidence_bundle": {},
                "top_risk_findings": context.get("top_risk_findings", []),
                "causal_chains": context.get("causal_chains", []),
                "event_led_reversals": context.get("event_led_reversals", []),
                "top_packaging_hooks": context.get("top_packaging_hooks", []),
                "top_trust_objections": context.get("top_trust_objections", []),
                "top_confusion_triggers": context.get("top_confusion_triggers", []),
                "winning_variant": context.get("winning_variant", ""),
                "top_variant_deltas": context.get("top_variant_deltas", []),
                "top_persona_divergences": context.get("top_persona_divergences", []),
                "acceptable_price_points": context.get("acceptable_price_points", []),
                "resisted_price_points": context.get("resisted_price_points", []),
                "top_price_objections": context.get("top_price_objections", []),
                "price_context": context.get("price_context", ""),
            }
        )
        context.update(self._build_research_synthesis(context))
        return context

    @staticmethod
    def _string_list(value: Any) -> List[str]:
        if not isinstance(value, list):
            return []
        return [str(item).strip() for item in value if str(item).strip()]

    @staticmethod
    def _voc_quote_groups(value: Any) -> Dict[str, List[Dict[str, Any]]]:
        groups = {"resonance": [], "risk": [], "misread": []}
        if not isinstance(value, dict):
            return groups
        for key in groups:
            raw_items = value.get(key, [])
            if not isinstance(raw_items, list):
                continue
            groups[key] = [
                dict(item)
                for item in raw_items
                if isinstance(item, dict) and str(item.get("quote", "")).strip()
            ]
        return groups

    def _build_research_synthesis(self, context: Dict[str, Any]) -> Dict[str, Any]:
        findings = self._research_finding_records(context)
        if not findings:
            return {
                "research_findings_count": int(context.get("research_findings_count", 0) or 0),
                "research_finding_type_counts": dict(context.get("research_finding_type_counts", {}) or {}),
                "research_insight_pillars": list(context.get("research_insight_pillars", []) or []),
                "research_insight_summary": str(
                    context.get("research_insight_summary") or "暂无研究发现综合。"
                ),
            }

        type_counts: Counter[str] = Counter()
        grouped: Dict[str, List[Dict[str, Any]]] = {}
        for finding in findings:
            finding_type = str(finding.get("finding_type") or "unknown").strip() or "unknown"
            type_counts[finding_type] += 1
            grouped.setdefault(finding_type, []).append(finding)

        preferred_order = [
            "category_context",
            "competitor_signal",
            "risk_signal",
            "trend_signal",
            "propagation_signal",
        ]
        ordered_types = [ftype for ftype in preferred_order if ftype in grouped]
        ordered_types.extend(sorted(ftype for ftype in grouped if ftype not in preferred_order))

        pillars = [
            self._build_research_pillar(finding_type, grouped[finding_type])
            for finding_type in ordered_types
        ]
        summary_chunks = [
            f"{pillar['finding_type_label']}：{pillar['summary']}"
            for pillar in pillars[:4]
            if pillar.get("summary")
        ]
        if summary_chunks:
            summary_text = f"基于 {len(findings)} 条研究发现，" + "；".join(summary_chunks)
        else:
            summary_text = f"基于 {len(findings)} 条研究发现，已形成多条可执行洞察。"

        quote_parts: List[str] = []
        resonance_point = self._first_point(self._string_list(context.get("top_resonance_points")), "")
        risk_point = self._first_point(self._string_list(context.get("top_risk_points")), "")
        misread_point = self._first_point(self._string_list(context.get("top_misreads")), "")
        if resonance_point:
            quote_parts.append(f"正向原声指向“{resonance_point}”")
        if risk_point:
            quote_parts.append(f"风险原声集中在“{risk_point}”")
        if misread_point:
            quote_parts.append(f"误读点落在“{misread_point}”")
        if quote_parts:
            summary_text += "；" + "，".join(quote_parts)
        summary_text += "。"

        result: Dict[str, Any] = {
            "research_findings_count": len(findings),
            "research_finding_type_counts": dict(type_counts),
            "research_insight_pillars": pillars,
            "research_insight_summary": summary_text,
        }
        if not context.get("top_risk_findings"):
            result["top_risk_findings"] = self._research_risk_findings(findings)
        return result

    def _research_finding_records(self, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        candidates = context.get("enriched_findings") or context.get("research_findings") or []
        if not isinstance(candidates, list):
            return []
        records: List[Dict[str, Any]] = []
        for item in candidates:
            record = self._normalize_finding_record(item)
            if record is not None:
                records.append(record)
        return records

    def _normalize_finding_record(self, item: Any) -> Optional[Dict[str, Any]]:
        if isinstance(item, dict):
            record = dict(item)
        else:
            record = {
                "finding_id": getattr(item, "finding_id", ""),
                "finding_type": getattr(item, "finding_type", ""),
                "summary": getattr(item, "summary", ""),
                "evidence_snippets": list(getattr(item, "evidence_snippets", []) or []),
                "source_label": getattr(item, "source_label", ""),
                "source_title": getattr(item, "source_title", ""),
                "source_id": getattr(item, "source_id", ""),
                "confidence": getattr(item, "confidence", 0),
                "confidence_label": getattr(item, "confidence_label", ""),
                "gatekeeping_status": getattr(item, "gatekeeping_status", ""),
                "evidence_preview": getattr(item, "evidence_preview", ""),
                "visibility": getattr(item, "visibility", ""),
            }

        record["finding_id"] = str(record.get("finding_id", "") or "").strip()
        record["finding_type"] = str(record.get("finding_type", "") or "unknown").strip() or "unknown"
        summary = str(record.get("summary") or record.get("claim") or record.get("finding_id") or "").strip()
        if not summary:
            return None
        record["summary"] = summary
        record["source_label"] = str(record.get("source_label") or "").strip()
        record["source_title"] = str(record.get("source_title") or record.get("source_label") or "").strip()
        record["source_id"] = str(record.get("source_id") or "").strip()
        record["confidence_label"] = str(record.get("confidence_label") or "").strip()
        record["gatekeeping_status"] = str(record.get("gatekeeping_status") or "").strip().lower()
        record["evidence_preview"] = self._finding_evidence_preview(record)
        return record

    @staticmethod
    def _finding_evidence_preview(finding: Dict[str, Any]) -> str:
        preview = str(finding.get("evidence_preview") or "").strip()
        if preview:
            return preview[:240]
        snippets = finding.get("evidence_snippets")
        if isinstance(snippets, list):
            for snippet in snippets:
                text = str(snippet or "").strip()
                if text:
                    return text[:240]
        for key in ("summary", "claim"):
            text = str(finding.get(key) or "").strip()
            if text:
                return text[:240]
        return ""

    @staticmethod
    def _finding_digest_sort_key(finding: Dict[str, Any]) -> tuple[int, float, int, str]:
        status_rank = {
            "allowed": 0,
            "downgraded": 1,
            "blocked": 2,
        }.get(str(finding.get("gatekeeping_status") or "").strip().lower(), 3)
        confidence_value = finding.get("confidence", 0)
        try:
            confidence_score = float(confidence_value)
        except (TypeError, ValueError):
            confidence_score = {
                "high": 0.9,
                "medium": 0.6,
                "low": 0.3,
            }.get(str(finding.get("confidence_label") or "").strip().lower(), 0.0)
        evidence_rank = 0 if str(finding.get("evidence_preview") or "").strip() else 1
        summary = str(finding.get("summary") or "").strip().casefold()
        return (status_rank, -confidence_score, evidence_rank, summary)

    @staticmethod
    def _finding_type_label(finding_type: str) -> str:
        labels = {
            "category_context": "品类背景",
            "competitor_signal": "竞品信号",
            "risk_signal": "风险信号",
            "trend_signal": "趋势信号",
            "propagation_signal": "传播信号",
        }
        cleaned = str(finding_type or "").strip()
        return labels.get(cleaned, cleaned or "未分类")

    def _build_research_pillar(self, finding_type: str, candidates: List[Dict[str, Any]]) -> Dict[str, Any]:
        best = min(candidates, key=self._finding_digest_sort_key)
        return {
            "finding_type": finding_type,
            "finding_type_label": self._finding_type_label(finding_type),
            "finding_id": str(best.get("finding_id", "") or ""),
            "summary": str(best.get("summary", "") or ""),
            "evidence_preview": str(best.get("evidence_preview", "") or ""),
            "source_title": str(best.get("source_title", "") or ""),
            "source_label": str(best.get("source_label", "") or ""),
            "confidence": best.get("confidence", 0),
            "confidence_label": str(best.get("confidence_label", "") or ""),
            "gatekeeping_status": str(best.get("gatekeeping_status", "") or ""),
        }

    def _research_risk_findings(self, findings: List[Dict[str, Any]], limit: int = 3) -> List[Dict[str, Any]]:
        risk_candidates = [
            finding for finding in findings
            if str(finding.get("finding_type") or "").strip() == "risk_signal"
        ]
        if not risk_candidates:
            risk_candidates = list(findings)
        selected = sorted(risk_candidates, key=self._finding_digest_sort_key)[:limit]
        result: List[Dict[str, Any]] = []
        for finding in selected:
            result.append(
                {
                    "finding_id": str(finding.get("finding_id", "") or ""),
                    "finding_type": str(finding.get("finding_type", "") or ""),
                    "summary": str(finding.get("summary", "") or ""),
                    "source_id": str(finding.get("source_id", "") or ""),
                    "source_title": str(finding.get("source_title", "") or ""),
                    "evidence_preview": str(finding.get("evidence_preview", "") or ""),
                    "confidence": finding.get("confidence", 0),
                }
            )
        return result

    def _load_latest_replay_alignment(self) -> Dict[str, Any]:
        """Load the latest replay result for this simulation, if any."""
        replay_dir = os.path.join(Config.UPLOAD_FOLDER, "benchmarks", "replay_runs")
        if not os.path.exists(replay_dir):
            return {"status": "not_replayed", "replay_id": None, "benchmark_id": None}

        latest_replay: Optional[Dict[str, Any]] = None
        latest_at = ""
        for filename in os.listdir(replay_dir):
            if not filename.startswith("replay_") or not filename.endswith(".json"):
                continue
            path = os.path.join(replay_dir, filename)
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if data.get("simulation_id") != self.simulation_id:
                    continue
                replayed_at = data.get("replayed_at", "")
                if replayed_at > latest_at:
                    latest_at = replayed_at
                    latest_replay = data
            except Exception:
                continue

        if latest_replay is None:
            return {"status": "not_replayed", "replay_id": None, "benchmark_id": None}

        return {
            "status": latest_replay.get("alignment_status", "unknown"),
            "replay_id": latest_replay.get("replay_id"),
            "benchmark_id": latest_replay.get("benchmark_id"),
            "overall_score": latest_replay.get("overall_score", 0.0),
            "drift_signals": latest_replay.get("drift_signals", []),
            "replay_summary": latest_replay.get("replay_summary", ""),
        }

    def _build_consumer_outline(self, context: Dict[str, Any]) -> ReportOutline:
        summary = context["summary"]
        task_type = str(context.get("task_type", "")).strip().lower()
        research_findings_value = context.get("research_findings", [])
        research_findings_count = int(
            context.get("research_findings_count")
            or (len(research_findings_value) if isinstance(research_findings_value, list) else 0)
        )

        # Determine concept recommendation for summary
        post_pos = summary['post_propagation_acceptance']['positive']
        init_pos = summary['initial_acceptance']['positive']
        shift_rate = summary['attitude_shift_rate']
        neg_growth = summary['post_propagation_acceptance']['negative'] - summary['initial_acceptance']['negative']
        if post_pos > init_pos and shift_rate > 0.1:
            recommendation = "建议继续推进"
        elif neg_growth > 0.1:
            recommendation = "建议暂缓"
        else:
            recommendation = "建议优化后继续"

        outline_summary = (
            f"本报告基于 {research_findings_count} 条研究发现与消费者原声综合生成，"
            f"概念决策：{recommendation}。"
            f"初始正向接受度 {init_pos:.0%}，"
            f"传播后正向接受度 {post_pos:.0%}，"
            f"态度转向率 {shift_rate:.0%}。"
        )

        sections = [
            # Layer 1: Executive Summary
            ReportSection(title="总裁结论页", content=""),
            # Layer 2: Action Playbook
            ReportSection(title="卖点决策表", content=""),
            ReportSection(title="合规话术边界", content=""),
            ReportSection(title="渠道策略与执行建议", content=""),
            # Layer 3: Technical Appendix
            ReportSection(title="测试概览", content=""),
            ReportSection(title="研究发现综合", content=""),
            ReportSection(title="传播演化", content=""),
            ReportSection(title="风险与误读", content=""),
            ReportSection(title="代表性消费者原声", content=""),
        ]

        # Task-specific sections still appended to Layer 3
        if task_type == "price_test":
            sections.insert(7, ReportSection(title="价格敏感度与 WTP 分析", content=""))
            sections.insert(8, ReportSection(title="价格接受区间与弹性", content=""))
        elif task_type == "packaging_test":
            sections.insert(7, ReportSection(title="视觉认知与货架吸引力", content=""))
            sections.insert(8, ReportSection(title="包装识别与注意力路径", content=""))
        elif task_type == "ab_test":
            sections.insert(7, ReportSection(title="偏好对比与统计显著性", content=""))
            sections.insert(8, ReportSection(title="版本差异与选择理由", content=""))

        return ReportOutline(
            title="消费者传播测试与市场决策报告",
            summary=outline_summary,
            sections=sections,
        )

    # ── Layer 1 & 2 rendering methods ──────────────────────────────────

    def _render_executive_summary(self, context: Dict[str, Any]) -> str:
        """Render 总裁结论页 — Layer 1 executive summary."""
        summary = context["summary"]
        init_pos = summary['initial_acceptance']['positive']
        post_pos = summary['post_propagation_acceptance']['positive']
        shift_rate = summary['attitude_shift_rate']
        neg_growth = summary['post_propagation_acceptance']['negative'] - summary['initial_acceptance']['negative']

        # Concept recommendation
        if post_pos > init_pos and shift_rate > 0.1:
            recommendation = "建议继续推进"
        elif neg_growth > 0.1:
            recommendation = "建议暂缓"
        else:
            recommendation = "建议优化后继续"

        lines: List[str] = []
        lines.append(f"## 概念决策：{recommendation}")
        lines.append("")

        # Core findings — top 3 resonance points
        lines.append("## 核心发现")
        resonance = context.get('top_resonance_points', [])
        for point in resonance[:3]:
            lines.append(f"- {point}")
        if not resonance:
            lines.append("- 暂无显著共鸣点")
        lines.append("")

        # Biggest opportunity & biggest risk
        top_opportunity = resonance[0] if resonance else "暂无"
        risk_points = context.get('top_risk_points', [])
        top_risk = risk_points[0] if risk_points else "暂无"
        lines.append(f"## 最大机会\n{top_opportunity}")
        lines.append("")
        lines.append(f"## 最大风险\n{top_risk}")
        lines.append("")

        # Main selling point suggestion
        sp_report = context.get('selling_point_report')
        main_rec = None
        if isinstance(sp_report, dict):
            main_rec = sp_report.get('main_recommendation')
            if not main_rec:
                analyses = sp_report.get('analyses') or sp_report.get('recommendations') or []
                if analyses:
                    a = analyses[0]
                    main_rec = a.get('claim_text', a.get('claim', '')) if isinstance(a, dict) else getattr(a, 'claim_text', '')
        elif sp_report is not None:
            main_rec = getattr(sp_report, 'main_recommendation', None)
            if not main_rec:
                analyses = getattr(sp_report, 'analyses', None) or getattr(sp_report, 'recommendations', None) or []
                if analyses:
                    main_rec = getattr(analyses[0], 'claim_text', '')
        if main_rec:
            lines.append(f"## 主卖点建议\n{main_rec}")
        else:
            anchor = resonance[0] if resonance else "暂无"
            lines.append(f"## 主卖点建议\n围绕核心共鸣点「{anchor}」构建主传播叙事")
        lines.append("")

        # Next steps
        lines.append("## 下一步行动")
        lines.append(f"1. 根据概念决策（{recommendation}），明确下一阶段资源配置")
        if resonance:
            lines.append(f"2. 围绕「{resonance[0]}」打磨核心文案与传播素材")
        if risk_points:
            lines.append(f"3. 针对风险点「{risk_points[0]}」准备应对话术与证据")
        lines.append("4. 参阅执行页（Layer 2）获取卖点、合规、渠道的具体落地方案")
        return "\n".join(lines)

    def _render_selling_point_table(self, context: Dict[str, Any]) -> str:
        """Render 卖点决策表 — Layer 2 selling point decision table."""
        sp_report = context.get('selling_point_report')
        # Handle both dict (model_dump) and object forms
        analyses = None
        if isinstance(sp_report, dict):
            analyses = sp_report.get('analyses') or sp_report.get('recommendations')
        elif sp_report is not None:
            analyses = getattr(sp_report, 'analyses', None) or getattr(sp_report, 'recommendations', None)
        if analyses:
            lines: List[str] = []
            lines.append("## 卖点决策表")
            lines.append("")
            lines.append("| 排名 | 卖点 | 建议角色 | 共鸣度 | 风险度 | 最佳渠道 | 处理方式 |")
            lines.append("| --- | --- | --- | --- | --- | --- | --- |")
            for a in analyses:
                if isinstance(a, dict):
                    rank = a.get('priority_rank', a.get('rank', ''))
                    claim = a.get('claim_text', a.get('claim', ''))
                    role = a.get('role', '')
                    resonance = a.get('resonance_score', 0)
                    risk = a.get('risk_score', 0)
                    best_ch = a.get('best_channel', '')
                    handling = a.get('handling_suggestion', a.get('handling', ''))
                else:
                    rank = getattr(a, 'priority_rank', '')
                    claim = getattr(a, 'claim_text', '')
                    role = getattr(a, 'role', '')
                    resonance = getattr(a, 'resonance_score', 0)
                    risk = getattr(a, 'risk_score', 0)
                    best_ch = getattr(a, 'best_channel', '')
                    handling = getattr(a, 'handling_suggestion', '')
                try:
                    resonance_str = f"{float(resonance):.0%}"
                except (ValueError, TypeError):
                    resonance_str = str(resonance)
                try:
                    risk_str = f"{float(risk):.0%}"
                except (ValueError, TypeError):
                    risk_str = str(risk)
                lines.append(
                    f"| {rank} | {claim} | {role} | {resonance_str} | {risk_str} | {best_ch} | {handling} |"
                )
            return "\n".join(lines)

        # Fallback: simplified table from existing context data
        lines = []
        lines.append("## 卖点决策表")
        lines.append("")
        lines.append("| 卖点 | 建议角色 | 原因 | 风险 | 处理方式 |")
        lines.append("| --- | --- | --- | --- | --- |")
        resonance = context.get('top_resonance_points', [])
        risk_points = context.get('top_risk_points', [])
        for i, point in enumerate(resonance[:5]):
            role = "主打卖点" if i == 0 else "辅助卖点"
            reason = "消费者高共鸣" if i == 0 else "强化概念支撑"
            risk = risk_points[i] if i < len(risk_points) else "暂无已知风险"
            handling = "持续强化传播" if i == 0 else "配合主卖点使用"
            lines.append(f"| {point} | {role} | {reason} | {risk} | {handling} |")
        if not resonance:
            lines.append("| 暂无 | - | - | - | - |")
        return "\n".join(lines)

    def _render_compliance_table(self, context: Dict[str, Any]) -> str:
        """Render 合规话术边界 — Layer 2 compliance boundary table."""
        comp_report = context.get('compliance_report')
        # Handle both dict (model_dump) and object forms
        findings = None
        if isinstance(comp_report, dict):
            findings = comp_report.get('findings')
        elif comp_report is not None:
            findings = getattr(comp_report, 'findings', None)
        if findings:
            lines: List[str] = []
            lines.append("## 合规话术边界")
            lines.append("")
            lines.append("| 高风险表达 | 风险原因 | 建议替代表达 |")
            lines.append("| --- | --- | --- |")
            for finding in findings:
                if isinstance(finding, dict):
                    expr = finding.get('expression', '')
                    reason = finding.get('risk_reason', '')
                    alternative = finding.get('suggested_alternative', '')
                else:
                    expr = getattr(finding, 'expression', '')
                    reason = getattr(finding, 'risk_reason', '')
                    alternative = getattr(finding, 'suggested_alternative', '')
                lines.append(f"| {expr} | {reason} | {alternative} |")
            return "\n".join(lines)

        # Fallback: derive from misreads and risk points
        lines = []
        lines.append("## 合规话术边界")
        lines.append("")
        lines.append("| 高风险表达 | 风险原因 | 建议替代表达 |")
        lines.append("| --- | --- | --- |")
        misreads = context.get('top_misreads', [])
        for misread in misreads[:3]:
            lines.append(f"| {misread} | 消费者误读/歧义 | 建议使用更明确、具体化表述 |")
        risk_points = context.get('top_risk_points', [])
        for risk in risk_points[:3]:
            lines.append(f"| {risk} | 可能引发负面解读 | 建议补充证据支撑或弱化表述 |")
        if not misreads and not risk_points:
            lines.append("| 暂无 | - | - |")
        lines.append("")
        lines.append("> 注：以上为自动生成的初步筛查，正式发布前请法务/合规团队复核。")
        return "\n".join(lines)

    def _render_channel_strategy(self, context: Dict[str, Any]) -> str:
        """Render 渠道策略与执行建议 — Layer 2 channel strategy."""
        channel_metrics = context.get('channel_metrics', {})
        channel_fit = context.get('channel_fit_scores', {})
        resonance = context.get('top_resonance_points', [])
        risk_points = context.get('top_risk_points', [])
        main_hook = resonance[0] if resonance else "产品核心价值"
        main_risk = risk_points[0] if risk_points else "暂无已知风险"

        lines: List[str] = []
        lines.append("## 渠道策略与执行建议")
        lines.append("")

        # Per-channel recommendations
        channels = [
            ("小红书", "种草笔记 + 素人口碑", "图文笔记、合集测评、素人试用分享"),
            ("抖音", "短视频 + 信息流", "15-60秒短视频、达人合作、信息流投放"),
            ("直播间", "即时转化场景", "主播话术、互动引导、限时促销"),
            ("详情页", "深度说服场景", "长图文、对比数据、FAQ、用户证言"),
        ]
        for name, positioning, format_hint in channels:
            fit_score = channel_fit.get(name, channel_fit.get(name.lower(), ""))
            fit_label = f"（适配度: {fit_score}）" if fit_score else ""
            ch_metric = channel_metrics.get(name, channel_metrics.get(name.lower(), {}))
            lines.append(f"### {name} {fit_label}")
            lines.append(f"- 定位：{positioning}")
            lines.append(f"- 推荐形式：{format_hint}")
            lines.append(f"- 核心传播锚点：「{main_hook}」")
            if ch_metric and isinstance(ch_metric, dict):
                for k, v in ch_metric.items():
                    lines.append(f"- {k}: {v}")
            lines.append("")

        # 直播间FAQ预埋
        lines.append("## 直播间FAQ预埋")
        lines.append("")
        faq_items = [
            (f"这个产品的核心优势是什么？", f"核心优势在于「{main_hook}」，这是我们测试中消费者最认可的点。"),
            ("跟竞品相比有什么不同？", "我们的差异化在于经过消费者传播验证的独特卖点组合。"),
            ("适合什么样的人群？", f"目标人群画像详见报告，核心受众对「{main_hook}」有强需求。"),
            ("有没有什么需要注意的？", f"关于「{main_risk}」的疑问，我们准备了专业的解答话术。"),
            ("效果怎么样？有数据吗？", "消费者传播测试显示了明确的正向接受度，具体数据可在详情页查看。"),
        ]
        for i, (q, a) in enumerate(faq_items, 1):
            lines.append(f"**Q{i}: {q}**")
            lines.append(f"A: {a}")
            lines.append("")

        # 短视频脚本建议
        lines.append("## 短视频脚本建议")
        lines.append("")
        angles = [
            ("痛点切入", f"从消费者常见痛点出发，引出「{main_hook}」作为解决方案"),
            ("对比实验", f"通过与现有方案的对比，直观展示「{main_hook}」的优势"),
            ("用户证言", f"用真实消费者原声包装，围绕「{main_hook}」讲述使用体验"),
        ]
        for i, (title, desc) in enumerate(angles, 1):
            lines.append(f"**角度{i}: {title}**")
            lines.append(f"- {desc}")
            lines.append("")

        # 评论区回复模板
        lines.append("## 评论区回复模板")
        lines.append("")
        lines.append("**正面评论回复：**")
        lines.append(f"「感谢认可！「{main_hook}」确实是我们最引以为傲的特点，感谢您的支持！」")
        lines.append("")
        lines.append("**质疑/负面评论回复：**")
        lines.append(f"「感谢您的反馈。关于您提到的「{main_risk}」，我们非常重视，这里补充一些说明……」")
        lines.append("")
        lines.append("**咨询类评论回复：**")
        lines.append(f"「您好！关于产品详情，核心卖点是「{main_hook}」，详情页有完整的数据和说明，欢迎查看～」")
        return "\n".join(lines)

    # ── Layer 3 rendering (existing) ───────────────────────────────────

    def _render_consumer_section(self, section_title: str, context: Dict[str, Any]) -> str:
        # Layer 1 & 2 sections — delegate to dedicated renderers
        if section_title == "总裁结论页":
            return self._render_executive_summary(context)
        if section_title == "卖点决策表":
            return self._render_selling_point_table(context)
        if section_title == "合规话术边界":
            return self._render_compliance_table(context)
        if section_title == "渠道策略与执行建议":
            return self._render_channel_strategy(context)

        # Layer 3 sections — existing template-based rendering
        summary = context["summary"]
        task_type = str(context.get("task_type", "")).strip().lower()
        research_findings_value = context.get("research_findings", [])
        research_findings_count = int(
            context.get("research_findings_count")
            or (len(research_findings_value) if isinstance(research_findings_value, list) else 0)
        )

        if section_title == "测试概览":
            lines = [
                f"- 事件样本数：{context['events_count']}",
                f"- 研究发现总数：{research_findings_count}",
                f"- 证据原子数：{context.get('evidence_atom_count', 0)}",
                f"- 初始接受度：{self._format_acceptance(summary['initial_acceptance'])}",
                f"- 传播后接受度：{self._format_acceptance(summary['post_propagation_acceptance'])}",
                f"- 态度转向率：{summary['attitude_shift_rate']:.0%}",
            ]
            if task_type == "packaging_test" and context.get("top_packaging_hooks"):
                lines.append(f"- 包装吸引点：{self._format_points(context['top_packaging_hooks'])}")
            if task_type == "ab_test" and context.get("winning_variant"):
                lines.append(f"- 占优 variant：{context['winning_variant']}")
            if task_type == "price_test" and context.get("price_context"):
                lines.append(f"- 价格背景：{context['price_context']}")
            return "\n".join(lines)

        if section_title == "研究发现综合":
            type_counts = context.get("research_finding_type_counts") or {}
            pillars = context.get("research_insight_pillars") or []
            quote_groups = context.get("representative_voc_quotes") or {}
            lines = [
                f"- 研究发现总数：{research_findings_count}",
                f"- 主题分布：{self._format_finding_type_counts(type_counts)}",
                f"- 综合洞察：{context.get('research_insight_summary') or '暂无'}",
            ]
            if pillars:
                lines.append("- 关键研究主线：")
                for pillar in pillars[:4]:
                    lines.append(f"  - [{pillar.get('finding_type_label', pillar.get('finding_type', ''))}] {pillar.get('summary', '')}")
                    evidence_preview = str(pillar.get("evidence_preview", "") or "").strip()
                    if evidence_preview:
                        lines.append(f"    - 证据：{evidence_preview}")
            quote_bridge: List[str] = []
            if quote_groups.get("resonance"):
                quote_bridge.append(f'正向："{quote_groups["resonance"][0].get("quote", "")}"')
            if quote_groups.get("risk"):
                quote_bridge.append(f'风险："{quote_groups["risk"][0].get("quote", "")}"')
            if quote_groups.get("misread"):
                quote_bridge.append(f'误读："{quote_groups["misread"][0].get("quote", "")}"')
            if quote_bridge:
                lines.append("- 原声印证：")
                for item in quote_bridge:
                    lines.append(f"  - {item}")
            return "\n".join(lines)

        if section_title == "初始反应":
            lines = [
                f"- 高共鸣点：{self._format_points(context['top_resonance_points'])}",
                f"- 代表性正向原声：\n{self._format_quotes(context['representative_voc_quotes']['resonance'])}",
            ]
            if task_type == "packaging_test" and context.get("top_packaging_hooks"):
                lines.append(f"- 包装第一眼吸引：{self._format_points(context['top_packaging_hooks'])}")
            if task_type == "ab_test" and context.get("top_variant_deltas"):
                lines.append("- Variant 差异感知：")
                for delta in context["top_variant_deltas"][:3]:
                    d_type = delta.get("type", "")
                    d_quote = delta.get("quote", "")
                    lines.append(f"  - [{d_type}] {d_quote}")
            if task_type == "price_test" and context.get("acceptable_price_points"):
                lines.append(f"- 可接受价格：{self._format_points(context['acceptable_price_points'])}")
            return "\n".join(lines)

        if section_title == "传播演化":
            lines = [
                f"- 传播后接受度：{self._format_acceptance(summary['post_propagation_acceptance'])}",
                f"- 态度转向率：{summary['attitude_shift_rate']:.0%}",
                f"- 扩散中的高频讨论点：{self._format_points(context['top_resonance_points'])}",
            ]
            if task_type == "packaging_test" and context.get("top_trust_objections"):
                lines.append(f"- 信任疑虑：{self._format_points(context['top_trust_objections'])}")
            if task_type == "ab_test" and context.get("top_persona_divergences"):
                lines.append(f"- 人群差异：{self._format_points(context['top_persona_divergences'])}")
            if task_type == "price_test" and context.get("resisted_price_points"):
                lines.append(f"- 抗拒价格：{self._format_points(context['resisted_price_points'])}")
            return "\n".join(lines)

        if section_title == "价格敏感度与 WTP 分析":
            return "\n".join([
                f"- 可接受价格：{self._format_points(context.get('acceptable_price_points', []))}",
                f"- 抗拒价格：{self._format_points(context.get('resisted_price_points', []))}",
                f"- 价格异议：{self._format_points(context.get('top_price_objections', []))}",
            ])

        if section_title == "价格接受区间与弹性":
            return "\n".join([
                f"- 价格背景：{context.get('price_context', '') or '暂无'}",
                "- WTP 分布应结合真实价格带和传播后接受度共同解释。",
            ])

        if section_title == "视觉认知与货架吸引力":
            return "\n".join([
                f"- 包装吸引点：{self._format_points(context.get('top_packaging_hooks', []))}",
                f"- 混淆触发点：{self._format_points(context.get('top_confusion_triggers', []))}",
            ])

        if section_title == "包装识别与注意力路径":
            return "\n".join([
                f"- 信任疑虑：{self._format_points(context.get('top_trust_objections', []))}",
                "- 货架吸引力应结合第一眼理解、证据位置和包装差异化判断。",
            ])

        if section_title == "偏好对比与统计显著性":
            lines = [f"- 占优 variant：{context.get('winning_variant', '') or '暂无'}"]
            for delta in context.get("top_variant_deltas", [])[:3]:
                lines.append(f"  - {delta.get('quote', delta)}")
            lines.append("- 统计显著性需结合样本量、重复种子和置信度输出。")
            return "\n".join(lines)

        if section_title == "版本差异与选择理由":
            return "\n".join([
                f"- 人群差异：{self._format_points(context.get('top_persona_divergences', []))}",
                "- 版本选择理由应优先引用差异化 VOC 与事件链。",
            ])

        if section_title == "风险与误读":
            lines = [
                f"- 高风险点：{self._format_points(context['top_risk_points'])}",
                f"- 高误读点：{self._format_points(context['top_misreads'])}",
                f"- 风险原声：\n{self._format_quotes(context['representative_voc_quotes']['risk'])}",
                f"- 误读/疑问原声：\n{self._format_quotes(context['representative_voc_quotes']['misread'])}",
            ]
            if task_type == "packaging_test" and context.get("top_confusion_triggers"):
                lines.append(f"- 包装混淆点：{self._format_points(context['top_confusion_triggers'])}")
            if task_type == "price_test" and context.get("top_price_objections"):
                lines.append(f"- 价格异议：{self._format_points(context['top_price_objections'])}")
            if context.get("top_risk_findings"):
                lines.append("- 因果触发发现：")
                for finding in context["top_risk_findings"]:
                    lines.append(f"  - [{finding['finding_type']}] {finding['summary']}")
            if context.get("causal_chains"):
                lines.append("- 事件因果链：")
                for chain in context["causal_chains"][:3]:
                    lines.append(f"  - 发现 {chain['finding_summary']} 触发了事件 {', '.join(chain['event_ids'])}")
            return "\n".join(lines)

        if section_title == "代表性消费者原声":
            lines = [
                f"**正向原声**\n{self._format_quotes(context['representative_voc_quotes']['resonance'])}",
                f"**风险原声**\n{self._format_quotes(context['representative_voc_quotes']['risk'])}",
                f"**误读/疑问原声**\n{self._format_quotes(context['representative_voc_quotes']['misread'])}",
            ]
            if task_type == "packaging_test" and context.get("top_packaging_hooks"):
                lines.append(f"**包装相关原声**\n{self._format_task_quotes(context['top_packaging_hooks'])}")
            if task_type == "price_test" and context.get("top_price_objections"):
                lines.append(f"**价格相关原声**\n{self._format_task_quotes(context['top_price_objections'])}")
            return "\n\n".join(lines)

        if section_title == "行动建议":
            resonance_point = self._first_point(context["top_resonance_points"], "现有核心卖点")
            risk_point = self._first_point(context["top_risk_points"], "潜在争议点")
            misread_point = self._first_point(context["top_misreads"], "传播中的模糊表述")
            lines = [
                f"- 放大高共鸣表达：围绕“{resonance_point}”继续强化概念与文案。",
                f"- 提前澄清风险：针对“{risk_point}”准备更直接的解释与证据。",
                f"- 修正文案误读：对“{misread_point}”补充更具体、更少歧义的表述。",
            ]
            pillars = context.get("research_insight_pillars") or []
            if pillars:
                anchor = self._first_point([str(p.get("summary", "")).strip() for p in pillars if str(p.get("summary", "")).strip()], "研究发现")
                lines.append(f"- 综合传播锚点：优先围绕“{anchor}”统一原声、证据和文案。")
            if task_type == "packaging_test":
                trust = self._first_point(context.get("top_trust_objections", []), "信任疑虑")
                confusion = self._first_point(context.get("top_confusion_triggers", []), "混淆点")
                lines.append(f"- 优化包装信任感：针对“{trust}”增加背书或认证信息。")
                lines.append(f"- 消除包装混淆：对“{confusion}”简化设计或增加说明。")
            if task_type == "ab_test":
                variant = context.get("winning_variant", "") or "占优 variant"
                lines.append(f"- 推广优胜 variant：重点投放“{variant}”并分析其优势要素。")
            if task_type == "price_test":
                acceptable = self._first_point(context.get("acceptable_price_points", []), "可接受价格带")
                resisted = self._first_point(context.get("resisted_price_points", []), "抗拒价格点")
                lines.append(f"- 锚定合理价格：以“{acceptable}”为传播锚点强化价值感知。")
                lines.append(f"- 规避价格雷区：针对“{resisted}”提前准备价值解释或促销话术。")
            if context.get("top_risk_findings"):
                lines.append("- 针对风险发现的优先行动：")
                for finding in context["top_risk_findings"][:3]:
                    lines.append(f"  - 处理 [{finding['finding_type']}] {finding['summary']}")
            if context.get("event_counts"):
                lines.append(f"- 事件类型分布：{context['event_counts']}")
            return "\n".join(lines)

        return ""

    def _format_task_quotes(self, items: List[str]) -> str:
        if not items:
            return "- 暂无"
        lines = []
        for item in items:
            lines.append(f'- "{item}"')
        return "\n".join(lines)

    def _format_acceptance(self, acceptance: Dict[str, float]) -> str:
        return (
            f"正向 {acceptance.get('positive', 0.0):.0%} / "
            f"中立 {acceptance.get('neutral', 0.0):.0%} / "
            f"负向 {acceptance.get('negative', 0.0):.0%}"
        )

    def _format_points(self, points: List[str]) -> str:
        if not points:
            return "暂无显著点位"
        return "；".join(points)

    def _format_finding_type_counts(self, counts: Any) -> str:
        if not isinstance(counts, dict) or not counts:
            return "暂无"

        preferred_order = [
            "category_context",
            "competitor_signal",
            "risk_signal",
            "trend_signal",
            "propagation_signal",
        ]
        lines: List[str] = []
        seen: set[str] = set()
        for finding_type in preferred_order:
            if finding_type in counts:
                seen.add(finding_type)
                lines.append(
                    f"{self._finding_type_label(finding_type)} {int(counts.get(finding_type, 0) or 0)}"
                )
        for finding_type, value in counts.items():
            if finding_type in seen:
                continue
            lines.append(f"{self._finding_type_label(str(finding_type))} {int(value or 0)}")
        return "，".join(lines) if lines else "暂无"

    def _first_point(self, points: List[str], fallback: str) -> str:
        return points[0] if points else fallback

    def _extract_claims_from_context(self, context: Dict[str, Any]) -> List[str]:
        """Extract selling-point claims from consumer config or business brief."""
        claims: List[str] = []
        # Try resonance points as primary claims
        resonance = context.get("top_resonance_points", [])
        if resonance:
            claims.extend(resonance[:5])
        # Try consumer_brief claims
        brief_summary = context.get("consumer_brief", {})
        if isinstance(brief_summary, dict):
            brief_claims = brief_summary.get("claims") or brief_summary.get("selling_points") or []
            for c in brief_claims:
                if isinstance(c, str) and c not in claims:
                    claims.append(c)
        # Try research insight pillars
        for pillar in context.get("research_insight_pillars", []):
            summary_text = str(pillar.get("summary", "")).strip()
            if summary_text and summary_text not in claims:
                claims.append(summary_text)
        return claims

    def _format_quotes(self, quotes: List[Dict[str, Any]]) -> str:
        if not quotes:
            return "- 暂无代表性原声"

        def is_template_generated(item: Dict[str, Any]) -> bool:
            metadata = item.get("quote_metadata") or {}
            if isinstance(metadata, dict) and "template_generated" in metadata:
                return bool(metadata.get("template_generated"))
            return True

        sorted_quotes = sorted(quotes, key=is_template_generated)
        llm_count = sum(1 for item in sorted_quotes if not is_template_generated(item))
        template_count = len(sorted_quotes) - llm_count
        lines = [f"- Source: LLM\u751f\u6210 {llm_count} / \u6a21\u62df\u751f\u6210 {template_count}"]
        for item in sorted_quotes:
            quote = str(item.get("quote", "")).strip()
            if not quote:
                continue
            engagement = item.get("engagement", 0)
            source_label = " [\u6a21\u62df\u751f\u6210\uff0c\u975eLLM\u63a8\u7406]" if is_template_generated(item) else ""
            lines.append(f'- "{quote}"{source_label} (engagement {engagement})')
        return "\n".join(lines) if len(lines) > 1 else "- 暂无代表性原声"
    def chat(
        self, 
        message: str,
        chat_history: List[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        与Report Agent对话
        
        在对话中Agent可以自主调用检索工具来回答问题
        
        Args:
            message: 用户消息
            chat_history: 对话历史
            
        Returns:
            {
                "response": "Agent回复",
                "tool_calls": [调用的工具列表],
                "sources": [信息来源]
            }
        """
        logger.info(t('report.agentChat', message=message[:50]))
        
        chat_history = chat_history or []
        
        # 获取已生成的报告内容
        report_content = ""
        try:
            report = ReportManager.get_report_by_simulation(self.simulation_id)
            if report and report.markdown_content:
                # 限制报告长度，避免上下文过长
                report_content = report.markdown_content[:15000]
                if len(report.markdown_content) > 15000:
                    report_content += "\n\n... [报告内容已截断] ..."
        except Exception as e:
            logger.warning(t('report.fetchReportFailed', error=e))
        
        if self.project_type == "consumer_test":
            system_prompt = CONSUMER_CHAT_SYSTEM_PROMPT_TEMPLATE.format(
                simulation_requirement=self.simulation_requirement,
                report_content=report_content if report_content else "（暂无报告）",
                tools_description=self._get_tools_description(),
            )
        else:
            system_prompt = CHAT_SYSTEM_PROMPT_TEMPLATE.format(
                simulation_requirement=self.simulation_requirement,
                report_content=report_content if report_content else "（暂无报告）",
                tools_description=self._get_tools_description(),
            )
        system_prompt = f"{system_prompt}\n\n{get_language_instruction()}"

        # 构建消息
        messages = [{"role": "system", "content": system_prompt}]
        
        # 添加历史对话
        for h in chat_history[-10:]:  # 限制历史长度
            messages.append(h)
        
        # 添加用户消息
        messages.append({
            "role": "user", 
            "content": message
        })
        
        # ReACT循环（简化版）
        tool_calls_made = []
        max_iterations = 2  # 减少迭代轮数
        
        for iteration in range(max_iterations):
            response = self.llm.chat(
                messages=messages,
                temperature=0.5
            )
            
            # 解析工具调用
            tool_calls = self._parse_tool_calls(response)
            
            if not tool_calls:
                # 没有工具调用，直接返回响应
                clean_response = re.sub(r'<tool_call>.*?</tool_call>', '', response, flags=re.DOTALL)
                clean_response = re.sub(r'\[TOOL_CALL\].*?\)', '', clean_response)
                
                return {
                    "response": clean_response.strip(),
                    "tool_calls": tool_calls_made,
                    "sources": [tc.get("parameters", {}).get("query", "") for tc in tool_calls_made]
                }
            
            # 执行工具调用（限制数量）
            tool_results = []
            for call in tool_calls[:1]:  # 每轮最多执行1次工具调用
                if len(tool_calls_made) >= self.MAX_TOOL_CALLS_PER_CHAT:
                    break
                result = self._execute_tool(call["name"], call.get("parameters", {}))
                tool_results.append({
                    "tool": call["name"],
                    "result": result[:1500]  # 限制结果长度
                })
                tool_calls_made.append(call)
            
            # 将结果添加到消息
            messages.append({"role": "assistant", "content": response})
            observation = "\n".join([f"[{r['tool']}结果]\n{r['result']}" for r in tool_results])
            messages.append({
                "role": "user",
                "content": observation + CHAT_OBSERVATION_SUFFIX
            })
        
        # 达到最大迭代，获取最终响应
        final_response = self.llm.chat(
            messages=messages,
            temperature=0.5
        )
        
        # 清理响应
        clean_response = re.sub(r'<tool_call>.*?</tool_call>', '', final_response, flags=re.DOTALL)
        clean_response = re.sub(r'\[TOOL_CALL\].*?\)', '', clean_response)
        
        return {
            "response": clean_response.strip(),
            "tool_calls": tool_calls_made,
            "sources": [tc.get("parameters", {}).get("query", "") for tc in tool_calls_made]
        }
