"""Expression layer — generates opinions, social posts, and formatted responses."""

from __future__ import annotations

import logging
from typing import Any, Dict, Mapping

from ....utils.llm_governance import get_fallback_response, validate_llm_output
from ..society.population_models import ConsumerSocietyAgent

logger = logging.getLogger(__name__)


class ExpressionEngine:
    """Expression layer of the three-layer cognition architecture.

    Translates decisions into human-readable opinions, social-media posts,
    or structured responses.  Can operate in template mode (no LLM) or
    delegate to an LLM client for richer output.
    """

    def __init__(self, llm_client: Any | None = None):
        self.llm_client = llm_client

    def generate_opinion(
        self,
        agent: ConsumerSocietyAgent,
        decision: Mapping[str, Any],
        context: Mapping[str, Any] | None = None,
    ) -> str:
        """Generate a textual opinion based on the decision."""
        context = context or {}
        choice = str(decision.get("choice", "wait"))
        reasoning = str(decision.get("reasoning", ""))

        if self.llm_client is not None:
            try:
                return self._llm_generate_opinion(agent, decision, context)
            except Exception as exc:
                logger.warning("LLM opinion generation failed, using template: %s", exc)

        return self._template_opinion(agent, choice, reasoning)

    def generate_misread_variant(
        self,
        perception_state: Mapping[str, Any],
    ) -> str | None:
        """Generate a misread variant if the perception has confusion points."""
        confusion_points = perception_state.get("confusion_points", [])
        if confusion_points:
            return f"消费者可能误解为: {confusion_points[0]}"
        return None

    def generate_social_post(
        self,
        agent: ConsumerSocietyAgent,
        decision: Mapping[str, Any],
        context: Mapping[str, Any] | None = None,
    ) -> str:
        """Generate social-media content based on the decision."""
        context = context or {}
        choice = str(decision.get("choice", "wait"))

        if self.llm_client is not None:
            try:
                return self._llm_generate_social_post(agent, decision, context)
            except Exception as exc:
                logger.warning("LLM social post generation failed, using template: %s", exc)

        return self._template_social_post(agent, choice)

    def format_response(
        self,
        agent: ConsumerSocietyAgent,
        raw_expression: str,
    ) -> str:
        """Format and validate raw expression output."""
        if not raw_expression or not raw_expression.strip():
            return get_fallback_response("expression")

        if self.llm_client is not None:
            validation = validate_llm_output(raw_expression, context="expression.format")
            if not validation["valid"]:
                logger.warning("Expression validation failed: %s", validation["issues"])
                return get_fallback_response("expression")

        return raw_expression.strip()

    # ------------------------------------------------------------------
    # LLM-backed generation
    # ------------------------------------------------------------------

    def _llm_generate_opinion(
        self,
        agent: ConsumerSocietyAgent,
        decision: Mapping[str, Any],
        context: Mapping[str, Any],
    ) -> str:
        prompt = (
            f"你是消费者 {agent.agent_id}，属于 {agent.segment} 细分市场，角色为 {agent.role.value}。\n"
            f"你的特征：怀疑度={agent.skepticism}，价格敏感度={agent.price_sensitivity}，"
            f"证据敏感度={agent.evidence_sensitivity}。\n"
            f"你的决策是：{decision.get('choice', 'wait')}。\n"
            f"决策理由：{decision.get('reasoning', '')}。\n"
            f"请用 1-2 句话表达你作为消费者的观点。"
        )
        result = self.llm_client.chat_json(
            messages=[
                {"role": "system", "content": "你是消费者Agent的表达层。返回JSON: {\"opinion\": \"...\"}"},
                {"role": "user", "content": prompt},
            ],
            temperature=0.4,
            max_tokens=200,
        )
        opinion = str(result.get("opinion", ""))
        validation = validate_llm_output(opinion, context="expression.opinion")
        if not validation["valid"]:
            return get_fallback_response("opinion")
        return opinion

    def _llm_generate_social_post(
        self,
        agent: ConsumerSocietyAgent,
        decision: Mapping[str, Any],
        context: Mapping[str, Any],
    ) -> str:
        prompt = (
            f"你是消费者 {agent.agent_id} ({agent.segment})。\n"
            f"你决定：{decision.get('choice', 'wait')}。\n"
            f"请写一条简短的社交媒体帖子（不超过50字），表达你的消费体验或观点。"
        )
        result = self.llm_client.chat_json(
            messages=[
                {"role": "system", "content": "你是消费者Agent的社交媒体表达层。返回JSON: {\"post\": \"...\"}"},
                {"role": "user", "content": prompt},
            ],
            temperature=0.5,
            max_tokens=100,
        )
        post = str(result.get("post", ""))
        validation = validate_llm_output(post, context="expression.social_post")
        if not validation["valid"]:
            return get_fallback_response("expression")
        return post

    # ------------------------------------------------------------------
    # Template fallback
    # ------------------------------------------------------------------

    @staticmethod
    def _template_opinion(agent: ConsumerSocietyAgent, choice: str, reasoning: str) -> str:
        templates = {
            "accept": f"作为{agent.segment}消费者，我认为这个产品/概念值得信赖。",
            "reject": f"作为{agent.segment}消费者，我对这个产品/概念持保留态度。",
            "wait": f"作为{agent.segment}消费者，我需要更多信息才能做出判断。",
            "share": f"作为{agent.segment}消费者，我会把这个信息分享给身边的朋友。",
            "seek_evidence": f"作为{agent.segment}消费者，我希望看到更多证据。",
        }
        return templates.get(choice, f"作为{agent.segment}消费者，我暂时没有明确看法。")

    @staticmethod
    def _template_social_post(agent: ConsumerSocietyAgent, choice: str) -> str:
        templates = {
            "accept": f"体验不错，推荐给大家！#{agent.segment}",
            "reject": f"不太适合我，大家慎选。#{agent.segment}",
            "wait": f"还在观望中，等更多评价。#{agent.segment}",
            "share": f"发现一个有趣的产品，分享给大家！#{agent.segment}",
            "seek_evidence": f"有谁了解这个产品？求真实评价。#{agent.segment}",
        }
        return templates.get(choice, f"聊聊消费那些事。#{agent.segment}")


