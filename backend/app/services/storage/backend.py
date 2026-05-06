"""Phase 7E storage backend configuration."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict

from ...config import Config


@dataclass(frozen=True)
class StorageBackendConfig:
    backend: str
    local_paths: Dict[str, str]
    s3: Dict[str, str]


def get_storage_backend(config: type[Config] = Config) -> StorageBackendConfig:
    errors = []
    storage_backend = config.STORAGE_BACKEND
    if storage_backend not in {"local", "s3"}:
        errors.append(f"Unsupported STORAGE_BACKEND: {storage_backend}")
    if storage_backend == "s3":
        missing = [
            name
            for name, value in (
                ("S3_ENDPOINT", config.S3_ENDPOINT),
                ("S3_BUCKET", config.S3_BUCKET),
                ("S3_ACCESS_KEY", config.S3_ACCESS_KEY),
                ("S3_SECRET_KEY", config.S3_SECRET_KEY),
            )
            if not value
        ]
        if missing:
            errors.append(f"STORAGE_BACKEND=s3 requires: {', '.join(missing)}")
    if errors:
        raise ValueError("; ".join(errors))

    backend_root = Path(__file__).resolve().parents[3]
    return StorageBackendConfig(
        backend=storage_backend,
        local_paths={
            "uploads": str(backend_root / "uploads"),
            "data": str(backend_root / "data"),
        },
        s3={
            "endpoint": config.S3_ENDPOINT,
            "bucket": config.S3_BUCKET,
            "access_key": config.S3_ACCESS_KEY,
            "secret_key": config.S3_SECRET_KEY,
            "region": config.S3_REGION,
        },
    )
