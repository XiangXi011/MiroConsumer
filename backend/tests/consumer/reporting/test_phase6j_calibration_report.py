"""Phase 6J calibration report deterministic coverage."""

from app.services.consumer.phase6j_calibration import Phase6JCalibrationService, Phase6JCalibrationReport
from app.services.consumer.evidence_validator import (
    EvidenceValidationResult,
    EvidenceGatekeepingResult,
)


def test_calibration_report_outputs_all_required_fields():
    """Report must contain all 8 required Phase 6J fields."""
    service = Phase6JCalibrationService()
    report = service.build_report()

    d = report.to_dict()
    assert "golden_flow_result" in d
    assert "evidence_gatekeeping_result" in d
    assert "reasoning_backend_coverage" in d
    assert "template_fallback_coverage" in d
    assert "weak_support_finding_count" in d
    assert "insufficient_support_finding_count" in d
    assert "unknown_recommendation_count" in d
    assert "phase7_entry_decision" in d
    assert d["phase7_entry_decision"] in {"PASS", "BLOCKED"}
    assert d["golden_flow_result"] in {"PASS", "BLOCKED"}
    assert d["evidence_gatekeeping_result"] in {"PASS", "BLOCKED"}


def test_calibration_report_passes_with_clean_artifacts():
    """All clean artifacts should yield PASS for all gates."""
    service = Phase6JCalibrationService()
    report = service.build_report(
        gatekeeping_results=[
            EvidenceGatekeepingResult(finding_id="f1", gatekeeping_status="allowed", policy_violations=[], gatekeeping_notes="ok"),
        ],
        validation_results=[
            EvidenceValidationResult(finding_id="f1", validation_status="supported", evidence_sufficiency=0.8, aligned_snippet_ids=["c1"], missing_support_reasons=[], validator_notes="ok"),
        ],
        reasoning_events=[
            {"reasoning_backend": "llm", "reasoning_summary": "good reasoning"},
            {"reasoning_backend": "llm", "reasoning_summary": "more reasoning"},
        ],
        golden_flow_checks=[
            {"status": "passed", "check": "flow_a"},
            {"status": "passed", "check": "flow_b"},
        ],
    )

    assert report.golden_flow_result == "PASS"
    assert report.evidence_gatekeeping_result == "PASS"
    assert report.reasoning_backend_coverage == 1.0
    assert report.template_fallback_coverage == 0.0
    assert report.weak_support_finding_count == 0
    assert report.insufficient_support_finding_count == 0
    assert report.unknown_recommendation_count == 0
    assert report.phase7_entry_decision == "PASS"


def test_calibration_report_blocks_on_gatekeeping_failure():
    """Any blocked gatekeeping result must block evidence_gatekeeping and phase7."""
    service = Phase6JCalibrationService()
    report = service.build_report(
        gatekeeping_results=[
            EvidenceGatekeepingResult(finding_id="f1", gatekeeping_status="allowed", policy_violations=[], gatekeeping_notes="ok"),
            EvidenceGatekeepingResult(finding_id="f2", gatekeeping_status="blocked", policy_violations=["insufficient_support"], gatekeeping_notes="blocked"),
        ],
        validation_results=[
            EvidenceValidationResult(finding_id="f1", validation_status="supported", evidence_sufficiency=0.8, aligned_snippet_ids=["c1"], missing_support_reasons=[], validator_notes="ok"),
            EvidenceValidationResult(finding_id="f2", validation_status="insufficient_support", evidence_sufficiency=0.1, aligned_snippet_ids=[], missing_support_reasons=["no_snippet"], validator_notes="insufficient"),
        ],
        reasoning_events=[{"reasoning_backend": "llm", "reasoning_summary": "reasoning"}],
        golden_flow_checks=[{"status": "passed", "check": "flow"}],
    )

    assert report.evidence_gatekeeping_result == "BLOCKED"
    assert report.weak_support_finding_count == 0
    assert report.insufficient_support_finding_count == 1
    assert report.phase7_entry_decision == "BLOCKED"


