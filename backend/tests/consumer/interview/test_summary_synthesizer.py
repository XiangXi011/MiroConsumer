from app.services.consumer.interview.summary_synthesizer import InterviewSummarySynthesizer


def test_summary_synthesizer_outputs_required_interview_sections():
    summary = InterviewSummarySynthesizer().synthesize_interview(
        answers=[
            {
                "agent_id": "agent-1",
                "role": "skeptic",
                "question": "What is unclear?",
                "answer": "The benefit sounds good, but the evidence is not enough.",
            },
            {
                "agent_id": "agent-2",
                "role": "advocate",
                "question": "What would you share?",
                "answer": "The convenience claim is easy to retell.",
            },
        ],
        evidence_map={"agent-1": {"support_level": "weak_support"}},
        followup_questions=[
            {"type": "evidence_demand", "question": "Which proof would repair trust?", "target_role": "skeptic"}
        ],
    )

    for required in [
        "Core conclusion",
        "Strongest supporting quote",
        "Strongest opposing quote",
        "Misread point",
        "Evidence demand",
        "Price resistance",
        "Trust repair condition",
        "Next What-if experiment",
    ]:
        assert required in summary
