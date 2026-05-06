"""Contract tests for SQLAlchemy repository implementations.

These tests verify that SQLAlchemy-backed repositories satisfy the same
interface contracts as filesystem-backed ones. They use an in-memory SQLite
engine with StaticPool so no PostgreSQL server is required.
"""

import uuid
from typing import Any, Dict, List, Optional

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from app.repositories.sqlalchemy import (
    metadata,
    SQLAlchemyProjectRepository,
    SQLAlchemySimulationRepository,
    SQLAlchemyBranchRepository,
    SQLAlchemyReportRepository,
    SQLAlchemyBenchmarkRepository,
    SQLAlchemyConsumerStateRepository,
    SQLAlchemyConsumerProjectResearchProvider,
)
from app.repositories import ConsumerProjectResearchContext
from app.models.project import Project, ProjectStatus
from app.services.simulation_manager import SimulationState, SimulationStatus
from app.services.consumer.intervention_manager import ConsumerBranch, ConsumerIntervention
from app.services.report_agent import Report, ReportStatus, ReportOutline, ReportSection


@pytest.fixture
def in_memory_engine():
    """Create a fresh in-memory SQLite engine."""
    engine = create_engine("sqlite:///:memory:", poolclass=__import__("sqlalchemy.pool").pool.StaticPool)
    metadata.create_all(engine)
    return engine


@pytest.fixture
def session_factory(in_memory_engine):
    """Create a session factory bound to the in-memory engine."""
    return sessionmaker(bind=in_memory_engine, class_=Session)


@pytest.fixture
def project_repo(session_factory):
    return SQLAlchemyProjectRepository(session_factory=session_factory)


@pytest.fixture
def simulation_repo(session_factory):
    return SQLAlchemySimulationRepository(session_factory=session_factory)


@pytest.fixture
def branch_repo(session_factory):
    return SQLAlchemyBranchRepository(session_factory=session_factory)


@pytest.fixture
def report_repo(session_factory):
    return SQLAlchemyReportRepository(session_factory=session_factory)


@pytest.fixture
def benchmark_repo(session_factory):
    return SQLAlchemyBenchmarkRepository(session_factory=session_factory)


@pytest.fixture
def consumer_state_repo(session_factory):
    return SQLAlchemyConsumerStateRepository(session_factory=session_factory)


@pytest.fixture
def consumer_research_provider(session_factory):
    return SQLAlchemyConsumerProjectResearchProvider(session_factory=session_factory)


# ── Project Repository ─────────────────────────────────────────


