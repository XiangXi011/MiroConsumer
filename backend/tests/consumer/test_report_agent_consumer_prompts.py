"""Tests for consumer prompt selection in ReportAgent (Phase 6F)."""

from unittest.mock import MagicMock, patch

from app.services.report_agent import (
    CONSUMER_CHAT_SYSTEM_PROMPT_TEMPLATE,
    CONSUMER_PLAN_SYSTEM_PROMPT,
    CONSUMER_PLAN_USER_PROMPT_TEMPLATE,
    CONSUMER_SECTION_SYSTEM_PROMPT_TEMPLATE,
    CONSUMER_SECTION_USER_PROMPT_TEMPLATE,
    PLAN_SYSTEM_PROMPT,
    PLAN_USER_PROMPT_TEMPLATE,
    SECTION_SYSTEM_PROMPT_TEMPLATE,
    SECTION_USER_PROMPT_TEMPLATE,
    CHAT_SYSTEM_PROMPT_TEMPLATE,
    ReportAgent,
)


class TestConsumerPromptConstants:
    def test_consumer_plan_system_prompt_identifies_agent(self):
        assert "消费者研究总监 Agent" in CONSUMER_PLAN_SYSTEM_PROMPT

    def test_consumer_section_system_prompt_identifies_agent(self):
        assert "消费者研究总监 Agent" in CONSUMER_SECTION_SYSTEM_PROMPT_TEMPLATE

    def test_consumer_chat_system_prompt_identifies_agent(self):
        assert "消费者研究总监 Agent" in CONSUMER_CHAT_SYSTEM_PROMPT_TEMPLATE

    def test_consumer_prompts_also_have_english_agent_name(self):
        assert "Consumer Research Director Agent" in CONSUMER_PLAN_SYSTEM_PROMPT
        assert "Consumer Research Director Agent" in CONSUMER_SECTION_SYSTEM_PROMPT_TEMPLATE
        assert "Consumer Research Director Agent" in CONSUMER_CHAT_SYSTEM_PROMPT_TEMPLATE

    def test_consumer_prompts_use_consumer_research_wording(self):
        assert "消费者" in CONSUMER_PLAN_SYSTEM_PROMPT
        assert "消费者" in CONSUMER_SECTION_SYSTEM_PROMPT_TEMPLATE
        assert "消费者" in CONSUMER_CHAT_SYSTEM_PROMPT_TEMPLATE
        assert "消费者" in CONSUMER_PLAN_USER_PROMPT_TEMPLATE
        assert "消费者" in CONSUMER_SECTION_USER_PROMPT_TEMPLATE

    def test_consumer_prompts_preserve_raw_tool_names(self):
        assert "insight_forge" in CONSUMER_SECTION_SYSTEM_PROMPT_TEMPLATE
        assert "panorama_search" in CONSUMER_SECTION_SYSTEM_PROMPT_TEMPLATE
        assert "quick_search" in CONSUMER_SECTION_SYSTEM_PROMPT_TEMPLATE
        assert "interview_agents" in CONSUMER_SECTION_SYSTEM_PROMPT_TEMPLATE

    def test_consumer_prompts_forbid_old_forecast_wording(self):
        """Consumer prompts must not describe outputs as old future prediction reports."""
        # Forbidden words/phrases from old future-prediction framing.
        forbidden = ["预测", "预演"]
        prompts = [
            CONSUMER_PLAN_SYSTEM_PROMPT,
            CONSUMER_PLAN_USER_PROMPT_TEMPLATE,
            CONSUMER_SECTION_SYSTEM_PROMPT_TEMPLATE,
            CONSUMER_SECTION_USER_PROMPT_TEMPLATE,
            CONSUMER_CHAT_SYSTEM_PROMPT_TEMPLATE,
        ]
        for prompt in prompts:
            for word in forbidden:
                assert word not in prompt, f"Forbidden word '{word}' found in prompt"

    def test_consumer_prompts_focus_on_reactions_and_misreading(self):
        """Consumer prompts must focus on reactions, selling points, misreading, trust."""
        prompts = [
            CONSUMER_PLAN_SYSTEM_PROMPT,
            CONSUMER_PLAN_USER_PROMPT_TEMPLATE,
            CONSUMER_SECTION_SYSTEM_PROMPT_TEMPLATE,
            CONSUMER_SECTION_USER_PROMPT_TEMPLATE,
            CONSUMER_CHAT_SYSTEM_PROMPT_TEMPLATE,
        ]
        required_topics = [
            "消费者反应",
            "可传播卖点",
            "质疑",
            "误读",
            "信任衰减",
            "信任修复",
            "证据",
            "What-if",
        ]
        combined = "".join(prompts)
        for topic in required_topics:
            assert topic in combined, f"Required topic '{topic}' missing from consumer prompts"

    def test_consumer_prompts_include_phase6h_channel_outputs(self):
        """Phase 6H reports must instruct ReportAgent to use channel propagation context."""
        combined = "\n".join([
            CONSUMER_PLAN_SYSTEM_PROMPT,
            CONSUMER_PLAN_USER_PROMPT_TEMPLATE,
            CONSUMER_SECTION_SYSTEM_PROMPT_TEMPLATE,
            CONSUMER_CHAT_SYSTEM_PROMPT_TEMPLATE,
        ])
        for topic in [
            "best_launch_channel",
            "highest_misread_channel",
            "highest_evidence_demand_channel",
            "highest_price_resistance_channel",
            "KOL",
            "expert_endorsement_channel",
        ]:
            assert topic in combined, f"Required channel topic '{topic}' missing"