def test_calibration_report_blocks_when_gatekeeping_has_not_run():
    """No gatekeeping artifact means UNKNOWN evidence state and blocks Phase 7."""
    service = Phase6JCalibrationService()
    report = service.build_report(
        gatekeeping_results=[],
        validation_results=[
            EvidenceValidationResult(finding_id="f1", validation_status="supported", evidence_sufficiency=0.8, aligned_snippet_ids=["c1"], missing_support_reasons=[], validator_notes="ok"),
        ],
        reasoning_events=[{"reasoning_backend": "llm", "reasoning_summary": "reasoning"}],
        golden_flow_checks=[{"status": "passed", "check": "flow"}],
    )

    assert report.evidence_gatekeeping_result == "BLOCKED"
    assert report.phase7_entry_decision == "BLOCKED"


def test_calibration_report_blocks_on_golden_flow_failure():
    """Any failed golden flow check must block golden_flow and phase7."""
    service = Phase6JCalibrationService()
    report = service.build_report(
        gatekeeping_results=[
            EvidenceGatekeepingResult(finding_id="f1", gatekeeping_status="allowed", policy_violations=[], gatekeeping_notes="ok"),
        ],
        validation_results=[
            EvidenceValidationResult(finding_id="f1", validation_status="supported", evidence_sufficiency=0.8, aligned_snippet_ids=["c1"], missing_support_reasons=[], validator_notes="ok"),
        ],
        reasoning_events=[{"reasoning_backend": "llm", "reasoning_summary": "reasoning"}],
        golden_flow_checks=[
            {"status": "passed", "check": "flow_a"},
            {"status": "failed", "check": "flow_b"},
        ],
    )

    assert report.golden_flow_result == "BLOCKED"
    assert report.phase7_entry_decision == "BLOCKED"


def test_calibration_report_counts_weak_and_insufficient_support():
    """Report must accurately count weak_support and insufficient_support findings."""
    service = Phase6JCalibrationService()
    report = service.build_report(
        validation_results=[
            EvidenceValidationResult(finding_id="f1", validation_status="supported", evidence_sufficiency=0.8, aligned_snippet_ids=["c1"], missing_support_reasons=[], validator_notes="ok"),
            EvidenceValidationResult(finding_id="f2", validation_status="weak_support", evidence_sufficiency=0.4, aligned_snippet_ids=[], missing_support_reasons=["no_trace"], validator_notes="weak"),
            EvidenceValidationResult(finding_id="f3", validation_status="weak_support", evidence_sufficiency=0.3, aligned_snippet_ids=[], missing_support_reasons=["no_trace"], validator_notes="weak"),
            EvidenceValidationResult(finding_id="f4", validation_status="insufficient_support", evidence_sufficiency=0.1, aligned_snippet_ids=[], missing_support_reasons=["no_snippet"], validator_notes="insufficient"),
            EvidenceValidationResult(finding_id="f5", validation_status="insufficient_support", evidence_sufficiency=0.0, aligned_snippet_ids=[], missing_support_reasons=["no_snippet"], validator_notes="insufficient"),
        ],
        gatekeeping_results=[
            EvidenceGatekeepingResult(finding_id="f1", gatekeeping_status="allowed", policy_violations=[], gatekeeping_notes="ok"),
            EvidenceGatekeepingResult(finding_id="f2", gatekeeping_status="downgraded", policy_violations=[], gatekeeping_notes="downgraded"),
            EvidenceGatekeepingResult(finding_id="f3", gatekeeping_status="downgraded", policy_violations=[], gatekeeping_notes="downgraded"),
            EvidenceGatekeepingResult(finding_id="f4", gatekeeping_status="blocked", policy_violations=["insufficient_support"], gatekeeping_notes="blocked"),
            EvidenceGatekeepingResult(finding_id="f5", gatekeeping_status="blocked", policy_violations=["insufficient_support"], gatekeeping_notes="blocked"),
        ],
        golden_flow_checks=[{"status": "passed", "check": "flow"}],
    )

    assert report.weak_support_finding_count == 2
    assert report.insufficient_support_finding_count == 2
    assert report.evidence_gatekeeping_result == "BLOCKED"


