from app.services.consumer.society.consumer_roles import ConsumerRole
from app.services.consumer.society.population_models import ConsumerSocietyAgent
from app.services.consumer.society.reasoning_engine import LayeredSocietyReasoningEngine
import time


class _FakeLLMClient:
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


def test_reasoning_engine_fake_llm_clamps_scores_and_keeps_invalid_event_type(monkeypatch):
    monkeypatch.setenv("SOCIETY_REASONING_BACKEND", "llm")
    monkeypatch.delenv("SOCIETY_DETERMINISTIC_MODE", raising=False)
    fake_client = _FakeLLMClient(
        {
            "consumer_event_type": "NOT_A_CONSUMER_EVENT",
            "quote": "I need stronger proof before I trust this.",
            "trust": 2.4,
            "purchase_intent": -0.2,
            "reasoning_summary": "skeptic asks for better evidence",
        }
    )
    engine = LayeredSocietyReasoningEngine(llm_client_factory=lambda: fake_client)
    base_event = {
        "event_id": "event-1",
        "consumer_event_type": "ASK_PROOF",
        "quote": "base quote",
        "trust": 0.4,
        "purchase_intent": 0.6,
    }

    result = engine.reason(
        agent=_agent(),
        base_event=base_event,
        brief_context={"claims": ["low sugar"]},
        research_findings=[],
        reasoning_mode="llm_deep_reasoning",
    )

    assert fake_client.calls
    assert result["llm_invoked"] is True
    assert result["reasoning_backend"] == "llm"
    assert result["consumer_event_type"] == "ASK_PROOF"
    assert result["quote"] == "I need stronger proof before I trust this."
    assert result["trust"] == 1.0
    assert result["purchase_intent"] == 0.0
    assert result["reasoning_summary"] == "skeptic asks for better evidence"


def test_reasoning_engine_llm_exception_falls_back_to_template(monkeypatch):
    monkeypatch.setenv("SOCIETY_REASONING_BACKEND", "llm")
    monkeypatch.delenv("SOCIETY_DETERMINISTIC_MODE", raising=False)
    fake_client = _FakeLLMClient(exc=RuntimeError("llm unavailable"))
    engine = LayeredSocietyReasoningEngine(llm_client_factory=lambda: fake_client)
    base_event = {
        "event_id": "event-2",
        "consumer_event_type": "ASK_PROOF",
        "claim": "low sugar",
        "trust": 0.4,
        "purchase_intent": 0.6,
    }

    result = engine.reason(
        agent=_agent(),
        base_event=base_event,
        brief_context={"claims": ["low sugar"]},
        research_findings=[],
        reasoning_mode="llm_deep_reasoning",
    )

    assert fake_client.calls
    assert result["llm_invoked"] is False
    assert result["reasoning_backend"] == "template_fallback"
    assert result["reasoning_error"] == "llm unavailable"
    assert result["consumer_event_type"] == "ASK_PROOF"
    assert "ingredient readers / skeptic" in result["quote"]


def test_reasoning_engine_prompt_includes_structured_evidence_digest(monkeypatch):
    monkeypatch.setenv("SOCIETY_REASONING_BACKEND", "llm")
    monkeypatch.delenv("SOCIETY_DETERMINISTIC_MODE", raising=False)
    fake_client = _FakeLLMClient(
        {
            "consumer_event_type": "ASK_PROOF",
            "quote": "The ingredient-source proof matters before I buy.",
            "trust": 0.42,
            "purchase_intent": 0.31,
            "reasoning_summary": "used evidence digest",
        }
    )
    engine = LayeredSocietyReasoningEngine(llm_client_factory=lambda: fake_client)

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
        research_findings=[
            {
                "finding_id": "finding-proof",
                "claim": "low sugar",
                "summary": "Ingredient-source proof reduces skepticism.",
                "supporting_evidence": ["ingredient-source proof from uploaded QA"],
                "contradicting_evidence": ["reviewers doubt sweetener aftertaste"],
                "source_quality": "lane_a",
                "confidence": "high",
            }
        ],
        reasoning_mode="llm_deep_reasoning",
    )

    prompt = " ".join(
        message.get("content", "")
        for message in fake_client.calls[0]["messages"]
    )
    assert "evidence_digest" in prompt
    assert "finding-proof" in prompt
    assert "ingredient-source proof from uploaded QA" in prompt
    assert "reviewers doubt sweetener aftertaste" in prompt
    assert "lane_a" in prompt
    assert "high" in prompt


def test_reasoning_engine_passes_request_timeout_to_llm_client(monkeypatch):
    monkeypatch.setenv("SOCIETY_REASONING_BACKEND", "llm")
    monkeypatch.delenv("SOCIETY_DETERMINISTIC_MODE", raising=False)
    fake_client = _FakeLLMClient(
        {
            "consumer_event_type": "ASK_PROOF",
            "quote": "timeout aware response",
            "trust": 0.5,
            "purchase_intent": 0.4,
        }
    )
    engine = LayeredSocietyReasoningEngine(
        llm_client_factory=lambda: fake_client,
        per_call_timeout_seconds=2,
    )

    engine.reason(
        agent=_agent(),
        base_event={
            "event_id": "event-timeout",
            "consumer_event_type": "ASK_PROOF",
            "claim": "low sugar",
            "trust": 0.4,
            "purchase_intent": 0.6,
        },
        brief_context={"claims": ["low sugar"]},
        research_findings=[],
        reasoning_mode="llm_deep_reasoning",
    )

    assert fake_client.calls[0]["timeout"] == 2


