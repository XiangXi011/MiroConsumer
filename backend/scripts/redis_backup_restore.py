"""Backup and restore Redis persistence artifacts for production operations.

The script copies Redis RDB/AOF artifacts between a Redis data directory and a
backup directory. Stop Redis or run against a filesystem snapshot when restoring.
"""

from __future__ import annotations

import argparse
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

ARTIFACT_NAMES = ("dump.rdb", "appendonly.aof", "appendonlydir")


def _copy_artifact(source: Path, target: Path, force: bool = False) -> bool:
    if not source.exists():
        return False
    if target.exists():
        if not force:
            raise FileExistsError(f"Refusing to overwrite existing artifact: {target}")
        if target.is_dir():
            shutil.rmtree(target)
        else:
            target.unlink()
    if source.is_dir():
        shutil.copytree(source, target)
    else:
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
    return True


def backup(redis_data_dir: Path, output_dir: Path, timestamped: bool = True) -> Path:
    destination = output_dir
    if timestamped:
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        destination = output_dir / f"redis-{stamp}"
    destination.mkdir(parents=True, exist_ok=True)

    copied = []
    for artifact_name in ARTIFACT_NAMES:
        if _copy_artifact(redis_data_dir / artifact_name, destination / artifact_name, force=True):
            copied.append(artifact_name)

    manifest = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "redis_data_dir": str(redis_data_dir),
        "artifacts": copied,
    }
    (destination / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return destination


def restore(input_dir: Path, redis_data_dir: Path, force: bool = False) -> list[str]:
    redis_data_dir.mkdir(parents=True, exist_ok=True)
    restored = []
    for artifact_name in ARTIFACT_NAMES:
        if _copy_artifact(input_dir / artifact_name, redis_data_dir / artifact_name, force=force):
            restored.append(artifact_name)
    return restored


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Backup or restore Redis dump.rdb and appendonly.aof artifacts")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--backup", action="store_true", help="copy Redis artifacts into --output-dir")
    mode.add_argument("--restore", action="store_true", help="copy Redis artifacts from --input-dir into --redis-data-dir")
    parser.add_argument("--redis-data-dir", default="/data", help="Redis data directory that contains dump.rdb or appendonly.aof")
    parser.add_argument("--output-dir", default="redis-backups", help="backup destination directory")
    parser.add_argument("--input-dir", help="backup directory to restore from")
    parser.add_argument("--force", action="store_true", help="overwrite existing restore targets")
    parser.add_argument("--no-timestamp", action="store_true", help="write backup directly to --output-dir")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    redis_data_dir = Path(args.redis_data_dir)
    if args.backup:
        destination = backup(redis_data_dir, Path(args.output_dir), timestamped=not args.no_timestamp)
        print(f"Redis backup written to {destination}")
        return 0

    if not args.input_dir:
        raise SystemExit("--input-dir is required with --restore")
    restored = restore(Path(args.input_dir), redis_data_dir, force=args.force)
    print("Redis artifacts restored: " + (", ".join(restored) if restored else "none found"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())