class TestProjectRepository:
    def test_create_project_returns_project_with_id(self, project_repo):
        project = project_repo.create_project(name="Test Project")
        assert project is not None
        assert project.project_id is not None
        assert project.name == "Test Project"
        assert project.status == ProjectStatus.CREATED

    def test_get_project_returns_project(self, project_repo):
        created = project_repo.create_project(name="Get Test")
        fetched = project_repo.get_project(created.project_id)
        assert fetched is not None
        assert fetched.project_id == created.project_id
        assert fetched.name == "Get Test"

    def test_get_missing_project_returns_none(self, project_repo):
        assert project_repo.get_project("nonexistent") is None

    def test_save_project_updates_fields(self, project_repo):
        project = project_repo.create_project(name="Before")
        project.name = "After"
        project_repo.save_project(project)
        fetched = project_repo.get_project(project.project_id)
        assert fetched.name == "After"

    def test_list_projects_returns_projects(self, project_repo):
        p1 = project_repo.create_project(name="P1")
        p2 = project_repo.create_project(name="P2")
        projects = project_repo.list_projects()
        ids = {p.project_id for p in projects}
        assert p1.project_id in ids
        assert p2.project_id in ids

    def test_delete_project_removes_project(self, project_repo):
        project = project_repo.create_project(name="To Delete")
        result = project_repo.delete_project(project.project_id)
        assert result is True
        assert project_repo.get_project(project.project_id) is None

    def test_delete_project_cascades_simulation_branch_report_state(
        self,
        project_repo,
        simulation_repo,
        branch_repo,
        report_repo,
    ):
        project = project_repo.create_project(name="Cascade Delete")
        sim = simulation_repo.create_simulation(project_id=project.project_id, graph_id="g1")
        branch = branch_repo.create_branch(sim.simulation_id, "branch", fork_round=0)
        branch_repo.add_intervention(sim.simulation_id, branch.branch_id, "evidence_reveal", {"msg": "x"})
        report = Report(
            report_id="rep_cascade",
            simulation_id=sim.simulation_id,
            graph_id="g1",
            simulation_requirement="test",
            status=ReportStatus.COMPLETED,
        )
        report_repo.save_report(report)

        assert project_repo.delete_project(project.project_id) is True

        assert simulation_repo.get_simulation(sim.simulation_id) is None
        assert branch_repo.list_branches(sim.simulation_id) == []
        assert branch_repo.list_interventions(sim.simulation_id) == []
        assert report_repo.get_report("rep_cascade") is None

    def test_delete_missing_project_returns_false(self, project_repo):
        assert project_repo.delete_project("nonexistent") is False

    def test_extracted_text_round_trip(self, project_repo):
        project = project_repo.create_project(name="Text Test")
        project_repo.save_extracted_text(project.project_id, "hello world")
        text = project_repo.get_extracted_text(project.project_id)
        assert text == "hello world"

    def test_get_extracted_text_missing_returns_none(self, project_repo):
        assert project_repo.get_extracted_text("nonexistent") is None

    def test_consumer_graph_payload_round_trip(self, project_repo):
        project = project_repo.create_project(name="Graph Test")
        payload = {"nodes": [{"id": "n1", "label": "A"}]}
        project_repo.save_consumer_graph_payload(project.project_id, payload)
        loaded = project_repo.load_consumer_graph_payload(project.project_id)
        assert loaded == payload

    def test_load_consumer_graph_payload_missing_returns_none(self, project_repo):
        assert project_repo.load_consumer_graph_payload("nonexistent") is None


# ── Simulation Repository ──────────────────────────────────────


