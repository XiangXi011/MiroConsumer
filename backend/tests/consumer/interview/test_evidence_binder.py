from app.services.consumer.interview.evidence_binder import InterviewEvidenceBinder


def test_evidence_binder_outputs_fixed_fields_and_phase6f_support_level():
    binder = InterviewEvidenceBinder()

    evidence = binder.bind_answer(
        card={
            "agent_id": "agent-1",
            "event_ids": ["event-1"],
            "evidence_ids": ["source-1"],
            "key_quote": "I need clinical proof before trusting it.",
        },
        answer={
            "question": "What proof changes your mind?",
            "answer": "A credible ingredient test changes my trust.",
        },
        target_context={
            "finding_id": "finding-1",
            "source_ids": ["source-2"],
            "quote_ids": ["quote-1"],
        },
    )

    assert set(evidence) == {
        "agent_id",
        "event_ids",
        "finding_ids",
        "source_ids",
        "quote_ids",
        "support_level",
    }
    assert evidence["agent_id"] == "agent-1"
    assert evidence["event_ids"] == ["event-1"]
    assert evidence["finding_ids"] == ["finding-1"]
    assert evidence["source_ids"] == ["source-1", "source-2"]
    assert evidence["quote_ids"] == ["quote-1"]
    assert evidence["support_level"] == "supported"


def test_evidence_binder_downgrades_when_only_simulation_quote_exists():
    evidence = InterviewEvidenceBinder().bind_answer(
        card={"agent_id": "agent-2", "event_ids": ["event-2"], "evidence_ids": []},
        answer={"answer": "I would still hesitate."},
        target_context={},
    )

    assert evidence["support_level"] == "weak_support"