class TestReportAgentPromptSelection:
    def _make_agent(self, project_type="default"):
        return ReportAgent(
            graph_id="g1",
            simulation_id="sim_1",
            simulation_requirement="test req",
            llm_client=MagicMock(),
            zep_tools=MagicMock(),
            project_type=project_type,
        )

    @patch.object(ReportAgent, "_get_tools_description", return_value="tools")
    def test_default_project_uses_legacy_plan_prompt(self, _mock_tools):
        agent = self._make_agent("default")
        agent.llm.chat_json = MagicMock(return_value={
            "title": "T", "summary": "S", "sections": []
        })
        agent.zep_tools.get_simulation_context.return_value = {}
        agent.plan_outline()
        call_args = agent.llm.chat_json.call_args
        system_msg = call_args.kwargs["messages"][0]["content"]
        assert PLAN_SYSTEM_PROMPT in system_msg

    @patch.object(ReportAgent, "_get_tools_description", return_value="tools")
    def test_consumer_test_uses_consumer_plan_prompt(self, _mock_tools):
        agent = self._make_agent("consumer_test")
        agent.llm.chat_json = MagicMock(return_value={
            "title": "T", "summary": "S", "sections": []
        })
        agent.zep_tools.get_simulation_context.return_value = {}
        agent.plan_outline()
        call_args = agent.llm.chat_json.call_args
        system_msg = call_args.kwargs["messages"][0]["content"]
        assert CONSUMER_PLAN_SYSTEM_PROMPT in system_msg
        user_msg = call_args.kwargs["messages"][1]["content"]
        assert "消费者研究场景" in user_msg

    @patch.object(ReportAgent, "_get_tools_description", return_value="tools")
    def test_default_project_uses_legacy_section_prompt(self, _mock_tools):
        agent = self._make_agent("default")
        agent.llm.chat = MagicMock(return_value="Final Answer: content")
        from app.services.report_agent import ReportSection, ReportOutline
        section = ReportSection(title="Test")
        outline = ReportOutline(title="O", summary="S", sections=[section])
        agent._generate_section_react(section, outline, [])
        call_args = agent.llm.chat.call_args
        system_msg = call_args.kwargs["messages"][0]["content"]
        assert SECTION_SYSTEM_PROMPT_TEMPLATE.split("{")[0] in system_msg

    @patch.object(ReportAgent, "_get_tools_description", return_value="tools")
    def test_consumer_test_uses_consumer_section_prompt(self, _mock_tools):
        agent = self._make_agent("consumer_test")
        agent.llm.chat = MagicMock(return_value="Final Answer: content")
        from app.services.report_agent import ReportSection, ReportOutline
        section = ReportSection(title="Test")
        outline = ReportOutline(title="O", summary="S", sections=[section])
        agent._generate_section_react(section, outline, [])
        call_args = agent.llm.chat.call_args
        system_msg = call_args.kwargs["messages"][0]["content"]
        assert "消费者研究总监 Agent" in system_msg
        user_msg = call_args.kwargs["messages"][1]["content"]
        assert "消费者研究章节" in user_msg

    def test_default_project_uses_legacy_chat_prompt(self):
        agent = self._make_agent("default")
        agent.llm.chat = MagicMock(return_value="hello")
        with patch.object(
            agent, "_get_tools_description", return_value="tools"
        ), patch(
            "app.services.report_agent.ReportManager.get_report_by_simulation",
            return_value=None,
        ):
            agent.chat("hi")
        call_args = agent.llm.chat.call_args
        system_msg = call_args.kwargs["messages"][0]["content"]
        assert CHAT_SYSTEM_PROMPT_TEMPLATE.split("{")[0] in system_msg

    def test_consumer_test_uses_consumer_chat_prompt(self):
        agent = self._make_agent("consumer_test")
        agent.llm.chat = MagicMock(return_value="hello")
        with patch.object(
            agent, "_get_tools_description", return_value="tools"
        ), patch(
            "app.services.report_agent.ReportManager.get_report_by_simulation",
            return_value=None,
        ):
            agent.chat("hi")
        call_args = agent.llm.chat.call_args
        system_msg = call_args.kwargs["messages"][0]["content"]
        assert "消费者研究总监 Agent" in system_msg
        assert "消费者研究报告" in system_msg

    def test_legacy_prompts_not_removed(self):
        # Ensure legacy/default prompts still exist.
        assert PLAN_SYSTEM_PROMPT
        assert PLAN_USER_PROMPT_TEMPLATE
        assert SECTION_SYSTEM_PROMPT_TEMPLATE
        assert SECTION_USER_PROMPT_TEMPLATE
        assert CHAT_SYSTEM_PROMPT_TEMPLATE