class TestSimulationRepository:
    def test_create_simulation_returns_state(self, simulation_repo):
        state = simulation_repo.create_simulation(
            project_id="proj_123",
            graph_id="graph_456",
            project_type="default",
            enable_twitter=True,
            enable_reddit=True,
        )
        assert state is not None
        assert state.simulation_id is not None
        assert state.project_id == "proj_123"
        assert state.graph_id == "graph_456"
        assert state.status == SimulationStatus.CREATED

    def test_get_simulation_returns_state(self, simulation_repo):
        created = simulation_repo.create_simulation(
            project_id="proj_123", graph_id="graph_456"
        )
        fetched = simulation_repo.get_simulation(created.simulation_id)
        assert fetched is not None
        assert fetched.simulation_id == created.simulation_id

    def test_get_missing_simulation_returns_none(self, simulation_repo):
        assert simulation_repo.get_simulation("nonexistent") is None

    def test_save_simulation_updates_fields(self, simulation_repo):
        state = simulation_repo.create_simulation(
            project_id="proj_123", graph_id="graph_456"
        )
        state.entities_count = 42
        simulation_repo.save_simulation(state)
        fetched = simulation_repo.get_simulation(state.simulation_id)
        assert fetched.entities_count == 42

    def test_list_simulations_returns_all(self, simulation_repo):
        s1 = simulation_repo.create_simulation(project_id="p1", graph_id="g1")
        s2 = simulation_repo.create_simulation(project_id="p2", graph_id="g2")
        sims = simulation_repo.list_simulations()
        ids = {s.simulation_id for s in sims}
        assert s1.simulation_id in ids
        assert s2.simulation_id in ids

    def test_list_simulations_filtered_by_project(self, simulation_repo):
        s1 = simulation_repo.create_simulation(project_id="p1", graph_id="g1")
        simulation_repo.create_simulation(project_id="p2", graph_id="g2")
        sims = simulation_repo.list_simulations(project_id="p1")
        assert len(sims) == 1
        assert sims[0].simulation_id == s1.simulation_id

    def test_delete_simulation_removes_simulation(self, simulation_repo):
        state = simulation_repo.create_simulation(project_id="p1", graph_id="g1")
        result = simulation_repo.delete_simulation(state.simulation_id)
        assert result is True
        assert simulation_repo.get_simulation(state.simulation_id) is None

    def test_delete_simulation_cascades_branch_report_state(
        self,
        simulation_repo,
        branch_repo,
        report_repo,
    ):
        state = simulation_repo.create_simulation(project_id="p1", graph_id="g1")
        branch = branch_repo.create_branch(state.simulation_id, "branch", fork_round=0)
        branch_repo.add_intervention(state.simulation_id, branch.branch_id, "evidence_reveal", {"msg": "x"})
        report = Report(
            report_id="rep_sim_cascade",
            simulation_id=state.simulation_id,
            graph_id="g1",
            simulation_requirement="test",
            status=ReportStatus.COMPLETED,
        )
        report_repo.save_report(report)

        assert simulation_repo.delete_simulation(state.simulation_id) is True

        assert branch_repo.list_branches(state.simulation_id) == []
        assert branch_repo.list_interventions(state.simulation_id) == []
        assert report_repo.get_report("rep_sim_cascade") is None

    def test_delete_missing_simulation_returns_false(self, simulation_repo):
        assert simulation_repo.delete_simulation("nonexistent") is False

    def test_simulation_config_round_trip(self, simulation_repo):
        state = simulation_repo.create_simulation(project_id="p1", graph_id="g1")
        config = {"max_rounds": 10, "platforms": ["reddit"]}
        simulation_repo.save_simulation_config(state.simulation_id, config)
        loaded = simulation_repo.load_simulation_config(state.simulation_id)
        assert loaded == config
        assert simulation_repo.get_simulation_config(state.simulation_id) == config

    def test_load_simulation_config_missing_returns_none(self, simulation_repo):
        state = simulation_repo.create_simulation(project_id="p1", graph_id="g1")
        assert simulation_repo.load_simulation_config(state.simulation_id) is None
        assert simulation_repo.get_simulation_config(state.simulation_id) is None

    def test_consumer_config_round_trip(self, simulation_repo):
        state = simulation_repo.create_simulation(project_id="p1", graph_id="g1")
        config = {"consumer_mode": True, "brief": "test"}
        simulation_repo.save_consumer_config(state.simulation_id, config)
        loaded = simulation_repo.load_consumer_config(state.simulation_id)
        assert loaded == config

    def test_load_consumer_config_missing_returns_none(self, simulation_repo):
        state = simulation_repo.create_simulation(project_id="p1", graph_id="g1")
        assert simulation_repo.load_consumer_config(state.simulation_id) is None

    def test_get_profiles_returns_empty_list_when_absent(self, simulation_repo):
        state = simulation_repo.create_simulation(project_id="p1", graph_id="g1")
        profiles = simulation_repo.get_profiles(state.simulation_id, platform="reddit")
        assert profiles == []

    def test_get_prepare_manifest_returns_none(self, simulation_repo):
        state = simulation_repo.create_simulation(project_id="p1", graph_id="g1")
        assert simulation_repo.get_prepare_manifest(state.simulation_id) is None

    def test_record_manifest_reuse_returns_none(self, simulation_repo):
        state = simulation_repo.create_simulation(project_id="p1", graph_id="g1")
        assert simulation_repo.record_manifest_reuse(state.simulation_id) is None


# ── Branch Repository ──────────────────────────────────────────


