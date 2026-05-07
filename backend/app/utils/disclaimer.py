"""免责声明配置"""

DISCLAIMER_TEXT = (
    "本系统为学术研究工具，所有仿真结果均为基于大语言模型的模拟推演，"
    "不代表真实消费者行为或市场预测。仿真数据不可用于商业决策。"
)

SIMULATION_DISCLAIMER = (
    "⚠️ 本仿真实验结果由AI Agent推演生成，仅供学术研究参考。"
    "请勿将仿真结论作为真实市场判断依据。"
)

REPORT_DISCLAIMER = (
    "📋 本报告由AI自动生成，基于仿真数据推演。"
    "报告内容不代表真实市场情况，不构成任何商业建议。"
)


def get_methodology_limits(agent_count: int, run_count: int, mode: str) -> dict:
    """根据实验配置返回方法论限制"""
    limits = {
        "agent_count": agent_count,
        "run_count": run_count,
        "simulation_mode": mode,
        "can_do_statistical_inference": agent_count >= 30 and run_count >= 10,
        "confidence_level": (
            "high" if agent_count >= 100 and run_count >= 30
            else "medium" if agent_count >= 30 and run_count >= 10
            else "low"
        ),
        "display_label": (
            "Exploratory Simulation / 探索性仿真" if agent_count < 30
            else "Research Simulation / 研究仿真" if agent_count < 100
            else "Enterprise Validation / 企业验证"
        ),
        "forbidden_language": agent_count < 30,
        "limits": [],
    }
    if agent_count < 30:
        limits["limits"].append("样本量不足，禁止统计推断语言")
    if run_count < 10:
        limits["limits"].append("重复次数不足，置信区间不可靠")
    if mode == "quick":
        limits["limits"].append("快速模式仅用于灵感探索，不可用于决策")
    return limits
