"""OASIS-to-consumer mapping layer for Phase 6G."""

from __future__ import annotations

from typing import Any, Dict, Mapping


class OasisConsumerAdapter:
    """Keep society runtime isolated from raw OASIS action schemas."""

    def map_profile(self, profile: Mapping[str, Any]) -> Dict[str, Any]:
        return {
            "persona_id": str(profile.get("agent_id", profile.get("persona_id", ""))),
            "segment": str(profile.get("segment", profile.get("label", ""))),
            "traits": dict(profile.get("traits", {})),
        }

    def map_platform(self, platform: str) -> str:
        return "consumer_society"

    def map_action(self, action: Mapping[str, Any]) -> Dict[str, Any]:
        return {
            "raw_action_type": action.get("action_type", ""),
            "consumer_context": action.get("platform", "consumer_society"),
            "payload": dict(action.get("action_args", {})),
        }

    def map_memory(self, memory: Mapping[str, Any]) -> Dict[str, Any]:
        return {
            "category_memory_signal": memory.get("category", ""),
            "brand_memory_signal": memory.get("brand", ""),
            "payload": dict(memory),
        }

    def map_result(self, result: Mapping[str, Any]) -> Dict[str, Any]:
        return {"consumer_research_metrics": dict(result.get("metrics", result))}


__all__ = ["OasisConsumerAdapter"]