class TestBranchRepository:
    def _make_sim(self, simulation_repo):
        return simulation_repo.create_simulation(project_id="p1", graph_id="g1")

    def test_create_branch_returns_branch(self, branch_repo, simulation_repo):
        sim = self._make_sim(simulation_repo)
        branch = branch_repo.create_branch(
            simulation_id=sim.simulation_id,
            name="test-branch",
            fork_round=3,
            description="A test branch",
        )
        assert branch is not None
        assert branch.branch_id is not None
        assert branch.simulation_id == sim.simulation_id
        assert branch.name == "test-branch"
        assert branch.fork_round == 3
        assert branch.status == "active"

    def test_get_branch_returns_branch(self, branch_repo, simulation_repo):
        sim = self._make_sim(simulation_repo)
        created = branch_repo.create_branch(
            simulation_id=sim.simulation_id, name="b1", fork_round=1
        )
        fetched = branch_repo.get_branch(sim.simulation_id, created.branch_id)
        assert fetched is not None
        assert fetched.branch_id == created.branch_id

    def test_get_missing_branch_returns_none(self, branch_repo, simulation_repo):
        sim = self._make_sim(simulation_repo)
        assert branch_repo.get_branch(sim.simulation_id, "nonexistent") is None

    def test_list_branches_for_simulation(self, branch_repo, simulation_repo):
        sim = self._make_sim(simulation_repo)
        b1 = branch_repo.create_branch(sim.simulation_id, "b1", fork_round=1)
        b2 = branch_repo.create_branch(sim.simulation_id, "b2", fork_round=2)
        branches = branch_repo.list_branches(sim.simulation_id)
        ids = {b.branch_id for b in branches}
        assert b1.branch_id in ids
        assert b2.branch_id in ids

    def test_update_branch_status(self, branch_repo, simulation_repo):
        sim = self._make_sim(simulation_repo)
        branch = branch_repo.create_branch(sim.simulation_id, "b1", fork_round=1)
        updated = branch_repo.update_branch_status(
            sim.simulation_id, branch.branch_id, "completed"
        )
        assert updated is not None
        assert updated.status == "completed"
        fetched = branch_repo.get_branch(sim.simulation_id, branch.branch_id)
        assert fetched.status == "completed"

    def test_update_branch_status_missing_returns_none(self, branch_repo, simulation_repo):
        sim = self._make_sim(simulation_repo)
        assert branch_repo.update_branch_status(sim.simulation_id, "nonexistent", "completed") is None

    def test_add_and_list_interventions(self, branch_repo, simulation_repo):
        sim = self._make_sim(simulation_repo)
        branch = branch_repo.create_branch(sim.simulation_id, "b1", fork_round=1)
        intervention = branch_repo.add_intervention(
            simulation_id=sim.simulation_id,
            branch_id=branch.branch_id,
            intervention_type="evidence_reveal",
            payload={"claim": "test"},
            target_round=5,
        )
        assert intervention is not None
        assert intervention.intervention_id is not None
        interventions = branch_repo.list_interventions(sim.simulation_id, branch_id=branch.branch_id)
        assert len(interventions) == 1
        assert interventions[0].intervention_type == "evidence_reveal"

    def test_list_interventions_without_branch_id(self, branch_repo, simulation_repo):
        sim = self._make_sim(simulation_repo)
        b1 = branch_repo.create_branch(sim.simulation_id, "b1", fork_round=1)
        b2 = branch_repo.create_branch(sim.simulation_id, "b2", fork_round=2)
        branch_repo.add_intervention(sim.simulation_id, b1.branch_id, "evidence_reveal", {})
        branch_repo.add_intervention(sim.simulation_id, b2.branch_id, "clarification_injection", {})
        all_interventions = branch_repo.list_interventions(sim.simulation_id)
        assert len(all_interventions) == 2

    def test_run_status_round_trip(self, branch_repo, simulation_repo):
        sim = self._make_sim(simulation_repo)
        branch = branch_repo.create_branch(sim.simulation_id, "b1", fork_round=1)
        status_data = {"status": "running", "current_round": 2}
        branch_repo.update_branch_run_status(sim.simulation_id, branch.branch_id, status_data)
        loaded = branch_repo.get_branch_run_status(sim.simulation_id, branch.branch_id)
        assert loaded["status"] == "running"
        assert loaded["current_round"] == 2

    def test_get_branch_run_status_missing_returns_default(self, branch_repo, simulation_repo):
        sim = self._make_sim(simulation_repo)
        branch = branch_repo.create_branch(sim.simulation_id, "b1", fork_round=1)
        status = branch_repo.get_branch_run_status(sim.simulation_id, branch.branch_id)
        assert status["status"] == "idle"
        assert status["branch_id"] == branch.branch_id
        assert status["simulation_id"] == sim.simulation_id

    def test_build_comparison_context_keys(self, branch_repo, simulation_repo):
        sim = self._make_sim(simulation_repo)
        branch = branch_repo.create_branch(sim.simulation_id, "b1", fork_round=1)
        ctx = branch_repo.build_comparison_context(sim.simulation_id, branch.branch_id)
        assert "branch_id" in ctx
        assert "fork_round" in ctx
        assert "interventions" in ctx
        assert "base_summary" in ctx
        assert "branch_summary" in ctx


