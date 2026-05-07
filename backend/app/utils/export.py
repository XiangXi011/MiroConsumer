"""仿真结果导出工具"""

import json
import csv
import io
from typing import Dict, Any, List


def export_to_json(simulation_data: Dict[str, Any]) -> str:
    """导出为 JSON 字符串"""
    return json.dumps(simulation_data, ensure_ascii=False, indent=2)


def export_metrics_to_csv(metrics: List[Dict[str, Any]]) -> str:
    """导出指标为 CSV"""
    if not metrics:
        return ""

    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=metrics[0].keys())
    writer.writeheader()
    writer.writerows(metrics)
    return output.getvalue()


def export_rounds_to_csv(rounds: List[Dict[str, Any]]) -> str:
    """导出轮次数据为 CSV"""
    if not rounds:
        return ""

    # 展平嵌套数据
    flat_rows = []
    for round_data in rounds:
        round_num = round_data.get("round", 0)
        for agent_id, agent_data in round_data.get("agents", {}).items():
            row = {"round": round_num, "agent_id": agent_id}
            if isinstance(agent_data, dict):
                row.update(agent_data)
            flat_rows.append(row)

    if not flat_rows:
        return ""

    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=flat_rows[0].keys())
    writer.writeheader()
    writer.writerows(flat_rows)
    return output.getvalue()


def export_simulation_manifest(simulation_data: dict, methodology: dict) -> str:
    """导出 simulation_manifest.json"""
    manifest = {
        "simulation_id": simulation_data.get("id"),
        "created_at": simulation_data.get("created_at"),
        "agent_count": methodology.get("agent_count"),
        "run_count": methodology.get("run_count"),
        "simulation_mode": methodology.get("simulation_mode"),
        "random_seed": methodology.get("random_seed"),
        "methodology_limits": methodology,
        "graph_config": simulation_data.get("graph_config", {}),
        "persona_config": simulation_data.get("persona_config", {}),
        "event_sequence": simulation_data.get("event_sequence", []),
    }
    return json.dumps(manifest, ensure_ascii=False, indent=2)


# ── P3-6: PDF/Word/PPT 导出 ──────────────────────────

def export_to_pdf(title: str, content: str, output_path: str) -> str:
    """导出报告为 PDF。"""
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
    from reportlab.lib.units import cm

    doc = SimpleDocTemplate(output_path, pagesize=A4)
    styles = getSampleStyleSheet()
    story = []

    story.append(Paragraph(title, styles["Title"]))
    story.append(Spacer(1, 1 * cm))

    for line in content.split("\n"):
        line = line.strip()
        if not line:
            story.append(Spacer(1, 0.3 * cm))
        elif line.startswith("# "):
            story.append(Paragraph(line[2:], styles["Heading1"]))
        elif line.startswith("## "):
            story.append(Paragraph(line[3:], styles["Heading2"]))
        elif line.startswith("- "):
            story.append(Paragraph(f"• {line[2:]}", styles["BodyText"]))
        else:
            story.append(Paragraph(line, styles["BodyText"]))

    doc.build(story)
    return output_path


def export_to_docx(title: str, content: str, output_path: str) -> str:
    """导出报告为 Word (.docx)。"""
    from docx import Document
    from docx.shared import Pt, Inches

    doc = Document()
    doc.add_heading(title, level=0)

    for line in content.split("\n"):
        line = line.strip()
        if not line:
            continue
        if line.startswith("# "):
            doc.add_heading(line[2:], level=1)
        elif line.startswith("## "):
            doc.add_heading(line[3:], level=2)
        elif line.startswith("- "):
            doc.add_paragraph(line[2:], style="List Bullet")
        else:
            doc.add_paragraph(line)

    doc.save(output_path)
    return output_path


def export_to_pptx(title: str, content: str, output_path: str) -> str:
    """导出报告为 PowerPoint (.pptx)。"""
    from pptx import Presentation
    from pptx.util import Inches, Pt

    prs = Presentation()

    # Title slide
    slide_layout = prs.slide_layouts[0]
    slide = prs.slides.add_slide(slide_layout)
    slide.shapes.title.text = title

    # Content slides — split by ## headings
    sections = content.split("## ")
    for section in sections[1:]:  # skip first (before first heading)
        lines = section.strip().split("\n")
        heading = lines[0].strip()
        body = "\n".join(lines[1:]).strip()

        slide_layout = prs.slide_layouts[1]
        slide = prs.slides.add_slide(slide_layout)
        slide.shapes.title.text = heading
        if body:
            slide.placeholders[1].text = body[:500]  # PPT placeholder limit

    prs.save(output_path)
    return output_path
