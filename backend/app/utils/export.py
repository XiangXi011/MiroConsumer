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