def test_calibration_report_counts_unknown_recommendations():
    """Reasoning events with empty/unknown summaries must be counted."""
    service = Phase6JCalibrationService()
    report = service.build_report(
        reasoning_events=[
            {"reasoning_backend": "llm", "reasoning_summary": "good reasoning"},
            {"reasoning_backend": "llm", "reasoning_summary": ""},
            {"reasoning_backend": "template", "reasoning_summary": "unknown"},
            {"reasoning_backend": "template", "reasoning_summary": "n/a"},
            {"reasoning_backend": "llm", "reasoning_summary": "Valid reasoning"},
        ],
        golden_flow_checks=[{"status": "passed", "check": "flow"}],
    )

    assert report.unknown_recommendation_count == 3


def test_calibration_report_reasoning_backend_coverage():
    """Coverage metrics must reflect LLM vs template_fallback ratios."""
    service = Phase6JCalibrationService()
    report = service.build_report(
        reasoning_events=[
            {"reasoning_backend": "llm", "reasoning_summary": "a"},
            {"reasoning_backend": "llm", "reasoning_summary": "b"},
            {"reasoning_backend": "llm", "reasoning_summary": "c"},
            {"reasoning_backend": "template_fallback", "reasoning_summary": "d"},
            {"reasoning_backend": "mock", "reasoning_summary": "e"},
        ],
        golden_flow_checks=[{"status": "passed", "check": "flow"}],
    )

    assert report.reasoning_backend_coverage == 0.6  # 3/5
    assert report.template_fallback_coverage == 0.4  # 2/5


def test_calibration_report_blocks_when_no_backend_dominates():
    """If neither LLM nor template covers >= 50%, phase7 must be BLOCKED."""
    service = Phase6JCalibrationService()
    report = service.build_report(
        reasoning_events=[
            {"reasoning_backend": "llm", "reasoning_summary": "a"},
            {"reasoning_backend": "other", "reasoning_summary": "b"},
            {"reasoning_backend": "other", "reasoning_summary": "c"},
        ],
        golden_flow_checks=[{"status": "passed", "check": "flow"}],
        gatekeeping_results=[
            EvidenceGatekeepingResult(finding_id="f1", gatekeeping_status="allowed", policy_violations=[], gatekeeping_notes="ok"),
        ],
    )

    assert report.reasoning_backend_coverage == 0.3333
    assert report.template_fallback_coverage == 0.0
    assert report.phase7_entry_decision == "BLOCKED"


def test_calibration_report_blocks_when_reasoning_events_are_missing():
    """Reasoning coverage cannot pass when no reasoning events were audited."""
    service = Phase6JCalibrationService()
    report = service.build_report(
        gatekeeping_results=[
            EvidenceGatekeepingResult(finding_id="f1", gatekeeping_status="allowed", policy_violations=[], gatekeeping_notes="ok"),
        ],
        validation_results=[
            EvidenceValidationResult(finding_id="f1", validation_status="supported", evidence_sufficiency=0.8, aligned_snippet_ids=["c1"], missing_support_reasons=[], validator_notes="ok"),
        ],
        reasoning_events=[],
        golden_flow_checks=[{"status": "passed", "check": "flow"}],
    )

    assert report.reasoning_backend_coverage == 0.0
    assert report.template_fallback_coverage == 0.0
    assert report.phase7_entry_decision == "BLOCKED"


def test_calibration_report_empty_inputs_blocks_phase7():
    """With no golden_flow_checks, phase7 must be BLOCKED."""
    service = Phase6JCalibrationService()
    report = service.build_report()

    assert report.golden_flow_result == "BLOCKED"
    assert report.phase7_entry_decision == "BLOCKED"
    assert report.reasoning_backend_coverage == 0.0
    assert report.template_fallback_coverage == 0.0


def test_calibration_report_deterministic_for_same_inputs():
    """Same inputs must produce identical reports."""
    service = Phase6JCalibrationService()
    kwargs = {
        "gatekeeping_results": [
            EvidenceGatekeepingResult(finding_id="f1", gatekeeping_status="allowed", policy_violations=[], gatekeeping_notes="ok"),
        ],
        "validation_results": [
            EvidenceValidationResult(finding_id="f1", validation_status="supported", evidence_sufficiency=0.8, aligned_snippet_ids=["c1"], missing_support_reasons=[], validator_notes="ok"),
        ],
        "reasoning_events": [
            {"reasoning_backend": "llm", "reasoning_summary": "reasoning"},
        ],
        "golden_flow_checks": [
            {"status": "passed", "check": "flow"},
        ],
    }

    report_a = service.build_report(**kwargs)
    report_b = service.build_report(**kwargs)

    assert report_a.to_dict() == report_b.to_dict()


