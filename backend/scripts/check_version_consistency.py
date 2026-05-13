"""Check pyproject and changelog version alignment for CI."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig")


def _pyproject_version(path: Path) -> str:
    match = re.search(r'^version = "([^"]+)"', _read(path), re.MULTILINE)
    if not match:
        raise ValueError(f"Missing project version in {path}")
    return match.group(1)


def _changelog_versions(path: Path) -> list[str]:
    return re.findall(r"^## \[([0-9]+\.[0-9]+\.[0-9]+)\]", _read(path), re.MULTILINE)


def check_versions(root: Path) -> list[str]:
    backend_version = _pyproject_version(root / "backend" / "pyproject.toml")
    changelog_versions = _changelog_versions(root / "CHANGELOG.md")
    failures: list[str] = []
    if not changelog_versions:
        failures.append("CHANGELOG.md has no Keep a Changelog release heading")
    elif changelog_versions[0] != backend_version:
        failures.append(
            f"backend/pyproject.toml version {backend_version} does not match CHANGELOG.md {changelog_versions[0]}"
        )
    return failures


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[2])
    args = parser.parse_args(argv)
    failures = check_versions(args.root.resolve())
    if failures:
        for failure in failures:
            print(failure)
        return 1
    print("Version consistency check passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
