"""OpenAI-compatible LLM client wrapper."""

from __future__ import annotations

import datetime
import hashlib
import json
import logging
import os
import re
import time
from typing import Any, Dict, List, Optional

from openai import OpenAI

from ..config import Config
from ..security.prompt_guard import get_prompt_guard
from .llm_governance import validate_llm_output
from .llm_governor import governor
from .retry import retry_with_backoff

logger = logging.getLogger(__name__)

RedisCache = None

LLM_LOG_DIR = os.path.join(os.path.dirname(__file__), "../../logs/llm")


def _usage_token_counts(usage: Any) -> Optional[tuple[int, int]]:
    prompt_tokens = getattr(usage, "prompt_tokens", None)
    completion_tokens = getattr(usage, "completion_tokens", None)
    if isinstance(prompt_tokens, int) and isinstance(completion_tokens, int):
        return prompt_tokens, completion_tokens
    return None


class LLMClient:
    """Small OpenAI-compatible chat client with governance and JSON helpers."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        request_timeout: Optional[float] = None,
    ):
        self.api_key = api_key or Config.LLM_API_KEY
        self.base_url = base_url or Config.LLM_BASE_URL
        self.model = model or Config.LLM_MODEL_NAME
        self.request_timeout = request_timeout

        if not self.api_key:
            raise ValueError("LLM_API_KEY is not configured")

        self.client = OpenAI(api_key=self.api_key, base_url=self.base_url)
        self._response_cache = None
        self._response_cache_url = None

    def _get_response_cache(self):
        if not getattr(Config, "LLM_CACHE_ENABLED", True):
            return None
        redis_url = Config.REDIS_URL
        if not redis_url:
            return None
        if not hasattr(self, "_response_cache") or self._response_cache is None or self._response_cache_url != redis_url:
            global RedisCache
            if RedisCache is None:
                from ..services.application.redis_cache import RedisCache as _RedisCache
                RedisCache = _RedisCache
            self._response_cache = RedisCache(redis_url=redis_url)
            self._response_cache_url = redis_url
        return self._response_cache

    @staticmethod
    def _chat_cache_key(
        prefix: str,
        model: str,
        messages: List[Dict[str, str]],
        temperature: float,
        max_tokens: int,
        response_format: Optional[Dict],
    ) -> str:
        payload = json.dumps(
            {
                "model": model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
                "response_format": response_format or {},
            },
            ensure_ascii=False,
            sort_keys=True,
            default=str,
        )
        digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
        return f"llm:{prefix}:{digest}"

    def _resolve_governance_ids(self):
        """Resolve tenant/user/project identifiers from Flask request context."""
        tenant_id = "default"
        user_id = None
        project_id = None
        try:
            from flask import g, request

            if hasattr(g, "current_user") and g.current_user:
                tenant_id = g.current_user.tenant_id
                user_id = g.current_user.user_id
            if request and request.args:
                project_id = request.args.get("project_id")
        except RuntimeError:
            pass
        return tenant_id, user_id, project_id

    @staticmethod
    def _guard_user_messages(messages: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """Wrap user-controlled message content before it reaches the LLM API."""
        guard = get_prompt_guard()
        guarded_messages: List[Dict[str, str]] = []
        for message in messages:
            message_copy = dict(message)
            content = message_copy.get("content", "")
            if message_copy.get("role") == "user" and isinstance(content, str):
                stripped = content.strip()
                already_wrapped = stripped.startswith("<user_content>") and stripped.endswith(
                    "</user_content>"
                )
                if not already_wrapped:
                    message_copy["content"] = guard.wrap_user_content(content)
            guarded_messages.append(message_copy)
        return guarded_messages

    @retry_with_backoff(
        max_retries=3,
        initial_delay=1.0,
        max_delay=30.0,
        exceptions=(TimeoutError, ConnectionError),
    )
    def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 4096,
        response_format: Optional[Dict] = None,
        timeout: Optional[float] = None,
    ) -> str:
        """Send a chat completion request and return text content."""
        messages = self._guard_user_messages(messages)
        cache = self._get_response_cache()
        cache_key = self._chat_cache_key("chat", self.model, messages, temperature, max_tokens, response_format)
        if cache is not None:
            cached_content = cache.get(cache_key)
            if isinstance(cached_content, str):
                return cached_content
        tenant_id, user_id, project_id = self._resolve_governance_ids()

        if not governor.check_budget(tenant_id, user_id, project_id):
            raise RuntimeError(f"LLM budget exhausted for tenant {tenant_id}")

        service = "llm"
        if not governor.check_circuit(service):
            raise RuntimeError(f"LLM circuit breaker open for service {service}")

        kwargs = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if response_format:
            kwargs["response_format"] = response_format
        request_timeout = timeout if timeout is not None else self.request_timeout
        if request_timeout is not None:
            kwargs["timeout"] = request_timeout

        start_time = time.time()
        prompt_hash = hashlib.sha256(str(messages).encode()).hexdigest()[:8]
        try:
            response = self.client.chat.completions.create(**kwargs)
        except Exception:
            governor.record_circuit_failure(service)
            raise

        elapsed = time.time() - start_time
        content = response.choices[0].message.content
        content = re.sub(r"<think>[\s\S]*?</think>", "", content).strip()

        governor.record_circuit_success(service)
        usage = response.usage
        token_counts = _usage_token_counts(usage)
        metric_tokens = 0
        if token_counts:
            prompt_tokens, completion_tokens = token_counts
            metric_tokens = prompt_tokens + completion_tokens
            total_tokens = metric_tokens
            cost = total_tokens * 0.002 / 1000
            governor.record_cost(tenant_id, user_id, project_id, total_tokens, cost)
            tokens_str = f"prompt={prompt_tokens},completion={completion_tokens}"
        else:
            tokens_str = "N/A"

        from .metrics import record_llm_call
        record_llm_call(tokens=metric_tokens, latency_ms=elapsed * 1000)

        logger.info(
            "LLM call: model=%s, prompt_hash=%s, tokens=%s, elapsed=%.2fs",
            self.model,
            prompt_hash,
            tokens_str,
            elapsed,
        )
        self._log_llm_call(
            model=self.model,
            prompt_hash=prompt_hash,
            tokens=tokens_str,
            elapsed=elapsed,
            status="success",
        )

        validation = validate_llm_output(content, context="llm_client.chat")
        if not validation["valid"]:
            logger.warning("LLM output governance issues: %s", validation["issues"])

        if cache is not None:
            cache.set(cache_key, content, ttl=Config.LLM_CACHE_TTL_SECONDS)
        return content

    def chat_with_finish_reason(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 4096,
        response_format: Optional[Dict] = None,
        timeout: Optional[float] = None,
    ) -> tuple[str, str]:
        """Send a chat request and return content plus finish_reason."""
        messages = self._guard_user_messages(messages)
        cache = self._get_response_cache()
        cache_key = self._chat_cache_key("chat_finish", self.model, messages, temperature, max_tokens, response_format)
        if cache is not None:
            cached = cache.get(cache_key)
            if isinstance(cached, dict) and "content" in cached and "finish_reason" in cached:
                return cached["content"], cached["finish_reason"]
        tenant_id, user_id, project_id = self._resolve_governance_ids()

        if not governor.check_budget(tenant_id, user_id, project_id):
            raise RuntimeError(f"LLM budget exhausted for tenant {tenant_id}")

        service = "llm"
        if not governor.check_circuit(service):
            raise RuntimeError(f"LLM circuit breaker open for service {service}")

        kwargs = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if response_format:
            kwargs["response_format"] = response_format
        request_timeout = timeout if timeout is not None else self.request_timeout
        if request_timeout is not None:
            kwargs["timeout"] = request_timeout

        start_time = time.time()
        prompt_hash = hashlib.sha256(str(messages).encode()).hexdigest()[:8]
        try:
            response = self.client.chat.completions.create(**kwargs)
        except Exception:
            governor.record_circuit_failure(service)
            raise

        elapsed = time.time() - start_time
        content = response.choices[0].message.content
        content = re.sub(r"<think>[\s\S]*?</think>", "", content).strip()
        finish_reason = response.choices[0].finish_reason

        governor.record_circuit_success(service)
        usage = response.usage
        token_counts = _usage_token_counts(usage)
        metric_tokens = 0
        if token_counts:
            prompt_tokens, completion_tokens = token_counts
            metric_tokens = prompt_tokens + completion_tokens
            total_tokens = metric_tokens
            cost = total_tokens * 0.002 / 1000
            governor.record_cost(tenant_id, user_id, project_id, total_tokens, cost)
            tokens_str = f"prompt={prompt_tokens},completion={completion_tokens}"
        else:
            tokens_str = "N/A"

        from .metrics import record_llm_call
        record_llm_call(tokens=metric_tokens, latency_ms=elapsed * 1000)

        logger.info(
            "LLM call with finish_reason: model=%s, prompt_hash=%s, tokens=%s, elapsed=%.2fs",
            self.model,
            prompt_hash,
            tokens_str,
            elapsed,
        )
        self._log_llm_call(
            model=self.model,
            prompt_hash=prompt_hash,
            tokens=tokens_str,
            elapsed=elapsed,
            status="success",
        )

        if cache is not None:
            cache.set(
                cache_key,
                {"content": content, "finish_reason": finish_reason},
                ttl=Config.LLM_CACHE_TTL_SECONDS,
            )
        return content, finish_reason

    def _log_llm_call(self, model, prompt_hash, tokens, elapsed, status):
        """Append LLM call diagnostics to a daily JSONL file."""
        try:
            os.makedirs(LLM_LOG_DIR, exist_ok=True)
            log_entry = {
                "timestamp": datetime.datetime.now(datetime.UTC).isoformat(),
                "model": model,
                "prompt_hash": prompt_hash,
                "tokens": tokens,
                "elapsed_seconds": round(elapsed, 3),
                "status": status,
            }
            log_file = os.path.join(
                LLM_LOG_DIR, f"llm_{datetime.date.today().isoformat()}.jsonl"
            )
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
        except Exception:
            logger.debug("Failed to write LLM log", exc_info=True)

    @staticmethod
    def clean_llm_text(text: str) -> str:
        """Remove markdown fences and hidden think blocks from LLM output."""
        text = re.sub(r"<think>[\s\S]*?</think>", "", text)
        text = text.strip()
        text = re.sub(r"^```(?:json)?\s*\n?", "", text, flags=re.IGNORECASE)
        text = re.sub(r"\n?```\s*$", "", text)
        return text.strip()

    @staticmethod
    def extract_json(text: str) -> Dict[str, Any]:
        """Extract a JSON object from raw LLM text."""
        cleaned = LLMClient.clean_llm_text(text)
        try:
            result = json.loads(cleaned)
            if not isinstance(result, dict):
                raise ValueError(f"Expected JSON object, got {type(result).__name__}")
            return result
        except (json.JSONDecodeError, ValueError):
            match = re.search(r"\{[\s\S]*\}", cleaned)
            if match:
                try:
                    result = json.loads(match.group())
                    if isinstance(result, dict):
                        return result
                except (json.JSONDecodeError, ValueError):
                    pass
            raise ValueError(f"Invalid JSON returned by LLM: {cleaned[:200]}...")

    def chat_json(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.3,
        max_tokens: int = 4096,
        fallback_on_failure: bool = True,
        timeout: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Send a chat request and parse the response as a JSON object."""
        data, _ = self.chat_json_with_meta(
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            fallback_on_failure=fallback_on_failure,
            timeout=timeout,
        )
        return data

    def chat_json_with_meta(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.3,
        max_tokens: int = 4096,
        fallback_on_failure: bool = True,
        timeout: Optional[float] = None,
    ) -> tuple[Dict[str, Any], Dict[str, Any]]:
        """Send a chat request and return parsed JSON with diagnostics."""
        diagnostics: Dict[str, Any] = {
            "primary_attempted": False,
            "primary_succeeded": False,
            "fallback_attempted": False,
            "fallback_succeeded": False,
            "parse_path": None,
            "cleanups_applied": [],
            "raw_preview": "",
        }

        diagnostics["primary_attempted"] = True
        try:
            content = self.chat(
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                response_format={"type": "json_object"},
                timeout=timeout,
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

        diagnostics["fallback_attempted"] = True
        json_instruction = (
            "\n\nIMPORTANT: You must respond with valid JSON only, "
            "no markdown formatting, no extra text."
        )
        fallback_messages: List[Dict[str, str]] = []
        system_found = False
        for message in messages:
            message_copy = dict(message)
            if message_copy.get("role") == "system" and not system_found:
                message_copy["content"] = message_copy.get("content", "") + json_instruction
                system_found = True
            fallback_messages.append(message_copy)
        if not system_found:
            fallback_messages.insert(
                0,
                {
                    "role": "system",
                    "content": (
                        "You must respond with valid JSON only, "
                        "no markdown formatting, no extra text."
                    ),
                },
            )

        try:
            content = self.chat(
                messages=fallback_messages,
                temperature=temperature,
                max_tokens=max_tokens,
                timeout=timeout,
            )
            diagnostics["raw_preview"] = content[:500]
            data = self.extract_json(content)
            diagnostics["fallback_succeeded"] = True
            diagnostics["parse_path"] = "fallback"
            return data, diagnostics
        except Exception:
            diagnostics["fallback_succeeded"] = False
            raise