def test_calibration_report_branch_base_isolation():
    """Different inputs for branch vs base must produce different reports."""
    service = Phase6JCalibrationService()

    base_report = service.build_report(
        gatekeeping_results=[
            EvidenceGatekeepingResult(finding_id="f-base", gatekeeping_status="allowed", policy_violations=[], gatekeeping_notes="ok"),
        ],
        validation_results=[
            EvidenceValidationResult(finding_id="f-base", validation_status="supported", evidence_sufficiency=0.8, aligned_snippet_ids=["c1"], missing_support_reasons=[], validator_notes="ok"),
        ],
        reasoning_events=[{"reasoning_backend": "llm", "reasoning_summary": "base reasoning"}],
        golden_flow_checks=[{"status": "passed", "check": "base_flow"}],
    )

    branch_report = service.build_report(
        gatekeeping_results=[
            EvidenceGatekeepingResult(finding_id="f-branch", gatekeeping_status="blocked", policy_violations=["insufficient_support"], gatekeeping_notes="blocked"),
        ],
        validation_results=[
            EvidenceValidationResult(finding_id="f-branch", validation_status="insufficient_support", evidence_sufficiency=0.1, aligned_snippet_ids=[], missing_support_reasons=["no_snippet"], validator_notes="insufficient"),
        ],
        reasoning_events=[{"reasoning_backend": "template", "reasoning_summary": ""}],
        golden_flow_checks=[{"status": "failed", "check": "branch_flow"}],
    )

    assert base_report.phase7_entry_decision == "PASS"
    assert branch_report.phase7_entry_decision == "BLOCKED"
    assert base_report.golden_flow_result == "PASS"
    assert branch_report.golden_flow_result == "BLOCKED"
    assert base_report.to_dict() != branch_report.to_dict()


def test_phase7_passes_with_tightened_gate():
    """Phase7 PASS requires LLM>=0.5, template<=0.3, unknown_ratio<=0.05."""
    service = Phase6JCalibrationService()
    report = service.build_report(
        gatekeeping_results=[
            EvidenceGatekeepingResult(finding_id="f1", gatekeeping_status="allowed", policy_violations=[], gatekeeping_notes="ok"),
        ],
        reasoning_events=[
            {"reasoning_backend": "llm", "reasoning_summary": "a"},
            {"reasoning_backend": "llm", "reasoning_summary": "b"},
            {"reasoning_backend": "llm", "reasoning_summary": "c"},
            {"reasoning_backend": "llm", "reasoning_summary": "d"},
            {"reasoning_backend": "template", "reasoning_summary": "e"},
        ],
        golden_flow_checks=[{"status": "passed", "check": "flow"}],
    )
    assert report.reasoning_backend_coverage == 0.8
    assert report.template_fallback_coverage == 0.2
    assert report.unknown_recommendation_count == 0
    assert report.phase7_entry_decision == "PASS"


def test_phase7_blocks_when_template_too_high():
    """Template >= 0.4 blocks even if LLM coverage is >= 0.5."""
    service = Phase6JCalibrationService()
    report = service.build_report(
        gatekeeping_results=[
            EvidenceGatekeepingResult(finding_id="f1", gatekeeping_status="allowed", policy_violations=[], gatekeeping_notes="ok"),
        ],
        reasoning_events=[
            {"reasoning_backend": "llm", "reasoning_summary": "a"},
            {"reasoning_backend": "llm", "reasoning_summary": "b"},
            {"reasoning_backend": "llm", "reasoning_summary": "c"},
            {"reasoning_backend": "template_fallback", "reasoning_summary": "d"},
            {"reasoning_backend": "template_fallback", "reasoning_summary": "e"},
        ],
        golden_flow_checks=[{"status": "passed", "check": "flow"}],
    )
    assert report.reasoning_backend_coverage == 0.6
    assert report.template_fallback_coverage == 0.4
    assert report.phase7_entry_decision == "BLOCKED"


