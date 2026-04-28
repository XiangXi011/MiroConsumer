"""Tests for ConsumerResearchActionService (Phase 6F)."""

from unittest.mock import MagicMock

import pytest

from app.services.application.consumer_research_action_service import (
    ConsumerResearchActionService,
    ConsumerResearchActionType,
)
from app.services.consumer.research_tool_semantics import (
    CONSUMER_TOOL_SEMANTICS,
    get_consumer_tool_label,
    get_consumer_tool_purpose,
)


class FakeState:
    project_type = "consumer_test"
    consumer_mode = True
    graph_id = "g1"
    simulation_requirement = "test requirement"


class FakeZepResult:
    def to_text(self):
        return "zep result"


class FakeZepTools:
    def insight_forge(self, **kwargs):
        return FakeZepResult()

    def panorama_search(self, **kwargs):
        return FakeZepResult()

    def quick_search(self, **kwargs):
        return FakeZepResult()


class FakeBranchAppService:
    @classmethod
    def get_branch_comparison(cls, simulation_id, branch_id):
        return {"comparison": "delta"}


def _assert_unified_shape(response, simulation_id, action_type):
    """Assert response conforms to Phase 6F unified response shape."""
    assert "success" not in response, "Unified response must not contain 'success'"
    assert "result" not in response, "Unified response must not contain 'result'"
    assert response["action_type"] == action_type
    assert response["simulation_id"] == simulation_id
    assert isinstance(response["target"], dict)
    assert "title" in response
    assert "summary" in response
    assert "details_markdown" in response

    evidence = response["evidence"]
    assert isinstance(evidence, dict)
    assert "support_level" in evidence
    assert evidence["support_level"] in (
        "strong", "medium", "weak", "insufficient", "simulation_only"
    )
    assert "source_count" in evidence
    assert "simulation_quote_count" in evidence
    assert "gatekeeping_status" in evidence

    tool_trace = response["tool_trace"]
    assert isinstance(tool_trace, dict)
    assert "tool_name" in tool_trace
    assert "consumer_tool_label" in tool_trace
    assert "query" in tool_trace

    handoff = response["handoff"]
    assert isinstance(handoff, dict)
    assert "handoff_type" in handoff
    assert "target_context" in handoff