class NLGExpressionAdapter:
    """Generate VOC text with LLM-first behavior and platform-aware fallback."""

    PLATFORM_STYLES = {
        "xiaohongshu": "真实、轻量、带一点种草语气",
        "zhihu": "理性、解释充分、少口号",
        "weibo": "短句、直接、传播感强",
    }

    def __init__(self, llm_client: Any | None = None):
        self.llm_client = llm_client

    def generate_voc(
        self,
        *,
        agent_profile: Mapping[str, Any],
        claim: str,
        platform: str = "xiaohongshu",
        context: Mapping[str, Any] | None = None,
    ) -> Dict[str, Any]:
        platform_key = str(platform or "xiaohongshu").lower()
        if self.llm_client is not None:
            try:
                payload = self.llm_client.chat_json(
                    messages=[
                        {
                            "role": "system",
                            "content": "Return JSON only: {\"voc\": \"consumer quote\"}.",
                        },
                        {
                            "role": "user",
                            "content": self._build_prompt(agent_profile, claim, platform_key, context or {}),
                        },
                    ],
                    temperature=0.45,
                    max_tokens=160,
                )
                text = str(payload.get("voc") or payload.get("text") or "").strip()
                if text:
                    return {
                        "text": text,
                        "generation_source": "llm",
                        "platform": platform_key,
                    }
            except Exception as exc:
                logger.warning("NLG VOC generation failed, using template: %s", exc)

        return {
            "text": self._template_voc(agent_profile, claim, platform_key),
            "generation_source": "template_fallback",
            "platform": platform_key,
        }

    def _build_prompt(
        self,
        agent_profile: Mapping[str, Any],
        claim: str,
        platform: str,
        context: Mapping[str, Any],
    ) -> str:
        style = self.PLATFORM_STYLES.get(platform, "自然、具体、像真实消费者")
        return (
            f"消费者画像: {dict(agent_profile)}\n"
            f"卖点: {claim}\n"
            f"平台风格: {style}\n"
            f"上下文: {dict(context)}\n"
            "生成一句真实消费者VOC，不要写解释。"
        )

    @staticmethod
    def _template_voc(agent_profile: Mapping[str, Any], claim: str, platform: str) -> str:
        segment = str(agent_profile.get("segment") or agent_profile.get("name") or "消费者")
        if platform == "zhihu":
            return f"作为{segment}，我会先看{claim}有没有真实证据，再决定是否尝试。"
        if platform == "weibo":
            return f"{claim}听着有点吸引人，但我还想看真实反馈。"
        return f"{claim}如果体验和描述一致，我会愿意先小范围试试。"


__all__ = ["ExpressionEngine", "NLGExpressionAdapter"]
