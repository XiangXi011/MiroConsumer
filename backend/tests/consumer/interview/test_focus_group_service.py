from app.services.consumer.interview.focus_group_service import FocusGroupService
from app.services.consumer.interview.focus_group_dialogue_engine import FocusGroupDialogueEngine
from app.services.consumer.interview.history_store import HistoryStore
from app.services.consumer.interview.interview_models import ConsumerInterviewRequest
from app.services.simulation_manager import SimulationStatus
from test_representative_sampler import _write_society_fixture


class _Repo:
    def get_simulation(self, simulation_id):
        return type(
            "State",
            (),
            {
                "status": SimulationStatus.READY,
                "project_id": "project-1",
                "graph_id": "graph-1",
                "project_type": "consumer_test",
                "consumer_mode": True,
            },
        )()


class _FakeDialogueEngine:
    def __init__(self):
        self.moderator_calls = []
        self.participant_calls = []

    def build_moderator_instruction(
        self,
        *,
        turn_number,
        topic,
        moderator_prompt,
        participant_cards,
        target_context,
        discussion_contexts,
        prior_turns,
    ):
        self.moderator_calls.append(
            {
                "turn_number": turn_number,
                "topic": topic,
                "target_context": target_context,
                "discussion_contexts": discussion_contexts,
                "prior_turns": list(prior_turns),
            }
        )
        return {
            "instruction": f"Probe {target_context.get('finding_id')} through prior answers",
            "source": "fake_context_aware_llm_moderator",
        }

    def generate_participant_response(
        self,
        *,
        turn_number,
        topic,
        card,
        role_template,
        moderator_instruction,
        discussion_context,
        prior_turns,
        target_context,
    ):
        self.participant_calls.append(
            {
                "turn_number": turn_number,
                "agent_id": card["agent_id"],
                "role_template": role_template,
                "moderator_instruction": moderator_instruction,
                "discussion_context": discussion_context,
                "prior_turns": list(prior_turns),
                "target_context": target_context,
            }
        )
        prior_answer = discussion_context["prior_answers"][0]["answer"]
        event_quote = discussion_context["event_stream"][0]["quote"]
        return {
            "response": (
                f"LLM response uses memory '{prior_answer}' and event '{event_quote}' "
                f"under {moderator_instruction['instruction']}."
            ),
            "source": "fake_memory_aware_llm_participant",
            "reasoning_summary": "memory-aware debate response",
        }


class _FakeFocusLLMClient:
    def __init__(self):
        self.calls = []

    def chat_json(self, **kwargs):
        self.calls.append(kwargs)
        content = " ".join(message.get("content", "") for message in kwargs.get("messages", []))
        if "moderator instruction" in content:
            return {
                "instruction": "Ask the skeptic to confront the weak evidence map and prior proof demand.",
                "reasoning_summary": "moderator grounded the turn in evidence and memory",
            }
        return {
            "response": "LLM participant cites prior proof demand and weak_support before changing trust.",
            "reasoning_summary": "participant used memory and evidence context",
        }


def test_focus_group_runs_fixed_four_turns_and_writes_history(tmp_path):
    _write_society_fixture(tmp_path, simulation_id="sim-focus")
    service = FocusGroupService(base_dir=tmp_path, simulation_repo=_Repo())
    request = ConsumerInterviewRequest(
        simulation_id="sim-focus",
        topic="packaging proof and price resistance",
        questions=[],
        agent_ids=[],
        roles=["skeptic", "advocate"],
        mode="snapshot",
        max_agents=8,
        target_context={"claim": "low sugar", "branch_id": "branch-1"},
    )

    session = service.run_focus_group(request, moderator_goal="Find trust repair path")

    assert len(session.turns) == 4
    assert [turn["turn"] for turn in session.turns] == [1, 2, 3, 4]
    assert len(session.participant_cards) <= 8
    assert session.consensus
    assert session.disagreements
    assert session.next_what_if_experiments
    assert session.evidence_map
    history = service.history_store.list_focus_groups("sim-focus")
    assert history[0]["focus_group_id"] == session.focus_group_id


def test_focus_group_responses_are_grounded_in_history_channel_evidence_and_finding(tmp_path):
    _write_society_fixture(tmp_path, simulation_id="sim-grounded-focus")
    HistoryStore(base_dir=tmp_path).write_interview(
        "sim-grounded-focus",
        {
            "interview_id": "interview-prior",
            "answers": [
                {
                    "agent_id": "agent-skeptic",
                    "answer": "I still need ingredient-source proof before I trust the claim.",
                }
            ],
        },
    )
    service = FocusGroupService(base_dir=tmp_path, simulation_repo=_Repo())
    request = ConsumerInterviewRequest(
        simulation_id="sim-grounded-focus",
        topic="low sugar claim",
        questions=[],
        agent_ids=["agent-skeptic"],
        roles=["skeptic"],
        mode="snapshot",
        max_agents=1,
        target_context={
            "finding_id": "finding-1",
            "claim": "low sugar",
            "evidence_map": {"finding-1": {"support_level": "weak_support"}},
        },
    )

    session = service.run_focus_group(request, moderator_goal="Explain the trust blocker")

    first_response = session.turns[0]["responses"][0]
    context = first_response["context"]
    assert context["channel_id"] == "zhihu_qa"
    assert context["target_finding"] == "finding-1"
    assert context["event_stream"][0]["quote"] == "Show me proof before I believe this."
    assert context["evidence_map"]["finding-1"]["support_level"] == "weak_support"
    assert context["prior_answers"][0]["answer"] == "I still need ingredient-source proof before I trust the claim."
    assert "zhihu_qa" in first_response["response"]
    assert "Show me proof before I believe this." in first_response["response"]


