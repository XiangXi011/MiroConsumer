from app.services.consumer.society.consumer_roles import ConsumerRole
from app.services.consumer.society.population_models import ConsumerSocietyAgent
from app.services.consumer.society.reasoning_engine import LayeredSocietyReasoningEngine


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
