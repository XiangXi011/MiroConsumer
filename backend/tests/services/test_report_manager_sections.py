from app.services.report_agent import ReportManager


def test_get_generated_sections_includes_title_from_markdown_heading(monkeypatch, tmp_path):
    monkeypatch.setattr(ReportManager, "REPORTS_DIR", str(tmp_path))
    report_dir = tmp_path / "report_titles"
    report_dir.mkdir()
    (report_dir / "section_01.md").write_text("## 测试概览\n\n正文", encoding="utf-8")

    sections = ReportManager.get_generated_sections("report_titles")

    assert sections == [
        {
            "filename": "section_01.md",
            "section_index": 1,
            "title": "测试概览",
            "content": "## 测试概览\n\n正文",
        }
    ]
