from app.api import report as report_api
from app.services.report_agent import Report, ReportStatus


def test_report_data_includes_generated_sections_when_report_metadata_lacks_top_level_sections(monkeypatch):
    report = Report(
        report_id="report_sections",
        simulation_id="sim_sections",
        graph_id="graph_sections",
        simulation_requirement="check sections",
        status=ReportStatus.COMPLETED,
        markdown_content="# Report",
    )
    generated_sections = [
        {"index": 1, "title": "Overview", "content": "Body", "filename": "section_01.md"}
    ]

    monkeypatch.setattr(
        report_api.ReportManager,
        "get_generated_sections",
        lambda report_id: generated_sections,
    )

    data = report_api._report_data_with_diagnostics(report)

    assert data["sections"] == generated_sections
