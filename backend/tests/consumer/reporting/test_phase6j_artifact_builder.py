"""Phase6JCalibrationArtifactBuilder deterministic coverage."""

import json
import pytest

from app.services.consumer.phase6j_artifact_builder import (
    Phase6JCalibrationArtifactBuilder,
    build_phase6j_calibration_artifact,
)
from app.services.consumer.phase6j_calibration import read_phase6j_calibration_artifact
from app.services.consumer.reasoning_trace import ReasoningTrace
from app.services.consumer.evidence_validator import (
    EvidenceValidationResult,
    EvidenceGatekeepingResult,
)


class TestArtifactBuilderInputContract:
    def test_required_inputs_reasoning_traces_and_golden_flow(self, tmp_path):
        sim_dir = tmp_path / "sim"
        sim_dir.mkdir(parents=True, exist_ok=True)
        society_dir = sim_dir / "society"
        society_dir.mkdir(parents=True, exist_ok=True)

        # Write required reasoning_traces
        traces = [
            ReasoningTrace(reasoning_backend="llm", llm_invoked=True, source="society_runtime", fallback_reason=""),
            ReasoningTrace(reasoning_backend="llm", llm_invoked=True, source="society_runtime", fallback_reason=""),
        ]
        with (society_dir / "reasoning_traces.jsonl").open("w", encoding="utf-8") as f:
            for t in traces:
                f.write(json.dumps(t.to_dict(), ensure_ascii=False) + "\n")

        # Write required golden_flow_checks
        with (sim_dir / "golden_flow_checks.json").open("w", encoding="utf-8") as f:
            json.dump([{"status": "passed", "check": "flow_a"}], f)

        builder = Phase6JCalibrationArtifactBuilder(str(sim_dir))
        result = builder.build()

        assert result["phase7_entry_decision"] == "BLOCKED"  # missing conditional-required evidence artifacts
        assert result["artifact_build_inputs"]["reasoning_traces"]["present"] is True
        assert result["artifact_build_inputs"]["golden_flow_checks"]["present"] is True
        assert result["artifact_build_inputs"]["evidence_gatekeeping_results"]["present"] is False
        assert result["artifact_build_inputs"]["evidence_validation_results"]["present"] is False

    def test_missing_required_reasoning_traces_produces_blocked(self, tmp_path):
        sim_dir = tmp_path / "sim"
        sim_dir.mkdir(parents=True, exist_ok=True)
        society_dir = sim_dir / "society"
        society_dir.mkdir(parents=True, exist_ok=True)

        # Missing reasoning_traces but has golden_flow_checks
        with (sim_dir / "golden_flow_checks.json").open("w", encoding="utf-8") as f:
            json.dump([{"status": "passed", "check": "flow_a"}], f)

        builder = Phase6JCalibrationArtifactBuilder(str(sim_dir))
        result = builder.build()

        assert result["phase7_entry_decision"] == "BLOCKED"
        assert result["artifact_build_inputs"]["reasoning_traces"]["present"] is False
        assert result["artifact_build_inputs"]["reasoning_traces"]["missing"] is True
        assert result["artifact_build_inputs"]["golden_flow_checks"]["present"] is True

    def test_missing_required_golden_flow_checks_produces_blocked(self, tmp_path):
        sim_dir = tmp_path / "sim"
        sim_dir.mkdir(parents=True, exist_ok=True)
        society_dir = sim_dir / "society"
        society_dir.mkdir(parents=True, exist_ok=True)

        # Has reasoning_traces but missing golden_flow_checks
        traces = [
            ReasoningTrace(reasoning_backend="llm", llm_invoked=True, source="society_runtime", fallback_reason=""),
        ]
        with (society_dir / "reasoning_traces.jsonl").open("w", encoding="utf-8") as f:
            for t in traces:
                f.write(json.dumps(t.to_dict(), ensure_ascii=False) + "\n")

        builder = Phase6JCalibrationArtifactBuilder(str(sim_dir))
        result = builder.build()

        assert result["phase7_entry_decision"] == "BLOCKED"
        assert result["artifact_build_inputs"]["golden_flow_checks"]["present"] is False

    def test_conditional_required_evidence_artifacts(self, tmp_path):
        sim_dir = tmp_path / "sim"
        sim_dir.mkdir(parents=True, exist_ok=True)
        society_dir = sim_dir / "society"
        society_dir.mkdir(parents=True, exist_ok=True)

        traces = [
            ReasoningTrace(reasoning_backend="llm", llm_invoked=True, source="society_runtime", fallback_reason="", reasoning_summary="good reasoning"),
        ]
        with (society_dir / "reasoning_traces.jsonl").open("w", encoding="utf-8") as f:
            for t in traces:
                f.write(json.dumps(t.to_dict(), ensure_ascii=False) + "\n")

        with (sim_dir / "golden_flow_checks.json").open("w", encoding="utf-8") as f:
            json.dump([{"status": "passed", "check": "flow_a"}], f)

        # Write conditional-required evidence artifacts
        gk = [EvidenceGatekeepingResult(finding_id="f1", gatekeeping_status="allowed", policy_violations=[], gatekeeping_notes="ok")]
        with (sim_dir / "evidence_gatekeeping_results.json").open("w", encoding="utf-8") as f:
            json.dump([g.to_dict() if hasattr(g, "to_dict") else dict(g.__dict__) for g in gk], f)

        vr = [EvidenceValidationResult(finding_id="f1", validation_status="supported", evidence_sufficiency=0.8, aligned_snippet_ids=["c1"], missing_support_reasons=[], validator_notes="ok")]
        with (sim_dir / "evidence_validation_results.json").open("w", encoding="utf-8") as f:
            json.dump([v.to_dict() if hasattr(v, "to_dict") else dict(v.__dict__) for v in vr], f)

        builder = Phase6JCalibrationArtifactBuilder(str(sim_dir))
        result = builder.build()

        assert result["artifact_build_inputs"]["evidence_gatekeeping_results"]["present"] is True
        assert result["artifact_build_inputs"]["evidence_validation_results"]["present"] is True
        assert result["phase7_entry_decision"] == "PASS"

    def test_optional_inputs_present_but_not_required(self, tmp_path):
        sim_dir = tmp_path / "sim"
        sim_dir.mkdir(parents=True, exist_ok=True)
        society_dir = sim_dir / "society"
        society_dir.mkdir(parents=True, exist_ok=True)

        traces = [
            ReasoningTrace(reasoning_backend="llm", llm_invoked=True, source="society_runtime", fallback_reason=""),
        ]
        with (society_dir / "reasoning_traces.jsonl").open("w", encoding="utf-8") as f:
            for t in traces:
                f.write(json.dumps(t.to_dict(), ensure_ascii=False) + "\n")

        with (sim_dir / "golden_flow_checks.json").open("w", encoding="utf-8") as f:
            json.dump([{"status": "passed", "check": "flow_a"}], f)

        # Optional files
        with (society_dir / "runtime_events.jsonl").open("w", encoding="utf-8") as f:
            f.write("{}\n")
        with (society_dir / "society_metrics.json").open("w", encoding="utf-8") as f:
            json.dump({}, f)
        with (society_dir / "channel_events.jsonl").open("w", encoding="utf-8") as f:
            f.write("{}\n")
        with (society_dir / "propagation_paths.json").open("w", encoding="utf-8") as f:
            json.dump([], f)
        with (society_dir / "network_topology.json").open("w", encoding="utf-8") as f:
            json.dump({}, f)
        rounds_dir = society_dir / "rounds"
        rounds_dir.mkdir(parents=True, exist_ok=True)
        with (rounds_dir / "round_0.json").open("w", encoding="utf-8") as f:
            json.dump({}, f)

        builder = Phase6JCalibrationArtifactBuilder(str(sim_dir))
        result = builder.build()

        # Optional inputs don't change BLOCKED due to missing conditional-required
        assert result["phase7_entry_decision"] == "BLOCKED"
        # But artifact_build_inputs should show what was present
        assert result["artifact_build_inputs"]["reasoning_traces"]["present"] is True
        assert result["artifact_build_inputs"]["golden_flow_checks"]["present"] is True

    def test_builder_does_not_guess_alternate_paths(self, tmp_path):
        sim_dir = tmp_path / "sim"
        sim_dir.mkdir(parents=True, exist_ok=True)
        society_dir = sim_dir / "society"
        society_dir.mkdir(parents=True, exist_ok=True)

        # Write traces to wrong path (not under society/)
        with (sim_dir / "reasoning_traces.jsonl").open("w", encoding="utf-8") as f:
            f.write("{}\n")

        with (sim_dir / "golden_flow_checks.json").open("w", encoding="utf-8") as f:
            json.dump([{"status": "passed"}], f)

        builder = Phase6JCalibrationArtifactBuilder(str(sim_dir))
        result = builder.build()

        # Must not find the traces at the wrong path
        assert result["artifact_build_inputs"]["reasoning_traces"]["present"] is False


