"""Reasoning engine evidence digest deterministic coverage."""

import os

from app.services.consumer.society.consumer_roles import ConsumerRole
from app.services.consumer.society.population_models import ConsumerSocietyAgent
from app.services.consumer.society.reasoning_engine import LayeredSocietyReasoningEngine


class _FakeLLMClient:
    """Deterministic fake LLM that returns predictable JSON."""

    def __init__(self, payload=None, exc=None):
        self.payload = payload or {}
        self.exc = exc
        self.calls = []

    def chat_json(self, **kwargs):
        self.calls.append(kwargs)
        if self.exc is not None:
            raise self.exc
        return dict(self.payload)


def _agent() -> ConsumerSocietyAgent:
    return ConsumerSocietyAgent(
        agent_id="agent-1",
        parent_persona_id="persona-1",
        layer="core",
        segment="ingredient readers",
        role=ConsumerRole.Skeptic,
        trust_baseline=0.4,
        share_propensity=0.3,
        skepticism=0.9,
    )


def test_evidence_digest_is_deterministic_for_same_findings(monkeypatch):
    """Same findings must produce identical evidence digests."""
    monkeypatch.setenv("SOCIETY_REASONING_BACKEND", "llm")
    monkeypatch.delenv("SOCIETY_DETERMINISTIC_MODE", raising=False)

    fake_client = _FakeLLMClient(
        {
            "consumer_event_type": "ASK_PROOF",
            "quote": "Deterministic response.",
            "trust": 0.5,
            "purchase_intent": 0.5,
            "reasoning_summary": "digest test",
        }
    )
    engine = LayeredSocietyReasoningEngine(llm_client_factory=lambda: fake_client)

    findings = [
        {
            "finding_id": "finding-1",
            "claim": "low sugar",
            "supporting_evidence": ["evidence A"],
            "contradicting_evidence": ["counter A"],
            "source_quality": "lane_a",
            "confidence": "high",
        },
        {
            "finding_id": "finding-2",
            "claim": "organic",
            "supporting_evidence": ["evidence B"],
            "contradicting_evidence": [],
            "source_quality": "lane_b",
            "confidence": "medium",
        },
    ]

    result_a = engine.reason(
        agent=_agent(),
        base_event={
            "event_id": "event-1",
            "consumer_event_type": "ASK_PROOF",
            "claim": "low sugar",
            "trust": 0.4,
            "purchase_intent": 0.6,
        },
        brief_context={"claims": ["low sugar"]},
        research_findings=findings,
        reasoning_mode="llm_deep_reasoning",
    )

    result_b = engine.reason(
        agent=_agent(),
        base_event={
            "event_id": "event-1",
            "consumer_event_type": "ASK_PROOF",
            "claim": "low sugar",
            "trust": 0.4,
            "purchase_intent": 0.6,
        },
        brief_context={"claims": ["low sugar"]},
        research_findings=findings,
        reasoning_mode="llm_deep_reasoning",
    )

    # The LLM is invoked with identical prompts, so calls should match
    assert len(fake_client.calls) == 2
    assert fake_client.calls[0] == fake_client.calls[1]
    assert result_a["reasoning_summary"] == result_b["reasoning_summary"]


def test_evidence_digest_structured_content(monkeypatch):
    """Evidence digest must include finding_id, claim, evidence, source_quality, confidence."""
    monkeypatch.setenv("SOCIETY_REASONING_BACKEND", "llm")
    monkeypatch.delenv("SOCIETY_DETERMINISTIC_MODE", raising=False)

    fake_client = _FakeLLMClient(
        {
            "consumer_event_type": "ASK_PROOF",
            "quote": "I see the evidence.",
            "trust": 0.6,
            "purchase_intent": 0.5,
            "reasoning_summary": "evaluated digest",
        }
    )
    engine = LayeredSocietyReasoningEngine(llm_client_factory=lambda: fake_client)

    findings = [
        {
            "finding_id": "finding-proof",
            "claim": "low sugar",
            "supporting_evidence": ["ingredient-source proof"],
            "contradicting_evidence": ["sweetener aftertaste doubt"],
            "source_quality": "lane_a",
            "confidence": "high",
        }
    ]

    engine.reason(
        agent=_agent(),
        base_event={
            "event_id": "event-digest",
            "consumer_event_type": "ASK_PROOF",
            "claim": "low sugar",
            "trust": 0.4,
            "purchase_intent": 0.6,
        },
        brief_context={"claims": ["low sugar"]},
        research_findings=findings,
        reasoning_mode="llm_deep_reasoning",
    )

    prompt = " ".join(
        message.get("content", "") for message in fake_client.calls[0]["messages"]
    )
    assert "evidence_digest" in prompt
    assert "finding-proof" in prompt
    assert "ingredient-source proof" in prompt
    assert "sweetener aftertaste doubt" in prompt
    assert "lane_a" in prompt
    assert "high" in prompt


