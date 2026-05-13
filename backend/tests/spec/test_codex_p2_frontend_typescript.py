"""SPEC-P2-022 frontend TypeScript migration contract."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
FRONTEND = ROOT / "frontend"


def test_frontend_has_strict_typescript_config_and_typecheck_script():
    package = json.loads((FRONTEND / "package.json").read_text(encoding="utf-8"))
    tsconfig = json.loads((FRONTEND / "tsconfig.json").read_text(encoding="utf-8"))

    assert package["scripts"]["typecheck"] == "vue-tsc --noEmit"
    assert "typescript" in package["devDependencies"]
    assert "vue-tsc" in package["devDependencies"]
    assert tsconfig["compilerOptions"]["strict"] is True
    assert tsconfig["compilerOptions"]["noImplicitAny"] is True
    assert "src/**/*.ts" in tsconfig["include"]
    assert "src/**/*.vue" in tsconfig["include"]


def test_frontend_src_is_migrated_from_javascript_to_typescript():
    js_files = sorted(FRONTEND.joinpath("src").rglob("*.js"))
    ts_files = sorted(FRONTEND.joinpath("src").rglob("*.ts"))

    assert js_files == []
    assert any(path.name == "main.ts" for path in ts_files)
    assert any("api" in path.parts and path.suffix == ".ts" for path in ts_files)
    assert (FRONTEND / "src" / "types" / "api.ts").exists()


def test_all_vue_files_use_typescript_script_setup():
    vue_files = sorted(FRONTEND.joinpath("src").rglob("*.vue"))
    assert vue_files

    for path in vue_files:
        text = path.read_text(encoding="utf-8")
        assert '<script setup lang="ts">' in text, path


def test_ci_runs_frontend_typecheck_before_build():
    ci_text = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")

    typecheck_index = ci_text.index("name: Run frontend typecheck")
    build_index = ci_text.index("name: Build frontend")
    assert typecheck_index < build_index
    assert "npm run typecheck" in ci_text
