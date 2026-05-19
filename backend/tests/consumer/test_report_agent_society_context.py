import json

from app.config import Config
from app.services.report_agent import ReportAgent
from app.services.consumer.models import ResearchFinding, ResearchSnapshot
from app.services.consumer.project_research_persistence import (
    persist_findings,
    persist_snapshot,
)


def test_consumer_report_context_supports_society_only_artifacts(tmp_path, monkeypatch):
    uploads_dir = tmp_path / "uploads"
    simulations_dir = uploads_dir / "simulations"
    simulation_id = "sim_society_only"
    society_dir = simulations_dir / simulation_id / "society"
    society_dir.mkdir(parents=True)

    monkeypatch.setattr(Config, "UPLOAD_FOLDER", str(uploads_dir))
    monkeypatch.setattr(Config, "OASIS_SIMULATION_DATA_DIR", str(simulations_dir))

    (society_dir / "society_config.json").write_text(
        json.dumps(
            {
                "mode": "standard",
                "llm_budget_used": 2,
                "reasoning_backend_counts": {"llm": 2, "rules": 1},
                "llm_invoked_count": 2,
                "reasoning_calibration_status": "golden_case_passed",
            }
        ),
        encoding="utf-8",
    )
    (society_dir / "population.json").write_text(
        json.dumps([{"agent_id": "agent_a"}, {"agent_id": "agent_b"}, {"agent_id": "agent_c"}]),
        encoding="utf-8",
    )
    (society_dir / "society_metrics.json").write_text(
        json.dumps(
            {
                "misread_rate": 0.2,
                "price_resistance_index": 0.1,
                "evidence_demand_rate": 0.1,
                "purchase_intent_delta": 0.4,
            }
        ),
        encoding="utf-8",
    )
    (society_dir / "society_rounds.jsonl").write_text(
        json.dumps(
            {
                "round_index": 0,
                "events": [
                    {
                        "agent_id": "agent_a",
                        "segment": "理性比较型消费者",
                        "consumer_event_type": "FIRST_IMPRESSION",
                        "claim": "7天白4度",
                        "quote": "我第一眼会注意到7天白4度，但还要看场景是否真实。",
                        "quote_metadata": {"source": "llm", "template_generated": False},
                    },
                    {
                        "agent_id": "agent_b",
                        "segment": "价格敏感型消费者",
                        "consumer_event_type": "MISREAD_CLAIM",
                        "claim": "7天白4度",
                        "quote": "7天白4度如果说得太满，我可能会误以为是全场景承诺。",
                        "quote_metadata": {"source": "llm", "template_generated": False},
                    },
                    {
                        "agent_id": "agent_c",
                        "segment": "价格敏感型消费者",
                        "consumer_event_type": "PRICE_RESISTANCE",
                        "claim": "7天白4度",
                        "quote": "如果贵太多，我会先和同类产品仔细比价格。",
                    },
                ],
            }
        )
        + "\n",
        encoding="utf-8",
    )

    agent = ReportAgent(
        graph_id="consumer_graph",
        simulation_id=simulation_id,
        simulation_requirement="Concept test",
        project_type="consumer_test",
    )

    context = agent._build_consumer_report_context()
    outline = agent._build_consumer_outline(context)
    overview_section = agent._render_consumer_section(outline.sections[0].title, context)
    initial_section = agent._render_consumer_section("初始反应", context)

    assert context["society_agents_count"] == 3
    assert context["summary"]["post_propagation_acceptance"]["positive"] == 1 / 3
    assert context["events_count"] == 3
    assert context["representative_voc_quotes"]["resonance"][0]["quote"].startswith("我第一眼")
    assert "7天白4度有第一眼记忆点" in context["top_resonance_points"][0]
    assert "全场景" in context["top_misreads"][0]
    assert overview_section
    assert "No representative quotes" not in initial_section
    assert "我第一眼会注意到7天白4度" in initial_section