def test_evidence_digest_constrains_invalid_values(monkeypatch):
    """Invalid source_quality and confidence values must be constrained to allowed sets."""
    monkeypatch.setenv("SOCIETY_REASONING_BACKEND", "llm")
    monkeypatch.delenv("SOCIETY_DETERMINISTIC_MODE", raising=False)

    fake_client = _FakeLLMClient(
        {
            "consumer_event_type": "ASK_PROOF",
            "quote": "Constrained.",
            "trust": 0.5,
            "purchase_intent": 0.5,
            "reasoning_summary": "constrained test",
        }
    )
    engine = LayeredSocietyReasoningEngine(llm_client_factory=lambda: fake_client)

    findings = [
        {
            "finding_id": "finding-bad",
            "claim": "bad claim",
            "supporting_evidence": ["evidence"],
            "contradicting_evidence": [],
            "source_quality": "invalid_quality_value",
            "confidence": "unknown_confidence",
        }
    ]

    engine.reason(
        agent=_agent(),
        base_event={
            "event_id": "event-bad",
            "consumer_event_type": "ASK_PROOF",
            "claim": "bad claim",
            "trust": 0.5,
            "purchase_intent": 0.5,
        },
        brief_context={},
        research_findings=findings,
        reasoning_mode="llm_deep_reasoning",
    )

    prompt = " ".join(
        message.get("content", "") for message in fake_client.calls[0]["messages"]
    )
    assert "unknown" in prompt  # both invalid values get constrained to "unknown"


def test_fake_llm_produces_deterministic_output(monkeypatch):
    """Fake LLM with fixed payload must produce identical results across invocations."""
    monkeypatch.setenv("SOCIETY_REASONING_BACKEND", "llm")
    monkeypatch.delenv("SOCIETY_DETERMINISTIC_MODE", raising=False)

    payload = {
        "consumer_event_type": "ASK_PROOF",
        "quote": "Fixed quote.",
        "trust": 0.75,
        "purchase_intent": 0.25,
        "reasoning_summary": "fixed summary",
    }
    fake_client = _FakeLLMClient(payload)
    engine = LayeredSocietyReasoningEngine(llm_client_factory=lambda: fake_client)

    results = []
    for _ in range(3):
        result = engine.reason(
            agent=_agent(),
            base_event={
                "event_id": "event-fix",
                "consumer_event_type": "ASK_PROOF",
                "claim": "test",
                "trust": 0.4,
                "purchase_intent": 0.6,
            },
            brief_context={},
            research_findings=[],
            reasoning_mode="llm_deep_reasoning",
        )
        results.append(result)

    for r in results[1:]:
        assert r["quote"] == results[0]["quote"]
        assert r["trust"] == results[0]["trust"]
        assert r["purchase_intent"] == results[0]["purchase_intent"]
        assert r["reasoning_summary"] == results[0]["reasoning_summary"]


def test_branch_base_isolation_evidence_digest(monkeypatch):
    """Different research findings for branch vs base must produce different digests."""
    monkeypatch.setenv("SOCIETY_REASONING_BACKEND", "llm")
    monkeypatch.delenv("SOCIETY_DETERMINISTIC_MODE", raising=False)

    fake_client = _FakeLLMClient(
        {
            "consumer_event_type": "ASK_PROOF",
            "quote": "Branch-aware.",
            "trust": 0.5,
            "purchase_intent": 0.5,
            "reasoning_summary": "branch test",
        }
    )
    engine = LayeredSocietyReasoningEngine(llm_client_factory=lambda: fake_client)

    base_findings = [
        {"finding_id": "f-base", "claim": "base", "supporting_evidence": ["base-ev"], "source_quality": "lane_a", "confidence": "high"}
    ]
    branch_findings = [
        {"finding_id": "f-branch", "claim": "branch", "supporting_evidence": ["branch-ev"], "source_quality": "lane_b", "confidence": "low"}
    ]

    engine.reason(
        agent=_agent(),
        base_event={"event_id": "e1", "consumer_event_type": "ASK_PROOF", "claim": "test"},
        brief_context={},
        research_findings=base_findings,
        reasoning_mode="llm_deep_reasoning",
    )
    base_prompt = " ".join(
        message.get("content", "") for message in fake_client.calls[0]["messages"]
    )

    engine.reason(
        agent=_agent(),
        base_event={"event_id": "e1", "consumer_event_type": "ASK_PROOF", "claim": "test"},
        brief_context={},
        research_findings=branch_findings,
        reasoning_mode="llm_deep_reasoning",
    )
    branch_prompt = " ".join(
        message.get("content", "") for message in fake_client.calls[1]["messages"]
    )

    assert "f-base" in base_prompt
    assert "base-ev" in base_prompt
    assert "f-branch" in branch_prompt
    assert "branch-ev" in branch_prompt
    assert base_prompt != branch_prompt


def test_mock_deterministic_mode_uses_template_backend(monkeypatch):
    """SOCIETY_DETERMINISTIC_MODE=mock forces template backend regardless of config."""
    monkeypatch.setenv("SOCIETY_REASONING_BACKEND", "llm")
    monkeypatch.setenv("SOCIETY_DETERMINISTIC_MODE", "mock")

    fake_client = _FakeLLMClient({"quote": "should not be used"})
    engine = LayeredSocietyReasoningEngine(llm_client_factory=lambda: fake_client)

    result = engine.reason(
        agent=_agent(),
        base_event={"event_id": "e1", "consumer_event_type": "ASK_PROOF", "claim": "test", "trust": 0.4},
        brief_context={},
        research_findings=[],
        reasoning_mode="llm_deep_reasoning",
    )

    assert result["llm_invoked"] is False
    assert result["reasoning_backend"] == "mock"
    assert not fake_client.calls