class TestArtifactBuilderCoverageLogic:
    def test_coverage_counts_only_society_runtime_llm_no_fallback(self, tmp_path):
        sim_dir = tmp_path / "sim"
        sim_dir.mkdir(parents=True, exist_ok=True)
        society_dir = sim_dir / "society"
        society_dir.mkdir(parents=True, exist_ok=True)

        traces = [
            # Counted
            ReasoningTrace(reasoning_backend="llm", llm_invoked=True, source="society_runtime", fallback_reason="", reasoning_summary="r1"),
            ReasoningTrace(reasoning_backend="llm", llm_invoked=True, source="society_runtime", fallback_reason="", reasoning_summary="r2"),
            # Not counted: focus_group
            ReasoningTrace(reasoning_backend="llm", llm_invoked=True, source="focus_group", fallback_reason="", reasoning_summary="fg"),
            # Not counted: interview
            ReasoningTrace(reasoning_backend="llm", llm_invoked=True, source="interview", fallback_reason="", reasoning_summary="iv"),
            # Not counted: report
            ReasoningTrace(reasoning_backend="llm", llm_invoked=True, source="report", fallback_reason="", reasoning_summary="rp"),
            # Not counted: fallback_reason non-empty
            ReasoningTrace(reasoning_backend="llm", llm_invoked=True, source="society_runtime", fallback_reason="timeout", reasoning_summary="fb"),
            # Not counted: llm_invoked False
            ReasoningTrace(reasoning_backend="rules", llm_invoked=False, source="society_runtime", fallback_reason="", reasoning_summary="rules"),
        ]
        with (society_dir / "reasoning_traces.jsonl").open("w", encoding="utf-8") as f:
            for t in traces:
                f.write(json.dumps(t.to_dict(), ensure_ascii=False) + "\n")

        with (sim_dir / "golden_flow_checks.json").open("w", encoding="utf-8") as f:
            json.dump([{"status": "passed", "check": "flow"}], f)

        gk = [EvidenceGatekeepingResult(finding_id="f1", gatekeeping_status="allowed", policy_violations=[], gatekeeping_notes="ok")]
        with (sim_dir / "evidence_gatekeeping_results.json").open("w", encoding="utf-8") as f:
            json.dump([g.to_dict() if hasattr(g, "to_dict") else dict(g.__dict__) for g in gk], f)

        vr = [EvidenceValidationResult(finding_id="f1", validation_status="supported", evidence_sufficiency=0.8, aligned_snippet_ids=["c1"], missing_support_reasons=[], validator_notes="ok")]
        with (sim_dir / "evidence_validation_results.json").open("w", encoding="utf-8") as f:
            json.dump([v.to_dict() if hasattr(v, "to_dict") else dict(v.__dict__) for v in vr], f)

        builder = Phase6JCalibrationArtifactBuilder(str(sim_dir))
        result = builder.build()

        # Phase6J counts only society_runtime traces for the denominator:
        # 2 clean LLM traces / 4 society_runtime traces.
        assert result["reasoning_backend_coverage"] == 0.5
        assert result["template_fallback_coverage"] == 0.25
        assert result["phase7_entry_decision"] == "PASS"

    def test_quick_run_cannot_automatically_pass(self, tmp_path):
        sim_dir = tmp_path / "sim"
        sim_dir.mkdir(parents=True, exist_ok=True)
        society_dir = sim_dir / "society"
        society_dir.mkdir(parents=True, exist_ok=True)

        # Quick run with only required inputs (no conditional-required evidence)
        traces = [
            ReasoningTrace(reasoning_backend="llm", llm_invoked=True, source="society_runtime", fallback_reason=""),
        ]
        with (society_dir / "reasoning_traces.jsonl").open("w", encoding="utf-8") as f:
            for t in traces:
                f.write(json.dumps(t.to_dict(), ensure_ascii=False) + "\n")

        with (sim_dir / "golden_flow_checks.json").open("w", encoding="utf-8") as f:
            json.dump([{"status": "passed", "check": "flow"}], f)

        builder = Phase6JCalibrationArtifactBuilder(str(sim_dir))
        result = builder.build()

        # Missing evidence_gatekeeping_results and evidence_validation_results -> BLOCKED
        assert result["phase7_entry_decision"] == "BLOCKED"
        assert result["evidence_gatekeeping_result"] == "BLOCKED"

    def test_focus_group_traces_normalized_but_excluded(self, tmp_path):
        sim_dir = tmp_path / "sim"
        sim_dir.mkdir(parents=True, exist_ok=True)
        society_dir = sim_dir / "society"
        society_dir.mkdir(parents=True, exist_ok=True)

        traces = [
            ReasoningTrace(reasoning_backend="llm", llm_invoked=True, source="society_runtime", fallback_reason="", reasoning_summary="r1"),
            ReasoningTrace(reasoning_backend="llm", llm_invoked=True, source="focus_group", fallback_reason="", reasoning_summary="fg"),
            ReasoningTrace(reasoning_backend="llm", llm_invoked=True, source="interview", fallback_reason="", reasoning_summary="iv"),
        ]
        with (society_dir / "reasoning_traces.jsonl").open("w", encoding="utf-8") as f:
            for t in traces:
                f.write(json.dumps(t.to_dict(), ensure_ascii=False) + "\n")

        with (sim_dir / "golden_flow_checks.json").open("w", encoding="utf-8") as f:
            json.dump([{"status": "passed", "check": "flow"}], f)

        gk = [EvidenceGatekeepingResult(finding_id="f1", gatekeeping_status="allowed", policy_violations=[], gatekeeping_notes="ok")]
        with (sim_dir / "evidence_gatekeeping_results.json").open("w", encoding="utf-8") as f:
            json.dump([g.to_dict() if hasattr(g, "to_dict") else dict(g.__dict__) for g in gk], f)

        vr = [EvidenceValidationResult(finding_id="f1", validation_status="supported", evidence_sufficiency=0.8, aligned_snippet_ids=["c1"], missing_support_reasons=[], validator_notes="ok")]
        with (sim_dir / "evidence_validation_results.json").open("w", encoding="utf-8") as f:
            json.dump([v.to_dict() if hasattr(v, "to_dict") else dict(v.__dict__) for v in vr], f)

        builder = Phase6JCalibrationArtifactBuilder(str(sim_dir))
        result = builder.build()

        # Only 1 society_runtime trace counts -> 100% LLM coverage of counted traces
        assert result["reasoning_backend_coverage"] == 1.0
        assert result["phase7_entry_decision"] == "PASS"
        # But details should show total traces (including non-society)
        assert result["details"]["total_reasoning_events"] == 1

    def test_no_evidence_unknown_equals_fail(self, tmp_path):
        sim_dir = tmp_path / "sim"
        sim_dir.mkdir(parents=True, exist_ok=True)
        society_dir = sim_dir / "society"
        society_dir.mkdir(parents=True, exist_ok=True)

        traces = [
            ReasoningTrace(reasoning_backend="llm", llm_invoked=True, source="society_runtime", fallback_reason=""),
        ]
        with (society_dir / "reasoning_traces.jsonl").open("w", encoding="utf-8") as f:
            for t in traces:
                f.write(json.dumps(t.to_dict(), ensure_ascii=False) + "\n")

        with (sim_dir / "golden_flow_checks.json").open("w", encoding="utf-8") as f:
            json.dump([{"status": "passed", "check": "flow"}], f)

        # No evidence_gatekeeping_results or evidence_validation_results
        builder = Phase6JCalibrationArtifactBuilder(str(sim_dir))
        result = builder.build()

        assert result["evidence_gatekeeping_result"] == "BLOCKED"
        assert result["phase7_entry_decision"] == "BLOCKED"


