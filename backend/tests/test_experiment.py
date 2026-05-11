"""实验模式、DOE、RuntimeControl 测试"""
import pytest
from app.services.consumer.experiment.modes import EXPERIMENT_MODES, validate_experiment_config
from app.services.consumer.experiment.doe import ExperimentDesigner, ExperimentDesign
from app.services.consumer.runtime.control import RuntimeControlLayer, EarlyStopConfig
from app.utils.disclaimer import get_methodology_limits


class TestExperimentModes:
    def test_quick_mode_exists(self):
        assert "quick" in EXPERIMENT_MODES

    def test_research_mode_exists(self):
        assert "research" in EXPERIMENT_MODES

    def test_enterprise_mode_exists(self):
        assert "enterprise" in EXPERIMENT_MODES

    def test_quick_mode_too_few_agents(self):
        errors = validate_experiment_config("quick", 5, 1)
        assert any("at least 8" in e for e in errors)

    def test_quick_mode_valid(self):
        errors = validate_experiment_config("quick", 10, 1)
        assert errors == []

    def test_research_mode_valid(self):
        errors = validate_experiment_config("research", 50, 15, hypothesis="Test hypothesis")
        assert errors == []

    def test_unknown_mode(self):
        errors = validate_experiment_config("invalid", 10, 1)
        assert len(errors) > 0


class TestDOE:
    def setup_method(self):
        self.designer = ExperimentDesigner()

    def test_create_ab_test(self):
        exp = self.designer.create_ab_test("Test", "H1", {"x": 1}, {"x": 2})
        assert len(exp.variants) == 2
        assert exp.control_variant_id == "control"

    def test_create_price_ladder(self):
        exp = self.designer.create_price_ladder("Price", [9.9, 19.9, 29.9])
        assert len(exp.variants) == 3

    def test_assign_agents(self):
        exp = self.designer.create_ab_test("Test", "H1", {}, {})
        agents = [f"a{i}" for i in range(100)]
        assignment = self.designer.assign_agents_to_variants(agents, exp, seed=42)
        assert len(assignment) == 100
        assert all(v in ["control", "treatment"] for v in assignment.values())


class TestRuntimeControl:
    def test_save_checkpoint(self):
        rtl = RuntimeControlLayer()
        cp = rtl.save_checkpoint(1, {"agents": {}}, {"avg_attitude": 0.5})
        assert cp.round_id == 1
        assert len(rtl.checkpoints) == 1

    def test_early_stop_not_triggered_too_early(self):
        config = EarlyStopConfig(min_rounds=5, patience=3)
        rtl = RuntimeControlLayer(config)
        rtl.save_checkpoint(1, {}, {"avg_attitude": 0.5})
        stop, reason = rtl.should_early_stop(2, {"avg_attitude": 0.5, "new_events": 0})
        assert not stop

    def test_early_stop_triggered(self):
        config = EarlyStopConfig(min_rounds=1, patience=2, event_threshold=5, attitude_change_threshold=0.01)
        rtl = RuntimeControlLayer(config)
        rtl.save_checkpoint(1, {}, {"avg_attitude": 0.5})
        stop, _ = rtl.should_early_stop(2, {"avg_attitude": 0.5, "new_events": 0})
        assert not stop  # only 1 stagnant round
        rtl.save_checkpoint(2, {}, {"avg_attitude": 0.5})
        stop, reason = rtl.should_early_stop(3, {"avg_attitude": 0.5, "new_events": 0})
        assert stop
        assert "Converged" in reason

    def test_resume_point(self):
        rtl = RuntimeControlLayer()
        rtl.save_checkpoint(1, {"state": "a"}, {"m": 1})
        rtl.save_checkpoint(3, {"state": "b"}, {"m": 2})
        cp = rtl.get_resume_point(2)
        assert cp.round_id == 1


class TestMethodologyLimits:
    def test_exploratory_mode(self):
        limits = get_methodology_limits(10, 1, "quick")
        assert "Exploratory" in limits["display_label"]
        assert limits["forbidden_language"]
        assert not limits["can_do_statistical_inference"]

    def test_research_mode(self):
        limits = get_methodology_limits(50, 15, "research")
        assert "Research" in limits["display_label"]
        assert not limits["forbidden_language"]
        assert limits["can_do_statistical_inference"]

    def test_enterprise_mode(self):
        limits = get_methodology_limits(200, 50, "enterprise")
        assert "Enterprise" in limits["display_label"]
        assert limits["confidence_level"] == "high"
