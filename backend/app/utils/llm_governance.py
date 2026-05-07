"""LLM 输出治理工具"""

import re
from typing import Optional

# 反数学规则：LLM 不擅长精确数值计算
ANTI_MATH_PATTERNS = [
    r'精确计算.*?结果为',
    r'经计算可得',
    r'通过公式.*?得出',
    r'数学推导如下',
]


def validate_llm_output(text: Optional[str], context: str = "") -> dict:
    """校验LLM输出质量"""
    issues = []

    # 1. 空输出检查
    if not text or not text.strip():
        issues.append("LLM返回空内容")

    # 2. 过短输出检查（可能是截断）
    if text and len(text.strip()) < 10:
        issues.append(f"LLM输出过短({len(text.strip())}字符)")

    # 3. 反数学规则检查
    if text:
        for pattern in ANTI_MATH_PATTERNS:
            if re.search(pattern, text):
                issues.append(f"检测到LLM数学推断（不可靠）: {pattern}")

    # 4. 重复内容检查
    if text and len(text) > 100:
        sentences = text.split('。')
        if len(sentences) > 3:
            unique = set(s.strip() for s in sentences if s.strip())
            if len(unique) < len(sentences) * 0.5:
                issues.append("检测到大量重复内容")

    return {
        "valid": len(issues) == 0,
        "issues": issues,
        "context": context,
        "output_length": len(text) if text else 0
    }


def get_fallback_response(task_type: str) -> str:
    """获取降级响应（LLM不可用时）"""
    fallbacks = {
        "opinion": "该消费者未形成明确观点。",
        "decision": "该消费者选择维持现状。",
        "expression": "（未生成表达内容）",
        "report": "报告生成失败，请稍后重试。",
    }
    return fallbacks.get(task_type, "服务暂时不可用，请稍后重试。")