def test_consumer_report_context_builds_research_synthesis_from_findings_and_voc():
    agent = ReportAgent(
        graph_id="consumer_graph",
        simulation_id="sim_society_synthesis",
        simulation_requirement="Concept test",
        project_type="consumer_test",
    )

    finding_types = [
        "category_context",
        "competitor_signal",
        "risk_signal",
        "trend_signal",
        "propagation_signal",
    ]
    research_findings = []
    for index in range(53):
        finding_type = finding_types[index % len(finding_types)]
        research_findings.append(
            {
                "finding_id": f"f{index:02d}",
                "finding_type": finding_type,
                "summary": f"{finding_type} insight {index}",
                "evidence_snippets": [f"{finding_type} evidence {index}"],
                "confidence": 0.9 if finding_type == "risk_signal" else 0.7,
                "source_title": f"Source {index}",
                "evidence_preview": f"{finding_type} evidence {index}",
            }
        )

    context = agent._build_consumer_context_from_society_context(
        {
            "society_mode": "standard",
            "society_agents_count": 8,
            "society_rounds_completed": 1,
            "society_metrics": {"misread_rate": 0.2, "price_resistance_index": 0.1},
            "society_event_summary": {"FIRST_IMPRESSION": 4, "MISREAD_CLAIM": 2, "ASK_PROOF": 1},
            "society_top_resonance_points": ["7天白4度有第一眼记忆点"],
            "society_top_risk_points": ["需要检测证明、备案信息和真实用户反馈"],
            "society_top_misreads": ["核心宣称容易被误读为全场景承诺"],
            "society_representative_voc_quotes": {
                "resonance": [
                    {
                        "quote": "我第一眼会注意到7天白4度，但还要看场景是否真实。",
                        "quote_metadata": {"template_generated": False},
                    }
                ],
                "risk": [
                    {
                        "quote": "我想看到7天白4度的检测证明，尤其要解释清楚可信度。",
                        "quote_metadata": {"template_generated": False},
                    }
                ],
                "misread": [
                    {
                        "quote": "7天白4度如果说得太满，我可能会误以为是全场景承诺。",
                        "quote_metadata": {"template_generated": True},
                    }
                ],
            },
            "research_findings": research_findings,
            "enriched_findings": research_findings,
        }
    )

    outline = agent._build_consumer_outline(context)
    overview_section = agent._render_consumer_section("测试概览", context)
    synthesis_section = agent._render_consumer_section("研究发现综合", context)

    assert context["research_findings_count"] == 53
    assert "基于 53 条研究发现" in context["research_insight_summary"]
    assert len(context["research_insight_pillars"]) >= 4
    assert any(pillar["finding_type"] == "risk_signal" for pillar in context["research_insight_pillars"])
    assert any(pillar["evidence_preview"] for pillar in context["research_insight_pillars"])
    assert any(section.title == "研究发现综合" for section in outline.sections)
    assert "研究发现总数：53" in overview_section
    assert "风险信号" in synthesis_section
    assert "我想看到7天白4度的检测证明" in synthesis_section


def test_build_consumer_report_context_prefers_project_research_assets_when_society_rounds_missing(tmp_path, monkeypatch):
    uploads_dir = tmp_path / "uploads"
    simulations_dir = uploads_dir / "simulations"
    project_id = "proj_research_synthesis"
    simulation_id = "sim_society_report"
    society_dir = simulations_dir / simulation_id / "society"
    society_dir.mkdir(parents=True)

    monkeypatch.setattr(Config, "UPLOAD_FOLDER", str(uploads_dir))
    monkeypatch.setattr(Config, "OASIS_SIMULATION_DATA_DIR", str(simulations_dir))

    finding_types = [
        "category_context",
        "competitor_signal",
        "risk_signal",
        "trend_signal",
        "propagation_signal",
    ]
    findings = []
    for index in range(53):
        finding_type = finding_types[index % len(finding_types)]
        findings.append(
            ResearchFinding(
                finding_id=f"f{index:02d}",
                finding_type=finding_type,
                summary=f"{finding_type} insight {index}",
                evidence_snippets=[f"{finding_type} evidence {index}"],
                source_label="brief_background",
                confidence=0.9 if finding_type == "risk_signal" else 0.7,
                source_id=f"src-{index:02d}",
                snippet_id=f"chunk-{index:02d}",
            )
        )

    persist_findings(project_id, findings, upload_root=str(uploads_dir))
    persist_snapshot(
        project_id,
        ResearchSnapshot(
            snapshot_id="snap-1",
            project_id=project_id,
            created_at="2026-05-19T00:00:00Z",
            sources=[],
            documents=[],
            chunks=[],
            findings=findings,
            retrieval_traces=[],
            summary="research snapshot",
        ),
        upload_root=str(uploads_dir),
    )

    (society_dir / "society_config.json").write_text(
        json.dumps(
            {
                "mode": "standard",
                "llm_budget_used": 0,
                "reasoning_backend_counts": {"template": 1},
                "llm_invoked_count": 0,
            }
        ),
        encoding="utf-8",
    )
    (society_dir / "population.json").write_text(json.dumps([{"agent_id": "agent_a"}]), encoding="utf-8")
    (society_dir / "society_metrics.json").write_text(
        json.dumps({"misread_rate": 0.1, "price_resistance_index": 0.1}),
        encoding="utf-8",
    )
    (society_dir / "society_rounds.jsonl").write_text("", encoding="utf-8")

    agent = ReportAgent(
        graph_id="consumer_graph",
        simulation_id=simulation_id,
        simulation_requirement="Concept test",
        project_type="consumer_test",
        project_id=project_id,
    )

    context = agent._build_consumer_report_context()

    assert context["research_findings_count"] == 53
    assert len(context["research_insight_pillars"]) >= 4
    assert "基于 53 条研究发现" in context["research_insight_summary"]
    assert context["research_insight_pillars"][0]["finding_type"] == "category_context"
    assert context["events_count"] == 0
