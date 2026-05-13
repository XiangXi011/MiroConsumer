"""SPEC-P2-021 README-ZH license contract."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def test_readme_zh_contains_agpl_license_section():
    text = (ROOT / "README-ZH.md").read_text(encoding="utf-8")

    assert "## 许可证" in text
    assert "AGPL-3.0" in text
    assert "SaaS" in text
    assert "完整源代码" in text
    assert "网络交互" in text
    assert "[LICENSE](LICENSE)" in text


def test_readme_zh_license_matches_english_readme_semantics():
    english = (ROOT / "README.md").read_text(encoding="utf-8")
    chinese = (ROOT / "README-ZH.md").read_text(encoding="utf-8")

    for phrase in ("AGPL-3.0", "SaaS", "LICENSE"):
        assert phrase in english
        assert phrase in chinese
    assert "修改后的代码" in chinese
    assert "同样以 AGPL-3.0 发布" in chinese