def test_format_quotes_prioritizes_llm_quotes_and_marks_template_sources():
    agent = ReportAgent(
        graph_id="g1",
        simulation_id="sim_1",
        simulation_requirement="test req",
        llm_client=MagicMock(),
        zep_tools=MagicMock(),
        project_type="consumer_test",
    )

    rendered = agent._format_quotes([
        {
            "quote": "Template quote",
            "engagement": 2,
            "quote_metadata": {"template_generated": True},
        },
        {
            "quote": "LLM quote",
            "engagement": 5,
            "quote_metadata": {"template_generated": False},
        },
        {"quote": "Legacy quote without metadata", "engagement": 1},
    ])

    lines = rendered.splitlines()
    assert "LLM生成 1" in lines[0]
    assert "模拟生成 2" in lines[0]
    assert "LLM quote" in lines[1]
    assert "[模拟生成，非LLM推理]" not in lines[1]
    assert "Template quote" in lines[2]
    assert "[模拟生成，非LLM推理]" in lines[2]
    assert "Legacy quote without metadata" in lines[3]
    assert "[模拟生成，非LLM推理]" in lines[3]


def test_format_quotes_uses_chinese_empty_state():
    agent = ReportAgent(
        graph_id="g1",
        simulation_id="sim_1",
        simulation_requirement="test req",
        llm_client=MagicMock(),
        zep_tools=MagicMock(),
        project_type="consumer_test",
    )

    rendered = agent._format_quotes([])

    assert rendered == "- 暂无代表性原声"
    assert "No representative quotes" not in rendered


def test_consumer_report_section_uses_llm_when_feature_flag_enabled(monkeypatch):
    from app.services.report_agent import ReportOutline, ReportSection

    agent = ReportAgent(
        graph_id="g1",
        simulation_id="sim_1",
        simulation_requirement="test req",
        llm_client=MagicMock(),
        zep_tools=MagicMock(),
        project_type="consumer_test",
    )
    section = ReportSection(title="Section")
    outline = ReportOutline(title="Report", summary="Summary", sections=[section])
    monkeypatch.setenv("CONSUMER_REPORT_LLM_ENABLED", "true")
    agent._generate_section_react = MagicMock(return_value="LLM generated section")
    agent._render_consumer_section = MagicMock(return_value="Template section")

    result = agent._render_consumer_section_with_optional_llm(
        section=section,
        outline=outline,
        context={"task_type": "concept_test"},
        previous_sections=[],
    )

    assert result == "LLM generated section"
    agent._generate_section_react.assert_called_once()
    agent._render_consumer_section.assert_not_called()


def test_consumer_report_section_falls_back_to_template_when_llm_fails(monkeypatch):
    from app.services.report_agent import ReportOutline, ReportSection

    agent = ReportAgent(
        graph_id="g1",
        simulation_id="sim_1",
        simulation_requirement="test req",
        llm_client=MagicMock(),
        zep_tools=MagicMock(),
        project_type="consumer_test",
    )
    section = ReportSection(title="Section")
    outline = ReportOutline(title="Report", summary="Summary", sections=[section])
    monkeypatch.setenv("CONSUMER_REPORT_LLM_ENABLED", "true")
    agent._generate_section_react = MagicMock(side_effect=RuntimeError("llm down"))
    agent._render_consumer_section = MagicMock(return_value="Template section")

    result = agent._render_consumer_section_with_optional_llm(
        section=section,
        outline=outline,
        context={"task_type": "concept_test"},
        previous_sections=[],
    )

    assert result == "Template section"
    agent._render_consumer_section.assert_called_once_with("Section", {"task_type": "concept_test"})


def test_consumer_report_section_uses_template_when_feature_flag_disabled(monkeypatch):
    from app.services.report_agent import ReportOutline, ReportSection

    agent = ReportAgent(
        graph_id="g1",
        simulation_id="sim_1",
        simulation_requirement="test req",
        llm_client=MagicMock(),
        zep_tools=MagicMock(),
        project_type="consumer_test",
    )
    section = ReportSection(title="Section")
    outline = ReportOutline(title="Report", summary="Summary", sections=[section])
    monkeypatch.delenv("CONSUMER_REPORT_LLM_ENABLED", raising=False)
    agent._generate_section_react = MagicMock(return_value="LLM generated section")
    agent._render_consumer_section = MagicMock(return_value="Template section")

    result = agent._render_consumer_section_with_optional_llm(
        section=section,
        outline=outline,
        context={"task_type": "concept_test"},
        previous_sections=[],
    )

    assert result == "Template section"
    agent._generate_section_react.assert_not_called()