class TestArtifactBuilderPersistence:
    def test_build_phase6j_calibration_artifact_persists(self, tmp_path):
        sim_dir = tmp_path / "sim"
        sim_dir.mkdir(parents=True, exist_ok=True)
        society_dir = sim_dir / "society"
        society_dir.mkdir(parents=True, exist_ok=True)

        traces = [
            ReasoningTrace(reasoning_backend="llm", llm_invoked=True, source="society_runtime", fallback_reason="", reasoning_summary="good"),
        ]
        with (society_dir / "reasoning_traces.jsonl").open("w", encoding="utf-8") as f:
            for t in traces:
                f.write(json.dumps(t.to_dict(), ensure_ascii=False) + "\n")

        with (sim_dir / "golden_flow_checks.json").open("w", encoding="utf-8") as f:
            json.dump([{"status": "passed", "check": "flow"}], f)

        gk = [EvidenceGatekeepingResult(finding_id="f1", gatekeeping_status="allowed", policy_violations=[], gatekeeping_notes="ok")]
        with (sim_dir / "evidence_gatekeeping_results.json").open("w", encoding="utf-8") as f:
            json.dump([g.to_dict() if hasattr(g, "to_dict") else dict(g.__dict__) for g in gk], f)

        vr = [EvidenceValidationResult(finding_id="f1", validation_status="supported", evidence_sufficiency=0.8, aligned_snippet_ids=["c1"], missing_support_reasons=[], validator_notes="ok")]
        with (sim_dir / "evidence_validation_results.json").open("w", encoding="utf-8") as f:
            json.dump([v.to_dict() if hasattr(v, "to_dict") else dict(v.__dict__) for v in vr], f)

        path = build_phase6j_calibration_artifact(str(sim_dir))
        assert path.endswith("phase6j_calibration_artifact.json")

        loaded = read_phase6j_calibration_artifact(str(sim_dir))
        assert loaded is not None
        assert loaded["phase7_entry_decision"] == "PASS"
        assert "artifact_build_inputs" in loaded
        assert "artifact_build_inputs" in loaded["details"]