# ── Report Repository ──────────────────────────────────────────


class TestReportRepository:
    def _make_report(self, report_id: str = "rep_1") -> Report:
        return Report(
            report_id=report_id,
            simulation_id="sim_1",
            graph_id="graph_1",
            simulation_requirement="test requirement",
            status=ReportStatus.PENDING,
            created_at="2024-01-01T00:00:00",
        )

    def test_save_and_get_report(self, report_repo):
        report = self._make_report("rep_save_get")
        report_repo.save_report(report)
        fetched = report_repo.get_report("rep_save_get")
        assert fetched is not None
        assert fetched.report_id == "rep_save_get"
        assert fetched.simulation_id == "sim_1"
        assert fetched.status == ReportStatus.PENDING

    def test_get_missing_report_returns_none(self, report_repo):
        assert report_repo.get_report("nonexistent") is None

    def test_get_report_by_simulation(self, report_repo):
        report = self._make_report("rep_by_sim")
        report_repo.save_report(report)
        fetched = report_repo.get_report_by_simulation("sim_1")
        assert fetched is not None
        assert fetched.simulation_id == "sim_1"

    def test_list_reports(self, report_repo):
        r1 = self._make_report("rep_a")
        r1.simulation_id = "sim_a"
        r2 = self._make_report("rep_b")
        r2.simulation_id = "sim_b"
        report_repo.save_report(r1)
        report_repo.save_report(r2)
        reports = report_repo.list_reports()
        ids = {r.report_id for r in reports}
        assert "rep_a" in ids
        assert "rep_b" in ids

    def test_list_reports_filtered_by_simulation(self, report_repo):
        r1 = self._make_report("rep_f1")
        r1.simulation_id = "sim_filter"
        r2 = self._make_report("rep_f2")
        r2.simulation_id = "sim_other"
        report_repo.save_report(r1)
        report_repo.save_report(r2)
        reports = report_repo.list_reports(simulation_id="sim_filter")
        assert len(reports) == 1
        assert reports[0].report_id == "rep_f1"

    def test_save_outline_and_get_report(self, report_repo):
        report = self._make_report("rep_outline")
        report_repo.save_report(report)
        outline = ReportOutline(
            title="Test Report",
            summary="A summary",
            sections=[ReportSection(title="Section 1", content="Content 1")],
        )
        report_repo.save_outline("rep_outline", outline)
        fetched = report_repo.get_report("rep_outline")
        assert fetched.outline is not None
        assert fetched.outline.title == "Test Report"

    def test_save_section(self, report_repo):
        report = self._make_report("rep_section")
        report_repo.save_report(report)
        section = ReportSection(title="Section 1", content="Some content")
        path = report_repo.save_section("rep_section", 1, section)
        assert path is not None

    def test_update_and_get_progress(self, report_repo):
        report = self._make_report("rep_progress")
        report_repo.save_report(report)
        report_repo.update_progress(
            "rep_progress",
            status="generating",
            progress=50,
            message="Halfway done",
            current_section="Section 1",
            completed_sections=["Intro"],
        )
        progress = report_repo.get_progress("rep_progress")
        assert progress is not None
        assert progress["status"] == "generating"
        assert progress["progress"] == 50
        assert progress["message"] == "Halfway done"
        assert progress["current_section"] == "Section 1"
        assert progress["completed_sections"] == ["Intro"]

    def test_get_progress_missing_returns_none(self, report_repo):
        assert report_repo.get_progress("nonexistent") is None

    def test_assemble_full_report(self, report_repo):
        report = self._make_report("rep_assemble")
        report_repo.save_report(report)
        section = ReportSection(title="Intro", content="Hello world")
        report_repo.save_section("rep_assemble", 1, section)
        outline = ReportOutline(
            title="Full Report",
            summary="A full report",
            sections=[ReportSection(title="Intro", content="Hello world")],
        )
        md = report_repo.assemble_full_report("rep_assemble", outline)
        assert "Full Report" in md
        assert "Hello world" in md

    def test_delete_report(self, report_repo):
        report = self._make_report("rep_del")
        report_repo.save_report(report)
        result = report_repo.delete_report("rep_del")
        assert result is True
        assert report_repo.get_report("rep_del") is None

    def test_delete_missing_report_returns_false(self, report_repo):
        assert report_repo.delete_report("nonexistent") is False

    def test_get_agent_log(self, report_repo):
        report = self._make_report("rep_agent_log")
        report_repo.save_report(report)
        result = report_repo.get_agent_log("rep_agent_log")
        assert "logs" in result
        assert result["logs"] == []

    def test_get_console_log(self, report_repo):
        report = self._make_report("rep_console_log")
        report_repo.save_report(report)
        result = report_repo.get_console_log("rep_console_log")
        assert "logs" in result
        assert result["logs"] == []


