"""Persona pack registry — configurable assets instead of hardcoded defaults."""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence

from .persona_pack import (
    AgentTraitProfile,
    PersonaRecord,
    _normalize_persona,
    _validate_unique_persona_ids,
)


class PersonaPackClass(str, Enum):
    Generic = "generic"
    Industry = "industry"
    Category = "category"
    Geography = "geography"
    Custom = "custom"


@dataclass
class PersonaPackMetadata:
    pack_id: str
    label: str
    description: str = ""
    pack_class: PersonaPackClass = PersonaPackClass.Generic
    persona_count: int = 0
    tags: List[str] = field(default_factory=list)
    source: str = "builtin"
    pack_origin: str = "default_rule_pack"
    path: Optional[str] = None

    def to_summary(self) -> Dict[str, Any]:
        return {
            "pack_id": self.pack_id,
            "label": self.label,
            "description": self.description,
            "pack_class": self.pack_class.value,
            "persona_count": self.persona_count,
            "tags": self.tags,
            "source": self.source,
            "pack_origin": self.pack_origin,
        }


@dataclass
class PersonaPackSelection:
    """Lightweight selection carried inside a consumer brief."""

    pack_id: str = "default_persona_pack"
    pack_class: PersonaPackClass = PersonaPackClass.Generic
    custom_upload: bool = False

    def to_summary(self) -> Dict[str, Any]:
        return {
            "pack_id": self.pack_id,
            "pack_class": self.pack_class.value,
            "custom_upload": self.custom_upload,
        }


_BUILTIN_DATA_DIR = Path(__file__).with_name("data")


class PersonaPackRegistry:
    """Discover, validate, and load persona packs from built-in and project storage."""

    _BUILTIN_PACKS: Dict[str, PersonaPackMetadata] = {}

    def __init__(self, project_persona_dir: Optional[Path] = None) -> None:
        self._project_dir = project_persona_dir
        self._custom_cache: Dict[str, PersonaPackMetadata] = {}

    @classmethod
    def _ensure_builtin_index(cls) -> None:
        if cls._BUILTIN_PACKS:
            return
        # default_persona_pack -> generic
        default_path = _BUILTIN_DATA_DIR / "default_personas.json"
        if default_path.exists():
            personas = _load_personas_from_path(default_path)
            cls._BUILTIN_PACKS["default_persona_pack"] = PersonaPackMetadata(
                pack_id="default_persona_pack",
                label="Default Consumer Pack",
                description="General consumer personas for concept and copy testing.",
                pack_class=PersonaPackClass.Generic,
                persona_count=len(personas),
                tags=["general", "balanced"],
                source="builtin",
                pack_origin="default_rule_pack",
                path=str(default_path),
            )
        # tech_early_adopters -> industry
        tech_path = _BUILTIN_DATA_DIR / "tech_early_adopters.json"
        if tech_path.exists():
            personas = _load_personas_from_path(tech_path)
            cls._BUILTIN_PACKS["tech_early_adopters"] = PersonaPackMetadata(
                pack_id="tech_early_adopters",
                label="Tech Early Adopters",
                description="Personas skewed toward technology-forward, early-adopter consumers.",
                pack_class=PersonaPackClass.Industry,
                persona_count=len(personas),
                tags=["tech", "early_adopter", "innovation"],
                source="builtin",
                pack_origin="industry_pack",
                path=str(tech_path),
            )

    @classmethod
    def list_builtin_packs(cls) -> List[PersonaPackMetadata]:
        cls._ensure_builtin_index()
        return list(cls._BUILTIN_PACKS.values())

    def list_packs(self) -> List[PersonaPackMetadata]:
        """Return all available packs: built-in + custom for this project."""
        self.__class__._ensure_builtin_index()
        results = list(self._BUILTIN_PACKS.values())
        results.extend(self._discover_custom_packs().values())
        return results

    def get_pack(self, pack_id: str) -> Optional[PersonaPackMetadata]:
        self.__class__._ensure_builtin_index()
        if pack_id in self._BUILTIN_PACKS:
            return self._BUILTIN_PACKS[pack_id]
        custom = self._discover_custom_packs()
        return custom.get(pack_id)

    def load_pack(self, pack_id: str) -> List[PersonaRecord]:
        """Load and validate the full persona list for a pack id."""
        self.__class__._ensure_builtin_index()
        if pack_id in self._BUILTIN_PACKS:
            path = Path(self._BUILTIN_PACKS[pack_id].path)
            return _load_personas_from_path(path)
        custom = self._discover_custom_packs()
        if pack_id in custom:
            path = Path(custom[pack_id].path)
            return _load_personas_from_path(path)
        raise ValueError(f"Persona pack not found: {pack_id}")

    def load_default(self) -> List[PersonaRecord]:
        return self.load_pack("default_persona_pack")

    def resolve_selection(self, selection: Optional[PersonaPackSelection]) -> List[PersonaRecord]:
        if selection is None or not selection.pack_id:
            return self.load_default()
        try:
            return self.load_pack(selection.pack_id)
        except ValueError:
            return self.load_default()

    def register_custom_pack(
        self,
        raw_json: str,
        pack_id: Optional[str] = None,
        label: Optional[str] = None,
        description: str = "",
        pack_class: PersonaPackClass = PersonaPackClass.Custom,
        pack_origin: str = "uploaded_persona_pack",
    ) -> PersonaPackMetadata:
        if self._project_dir is None:
            raise ValueError("Project persona directory is required for custom packs")

        # Validate before persisting
        personas = _parse_and_validate_persona_pack_json(raw_json)
        assigned_id = pack_id or f"custom_{uuid.uuid4().hex[:12]}"

        self._project_dir.mkdir(parents=True, exist_ok=True)
        pack_path = self._project_dir / f"{assigned_id}.json"
        pack_path.write_text(raw_json, encoding="utf-8")

        meta = PersonaPackMetadata(
            pack_id=assigned_id,
            label=label or assigned_id,
            description=description,
            pack_class=pack_class,
            persona_count=len(personas),
            tags=["custom"],
            source="custom",
            pack_origin=pack_origin,
            path=str(pack_path),
        )
        self._custom_cache[assigned_id] = meta
        return meta

    def _discover_custom_packs(self) -> Dict[str, PersonaPackMetadata]:
        if self._project_dir is None or not self._project_dir.exists():
            return {}
        if self._custom_cache:
            return self._custom_cache
        for path in self._project_dir.glob("*.json"):
            pack_id = path.stem
            try:
                personas = _load_personas_from_path(path)
                self._custom_cache[pack_id] = PersonaPackMetadata(
                    pack_id=pack_id,
                    label=pack_id,
                    description="Custom uploaded persona pack.",
                    pack_class=PersonaPackClass.Custom,
                    persona_count=len(personas),
                    tags=["custom"],
                    source="custom",
                    pack_origin="uploaded_persona_pack",
                    path=str(path),
                )
            except ValueError:
                continue
        return self._custom_cache