def test_reasoning_engine_per_call_timeout_falls_back(monkeypatch):
    monkeypatch.setenv("SOCIETY_REASONING_BACKEND", "llm")
    monkeypatch.delenv("SOCIETY_DETERMINISTIC_MODE", raising=False)

    class SlowClient:
        def chat_json(self, **kwargs):
            time.sleep(0.2)
            return {"quote": "too late"}

    engine = LayeredSocietyReasoningEngine(
        llm_client_factory=lambda: SlowClient(),
        per_call_timeout_seconds=0.01,
    )

    result = engine.reason(
        agent=_agent(),
        base_event={
            "event_id": "event-timeout-fallback",
            "consumer_event_type": "ASK_PROOF",
            "claim": "low sugar",
            "trust": 0.4,
            "purchase_intent": 0.6,
        },
        brief_context={"claims": ["low sugar"]},
        research_findings=[],
        reasoning_mode="llm_deep_reasoning",
    )

    assert result["reasoning_backend"] == "template_fallback"
    assert result["llm_invoked"] is False
    assert "TimeoutError" in result["reasoning_error"]

def test_reasoning_engine_llm_preserves_segmented_reasoning_fields(monkeypatch):
    monkeypatch.setenv("SOCIETY_REASONING_BACKEND", "llm")
    monkeypatch.delenv("SOCIETY_DETERMINISTIC_MODE", raising=False)
    fake_client = _FakeLLMClient(
        {
            "consumer_event_type": "ASK_PROOF",
            "quote": "I need source proof before I buy.",
            "trust": 0.42,
            "purchase_intent": 0.31,
            "reasoning_summary": "segmented reasoning",
            "perception_reasoning": "Perception: noticed low sugar claim and proof gap.",
            "decision_reasoning": "Decision: skepticism stays high until evidence appears.",
            "expression_reasoning": "Expression: asks for source proof.",
        }
    )
    engine = LayeredSocietyReasoningEngine(llm_client_factory=lambda: fake_client)

    result = engine.reason(
        agent=_agent(),
        base_event={"consumer_event_type": "ASK_PROOF", "claim": "low sugar", "trust": 0.4},
        brief_context={"claims": ["low sugar"]},
        research_findings=[],
        reasoning_mode="llm_deep_reasoning",
    )

    assert result["perception_reasoning"].startswith("Perception:")
    assert result["decision_reasoning"].startswith("Decision:")
    assert result["expression_reasoning"].startswith("Expression:")
    assert result["reasoning_triplets"][0]["input"] == result["perception_reasoning"]
    assert result["quote_metadata"]["template_generated"] is False


def test_reasoning_engine_llm_missing_segments_gets_summary_fallback(monkeypatch):
    monkeypatch.setenv("SOCIETY_REASONING_BACKEND", "llm")
    monkeypatch.delenv("SOCIETY_DETERMINISTIC_MODE", raising=False)
    fake_client = _FakeLLMClient(
        {
            "consumer_event_type": "ASK_PROOF",
            "quote": "The proof is not enough yet.",
            "trust": 0.4,
            "purchase_intent": 0.3,
            "reasoning_summary": "Agent sees a low-sugar claim, weighs missing source evidence, then asks for proof.",
        }
    )
    engine = LayeredSocietyReasoningEngine(llm_client_factory=lambda: fake_client)

    result = engine.reason(
        agent=_agent(),
        base_event={"consumer_event_type": "ASK_PROOF", "claim": "low sugar", "trust": 0.4},
        brief_context={"claims": ["low sugar"]},
        research_findings=[],
        reasoning_mode="llm_deep_reasoning",
    )

    assert result["perception_reasoning"]
    assert result["decision_reasoning"]
    assert result["expression_reasoning"]
    assert "low sugar" in result["perception_reasoning"]
    assert result["reasoning_triplets"][0]["conclusion"] == result["expression_reasoning"]


def test_reasoning_engine_template_reasoning_sets_segments_and_template_metadata(monkeypatch):
    monkeypatch.setenv("SOCIETY_REASONING_BACKEND", "template")
    monkeypatch.delenv("SOCIETY_DETERMINISTIC_MODE", raising=False)
    engine = LayeredSocietyReasoningEngine()

    result = engine.reason(
        agent=_agent(),
        base_event={"consumer_event_type": "ASK_PROOF", "claim": "low sugar", "trust": 0.4},
        brief_context={"claims": ["low sugar"]},
        research_findings=[],
        reasoning_mode="llm_deep_reasoning",
    )

    assert result["quote_metadata"] == {"template_generated": True, "source": "template"}
    assert result["perception_reasoning"]
    assert result["decision_reasoning"]
    assert result["expression_reasoning"]
    assert result["reasoning_triplets"][0]["input"] == result["perception_reasoning"]