class TestArtifactBuilderDeterministic:
    def test_same_inputs_produce_same_output(self, tmp_path):
        sim_dir = tmp_path / "sim"
        sim_dir.mkdir(parents=True, exist_ok=True)
        society_dir = sim_dir / "society"
        society_dir.mkdir(parents=True, exist_ok=True)

        traces = [
            ReasoningTrace(reasoning_backend="llm", llm_invoked=True, source="society_runtime", fallback_reason=""),
            ReasoningTrace(reasoning_backend="llm", llm_invoked=True, source="society_runtime", fallback_reason=""),
        ]
        with (society_dir / "reasoning_traces.jsonl").open("w", encoding="utf-8") as f:
            for t in traces:
                f.write(json.dumps(t.to_dict(), ensure_ascii=False) + "\n")

        with (sim_dir / "golden_flow_checks.json").open("w", encoding="utf-8") as f:
            json.dump([{"status": "passed", "check": "flow"}], f)

        gk = [EvidenceGatekeepingResult(finding_id="f1", gatekeeping_status="allowed", policy_violations=[], gatekeeping_notes="ok")]
        with (sim_dir / "evidence_gatekeeping_results.json").open("w", encoding="utf-8") as f:
            json.dump([g.to_dict() if hasattr(g, "to_dict") else dict(g.__dict__) for g in gk], f)

        vr = [EvidenceValidationResult(finding_id="f1", validation_status="supported", evidence_sufficiency=0.8, aligned_snippet_ids=["c1"], missing_support_reasons=[], validator_notes="ok")]
        with (sim_dir / "evidence_validation_results.json").open("w", encoding="utf-8") as f:
            json.dump([v.to_dict() if hasattr(v, "to_dict") else dict(v.__dict__) for v in vr], f)

        builder1 = Phase6JCalibrationArtifactBuilder(str(sim_dir))
        builder2 = Phase6JCalibrationArtifactBuilder(str(sim_dir))
        result1 = builder1.build()
        result2 = builder2.build()

        assert result1 == result2


