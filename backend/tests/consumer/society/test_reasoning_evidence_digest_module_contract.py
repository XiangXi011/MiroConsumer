"""Spec contract tests for the standalone reasoning evidence digest module."""

from app.services.consumer.society.population_models import ConsumerSocietyAgent
from app.services.consumer.society.consumer_roles import ConsumerRole
from app.services.consumer.society.reasoning_engine import LayeredSocietyReasoningEngine
from app.services.consumer.society.reasoning_evidence_digest import build_evidence_digest


def test_build_evidence_digest_is_importable_and_normalizes_findings():
    digest = build_evidence_digest([
        {
            "finding_id": "finding-1",
            "summary": "low sugar proof",
            "claim": "legacy claim",
            "evidence_snippets": ["ingredient panel"],
            "supporting_evidence": ["old evidence"],
            "contradicting_evidence": ["aftertaste doubt"],
            "source_label": "public_web",
            "confidence": 0.82,
        }
    ])

    assert digest == [
        {
            "finding_id": "finding-1",
            "claim": "low sugar proof",
            "supporting_evidence": ["ingredient panel"],
            "contradicting_evidence": ["aftertaste doubt"],
            "source_quality": "lane_b",
            "confidence": "high",
        }
    ]


def test_reasoning_engine_delegates_digest_to_standalone_module():
    engine = LayeredSocietyReasoningEngine()
    findings = [
        {"finding_id": "f1", "claim": "claim", "source_id": "lane_a:doc", "confidence": 0.5}
    ]

    assert engine._build_evidence_digest(findings) == build_evidence_digest(findings)


def test_template_reason_marks_quote_as_template_generated():
    agent = ConsumerSocietyAgent(
        agent_id="agent-1",
        parent_persona_id="persona-1",
        layer="core",
        segment="ingredient readers",
        role=ConsumerRole.Skeptic,
    )
    event = LayeredSocietyReasoningEngine()._template_reason(
        agent,
        {"event_id": "event-1", "claim": "low sugar"},
        "llm_deep_reasoning",
        backend="template",
    )

    assert event["quote_metadata"]["template_generated"] is True
    assert event["quote_metadata"]["source"] == "template"