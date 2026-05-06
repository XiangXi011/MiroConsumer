"""SQLAlchemy-specific repository tests.

These exercise implementation details specific to the SQLAlchemy backend
(e.g., JSON column round-trips, session handling).
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from app.repositories.sqlalchemy import (
    metadata,
    SQLAlchemyProjectRepository,
    SQLAlchemySimulationRepository,
    SQLAlchemyReportRepository,
)
from app.contracts.errors import ConcurrencyConflictError
from app.services.report_agent import Report, ReportStatus


@pytest.fixture
def in_memory_engine():
    engine = create_engine("sqlite:///:memory:", poolclass=__import__("sqlalchemy.pool").pool.StaticPool)
    metadata.create_all(engine)
    return engine


@pytest.fixture
def session_factory(in_memory_engine):
    return sessionmaker(bind=in_memory_engine, class_=Session)


class TestProjectJsonColumns:
    def test_project_data_column_stores_complex_nested_json(self, session_factory):
        repo = SQLAlchemyProjectRepository(session_factory=session_factory)
        project = repo.create_project(name="JSON Test")
        payload = {
            "ontology": {"entities": [{"id": "e1", "props": {"a": 1}}]},
            "consumer_context": {"deep": {"nested": [1, 2, 3]}},
        }
        repo.save_consumer_graph_payload(project.project_id, payload)
        loaded = repo.load_consumer_graph_payload(project.project_id)
        assert loaded == payload

    def test_extracted_text_empty_string_round_trip(self, session_factory):
        repo = SQLAlchemyProjectRepository(session_factory=session_factory)
        project = repo.create_project(name="Empty Text")
        repo.save_extracted_text(project.project_id, "")
        text = repo.get_extracted_text(project.project_id)
        assert text == ""


class TestSimulationJsonColumns:
    def test_simulation_config_complex_dict_round_trip(self, session_factory):
        repo = SQLAlchemySimulationRepository(session_factory=session_factory)
        state = repo.create_simulation(project_id="p1", graph_id="g1")
        config = {
            "agent_configs": [{"agent_id": 1, "active_hours": list(range(8, 23))}],
            "nested": {"a": {"b": [1, 2, 3]}},
        }
        repo.save_simulation_config(state.simulation_id, config)
        loaded = repo.load_simulation_config(state.simulation_id)
        assert loaded == config

    def test_consumer_config_with_research_findings_round_trip(self, session_factory):
        repo = SQLAlchemySimulationRepository(session_factory=session_factory)
        state = repo.create_simulation(project_id="p1", graph_id="g1")
        config = {
            "consumer_brief": {"research_goal": "test"},
            "research_findings": [
                {"id": "f1", "source_label": "auto_enrich"},
            ],
        }
        repo.save_consumer_config(state.simulation_id, config)
        loaded = repo.load_consumer_config(state.simulation_id)
        assert loaded == config

    def test_list_simulations_returns_simulation_state_objects(self, session_factory):
        repo = SQLAlchemySimulationRepository(session_factory=session_factory)
        s1 = repo.create_simulation(project_id="p1", graph_id="g1")
        s2 = repo.create_simulation(project_id="p2", graph_id="g2")
        sims = repo.list_simulations()
        assert len(sims) == 2
        for sim in sims:
            assert hasattr(sim, "simulation_id")
            assert hasattr(sim, "project_id")
            assert hasattr(sim, "status")


class TestOptimisticVersioning:
    def test_simulation_stale_update_raises_concurrency_conflict(self, session_factory):
        repo = SQLAlchemySimulationRepository(session_factory=session_factory)
        created = repo.create_simulation(project_id="p1", graph_id="g1")
        first = repo.get_simulation(created.simulation_id)
        second = repo.get_simulation(created.simulation_id)

        first.entities_count = 10
        repo.save_simulation(first)

        second.entities_count = 20
        with pytest.raises(ConcurrencyConflictError) as exc_info:
            repo.save_simulation(second)

        assert exc_info.value.reason == "version_conflict"

    def test_project_stale_update_raises_concurrency_conflict(self, session_factory):
        repo = SQLAlchemyProjectRepository(session_factory=session_factory)
        created = repo.create_project(name="Version")
        first = repo.get_project(created.project_id)
        second = repo.get_project(created.project_id)

        first.name = "first"
        repo.save_project(first)

        second.name = "second"
        with pytest.raises(ConcurrencyConflictError):
            repo.save_project(second)

    def test_report_stale_update_raises_concurrency_conflict(self, session_factory):
        repo = SQLAlchemyReportRepository(session_factory=session_factory)
        report = Report(
            report_id="report_version",
            simulation_id="sim_version",
            graph_id="g1",
            simulation_requirement="test",
            status=ReportStatus.PENDING,
        )
        repo.save_report(report)
        first = repo.get_report("report_version")
        second = repo.get_report("report_version")

        first.markdown_content = "first"
        repo.save_report(first)

        second.markdown_content = "second"
        with pytest.raises(ConcurrencyConflictError):
            repo.save_report(second)