# ── Benchmark Repository ───────────────────────────────────────


class TestBenchmarkRepository:
    def test_register_benchmark(self, benchmark_repo):
        bench = benchmark_repo.register_benchmark(
            name="Test Benchmark",
            source_pack_lineage="pack/lineage",
            expected_signals={"acceptance_band": "positive_lean"},
        )
        assert bench is not None
        assert "benchmark_id" in bench
        assert bench["name"] == "Test Benchmark"
        assert bench["expected_signals"]["acceptance_band"] == "positive_lean"

    def test_get_benchmark(self, benchmark_repo):
        registered = benchmark_repo.register_benchmark(
            name="Get Test", source_pack_lineage="l1", expected_signals={}
        )
        fetched = benchmark_repo.get_benchmark(registered["benchmark_id"])
        assert fetched is not None
        assert fetched["benchmark_id"] == registered["benchmark_id"]

    def test_get_missing_benchmark_returns_none(self, benchmark_repo):
        assert benchmark_repo.get_benchmark("nonexistent") is None

    def test_list_benchmarks(self, benchmark_repo):
        benchmark_repo.register_benchmark("B1", "l1", {})
        benchmark_repo.register_benchmark("B2", "l2", {})
        benches = benchmark_repo.list_benchmarks()
        names = {b["name"] for b in benches}
        assert "B1" in names
        assert "B2" in names

    def test_delete_benchmark(self, benchmark_repo):
        registered = benchmark_repo.register_benchmark("Del", "l1", {})
        result = benchmark_repo.delete_benchmark(registered["benchmark_id"])
        assert result is True
        assert benchmark_repo.get_benchmark(registered["benchmark_id"]) is None

    def test_delete_missing_benchmark_returns_false(self, benchmark_repo):
        assert benchmark_repo.delete_benchmark("nonexistent") is False

    def test_replay_benchmark(self, benchmark_repo):
        registered = benchmark_repo.register_benchmark(
            "Replay Test", "l1", {"acceptance_band": "positive_lean"}
        )
        report_context = {
            "summary": {"post_propagation_acceptance": {"positive": 0.6}},
            "top_resonance_points": ["r1"],
            "top_risk_points": ["risk1"],
            "top_misreads": [],
            "top_clarification_opportunities": [],
            "cascade_metrics": {"narrative_takeover_score": 0.3, "cross_community_event_count": 1},
        }
        replay = benchmark_repo.replay_benchmark(
            benchmark_id=registered["benchmark_id"],
            report_context=report_context,
        )
        assert replay is not None
        assert "replay_id" in replay
        assert replay["benchmark_id"] == registered["benchmark_id"]

    def test_get_replay_result(self, benchmark_repo):
        registered = benchmark_repo.register_benchmark("Replay Get", "l1", {})
        report_context = {
            "summary": {"post_propagation_acceptance": {"positive": 0.6}},
            "top_resonance_points": [],
            "top_risk_points": [],
            "top_misreads": [],
            "top_clarification_opportunities": [],
            "cascade_metrics": {},
        }
        replay = benchmark_repo.replay_benchmark(
            benchmark_id=registered["benchmark_id"],
            report_context=report_context,
        )
        fetched = benchmark_repo.get_replay_result(replay["replay_id"])
        assert fetched is not None
        assert fetched["replay_id"] == replay["replay_id"]

    def test_get_replay_result_missing_returns_none(self, benchmark_repo):
        assert benchmark_repo.get_replay_result("nonexistent") is None

    def test_list_replay_results(self, benchmark_repo):
        registered = benchmark_repo.register_benchmark("Replay List", "l1", {})
        report_context = {
            "summary": {"post_propagation_acceptance": {"positive": 0.6}},
            "top_resonance_points": [],
            "top_risk_points": [],
            "top_misreads": [],
            "top_clarification_opportunities": [],
            "cascade_metrics": {},
        }
        r1 = benchmark_repo.replay_benchmark(registered["benchmark_id"], report_context)
        r2 = benchmark_repo.replay_benchmark(registered["benchmark_id"], report_context)
        replays = benchmark_repo.list_replay_results(registered["benchmark_id"])
        ids = {r["replay_id"] for r in replays}
        assert r1["replay_id"] in ids
        assert r2["replay_id"] in ids