def test_focus_group_uses_context_aware_llm_moderator_and_memory_aware_participants(tmp_path):
    _write_society_fixture(tmp_path, simulation_id="sim-llm-focus")
    HistoryStore(base_dir=tmp_path).write_interview(
        "sim-llm-focus",
        {
            "interview_id": "interview-prior",
            "answers": [
                {
                    "agent_id": "agent-skeptic",
                    "answer": "I still need ingredient-source proof before I trust the claim.",
                }
            ],
        },
    )
    dialogue_engine = _FakeDialogueEngine()
    service = FocusGroupService(
        base_dir=tmp_path,
        simulation_repo=_Repo(),
        dialogue_engine=dialogue_engine,
    )
    request = ConsumerInterviewRequest(
        simulation_id="sim-llm-focus",
        topic="low sugar claim",
        questions=[],
        agent_ids=["agent-skeptic"],
        roles=["skeptic"],
        mode="snapshot",
        max_agents=1,
        target_context={
            "finding_id": "finding-1",
            "claim": "low sugar",
            "evidence_map": {"finding-1": {"support_level": "weak_support"}},
        },
    )

    session = service.run_focus_group(request, moderator_goal="Run a real debate")

    assert len(dialogue_engine.moderator_calls) == 4
    assert len(dialogue_engine.participant_calls) == 4
    first_turn = session.turns[0]
    first_response = first_turn["responses"][0]
    participant_call = dialogue_engine.participant_calls[0]
    assert first_turn["moderator_instruction"]["source"] == "fake_context_aware_llm_moderator"
    assert first_response["source"] == "fake_memory_aware_llm_participant"
    assert first_response["reasoning_summary"] == "memory-aware debate response"
    assert "LLM response uses memory" in first_response["response"]
    assert participant_call["role_template"]
    assert participant_call["discussion_context"]["prior_answers"][0]["answer"] == (
        "I still need ingredient-source proof before I trust the claim."
    )
    assert participant_call["discussion_context"]["event_stream"][0]["quote"] == (
        "Show me proof before I believe this."
    )
    assert dialogue_engine.participant_calls[1]["prior_turns"][0]["turn"] == 1


def test_focus_group_dialogue_engine_uses_fake_llm_for_moderator_and_participants(
    tmp_path,
    monkeypatch,
):
    monkeypatch.setenv("FOCUS_GROUP_DIALOGUE_BACKEND", "llm")
    monkeypatch.delenv("FOCUS_GROUP_DETERMINISTIC_MODE", raising=False)
    _write_society_fixture(tmp_path, simulation_id="sim-default-llm-focus")
    HistoryStore(base_dir=tmp_path).write_interview(
        "sim-default-llm-focus",
        {
            "interview_id": "interview-prior",
            "answers": [
                {
                    "agent_id": "agent-skeptic",
                    "answer": "I still need ingredient-source proof before I trust the claim.",
                }
            ],
        },
    )
    fake_client = _FakeFocusLLMClient()
    service = FocusGroupService(
        base_dir=tmp_path,
        simulation_repo=_Repo(),
        dialogue_engine=FocusGroupDialogueEngine(llm_client_factory=lambda: fake_client),
    )
    request = ConsumerInterviewRequest(
        simulation_id="sim-default-llm-focus",
        topic="low sugar claim",
        questions=[],
        agent_ids=["agent-skeptic"],
        roles=["skeptic"],
        mode="snapshot",
        max_agents=1,
        target_context={
            "finding_id": "finding-1",
            "claim": "low sugar",
            "evidence_map": {"finding-1": {"support_level": "weak_support"}},
        },
    )

    session = service.run_focus_group(request, moderator_goal="Run a real debate")

    assert fake_client.calls
    assert session.turns[0]["moderator_instruction"]["source"] == "llm_moderator"
    assert session.turns[0]["moderator_instruction"]["instruction"] == (
        "Ask the skeptic to confront the weak evidence map and prior proof demand."
    )
    first_response = session.turns[0]["responses"][0]
    assert first_response["source"] == "llm_participant"
    assert first_response["response"] == (
        "LLM participant cites prior proof demand and weak_support before changing trust."
    )
    assert first_response["reasoning_summary"] == "participant used memory and evidence context"