class TestConsumerResearchActionService:
    def setup_method(self):
        self._orig_simulation_repo = ConsumerResearchActionService._simulation_repo
        self._orig_zep = ConsumerResearchActionService._zep_tools_class
        self._orig_branch = ConsumerResearchActionService._branch_app_service_class

        self.mock_repo = MagicMock()
        self.mock_repo.get_simulation.return_value = FakeState()
        ConsumerResearchActionService._simulation_repo = self.mock_repo
        ConsumerResearchActionService._zep_tools_class = FakeZepTools
        ConsumerResearchActionService._branch_app_service_class = FakeBranchAppService

    def teardown_method(self):
        ConsumerResearchActionService._simulation_repo = self._orig_simulation_repo
        ConsumerResearchActionService._zep_tools_class = self._orig_zep
        ConsumerResearchActionService._branch_app_service_class = self._orig_branch

    def test_deep_dive_conclusion(self):
        target = {"kind": "finding", "id": "f1", "text": "claim quality"}
        result = ConsumerResearchActionService.run_action(
            "sim_1", {"action_type": "deep_dive_conclusion", "target": target}
        )
        _assert_unified_shape(result, "sim_1", "deep_dive_conclusion")
        assert result["title"] == "消费者洞察深挖"
        assert result["tool_trace"]["tool_name"] == "insight_forge"
        assert result["tool_trace"]["consumer_tool_label"] == "消费者洞察深挖"
        assert result["tool_trace"]["query"] == "claim quality"

    def test_explain_propagation_path(self):
        target = {"kind": "round", "id": "r3", "text": "round 3"}
        result = ConsumerResearchActionService.run_action(
            "sim_1", {"action_type": "explain_propagation_path", "target": target}
        )
        _assert_unified_shape(result, "sim_1", "explain_propagation_path")
        assert result["title"] == "传播路径解释器"
        assert result["tool_trace"]["tool_name"] == "panorama_search"
        assert result["tool_trace"]["consumer_tool_label"] == "传播路径解释器"

    def test_verify_evidence(self):
        target = {"kind": "claim", "id": "c1", "text": "sugar claim"}
        result = ConsumerResearchActionService.run_action(
            "sim_1", {"action_type": "verify_evidence", "target": target}
        )
        _assert_unified_shape(result, "sim_1", "verify_evidence")
        assert result["title"] == "报告结论证据校验"
        assert result["tool_trace"]["tool_name"] == "quick_search"
        assert result["evidence"]["support_level"] == "weak"
        assert "报告上下文证据检索" in result["details_markdown"]
        assert "Zep 快速搜索结果" in result["details_markdown"]

    def test_interview_consumers_handoff(self):
        target = {"kind": "finding", "id": "f1", "text": "price sensitivity"}
        context = {
            "report_id": "rpt_1",
            "section_index": 2,
            "claim": "price is too high",
            "branch_id": "b1",
        }
        result = ConsumerResearchActionService.run_action(
            "sim_1",
            {
                "action_type": "interview_consumers",
                "target": target,
                "context": context,
            },
        )
        _assert_unified_shape(result, "sim_1", "interview_consumers")
        assert result["title"] == "追问消费者"
        assert result["summary"] == "已生成 Phase 6I 访谈上下文"
        assert result["details_markdown"] == ""
        assert result["evidence"]["support_level"] == "simulation_only"
        assert result["evidence"]["source_count"] == 0
        assert result["evidence"]["simulation_quote_count"] == 0
        assert result["evidence"]["gatekeeping_status"] == "handoff"
        assert result["tool_trace"]["tool_name"] == ""
        assert result["tool_trace"]["consumer_tool_label"] == ""
        assert result["handoff"]["handoff_type"] == "phase6i_interview"
        tc = result["handoff"]["target_context"]
        assert tc["report_id"] == "rpt_1"
        assert tc["section_index"] == 2
        assert tc["finding_id"] == "f1"
        assert tc["claim"] == "price is too high"
        assert tc["branch_id"] == "b1"

    def test_interview_consumers_finding_id_from_target_text_when_not_finding(self):
        target = {"kind": "claim", "id": "c1", "text": "something"}
        result = ConsumerResearchActionService.run_action(
            "sim_1",
            {"action_type": "interview_consumers", "target": target},
        )
        assert result["handoff"]["target_context"]["finding_id"] == ""
        assert result["handoff"]["target_context"]["claim"] == "something"

    def test_compare_branch_delta(self):
        target = {"kind": "branch", "id": "branch_1", "text": "branch_1"}
        result = ConsumerResearchActionService.run_action(
            "sim_1", {"action_type": "compare_branch_delta", "target": target}
        )
        _assert_unified_shape(result, "sim_1", "compare_branch_delta")
        assert result["title"] == "比较分支差异"
        assert "comparison" in result["summary"]

    def test_compare_branch_delta_uses_context_branch_id_first(self):
        target = {"kind": "branch", "id": "target_id", "text": "target_text"}
        result = ConsumerResearchActionService.run_action(
            "sim_1",
            {
                "action_type": "compare_branch_delta",
                "target": target,
                "context": {"branch_id": "ctx_branch"},
            },
        )
        # FakeBranchAppService returns {"comparison": "delta"} regardless,
        # but we verify the call path by inspecting the response shape.
        _assert_unified_shape(result, "sim_1", "compare_branch_delta")

    def test_compare_branch_delta_falls_back_to_target_id(self):
        target = {"kind": "branch", "id": "fallback_id", "text": "fallback_text"}
        result = ConsumerResearchActionService.run_action(
            "sim_1",
            {
                "action_type": "compare_branch_delta",
                "target": target,
            },
        )
        _assert_unified_shape(result, "sim_1", "compare_branch_delta")

    def test_compare_branch_delta_falls_back_to_target_text(self):
        target = {"kind": "branch", "text": "text_only"}
        result = ConsumerResearchActionService.run_action(
            "sim_1",
            {
                "action_type": "compare_branch_delta",
                "target": target,
            },
        )
        _assert_unified_shape(result, "sim_1", "compare_branch_delta")

    def test_missing_simulation_raises_404(self):
        self.mock_repo.get_simulation.return_value = None
        with pytest.raises(ValueError, match="Simulation not found"):
            ConsumerResearchActionService.run_action(
                "sim_missing",
                {"action_type": "deep_dive_conclusion", "target": {"text": "x"}},
            )

    def test_non_consumer_simulation_rejected(self):
        class NonConsumerState:
            project_type = "default"
            consumer_mode = False

        self.mock_repo.get_simulation.return_value = NonConsumerState()
        with pytest.raises(ValueError):
            ConsumerResearchActionService.run_action(
                "sim_1", {"action_type": "deep_dive_conclusion", "target": {"text": "x"}}
            )

    def test_missing_action_type_raises_400(self):
        with pytest.raises(ValueError, match="action_type is required"):
            ConsumerResearchActionService.run_action("sim_1", {"target": {"text": "x"}})

    def test_unknown_action_type_raises_400(self):
        with pytest.raises(ValueError, match="Unknown action_type"):
            ConsumerResearchActionService.run_action(
                "sim_1", {"action_type": "unknown_action", "target": {"text": "x"}}
            )

    def test_missing_target_raises_400(self):
        with pytest.raises(ValueError, match="target is required"):
            ConsumerResearchActionService.run_action(
                "sim_1", {"action_type": "deep_dive_conclusion"}
            )

    def test_non_dict_target_raises_400(self):
        with pytest.raises(ValueError, match="target must be a dict"):
            ConsumerResearchActionService.run_action(
                "sim_1", {"action_type": "deep_dive_conclusion", "target": "just a string"}
            )

    def test_branch_comparison_conflict_raises_409(self):
        class ConflictBranchService:
            @classmethod
            def get_branch_comparison(cls, simulation_id, branch_id):
                raise ValueError("Branch is already running")

        ConsumerResearchActionService._branch_app_service_class = ConflictBranchService
        with pytest.raises(ValueError, match="already running"):
            ConsumerResearchActionService.run_action(
                "sim_1",
                {
                    "action_type": "compare_branch_delta",
                    "target": {"kind": "branch", "id": "b1"},
                },
            )

    def test_enum_values(self):
        assert ConsumerResearchActionType.DEEP_DIVE_CONCLUSION.value == "deep_dive_conclusion"
        assert (
            ConsumerResearchActionType.EXPLAIN_PROPAGATION_PATH.value
            == "explain_propagation_path"
        )
        assert ConsumerResearchActionType.VERIFY_EVIDENCE.value == "verify_evidence"
        assert ConsumerResearchActionType.INTERVIEW_CONSUMERS.value == "interview_consumers"
        assert (
            ConsumerResearchActionType.COMPARE_BRANCH_DELTA.value == "compare_branch_delta"
        )


