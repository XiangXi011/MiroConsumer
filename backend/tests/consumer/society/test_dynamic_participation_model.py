from unittest.mock import MagicMock

from app.services.consumer.event_ontology import ConsumerEventType
from app.services.consumer.society.agent_step_executor import AgentStepExecutor
from app.services.consumer.society.consumer_roles import ConsumerRole
from app.services.consumer.society.dynamic_participation import DynamicParticipationModel
from app.services.consumer.society.population_models import ConsumerSocietyAgent, ConsumerSocietyRunConfig
from app.services.consumer.society.round_scheduler import RoundScheduler


class FakeEventMapper:
    def __init__(self):
        self.calls = []

    def map_agent_event(self, *, agent, round_index, visible_claims, previous_events, brief_context, research_findings):
        self.calls.append(agent.agent_id)
        return {
            "event_id": f"{agent.agent_id}:r{round_index}:FIRST_IMPRESSION",
            "round_index": round_index,
            "agent_id": agent.agent_id,
            "segment": agent.segment,
            "role": agent.role.value,
            "layer": agent.layer,
            "consumer_event_type": ConsumerEventType.FIRST_IMPRESSION.value,
            "event_type": ConsumerEventType.FIRST_IMPRESSION.value,
            "channel": ConsumerEventType.FIRST_IMPRESSION.value,
            "claim": "low sugar claim",
            "trust": 0.5,
            "purchase_intent": 0.5,
            "quote": "first impression",
        }


class FakeReasoningEngine:
    def reason(self, *, agent, base_event, brief_context, research_findings, reasoning_mode):
        event = dict(base_event)
        event["reasoning_backend"] = "llm"
        event["reasoning_method"] = reasoning_mode
        event["llm_invoked"] = True
        return event


class FakeBudget:
    used_llm_calls = 0

    def record_llm_call(self, layer):
        self.used_llm_calls += 1
        return True


def _agent(agent_id, *, engagement, attention=None, segment="segment"):
    return ConsumerSocietyAgent(
        agent_id=agent_id,
        parent_persona_id=agent_id,
        layer="expanded",
        segment=segment,
        role=ConsumerRole.Lurker,
        traits={
            "attention_drivers": attention or [],
            "risk_sensitivities": [],
            "engagement_level": engagement,
        },
        share_propensity=engagement,
        evidence_sensitivity=engagement,
        skepticism=1.0 - engagement,
        state={
            "trust": 0.5,
            "purchase_intent": 0.5,
            "engagement_level": engagement,
        },
    )


def test_dynamic_participation_scores_topic_fit_fatigue_and_neighbor_activity():
    model = DynamicParticipationModel(seed=11)
    high = _agent("high", engagement=0.95, attention=["low sugar", "nutrition"], segment="fans")
    low = _agent("low", engagement=0.05, attention=["premium service"], segment="quiet")
    previous_events = [
        {"agent_id": "low", "segment": "quiet", "round_index": 0, "consumer_event_type": "FIRST_IMPRESSION"},
        {"agent_id": "low", "segment": "quiet", "round_index": 1, "consumer_event_type": "ASK_PROOF"},
        {"agent_id": "neighbor", "segment": "fans", "round_index": 1, "consumer_event_type": "SHARE_TO_CHANNEL"},
    ]

    high_decision = model.decide(
        agent=high,
        round_index=2,
        claims=["low sugar nutrition"],
        brief_context={"product_category": "healthy snack"},
        previous_events=previous_events,
    )
    low_decision = model.decide(
        agent=low,
        round_index=2,
        claims=["low sugar nutrition"],
        brief_context={"product_category": "healthy snack"},
        previous_events=previous_events,
    )

    assert high_decision.participation_probability > low_decision.participation_probability
    assert high_decision.topic_relevance > low_decision.topic_relevance
    assert high_decision.neighbor_activity > low_decision.neighbor_activity
    assert low_decision.fatigue > high_decision.fatigue


def test_round_scheduler_records_skipped_participation_without_invoking_reasoning():
    mapper = FakeEventMapper()
    executor = AgentStepExecutor(mapper, FakeReasoningEngine(), MagicMock(), "sim")
    active = _agent("active", engagement=0.95, attention=["low sugar", "nutrition"], segment="fans")
    quiet = _agent("quiet", engagement=0.0, attention=["premium service"], segment="quiet")
    config = ConsumerSocietyRunConfig(
        mode="standard",
        core_persona_count=0,
        expanded_persona_count=2,
        shadow_agent_count=0,
        max_rounds=2,
        random_seed=3,
        llm_budget_limit=2,
    )
    scheduler = RoundScheduler(executor, [active, quiet], config)
    previous_events = [
        {"agent_id": "quiet", "segment": "quiet", "round_index": 0, "consumer_event_type": "FIRST_IMPRESSION"},
        {"agent_id": "quiet", "segment": "quiet", "round_index": 1, "consumer_event_type": "ASK_PROOF"},
        {"agent_id": "neighbor", "segment": "fans", "round_index": 1, "consumer_event_type": "SHARE_TO_CHANNEL"},
    ]
    counters = {
        "completed_agents": 0,
        "failed_count": 0,
        "template_fallback_count": 0,
        "llm_invoked_count": 0,
        "rules_count": 0,
    }

    events, traces = scheduler.run_round(
        2,
        ["low sugar nutrition"],
        {"product_category": "healthy snack"},
        [],
        previous_events,
        FakeBudget(),
        MagicMock(),
        counters,
    )

    skipped = [event for event in events if event["agent_id"] == "quiet"][0]
    assert skipped["consumer_event_type"] == ConsumerEventType.PARTICIPATION_SKIPPED.value
    assert skipped["event_type"] == ConsumerEventType.IGNORE.value
    assert skipped["participation"]["participated"] is False
    assert "quiet" not in mapper.calls
    assert "active" in mapper.calls
    assert len(traces) == 2
