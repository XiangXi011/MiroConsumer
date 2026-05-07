"""测试校验函数"""

import pytest
from app.utils.validators import validate_simulation_params, validate_graph_data


class TestValidateSimulationParams:
    """测试仿真参数校验"""

    def test_valid_params(self):
        """正常值应该通过校验"""
        data = {"max_agents": 100, "max_rounds": 50, "mode": "standard"}
        errors = validate_simulation_params(data)
        assert errors == []

    def test_valid_params_advanced_mode(self):
        """advanced 模式应该通过校验"""
        data = {"mode": "advanced"}
        errors = validate_simulation_params(data)
        assert errors == []

    def test_empty_data(self):
        """空数据应该通过校验（所有字段可选）"""
        errors = validate_simulation_params({})
        assert errors == []

    def test_max_agents_too_large(self):
        """max_agents 超过 1000 应该报错"""
        data = {"max_agents": 1001}
        errors = validate_simulation_params(data)
        assert len(errors) == 1
        assert "max_agents" in errors[0]

    def test_max_agents_negative(self):
        """max_agents 为负数应该报错"""
        data = {"max_agents": -1}
        errors = validate_simulation_params(data)
        assert len(errors) == 1
        assert "max_agents" in errors[0]

    def test_max_agents_zero(self):
        """max_agents 为 0 应该报错"""
        data = {"max_agents": 0}
        errors = validate_simulation_params(data)
        assert len(errors) == 1
        assert "max_agents" in errors[0]

    def test_max_rounds_too_large(self):
        """max_rounds 超过 100 应该报错"""
        data = {"max_rounds": 101}
        errors = validate_simulation_params(data)
        assert len(errors) == 1
        assert "max_rounds" in errors[0]

    def test_max_rounds_negative(self):
        """max_rounds 为负数应该报错"""
        data = {"max_rounds": -5}
        errors = validate_simulation_params(data)
        assert len(errors) == 1
        assert "max_rounds" in errors[0]

    def test_invalid_mode(self):
        """非法 mode 应该报错"""
        data = {"mode": "invalid_mode"}
        errors = validate_simulation_params(data)
        assert len(errors) == 1
        assert "mode" in errors[0]

    def test_multiple_errors(self):
        """多个参数同时非法应该返回多条错误"""
        data = {"max_agents": 2000, "max_rounds": 0, "mode": "unknown"}
        errors = validate_simulation_params(data)
        assert len(errors) == 3

    def test_max_agents_boundary_1(self):
        """max_agents 边界值 1 应该通过"""
        data = {"max_agents": 1}
        errors = validate_simulation_params(data)
        assert errors == []

    def test_max_agents_boundary_1000(self):
        """max_agents 边界值 1000 应该通过"""
        data = {"max_agents": 1000}
        errors = validate_simulation_params(data)
        assert errors == []

    def test_max_rounds_boundary_1(self):
        """max_rounds 边界值 1 应该通过"""
        data = {"max_rounds": 1}
        errors = validate_simulation_params(data)
        assert errors == []

    def test_max_rounds_boundary_100(self):
        """max_rounds 边界值 100 应该通过"""
        data = {"max_rounds": 100}
        errors = validate_simulation_params(data)
        assert errors == []


class TestValidateGraphData:
    """测试图数据校验"""

    def test_valid_graph_data(self):
        """正常图数据应该通过校验"""
        data = {"nodes": [{"id": 1}], "edges": [{"source": 1, "target": 2}]}
        errors = validate_graph_data(data)
        assert errors == []

    def test_missing_nodes(self):
        """缺少 nodes 应该报错"""
        data = {"edges": []}
        errors = validate_graph_data(data)
        assert len(errors) == 1
        assert "nodes" in errors[0]

    def test_missing_edges(self):
        """缺少 edges 应该报错"""
        data = {"nodes": []}
        errors = validate_graph_data(data)
        assert len(errors) == 1
        assert "edges" in errors[0]

    def test_empty_data(self):
        """空数据应该报两条错"""
        errors = validate_graph_data({})
        assert len(errors) == 2

    def test_nodes_not_list(self):
        """nodes 不是列表应该报错"""
        data = {"nodes": "invalid", "edges": []}
        errors = validate_graph_data(data)
        assert len(errors) == 1
        assert "nodes" in errors[0]

    def test_edges_not_list(self):
        """edges 不是列表应该报错"""
        data = {"nodes": [], "edges": "invalid"}
        errors = validate_graph_data(data)
        assert len(errors) == 1
        assert "edges" in errors[0]