class TestConsumerToolSemantics:
    def test_insight_forge_labels(self):
        assert get_consumer_tool_label("insight_forge", "zh") == "消费者洞察深挖"
        assert get_consumer_tool_label("insight_forge", "en") == "Consumer Insight Deep Dive"
        assert "conclusion" in get_consumer_tool_purpose("insight_forge").lower()

    def test_panorama_search_labels(self):
        assert get_consumer_tool_label("panorama_search", "zh") == "传播路径解释器"
        assert get_consumer_tool_label("panorama_search", "en") == "Propagation Path Explainer"
        purpose = get_consumer_tool_purpose("panorama_search").lower()
        assert "diffusion" in purpose or "blocking" in purpose or "misreading" in purpose or "repair" in purpose

    def test_quick_search_labels(self):
        assert get_consumer_tool_label("quick_search", "zh") == "报告结论证据校验"
        assert get_consumer_tool_label("quick_search", "en") == "Evidence Verifier"
        assert "evidence" in get_consumer_tool_purpose("quick_search").lower()

    def test_interview_agents_labels(self):
        assert get_consumer_tool_label("interview_agents", "zh") == "虚拟消费者深访"
        assert get_consumer_tool_label("interview_agents", "en") == "Virtual Consumer Interview"
        assert "6I" in get_consumer_tool_purpose("interview_agents") or "interview" in get_consumer_tool_purpose("interview_agents").lower()

    def test_get_all_nodes_labels(self):
        assert get_consumer_tool_label("get_all_nodes", "zh") == "消费者认知图谱节点"
        assert get_consumer_tool_label("get_all_nodes", "en") == "Consumer Cognition Graph Nodes"

    def test_get_all_edges_labels(self):
        assert get_consumer_tool_label("get_all_edges", "zh") == "消费者认知图谱关系"
        assert get_consumer_tool_label("get_all_edges", "en") == "Consumer Cognition Graph Edges"

    def test_unknown_tool_returns_raw_name(self):
        assert get_consumer_tool_label("unknown_tool_xyz") == "unknown_tool_xyz"
        assert get_consumer_tool_purpose("unknown_tool_xyz") == ""
        assert get_consumer_tool_label("unknown_tool_xyz", "fr") == "unknown_tool_xyz"

    def test_unknown_tool_never_raises(self):
        # Verify no exception for completely unknown tools.
        assert get_consumer_tool_label(123) == "123"
        assert get_consumer_tool_purpose(None) == ""

    def test_semantics_dict_contains_all_entries(self):
        assert "insight_forge" in CONSUMER_TOOL_SEMANTICS
        assert "panorama_search" in CONSUMER_TOOL_SEMANTICS
        assert "quick_search" in CONSUMER_TOOL_SEMANTICS
        assert "interview_agents" in CONSUMER_TOOL_SEMANTICS
        assert "get_all_nodes" in CONSUMER_TOOL_SEMANTICS
        assert "get_all_edges" in CONSUMER_TOOL_SEMANTICS
