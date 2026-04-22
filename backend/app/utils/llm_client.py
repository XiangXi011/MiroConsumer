"""
LLM客户端封装
统一使用OpenAI格式调用
"""

import json
import re
from typing import Optional, Dict, Any, List
from openai import OpenAI

from ..config import Config


class LLMClient:
    """LLM客户端"""
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None
    ):
        self.api_key = api_key or Config.LLM_API_KEY
        self.base_url = base_url or Config.LLM_BASE_URL
        self.model = model or Config.LLM_MODEL_NAME
        
        if not self.api_key:
            raise ValueError("LLM_API_KEY 未配置")
        
        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url
        )
    
    def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 4096,
        response_format: Optional[Dict] = None
    ) -> str:
        """
        发送聊天请求
        
        Args:
            messages: 消息列表
            temperature: 温度参数
            max_tokens: 最大token数
            response_format: 响应格式（如JSON模式）
            
        Returns:
            模型响应文本
        """
        kwargs = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        
        if response_format:
            kwargs["response_format"] = response_format
        
        response = self.client.chat.completions.create(**kwargs)
        content = response.choices[0].message.content
        # 部分模型（如MiniMax M2.5）会在content中包含<think>思考内容，需要移除
        content = re.sub(r'<think>[\s\S]*?</think>', '', content).strip()
        return content
    
    def chat_with_finish_reason(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 4096,
        response_format: Optional[Dict] = None
    ) -> tuple[str, str]:
        """
        发送聊天请求并返回内容及其finish_reason

        Args:
            messages: 消息列表
            temperature: 温度参数
            max_tokens: 最大token数
            response_format: 响应格式（如JSON模式）

        Returns:
            (模型响应文本, finish_reason)
        """
        kwargs = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        if response_format:
            kwargs["response_format"] = response_format

        response = self.client.chat.completions.create(**kwargs)
        content = response.choices[0].message.content
        # 部分模型（如MiniMax M2.5）会在content中包含<think>思考内容，需要移除
        content = re.sub(r'<think>[\s\S]*?</think>', '', content).strip()
        finish_reason = response.choices[0].finish_reason
        return content, finish_reason

    @staticmethod
    def clean_llm_text(text: str) -> str:
        """移除LLM输出中的markdown代码块和<think>标签。"""
        text = re.sub(r'<think>[\s\S]*?</think>', '', text)
        text = text.strip()
        text = re.sub(r'^```(?:json)?\s*\n?', '', text, flags=re.IGNORECASE)
        text = re.sub(r'\n?```\s*$', '', text)
        return text.strip()

    @staticmethod
    def extract_json(text: str) -> Dict[str, Any]:
        """
        从原始LLM文本中提取JSON对象，自动应用清理。

        Args:
            text: 原始LLM响应文本

        Returns:
            解析后的JSON字典

        Raises:
            ValueError: 如果无法解析为JSON对象
        """
        cleaned = LLMClient.clean_llm_text(text)
        try:
            result = json.loads(cleaned)
            if not isinstance(result, dict):
                raise ValueError(f"期望JSON对象，实际得到 {type(result).__name__}")
            return result
        except (json.JSONDecodeError, ValueError):
            # 尝试提取文本中第一个JSON对象
            match = re.search(r'\{[\s\S]*\}', cleaned)
            if match:
                try:
                    result = json.loads(match.group())
                    if isinstance(result, dict):
                        return result
                except (json.JSONDecodeError, ValueError):
                    pass
            raise ValueError(f"LLM返回的JSON格式无效: {cleaned[:200]}...")

    def chat_json(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.3,
        max_tokens: int = 4096,
        fallback_on_failure: bool = True,
    ) -> Dict[str, Any]:
        """
        发送聊天请求并返回JSON

        主路径使用 response_format={"type": "json_object"}。
        若解析失败且 fallback_on_failure=True，则回退到无response_format
        的路径，并在system prompt中追加JSON格式约束后重试。

        Args:
            messages: 消息列表
            temperature: 温度参数
            max_tokens: 最大token数
            fallback_on_failure: 主路径失败时是否启用fallback路径

        Returns:
            解析后的JSON对象
        """
        data, _ = self.chat_json_with_meta(
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            fallback_on_failure=fallback_on_failure,
        )
        return data

    def chat_json_with_meta(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.3,
        max_tokens: int = 4096,
        fallback_on_failure: bool = True,
    ) -> tuple[Dict[str, Any], Dict[str, Any]]:
        """
        发送聊天请求并返回JSON及解析诊断信息

        Args:
            messages: 消息列表
            temperature: 温度参数
            max_tokens: 最大token数
            fallback_on_failure: 主路径失败时是否启用fallback路径

        Returns:
            (解析后的JSON对象, 诊断信息字典)

        诊断信息字典包含以下机器可读字段:
            - primary_attempted: bool  是否尝试了主路径
            - primary_succeeded: bool 主路径是否成功
            - fallback_attempted: bool 是否尝试了fallback路径
            - fallback_succeeded: bool fallback路径是否成功
            - parse_path: "primary" | "fallback" | None  最终成功路径
            - cleanups_applied: list[str] 应用的清理操作列表
            - raw_preview: str 原始响应前500字符
        """
        diagnostics: Dict[str, Any] = {
            "primary_attempted": False,
            "primary_succeeded": False,
            "fallback_attempted": False,
            "fallback_succeeded": False,
            "parse_path": None,
            "cleanups_applied": [],
            "raw_preview": "",
        }

        # 主路径: 使用 structured json_object
        diagnostics["primary_attempted"] = True
        try:
            content = self.chat(
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                response_format={"type": "json_object"},
            )
            diagnostics["raw_preview"] = content[:500]
            data = self.extract_json(content)
            diagnostics["primary_succeeded"] = True
            diagnostics["parse_path"] = "primary"
            return data, diagnostics
        except Exception:
            diagnostics["primary_succeeded"] = False
            if not fallback_on_failure:
                raise

        # Fallback路径: 不使用response_format，追加JSON格式约束
        diagnostics["fallback_attempted"] = True

        json_instruction = (
            "\n\nIMPORTANT: You must respond with valid JSON only, "
            "no markdown formatting, no extra text."
        )
        fallback_messages: List[Dict[str, str]] = []
        system_found = False
        for m in messages:
            m_copy = dict(m)
            if m_copy.get("role") == "system" and not system_found:
                m_copy["content"] = m_copy.get("content", "") + json_instruction
                system_found = True
            fallback_messages.append(m_copy)
        if not system_found:
            fallback_messages.insert(0, {
                "role": "system",
                "content": (
                    "You must respond with valid JSON only, "
                    "no markdown formatting, no extra text."
                ),
            })

        try:
            content = self.chat(
                messages=fallback_messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            diagnostics["raw_preview"] = content[:500]
            data = self.extract_json(content)
            diagnostics["fallback_succeeded"] = True
            diagnostics["parse_path"] = "fallback"
            return data, diagnostics
        except Exception:
            diagnostics["fallback_succeeded"] = False
            raise

