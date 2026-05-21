"""Prompt injection guard for user-controlled LLM inputs."""

from __future__ import annotations

import base64
import html
import logging
import re
import unicodedata
from dataclasses import dataclass
from typing import Iterable, List, Optional

logger = logging.getLogger(__name__)

INJECTION_PATTERNS = [
    r"</instruction>",
    r"</?system>",
    r"(?i)ignore\s+(all\s+)?(previous\s+)?instructions?",
    r"(?i)forget\s+(all\s+)?(your\s+)?(training|instructions?)",
    r"(?i)reveal\s+(the\s+)?system\s+prompt",
    r"(?i)show\s+(me\s+)?(the\s+)?system\s+prompt",
    r"(?i)you\s+are\s+now\s+",
    r"(?i)from\s+now\s+on\s+you\s+are\s+",
    r"(?i)new\s+instruction\s*:",
    r"(?i)system\s*:",
    r"(?i)developer\s*:",
    r"(?i)DAN\s*mode",
    r"(?i)jailbreak",
    r"\[SYSTEM\s*OVERRIDE\]",
    r"```\s*system",
]


@dataclass(frozen=True)
class SanitizationResult:
    is_safe: bool
    sanitized_input: str
    detected_patterns: List[str]
    risk_score: float
    action: str


class PromptInjectionBlocked(ValueError):
    """Raised when user-controlled content crosses the block threshold."""

    def __init__(self, result: SanitizationResult):
        super().__init__("Potential prompt injection detected")
        self.result = result


class PromptGuard:
    """Detect, sanitize, and boundary-wrap user-controlled prompt content."""

    def __init__(
        self,
        block_threshold: float = 0.7,
        sanitize_threshold: float = 0.3,
        custom_patterns: Optional[Iterable[str]] = None,
    ) -> None:
        self.block_threshold = block_threshold
        self.sanitize_threshold = sanitize_threshold
        pattern_sources = list(INJECTION_PATTERNS)
        if custom_patterns:
            pattern_sources.extend(custom_patterns)
        self.patterns = [re.compile(pattern) for pattern in pattern_sources]

    def _normalize_input(self, text: str) -> str:
        """Normalize text to defeat encoding/Unicode obfuscation attacks.

        Applies base64 decoding, Unicode NFKC normalization, and
        common confusable character removal before pattern matching.
        """
        # Try base64 decode first — attackers may encode payloads to evade regex.
        try:
            decoded = base64.b64decode(text, validate=True).decode("utf-8")
            return decoded
        except Exception:
            pass

        # Unicode NFKC normalization — collapses compat characters (e.g. fullwidth).
        normalized = unicodedata.normalize("NFKC", text)

        # Remove zero-width and control characters used to break tokenization.
        normalized = "".join(
            ch
            for ch in normalized
            if unicodedata.category(ch) not in ("Cc", "Cf", "Cs", "Co", "Cn")
        )

        return normalized

    def sanitize(self, user_input: str) -> SanitizationResult:
        if not user_input:
            return SanitizationResult(True, "", [], 0.0, "allow")

        # Normalize input to detect obfuscated injection attempts (base64/Unicode).
        # Detection runs on normalized text, but replacement uses original input.
        normalized_input = self._normalize_input(user_input)

        detected: List[str] = []
        sanitized = str(user_input)
        # Search against normalized text to catch encoding/Unicode evasion.
        for pattern in self.patterns:
            if pattern.search(normalized_input):
                detected.append(pattern.pattern)
                # Apply removal on original input to preserve legitimate content shape.
                sanitized = pattern.sub("[removed]", sanitized)

        risk_score = min(1.0, len(detected) * 0.35)
        if risk_score >= self.block_threshold:
            action = "block"
            is_safe = False
        elif risk_score >= self.sanitize_threshold:
            action = "sanitize"
            is_safe = True
        else:
            action = "allow"
            is_safe = True
            sanitized = str(user_input)

        if detected:
            logger.warning(
                "Prompt guard detected %s injection pattern(s); action=%s risk=%.2f",
                len(detected),
                action,
                risk_score,
            )

        return SanitizationResult(
            is_safe=is_safe,
            sanitized_input=sanitized,
            detected_patterns=detected,
            risk_score=round(risk_score, 4),
            action=action,
        )

    def validate_or_raise(self, user_input: str) -> str:
        result = self.sanitize(user_input)
        if not result.is_safe:
            raise PromptInjectionBlocked(result)
        return result.sanitized_input

    def wrap_user_content(self, user_input: str) -> str:
        sanitized = self.validate_or_raise(user_input)
        escaped = html.escape(sanitized, quote=False)
        return f"<user_content>\n{escaped}\n</user_content>"


_prompt_guard: Optional[PromptGuard] = None


def get_prompt_guard() -> PromptGuard:
    global _prompt_guard
    if _prompt_guard is None:
        _prompt_guard = PromptGuard()
    return _prompt_guard


def reset_prompt_guard(guard: Optional[PromptGuard] = None) -> None:
    global _prompt_guard
    _prompt_guard = guard
