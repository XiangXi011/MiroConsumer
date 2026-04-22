"""Lightweight prepare manifest persistence for simulation workspaces.

After a successful prepare, a manifest is written to the simulation directory
so that reuse metadata and prepare provenance can be exposed via APIs without
relying on a global cache.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


MANIFEST_FILE_NAME = "prepare_manifest.json"
MANIFEST_VERSION = "1.0"


@dataclass
class PrepareManifest:
    manifest_version: str = MANIFEST_VERSION
    simulation_id: str = ""
    project_id: str = ""
    project_type: str = "default"
    consumer_mode: bool = False
    prepared_at: str = ""
    profiles_count: int = 0
    entities_count: int = 0
    entity_types: List[str] = field(default_factory=list)
    config_generated: bool = False
    persona_pack_id: str = ""
    reuse_count: int = 0
    last_reused_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "manifest_version": self.manifest_version,
            "simulation_id": self.simulation_id,
            "project_id": self.project_id,
            "project_type": self.project_type,
            "consumer_mode": self.consumer_mode,
            "prepared_at": self.prepared_at,
            "profiles_count": self.profiles_count,
            "entities_count": self.entities_count,
            "entity_types": self.entity_types,
            "config_generated": self.config_generated,
            "persona_pack_id": self.persona_pack_id,
            "reuse_count": self.reuse_count,
            "last_reused_at": self.last_reused_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> PrepareManifest:
        return cls(
            manifest_version=data.get("manifest_version", MANIFEST_VERSION),
            simulation_id=data.get("simulation_id", ""),
            project_id=data.get("project_id", ""),
            project_type=data.get("project_type", "default"),
            consumer_mode=data.get("consumer_mode", False),
            prepared_at=data.get("prepared_at", ""),
            profiles_count=data.get("profiles_count", 0),
            entities_count=data.get("entities_count", 0),
            entity_types=data.get("entity_types", []),
            config_generated=data.get("config_generated", False),
            persona_pack_id=data.get("persona_pack_id", ""),
            reuse_count=data.get("reuse_count", 0),
            last_reused_at=data.get("last_reused_at"),
        )


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def write_manifest(
    simulation_dir: str,
    simulation_id: str,
    project_id: str,
    project_type: str,
    consumer_mode: bool,
    profiles_count: int,
    entities_count: int,
    entity_types: List[str],
    config_generated: bool,
    persona_pack_id: str = "",
) -> str:
    """Write or overwrite the prepare manifest for a simulation workspace.

    Returns the path to the written manifest file.
    """
    manifest_path = os.path.join(simulation_dir, MANIFEST_FILE_NAME)

    # Preserve existing reuse count if manifest already exists
    reuse_count = 0
    if os.path.exists(manifest_path):
        try:
            existing = read_manifest(simulation_dir)
            if existing:
                reuse_count = existing.reuse_count
        except Exception:
            pass

    manifest = PrepareManifest(
        simulation_id=simulation_id,
        project_id=project_id,
        project_type=project_type,
        consumer_mode=consumer_mode,
        prepared_at=_now_iso(),
        profiles_count=profiles_count,
        entities_count=entities_count,
        entity_types=list(entity_types),
        config_generated=config_generated,
        persona_pack_id=persona_pack_id,
        reuse_count=reuse_count,
    )

    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest.to_dict(), f, ensure_ascii=False, indent=2)

    return manifest_path


def read_manifest(simulation_dir: str) -> Optional[PrepareManifest]:
    """Read the prepare manifest from a simulation workspace if it exists."""
    manifest_path = os.path.join(simulation_dir, MANIFEST_FILE_NAME)
    if not os.path.exists(manifest_path):
        return None

    with open(manifest_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    return PrepareManifest.from_dict(data)


def touch_reuse(simulation_dir: str) -> Optional[PrepareManifest]:
    """Increment reuse_count and update last_reused_at on an existing manifest.

    Returns the updated manifest, or None if no manifest exists.
    """
    manifest = read_manifest(simulation_dir)
    if not manifest:
        return None

    manifest.reuse_count += 1
    manifest.last_reused_at = _now_iso()

    manifest_path = os.path.join(simulation_dir, MANIFEST_FILE_NAME)
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest.to_dict(), f, ensure_ascii=False, indent=2)

    return manifest
