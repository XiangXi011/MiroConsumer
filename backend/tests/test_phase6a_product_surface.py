"""
Phase 6A Task 2 – Product Surface Doc Tests
Guards that product-facing docs do not present default or project_type=default
as a visible product mode.
"""

from pathlib import Path
import re

PROJECT_ROOT = Path(__file__).resolve().parents[2]
README_EN = PROJECT_ROOT / "README.md"
README_ZH = PROJECT_ROOT / "README-ZH.md"
PRD = PROJECT_ROOT / "PRD.md"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# 1. README.md must not mention project_type=default
# ---------------------------------------------------------------------------

def test_readme_en_no_project_type_default():
    content = _read(README_EN)
    assert "project_type=default" not in content, (
        "README.md must not contain 'project_type=default'"
    )


# ---------------------------------------------------------------------------
# 2. README.md must not present default as a visible product mode
# ---------------------------------------------------------------------------

def test_readme_en_no_default_mode_wording():
    content = _read(README_EN).lower()
    # Allow "default" in technical contexts (e.g. "default ports") but
    # reject phrasing that frames it as a product mode or project type.
    pattern = re.compile(
        r"(project[\s_-]*type[\s:=]*default|default\s+mode|default\s+project)"
    )
    match = pattern.search(content)
    assert match is None, (
        f"README.md must not present default as a visible product mode; "
        f"found: '{match.group()}'"
    )


# ---------------------------------------------------------------------------
# 3. README-ZH.md must not mention project_type=default
# ---------------------------------------------------------------------------

def test_readme_zh_no_project_type_default():
    content = _read(README_ZH)
    assert "project_type=default" not in content, (
        "README-ZH.md must not contain 'project_type=default'"
    )


# ---------------------------------------------------------------------------
# 4. README-ZH.md must not present default as a visible product mode
# ---------------------------------------------------------------------------

def test_readme_zh_no_default_mode_wording():
    content = _read(README_ZH).lower()
    pattern = re.compile(
        r"(project[\s_-]*type[\s:=]*default|default\s+mode|default\s+project)"
    )
    match = pattern.search(content)
    assert match is None, (
        f"README-ZH.md must not present default as a visible product mode; "
        f"found: '{match.group()}'"
    )


# ---------------------------------------------------------------------------
# 5. PRD.md may only mention "default" inside the maintainer compatibility
#    section (section 4.3).
# ---------------------------------------------------------------------------

def test_prd_default_only_in_maintainer_section():
    content = _read(PRD)

    # Find the maintainer compatibility section header.
    maintainer_marker = "Maintainer-Only"
    idx = content.find(maintainer_marker)
    assert idx != -1, (
        "PRD.md must contain a 'Maintainer-Only' compatibility section"
    )

    # Extract the maintainer section (from its header to the next ### heading).
    section_start = idx
    next_heading = re.search(r"\n###\s", content[section_start + 1:])
    if next_heading:
        section_end = section_start + next_heading.start() + 1
    else:
        section_end = len(content)
    maintainer_block = content[section_start:section_end]

    # Every occurrence of "default" that is NOT inside the maintainer block
    # must only be a code identifier (e.g. default_auto_research_provider)
    # and not a project_type / mode reference.
    outside = content[:section_start] + content[section_end:]
    for line_no, line in enumerate(outside.splitlines(), 1):
        if "default" not in line.lower():
            continue
        # Allow code identifiers like default_auto_research_provider
        if "default_auto_research_provider" in line:
            continue
        # Allow un-related "default" in generic English (e.g. "default ports")
        # but reject anything tied to project_type or product mode.
        if re.search(r"project[\s_-]*type.*default", line, re.IGNORECASE):
            assert False, (
                f"PRD.md line {line_no} references 'project_type=default' "
                f"outside the maintainer compatibility section: {line.strip()}"
            )