def _load_personas_from_path(path: Path) -> List[PersonaRecord]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError("Persona pack top-level JSON payload must be a list")
    personas = [_normalize_persona(persona) for persona in payload]
    _validate_unique_persona_ids(personas)
    return personas


def _parse_and_validate_persona_pack_json(raw_json: str) -> List[PersonaRecord]:
    try:
        payload = json.loads(raw_json)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON: {exc}") from exc
    if not isinstance(payload, list):
        raise ValueError("Persona pack must be a JSON list of persona objects")
    if len(payload) == 0:
        raise ValueError("Persona pack must contain at least one persona")
    personas = []
    for idx, item in enumerate(payload):
        if not isinstance(item, Mapping):
            raise ValueError(f"Persona at index {idx} must be an object")
        try:
            personas.append(_normalize_persona(item))
        except ValueError as exc:
            raise ValueError(f"Persona at index {idx}: {exc}") from exc
    _validate_unique_persona_ids(personas)
    return personas


# Backward-compatible free functions that delegate through the registry

def get_registry(project_persona_dir: Optional[Path] = None) -> PersonaPackRegistry:
    return PersonaPackRegistry(project_persona_dir=project_persona_dir)


def list_builtin_persona_packs() -> List[PersonaPackMetadata]:
    return PersonaPackRegistry.list_builtin_packs()


def load_persona_pack_by_id(pack_id: str, project_persona_dir: Optional[Path] = None) -> List[PersonaRecord]:
    return get_registry(project_persona_dir).load_pack(pack_id)


__all__ = [
    "AgentTraitProfile",
    "PersonaPackClass",
    "PersonaPackMetadata",
    "PersonaPackRegistry",
    "PersonaPackSelection",
    "PersonaRecord",
    "get_registry",
    "list_builtin_persona_packs",
    "load_persona_pack_by_id",
]