class TestArtifactBuilderSimulationRunnerInputs:
    def test_runner_post_run_helper_writes_inputs_and_blocked_artifact_without_findings(
        self,
        monkeypatch,
        tmp_path,
    ):
        from app.services.simulation_runner import (
            RunnerStatus,
            SimulationRunState,
            RoundSummary,
            AgentAction,
            SimulationRunner,
        )

        monkeypatch.setattr(SimulationRunner, "RUN_STATE_DIR", str(tmp_path))
        state = SimulationRunState(
            simulation_id="sim-inputs",
            runner_status=RunnerStatus.COMPLETED,
            current_round=1,
            total_rounds=1,
        )
        round_summary = RoundSummary(round_num=0, start_time="2026-05-07T00:00:00")
        round_summary.actions.append(
            AgentAction(
                round_num=0,
                timestamp="2026-05-07T00:00:00",
                platform="reddit",
                agent_id=1,
                agent_name="测试消费者",
                action_type="CONSUMER_REACTION",
                action_args={},
                result="我需要更多证据。",
                success=True,
            )
        )
        state.rounds = [round_summary]
        monkeypatch.setattr(SimulationRunner, "get_run_state", lambda sim_id: state)

        SimulationRunner._build_phase6j_artifact_after_consumer_run("sim-inputs", research_findings=[])

        sim_dir = tmp_path / "sim-inputs"
        assert (sim_dir / "golden_flow_checks.json").exists()
        assert (sim_dir / "evidence_gatekeeping_results.json").exists()
        assert (sim_dir / "evidence_validation_results.json").exists()
        assert (sim_dir / "society" / "reasoning_traces.jsonl").exists()
        artifact = json.loads((sim_dir / "phase6j_calibration_artifact.json").read_text(encoding="utf-8"))
        assert artifact["phase7_entry_decision"] == "BLOCKED"
        assert artifact["artifact_build_inputs"]["golden_flow_checks"]["present"] is True

    def test_runner_quick_input_helper_writes_rules_reasoning_traces_when_missing(
        self,
        monkeypatch,
        tmp_path,
    ):
        from app.services.simulation_runner import (
            RunnerStatus,
            SimulationRunState,
            RoundSummary,
            AgentAction,
            SimulationRunner,
        )

        monkeypatch.setattr(SimulationRunner, "RUN_STATE_DIR", str(tmp_path))
        state = SimulationRunState(
            simulation_id="sim-quick-trace",
            runner_status=RunnerStatus.COMPLETED,
            current_round=1,
            total_rounds=1,
        )
        round_summary = RoundSummary(round_num=0, start_time="2026-05-07T00:00:00")
        round_summary.actions.append(
            AgentAction(
                round_num=0,
                timestamp="2026-05-07T00:00:00",
                platform="reddit",
                agent_id=1,
                agent_name="测试消费者",
                action_type="CONSUMER_REACTION",
                action_args={},
                result="先观望。",
                success=True,
            )
        )
        state.rounds = [round_summary]
        monkeypatch.setattr(SimulationRunner, "get_run_state", lambda sim_id: state)

        SimulationRunner._write_phase6j_calibration_inputs("sim-quick-trace", research_findings=[])

        trace_lines = (tmp_path / "sim-quick-trace" / "society" / "reasoning_traces.jsonl").read_text(
            encoding="utf-8"
        ).splitlines()
        traces = [json.loads(line) for line in trace_lines if line.strip()]
        assert traces
        assert traces[0]["source"] == "society_runtime"
        assert traces[0]["reasoning_backend"] == "rules"
        assert traces[0]["llm_invoked"] is False

    def test_runner_input_helper_does_not_overwrite_existing_society_reasoning_traces(
        self,
        monkeypatch,
        tmp_path,
    ):
        from app.services.simulation_runner import RunnerStatus, SimulationRunState, SimulationRunner

        monkeypatch.setattr(SimulationRunner, "RUN_STATE_DIR", str(tmp_path))
        sim_dir = tmp_path / "sim-standard" / "society"
        sim_dir.mkdir(parents=True, exist_ok=True)
        existing = {
            "reasoning_backend": "llm",
            "llm_invoked": True,
            "source": "society_runtime",
            "fallback_reason": "",
            "model": "fake",
            "latency_ms": 1,
            "reasoning_summary": "existing",
        }
        (sim_dir / "reasoning_traces.jsonl").write_text(
            json.dumps(existing, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        state = SimulationRunState(
            simulation_id="sim-standard",
            runner_status=RunnerStatus.COMPLETED,
            current_round=1,
            total_rounds=1,
            society_rounds_completed=1,
        )
        monkeypatch.setattr(SimulationRunner, "get_run_state", lambda sim_id: state)

        SimulationRunner._write_phase6j_calibration_inputs("sim-standard", research_findings=[])

        trace_lines = (sim_dir / "reasoning_traces.jsonl").read_text(encoding="utf-8").splitlines()
        assert len(trace_lines) == 1
        assert json.loads(trace_lines[0])["reasoning_summary"] == "existing"