# ── Consumer State Repository ──────────────────────────────────


class TestConsumerStateRepository:
    def test_load_consumer_config_reads_from_simulations_table(self, consumer_state_repo, simulation_repo):
        state = simulation_repo.create_simulation(project_id="p1", graph_id="g1")
        config = {"consumer_mode": True, "brief": "test brief"}
        simulation_repo.save_consumer_config(state.simulation_id, config)
        loaded = consumer_state_repo.load_consumer_config(state.simulation_id)
        assert loaded == config

    def test_load_consumer_config_missing_returns_empty_dict(self, consumer_state_repo, simulation_repo):
        state = simulation_repo.create_simulation(project_id="p1", graph_id="g1")
        loaded = consumer_state_repo.load_consumer_config(state.simulation_id)
        assert loaded == {}

    def test_load_consumer_rounds_empty_when_absent(self, consumer_state_repo, simulation_repo):
        state = simulation_repo.create_simulation(project_id="p1", graph_id="g1")
        rounds = consumer_state_repo.load_consumer_rounds(state.simulation_id)
        assert rounds == []

    def test_load_brief_none_when_absent(self, consumer_state_repo, simulation_repo):
        state = simulation_repo.create_simulation(project_id="p1", graph_id="g1")
        assert consumer_state_repo.load_brief(state.simulation_id) is None

    def test_load_research_findings_empty_when_absent(self, consumer_state_repo, simulation_repo):
        state = simulation_repo.create_simulation(project_id="p1", graph_id="g1")
        findings = consumer_state_repo.load_research_findings(state.simulation_id)
        assert findings == []


# ── Consumer Project Research Provider ─────────────────────────


class TestConsumerProjectResearchProvider:
    def test_default_project_returns_not_consumer(self, consumer_research_provider, project_repo):
        project = project_repo.create_project(name="Default")
        ctx = consumer_research_provider.get_context(project.project_id)
        assert ctx.is_consumer_project is False
        assert ctx.brief_payload is None

    def test_consumer_project_returns_is_consumer_and_brief(self, consumer_research_provider, project_repo):
        project = project_repo.create_project(name="Consumer")
        # Set project_type to consumer_test via save
        project.project_type = "consumer_test"
        project.consumer_brief = {"research_goal": "test goal"}
        project_repo.save_project(project)
        ctx = consumer_research_provider.get_context(project.project_id)
        assert ctx.is_consumer_project is True
        assert ctx.brief_payload == {"research_goal": "test goal"}

    def test_missing_project_returns_not_consumer(self, consumer_research_provider):
        ctx = consumer_research_provider.get_context("nonexistent")
        assert ctx.is_consumer_project is False