def test_phase7_blocks_when_template_exceeds_thirty_percent():
    """Template fallback above 0.3 blocks Phase 7 entry."""
    service = Phase6JCalibrationService()
    report = service.build_report(
        gatekeeping_results=[
            EvidenceGatekeepingResult(finding_id="f1", gatekeeping_status="allowed", policy_violations=[], gatekeeping_notes="ok"),
        ],
        reasoning_events=[
            {"reasoning_backend": "llm", "reasoning_summary": "a"},
            {"reasoning_backend": "llm", "reasoning_summary": "b"},
            {"reasoning_backend": "template_fallback", "reasoning_summary": "c"},
        ],
        golden_flow_checks=[{"status": "passed", "check": "flow"}],
    )
    assert report.reasoning_backend_coverage == 0.6667
    assert report.template_fallback_coverage == 0.3333
    assert report.phase7_entry_decision == "BLOCKED"


def test_phase7_blocks_when_llm_coverage_low():
    """LLM coverage below 0.5 blocks even if template coverage is low."""
    service = Phase6JCalibrationService()
    report = service.build_report(
        gatekeeping_results=[
            EvidenceGatekeepingResult(finding_id="f1", gatekeeping_status="allowed", policy_violations=[], gatekeeping_notes="ok"),
        ],
        reasoning_events=[
            {"reasoning_backend": "llm", "reasoning_summary": "a"},
            {"reasoning_backend": "llm", "reasoning_summary": "b"},
            {"reasoning_backend": "other", "reasoning_summary": "c"},
            {"reasoning_backend": "other", "reasoning_summary": "d"},
            {"reasoning_backend": "other", "reasoning_summary": "e"},
        ],
        golden_flow_checks=[{"status": "passed", "check": "flow"}],
    )
    assert report.reasoning_backend_coverage == 0.4
    assert report.template_fallback_coverage == 0.0
    assert report.phase7_entry_decision == "BLOCKED"


def test_phase7_passes_with_zero_unknown():
    """Zero unknown count trivially satisfies the unknown ratio gate."""
    service = Phase6JCalibrationService()
    report = service.build_report(
        gatekeeping_results=[
            EvidenceGatekeepingResult(finding_id="f1", gatekeeping_status="allowed", policy_violations=[], gatekeeping_notes="ok"),
        ],
        reasoning_events=[
            {"reasoning_backend": "llm", "reasoning_summary": "a"},
            {"reasoning_backend": "llm", "reasoning_summary": "b"},
            {"reasoning_backend": "llm", "reasoning_summary": "c"},
            {"reasoning_backend": "template", "reasoning_summary": "d"},
        ],
        golden_flow_checks=[{"status": "passed", "check": "flow"}],
    )
    assert report.unknown_recommendation_count == 0
    assert report.phase7_entry_decision == "PASS"


def test_phase7_passes_with_one_unknown_in_twenty():
    """One unknown in 20 events is exactly 0.05 and should PASS."""
    service = Phase6JCalibrationService()
    reasoning_events = [{"reasoning_backend": "llm", "reasoning_summary": f"r{i}"} for i in range(19)]
    reasoning_events.append({"reasoning_backend": "llm", "reasoning_summary": ""})
    report = service.build_report(
        gatekeeping_results=[
            EvidenceGatekeepingResult(finding_id="f1", gatekeeping_status="allowed", policy_violations=[], gatekeeping_notes="ok"),
        ],
        reasoning_events=reasoning_events,
        golden_flow_checks=[{"status": "passed", "check": "flow"}],
    )
    assert report.unknown_recommendation_count == 1
    assert report.phase7_entry_decision == "PASS"


def test_phase7_blocks_with_one_unknown_in_ten():
    """One unknown in 10 events is 0.1 and should BLOCK."""
    service = Phase6JCalibrationService()
    reasoning_events = [{"reasoning_backend": "llm", "reasoning_summary": f"r{i}"} for i in range(9)]
    reasoning_events.append({"reasoning_backend": "llm", "reasoning_summary": ""})
    report = service.build_report(
        gatekeeping_results=[
            EvidenceGatekeepingResult(finding_id="f1", gatekeeping_status="allowed", policy_violations=[], gatekeeping_notes="ok"),
        ],
        reasoning_events=reasoning_events,
        golden_flow_checks=[{"status": "passed", "check": "flow"}],
    )
    assert report.unknown_recommendation_count == 1
    assert report.phase7_entry_decision == "BLOCKED"
