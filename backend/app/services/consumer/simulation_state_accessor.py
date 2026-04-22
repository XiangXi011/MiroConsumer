"""Consumer-owned accessor for consumer-specific simulation artifacts.

Keeps file-path knowledge and low-level I/O for consumer simulation state
inside the consumer boundary rather than leaking it into API routes and
core services.
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from ...config import Config
from .brief_adapter import ConsumerBriefAdapter
from .models import ConsumerBusinessBrief


class ConsumerSimulationStateAccessor:
    """Owns the layout and loading of consumer-specific simulation artifacts."""

    @classmethod
    def _simulation_dir(cls, simulation_id: str) -> Path:
        return Path(Config.UPLOAD_FOLDER) / "simulations" / simulation_id

    @classmethod
    def rounds_path(cls, simulation_id: str) -> Path:
        """Path to consumer_rounds.jsonl for the given simulation."""
        return cls._simulation_dir(simulation_id) / "consumer_rounds.jsonl"

    @classmethod
    def config_path(cls, simulation_id: str) -> Path:
        """Path to consumer_config.json for the given simulation."""
        return cls._simulation_dir(simulation_id) / "consumer_config.json"

    @classmethod
    def load_consumer_config(cls, simulation_id: str) -> Dict[str, Any]:
        """Load consumer_config.json or return an empty dict."""
        path = cls.config_path(simulation_id)
        if not path.exists():
            return {}
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)

    @classmethod
    def load_consumer_rounds(cls, simulation_id: str) -> List[Dict[str, Any]]:
        """Load consumer_rounds.jsonl or return an empty list."""
        path = cls.rounds_path(simulation_id)
        if not path.exists():
            return []
        with path.open("r", encoding="utf-8") as f:
            return [json.loads(line) for line in f if line.strip()]

    @classmethod
    def load_brief(cls, simulation_id: str) -> Optional[ConsumerBusinessBrief]:
        """Load and adapt the consumer brief from consumer_config.json."""
        config = cls.load_consumer_config(simulation_id)
        brief_payload = config.get("consumer_brief") or {}
        if not brief_payload:
            return None
        return ConsumerBriefAdapter.from_payload(brief_payload)

    @classmethod
    def load_research_findings(cls, simulation_id: str) -> List[Dict[str, Any]]:
        """Load research findings list from consumer_config.json."""
        config = cls.load_consumer_config(simulation_id)
        return config.get("research_findings", [])
