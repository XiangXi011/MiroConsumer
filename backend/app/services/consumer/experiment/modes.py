"""实验模式定义"""

EXPERIMENT_MODES = {
    "quick": {
        "name": "Quick Test / 快速测试",
        "description": "快速灵感探索，不可用于决策",
        "agent_range": (8, 12),
        "run_count": 1,
        "allow_confidence_interval": False,
        "allow_statistical_language": False,
        "display_label": "Exploratory Simulation",
        "max_duration_minutes": 5,
    },
    "research": {
        "name": "Research Mode / 研究模式",
        "description": "研究预演，可输出趋势和稳定性",
        "agent_range": (30, 100),
        "run_count_range": (10, 30),
        "allow_confidence_interval": True,
        "allow_statistical_language": True,
        "display_label": "Research Simulation",
        "requires_hypothesis": True,
        "max_duration_minutes": 30,
    },
    "enterprise": {
        "name": "Enterprise Validation / 企业验证",
        "description": "企业级审计，可输出 benchmark 和审计包",
        "agent_range": (100, 1000),
        "run_count_range": (30, 100),
        "allow_confidence_interval": True,
        "allow_statistical_language": True,
        "display_label": "Enterprise Validation",
        "requires_hypothesis": True,
        "requires_control_group": True,
        "max_duration_minutes": 120,
    },
}


def validate_experiment_config(mode: str, agent_count: int, run_count: int) -> list:
    """校验实验配置是否符合模式要求"""
    errors = []
    config = EXPERIMENT_MODES.get(mode)
    if not config:
        return [f"Unknown mode: {mode}"]

    min_agents, max_agents = config["agent_range"]
    if agent_count < min_agents:
        errors.append(f"{mode} mode requires at least {min_agents} agents, got {agent_count}")
    if agent_count > max_agents:
        errors.append(f"{mode} mode supports at most {max_agents} agents, got {agent_count}")

    # quick mode has fixed run_count
    if mode == "quick" and run_count != config.get("run_count", 1):
        errors.append(f"quick mode requires run_count={config.get('run_count', 1)}, got {run_count}")

    # research/enterprise have run_count ranges
    if "run_count_range" in config:
        min_runs, max_runs = config["run_count_range"]
        if run_count < min_runs:
            errors.append(f"{mode} mode requires at least {min_runs} runs, got {run_count}")
        if run_count > max_runs:
            errors.append(f"{mode} mode supports at most {max_runs} runs, got {run_count}")

    return errors
