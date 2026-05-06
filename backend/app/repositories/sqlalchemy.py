"""SQLAlchemy metadata and repository implementations.

Table definitions use the generic JSON type so the schema works with both
SQLite and PostgreSQL without requiring a PostgreSQL server in tests.
"""

import uuid
from typing import Any, Dict, List, Optional

from sqlalchemy import (
    Column,
    DateTime,
    Integer,
    MetaData,
    String,
    JSON,
    Table,
    create_engine,
    func,
    select,
    insert,
    update,
    delete,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import sessionmaker, Session

from . import (
    ConsumerProjectResearchContext,
    ConsumerProjectResearchProvider,
    ProjectRepository,
    ConsumerStateRepository,
    SimulationRepository,
    BranchRepository,
    ReportRepository,
    BenchmarkRepository,
)
from ..contracts.errors import ConcurrencyConflictError

metadata = MetaData()

# ── Shared column helpers ──────────────────────────────────────


def _shared_columns():
    return [
        Column("id", String(36), primary_key=True),
        Column("created_at", DateTime, server_default=func.now()),
        Column("updated_at", DateTime, server_default=func.now(), onupdate=func.now()),
        Column("version", Integer, nullable=False, default=1),
    ]


def _sim_child_columns():
    return [
        Column("simulation_id", String(36), nullable=False),
        Column("run_id", String(36), nullable=False),
    ]


def _json_type():
    return JSON().with_variant(JSONB, "postgresql")


# ── 20 table definitions ───────────────────────────────────────

projects = Table(
    "projects",
    metadata,
    *_shared_columns(),
    Column("name", String(255), nullable=False),
    Column("project_type", String(50), default="default"),
    Column("status", String(50), default="created"),
    Column("data", _json_type(), default=dict),
)

consumer_briefs = Table(
    "consumer_briefs",
    metadata,
    *_shared_columns(),
    Column("project_id", String(36), nullable=False),
    Column("payload", _json_type(), default=dict),
)

simulations = Table(
    "simulations",
    metadata,
    *_shared_columns(),
    Column("project_id", String(36), nullable=False),
    Column("graph_id", String(36)),
    Column("project_type", String(50), default="default"),
    Column("consumer_mode", Integer, default=0),
    Column("status", String(50), default="created"),
    Column("data", _json_type(), default=dict),
)

simulation_runs = Table(
    "simulation_runs",
    metadata,
    *_shared_columns(),
    *_sim_child_columns(),
    Column("status", String(50), default="created"),
    Column("data", _json_type(), default=dict),
)

society_agents = Table(
    "society_agents",
    metadata,
    *_shared_columns(),
    *_sim_child_columns(),
    Column("platform", String(50)),
    Column("persona_data", _json_type(), default=dict),
)

persona_packs = Table(
    "persona_packs",
    metadata,
    *_shared_columns(),
    Column("name", String(255), nullable=False),
    Column("lineage", String(255)),
    Column("config", _json_type(), default=dict),
)

round_snapshots = Table(
    "round_snapshots",
    metadata,
    *_shared_columns(),
    *_sim_child_columns(),
    Column("round_number", Integer, nullable=False),
    Column("snapshot_data", _json_type(), default=dict),
)

consumer_events = Table(
    "consumer_events",
    metadata,
    *_shared_columns(),
    *_sim_child_columns(),
    Column("event_type", String(100)),
    Column("payload", _json_type(), default=dict),
)

branches = Table(
    "branches",
    metadata,
    *_shared_columns(),
    *_sim_child_columns(),
    Column("name", String(255), nullable=False),
    Column("fork_round", Integer, nullable=False),
    Column("description", String(1000)),
    Column("parent_branch_id", String(36)),
    Column("status", String(50), default="active"),
    Column("data", _json_type(), default=dict),
)

interventions = Table(
    "interventions",
    metadata,
    *_shared_columns(),
    *_sim_child_columns(),
    Column("branch_id", String(36), nullable=False),
    Column("intervention_type", String(100)),
    Column("payload", _json_type(), default=dict),
    Column("target_round", Integer),
)

reports = Table(
    "reports",
    metadata,
    *_shared_columns(),
    *_sim_child_columns(),
    Column("report_type", String(50)),
    Column("status", String(50), default="pending"),
    Column("progress", Integer, default=0),
    Column("data", _json_type(), default=dict),
)

report_sections = Table(
    "report_sections",
    metadata,
    *_shared_columns(),
    *_sim_child_columns(),
    Column("report_id", String(36), nullable=False),
    Column("section_index", Integer, nullable=False),
    Column("title", String(500)),
    Column("content", _json_type(), default=dict),
)

research_assets = Table(
    "research_assets",
    metadata,
    *_shared_columns(),
    Column("project_id", String(36), nullable=False),
    Column("asset_type", String(100)),
    Column("payload", _json_type(), default=dict),
)

benchmarks = Table(
    "benchmarks",
    metadata,
    *_shared_columns(),
    Column("name", String(255), nullable=False),
    Column("source_pack_lineage", String(255)),
    Column("expected_signals", _json_type(), default=dict),
    Column("simulation_context", _json_type(), default=dict),
)

benchmark_replays = Table(
    "benchmark_replays",
    metadata,
    *_shared_columns(),
    Column("benchmark_id", String(36), nullable=False),
    Column("replay_result", _json_type(), default=dict),
)

memory_entries = Table(
    "memory_entries",
    metadata,
    *_shared_columns(),
    *_sim_child_columns(),
    Column("agent_id", String(36)),
    Column("memory_type", String(100)),
    Column("content", _json_type(), default=dict),
)

tasks = Table(
    "tasks",
    metadata,
    *_shared_columns(),
    *_sim_child_columns(),
    Column("task_type", String(100)),
    Column("status", String(50), default="PENDING"),
    Column("payload", _json_type(), default=dict),
)

task_attempts = Table(
    "task_attempts",
    metadata,
    *_shared_columns(),
    *_sim_child_columns(),
    Column("task_id", String(36), nullable=False),
    Column("attempt_number", Integer, nullable=False, default=1),
    Column("result", _json_type(), default=dict),
    Column("error", _json_type()),
)

dead_letters = Table(
    "dead_letters",
    metadata,
    *_shared_columns(),
    *_sim_child_columns(),
    Column("task_id", String(36)),
    Column("reason", String(500)),
    Column("payload", _json_type(), default=dict),
)

locks = Table(
    "locks",
    metadata,
    *_shared_columns(),
    *_sim_child_columns(),
    Column("resource_id", String(255), nullable=False),
    Column("lock_type", String(100)),
    Column("owner", String(255)),
    Column("expires_at", DateTime),
)


# ── Helper utilities ───────────────────────────────────────────


def _generate_id(prefix: str = "") -> str:
    suffix = uuid.uuid4().hex[:12]
    return f"{prefix}{suffix}"


def _now_iso() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()


def _attach_version(obj: Any, version: int) -> Any:
    try:
        setattr(obj, "version", int(version))
    except Exception:
        pass
    return obj


def _expected_version(obj: Any, current_version: int) -> int:
    version = getattr(obj, "version", None)
    return int(current_version if version is None else version)


def _raise_version_conflict(resource: str, resource_id: str) -> None:
    raise ConcurrencyConflictError(
        resource=resource,
        resource_id=resource_id,
        reason="version_conflict",
    )


def _delete_simulation_tree(session: Session, simulation_ids: List[str]) -> None:
    if not simulation_ids:
        return

    report_ids = [
        row[0]
        for row in session.execute(
            select(reports.c.id).where(reports.c.simulation_id.in_(simulation_ids))
        ).fetchall()
    ]
    if report_ids:
        session.execute(
            delete(report_sections).where(report_sections.c.report_id.in_(report_ids))
        )

    for table in (
        report_sections,
        reports,
        interventions,
        branches,
        consumer_events,
        round_snapshots,
        society_agents,
        simulation_runs,
        memory_entries,
        task_attempts,
        tasks,
        dead_letters,
        locks,
    ):
        session.execute(
            delete(table).where(table.c.simulation_id.in_(simulation_ids))
        )

    session.execute(delete(simulations).where(simulations.c.id.in_(simulation_ids)))


# ── SQLAlchemy repository implementations ──────────────────────

class SQLAlchemyProjectRepository(ProjectRepository):
    def __init__(self, session_factory: Optional[sessionmaker] = None) -> None:
        self._session_factory = session_factory

    def _session(self):
        return self._session_factory()

    def get_project(self, project_id: str) -> Optional[Any]:
        from ..models.project import Project, ProjectStatus
        with self._session() as session:
            row = session.execute(
                select(projects).where(projects.c.id == project_id)
            ).mappings().fetchone()
            if row is None:
                return None
            data = dict(row.get("data", {}) or {})
            return _attach_version(Project(
                project_id=row["id"],
                name=row["name"],
                status=ProjectStatus(row["status"]) if row["status"] else ProjectStatus.CREATED,
                created_at=data.get("created_at", ""),
                updated_at=data.get("updated_at", ""),
                project_type=row["project_type"] or "default",
                files=data.get("files", []),
                total_text_length=data.get("total_text_length", 0),
                ontology=data.get("ontology"),
                analysis_summary=data.get("analysis_summary"),
                graph_id=data.get("graph_id"),
                graph_build_task_id=data.get("graph_build_task_id"),
                simulation_requirement=data.get("simulation_requirement"),
                chunk_size=data.get("chunk_size", 500),
                chunk_overlap=data.get("chunk_overlap", 50),
                consumer_brief=data.get("consumer_brief"),
                consumer_context=data.get("consumer_context"),
                error=data.get("error"),
            ), row["version"])

    def save_project(self, project: Any) -> None:
        data = project.to_dict()
        # Strip top-level fields stored in explicit columns
        data.pop("project_id", None)
        data.pop("name", None)
        data.pop("project_type", None)
        data.pop("status", None)
        with self._session() as session:
            existing = session.execute(
                select(projects.c.id, projects.c.version).where(projects.c.id == project.project_id)
            ).fetchone()
            if existing:
                expected = _expected_version(project, existing.version)
                result = session.execute(
                    update(projects)
                    .where(projects.c.id == project.project_id)
                    .where(projects.c.version == expected)
                    .values(
                        name=project.name,
                        project_type=project.project_type or "default",
                        status=project.status.value if hasattr(project.status, "value") else str(project.status),
                        data=data,
                        version=expected + 1,
                    )
                )
                if result.rowcount == 0:
                    session.rollback()
                    _raise_version_conflict("project", project.project_id)
                _attach_version(project, expected + 1)
            else:
                session.execute(
                    insert(projects).values(
                        id=project.project_id,
                        name=project.name,
                        project_type=project.project_type or "default",
                        status=project.status.value if hasattr(project.status, "value") else str(project.status),
                        data=data,
                        version=1,
                    )
                )
                _attach_version(project, 1)
            session.commit()

    def create_project(self, name: str = "Unnamed Project") -> Any:
        from ..models.project import Project, ProjectStatus
        project_id = _generate_id("proj_")
        now = _now_iso()
        project = Project(
            project_id=project_id,
            name=name,
            status=ProjectStatus.CREATED,
            created_at=now,
            updated_at=now,
        )
        self.save_project(project)
        return project

    def delete_project(self, project_id: str) -> bool:
        with self._session() as session:
            simulation_ids = [
                row[0]
                for row in session.execute(
                    select(simulations.c.id).where(simulations.c.project_id == project_id)
                ).fetchall()
            ]
            _delete_simulation_tree(session, simulation_ids)
            session.execute(
                delete(consumer_briefs).where(consumer_briefs.c.project_id == project_id)
            )
            session.execute(
                delete(research_assets).where(research_assets.c.project_id == project_id)
            )
            result = session.execute(
                delete(projects).where(projects.c.id == project_id)
            )
            session.commit()
            return result.rowcount > 0

    def list_projects(self, limit: int = 50) -> List[Any]:
        with self._session() as session:
            rows = session.execute(
                select(projects).order_by(projects.c.created_at.desc()).limit(limit)
            ).mappings().all()
            return [self.get_project(row["id"]) for row in rows]

    def get_extracted_text(self, project_id: str) -> Optional[str]:
        with self._session() as session:
            row = session.execute(
                select(projects.c.data).where(projects.c.id == project_id)
            ).fetchone()
            if row is None or row[0] is None:
                return None
            data = row[0] if isinstance(row[0], dict) else {}
            return data.get("_extracted_text")

    def save_extracted_text(self, project_id: str, text: str) -> None:
        with self._session() as session:
            row = session.execute(
                select(projects.c.data).where(projects.c.id == project_id)
            ).fetchone()
            data = dict(row[0]) if row and row[0] else {}
            data["_extracted_text"] = text
            session.execute(
                update(projects).where(projects.c.id == project_id).values(data=data)
            )
            session.commit()

    def save_consumer_graph_payload(self, project_id: str, graph_payload: Dict[str, Any]) -> None:
        with self._session() as session:
            row = session.execute(
                select(projects.c.data).where(projects.c.id == project_id)
            ).fetchone()
            data = dict(row[0]) if row and row[0] else {}
            data["_consumer_graph_payload"] = graph_payload
            session.execute(
                update(projects).where(projects.c.id == project_id).values(data=data)
            )
            session.commit()

    def load_consumer_graph_payload(self, project_id: str) -> Optional[Dict[str, Any]]:
        with self._session() as session:
            row = session.execute(
                select(projects.c.data).where(projects.c.id == project_id)
            ).fetchone()
            if row is None or row[0] is None:
                return None
            data = row[0] if isinstance(row[0], dict) else {}
            return data.get("_consumer_graph_payload")


class SQLAlchemyConsumerStateRepository(ConsumerStateRepository):
    def __init__(self, session_factory: Optional[sessionmaker] = None) -> None:
        self._session_factory = session_factory

    def _session(self):
        return self._session_factory()

    def load_consumer_config(self, simulation_id: str) -> Dict[str, Any]:
        with self._session() as session:
            row = session.execute(
                select(simulations.c.data).where(simulations.c.id == simulation_id)
            ).fetchone()
            if row is None or row[0] is None:
                return {}
            data = row[0] if isinstance(row[0], dict) else {}
            return data.get("_consumer_config", {})

    def load_consumer_rounds(self, simulation_id: str) -> List[Dict[str, Any]]:
        return []

    def load_brief(self, simulation_id: str) -> Optional[Any]:
        return None

    def load_research_findings(self, simulation_id: str) -> List[Dict[str, Any]]:
        return []


class SQLAlchemyConsumerProjectResearchProvider(ConsumerProjectResearchProvider):
    def __init__(self, session_factory: Optional[sessionmaker] = None) -> None:
        self._session_factory = session_factory

    def _session(self):
        return self._session_factory()

    def get_context(self, project_id: str) -> ConsumerProjectResearchContext:
        with self._session() as session:
            row = session.execute(
                select(projects.c.project_type, projects.c.data).where(projects.c.id == project_id)
            ).fetchone()
            if row is None:
                return ConsumerProjectResearchContext(is_consumer_project=False)
            project_type = row[0] or "default"
            data = row[1] if isinstance(row[1], dict) else {}
            if project_type != "consumer_test":
                return ConsumerProjectResearchContext(is_consumer_project=False)
            brief_payload = data.get("consumer_brief")
            return ConsumerProjectResearchContext(
                is_consumer_project=True,
                brief_payload=brief_payload,
            )


class SQLAlchemySimulationRepository(SimulationRepository):
    def __init__(self, session_factory: Optional[sessionmaker] = None) -> None:
        self._session_factory = session_factory

    def _session(self):
        return self._session_factory()

    def _state_from_row(self, row: Any) -> Any:
        from ..services.simulation_manager import SimulationState, SimulationStatus
        data = dict(row.get("data", {}) or {})
        return _attach_version(SimulationState(
            simulation_id=row["id"],
            project_id=row["project_id"],
            graph_id=row["graph_id"] or "",
            project_type=row["project_type"] or "default",
            consumer_mode=bool(row["consumer_mode"]),
            enable_twitter=data.get("enable_twitter", True),
            enable_reddit=data.get("enable_reddit", True),
            status=SimulationStatus(row["status"]) if row["status"] else SimulationStatus.CREATED,
            entities_count=data.get("entities_count", 0),
            profiles_count=data.get("profiles_count", 0),
            entity_types=data.get("entity_types", []),
            config_generated=data.get("config_generated", False),
            config_reasoning=data.get("config_reasoning", ""),
            persona_pack_id=data.get("persona_pack_id", ""),
            pinned_brief_summary=data.get("pinned_brief_summary", ""),
            enable_lane_b=data.get("enable_lane_b", False),
            current_round=data.get("current_round", 0),
            twitter_status=data.get("twitter_status", "not_started"),
            reddit_status=data.get("reddit_status", "not_started"),
            created_at=data.get("created_at", ""),
            updated_at=data.get("updated_at", ""),
            error=data.get("error"),
        ), row["version"])

    def get_simulation(self, simulation_id: str) -> Optional[Any]:
        with self._session() as session:
            row = session.execute(
                select(simulations).where(simulations.c.id == simulation_id)
            ).mappings().fetchone()
            if row is None:
                return None
            return self._state_from_row(row)

    def save_simulation(self, state: Any) -> None:
        data = state.to_dict()
        # Strip fields stored in explicit columns
        data.pop("simulation_id", None)
        data.pop("project_id", None)
        data.pop("graph_id", None)
        data.pop("project_type", None)
        data.pop("consumer_mode", None)
        data.pop("status", None)
        with self._session() as session:
            existing = session.execute(
                select(simulations.c.id, simulations.c.version).where(simulations.c.id == state.simulation_id)
            ).fetchone()
            if existing:
                expected = _expected_version(state, existing.version)
                result = session.execute(
                    update(simulations)
                    .where(simulations.c.id == state.simulation_id)
                    .where(simulations.c.version == expected)
                    .values(
                        project_id=state.project_id,
                        graph_id=state.graph_id,
                        project_type=state.project_type or "default",
                        consumer_mode=1 if state.consumer_mode else 0,
                        status=state.status.value if hasattr(state.status, "value") else str(state.status),
                        data=data,
                        version=expected + 1,
                    )
                )
                if result.rowcount == 0:
                    session.rollback()
                    _raise_version_conflict("simulation", state.simulation_id)
                _attach_version(state, expected + 1)
            else:
                session.execute(
                    insert(simulations).values(
                        id=state.simulation_id,
                        project_id=state.project_id,
                        graph_id=state.graph_id,
                        project_type=state.project_type or "default",
                        consumer_mode=1 if state.consumer_mode else 0,
                        status=state.status.value if hasattr(state.status, "value") else str(state.status),
                        data=data,
                        version=1,
                    )
                )
                _attach_version(state, 1)
            session.commit()

    def create_simulation(
        self,
        project_id: str,
        graph_id: str,
        project_type: str = "default",
        enable_twitter: bool = True,
        enable_reddit: bool = True,
    ) -> Any:
        from ..services.simulation_manager import SimulationState, SimulationStatus
        simulation_id = f"sim_{uuid.uuid4().hex[:12]}"
        normalized_project_type = project_type or "default"
        state = SimulationState(
            simulation_id=simulation_id,
            project_id=project_id,
            graph_id=graph_id,
            project_type=normalized_project_type,
            consumer_mode=(normalized_project_type == "consumer_test"),
            enable_twitter=enable_twitter,
            enable_reddit=enable_reddit,
            status=SimulationStatus.CREATED,
        )
        self.save_simulation(state)
        return state

    def list_simulations(self, project_id: Optional[str] = None) -> List[Any]:
        with self._session() as session:
            stmt = select(simulations)
            if project_id is not None:
                stmt = stmt.where(simulations.c.project_id == project_id)
            stmt = stmt.order_by(simulations.c.created_at.desc())
            rows = session.execute(stmt).mappings().all()
            return [self._state_from_row(row) for row in rows]

    def delete_simulation(self, simulation_id: str) -> bool:
        with self._session() as session:
            existing = session.execute(
                select(simulations.c.id).where(simulations.c.id == simulation_id)
            ).fetchone()
            if existing is None:
                return False
            _delete_simulation_tree(session, [simulation_id])
            session.commit()
            return True

    def get_profiles(self, simulation_id: str, platform: str = "reddit") -> List[Dict[str, Any]]:
        return []

    def get_simulation_config(self, simulation_id: str) -> Optional[Dict[str, Any]]:
        return self.load_simulation_config(simulation_id)

    def get_prepare_manifest(self, simulation_id: str) -> Optional[Dict[str, Any]]:
        return None

    def record_manifest_reuse(self, simulation_id: str) -> Optional[Dict[str, Any]]:
        return None

    def save_simulation_config(self, simulation_id: str, config: Dict[str, Any]) -> None:
        with self._session() as session:
            row = session.execute(
                select(simulations.c.data).where(simulations.c.id == simulation_id)
            ).fetchone()
            data = dict(row[0]) if row and row[0] else {}
            data["_simulation_config"] = config
            session.execute(
                update(simulations).where(simulations.c.id == simulation_id).values(data=data)
            )
            session.commit()

    def load_simulation_config(self, simulation_id: str) -> Optional[Dict[str, Any]]:
        with self._session() as session:
            row = session.execute(
                select(simulations.c.data).where(simulations.c.id == simulation_id)
            ).fetchone()
            if row is None or row[0] is None:
                return None
            data = row[0] if isinstance(row[0], dict) else {}
            return data.get("_simulation_config")

    def save_consumer_config(self, simulation_id: str, config: Dict[str, Any]) -> None:
        with self._session() as session:
            row = session.execute(
                select(simulations.c.data).where(simulations.c.id == simulation_id)
            ).fetchone()
            data = dict(row[0]) if row and row[0] else {}
            data["_consumer_config"] = config
            session.execute(
                update(simulations).where(simulations.c.id == simulation_id).values(data=data)
            )
            session.commit()

    def load_consumer_config(self, simulation_id: str) -> Optional[Dict[str, Any]]:
        with self._session() as session:
            row = session.execute(
                select(simulations.c.data).where(simulations.c.id == simulation_id)
            ).fetchone()
            if row is None or row[0] is None:
                return None
            data = row[0] if isinstance(row[0], dict) else {}
            return data.get("_consumer_config")


class SQLAlchemyBranchRepository(BranchRepository):
    def __init__(self, session_factory: Optional[sessionmaker] = None) -> None:
        self._session_factory = session_factory

    def _session(self):
        return self._session_factory()

    def _branch_from_row(self, row: Any) -> Any:
        from datetime import datetime
        from ..services.consumer.intervention_manager import ConsumerBranch
        created_at = row.get("created_at", "")
        if isinstance(created_at, datetime):
            created_at = created_at.isoformat()
        return _attach_version(ConsumerBranch(
            branch_id=row["id"],
            simulation_id=row["simulation_id"],
            parent_branch_id=row.get("parent_branch_id"),
            fork_round=row["fork_round"],
            name=row["name"],
            description=row.get("description") or "",
            status=row.get("status") or "active",
            created_at=created_at,
        ), row["version"])

    def create_branch(
        self,
        simulation_id: str,
        name: str,
        fork_round: int,
        description: str = "",
        parent_branch_id: Optional[str] = None,
    ) -> Any:
        from ..services.consumer.intervention_manager import ConsumerBranch
        branch_id = _generate_id("branch_")
        now = _now_iso()
        branch = ConsumerBranch(
            branch_id=branch_id,
            simulation_id=simulation_id,
            parent_branch_id=parent_branch_id,
            fork_round=fork_round,
            name=name,
            description=description,
            status="active",
            created_at=now,
        )
        with self._session() as session:
            session.execute(
                insert(branches).values(
                    id=branch.branch_id,
                    simulation_id=simulation_id,
                    run_id="base",
                    name=name,
                    fork_round=fork_round,
                    description=description,
                    parent_branch_id=parent_branch_id,
                    status="active",
                )
            )
            session.commit()
        return branch

    def get_branch(self, simulation_id: str, branch_id: str) -> Optional[Any]:
        with self._session() as session:
            row = session.execute(
                select(branches)
                .where(branches.c.id == branch_id)
                .where(branches.c.simulation_id == simulation_id)
            ).mappings().fetchone()
            if row is None:
                return None
            return self._branch_from_row(row)

    def list_branches(self, simulation_id: str) -> List[Any]:
        with self._session() as session:
            rows = session.execute(
                select(branches)
                .where(branches.c.simulation_id == simulation_id)
                .order_by(branches.c.created_at.desc())
            ).mappings().all()
            return [self._branch_from_row(row) for row in rows]

    def update_branch_status(self, simulation_id: str, branch_id: str, status: str) -> Optional[Any]:
        with self._session() as session:
            existing = session.execute(
                select(branches.c.version)
                .where(branches.c.id == branch_id)
                .where(branches.c.simulation_id == simulation_id)
            ).fetchone()
            if existing is None:
                return None
            result = session.execute(
                update(branches)
                .where(branches.c.id == branch_id)
                .where(branches.c.simulation_id == simulation_id)
                .where(branches.c.version == existing.version)
                .values(status=status, version=existing.version + 1)
            )
            session.commit()
            if result.rowcount == 0:
                return None
            return self.get_branch(simulation_id, branch_id)

    def add_intervention(
        self,
        simulation_id: str,
        branch_id: str,
        intervention_type: str,
        payload: Dict[str, Any],
        target_round: Optional[int] = None,
    ) -> Any:
        from ..services.consumer.intervention_manager import ConsumerIntervention, InterventionType
        intervention_id = _generate_id("int_")
        now = _now_iso()
        itype = intervention_type
        if isinstance(intervention_type, str):
            try:
                itype = InterventionType(intervention_type).value
            except ValueError:
                itype = intervention_type
        intervention = ConsumerIntervention(
            intervention_id=intervention_id,
            branch_id=branch_id,
            simulation_id=simulation_id,
            intervention_type=itype,
            payload=payload,
            target_round=target_round,
            created_at=now,
        )
        with self._session() as session:
            session.execute(
                insert(interventions).values(
                    id=intervention.intervention_id,
                    simulation_id=simulation_id,
                    run_id="base",
                    branch_id=branch_id,
                    intervention_type=itype,
                    payload=payload,
                    target_round=target_round,
                )
            )
            session.commit()
        return intervention

    def list_interventions(self, simulation_id: str, branch_id: Optional[str] = None) -> List[Any]:
        from datetime import datetime
        from ..services.consumer.intervention_manager import ConsumerIntervention
        with self._session() as session:
            stmt = select(interventions).where(interventions.c.simulation_id == simulation_id)
            if branch_id is not None:
                stmt = stmt.where(interventions.c.branch_id == branch_id)
            rows = session.execute(stmt.order_by(interventions.c.created_at)).mappings().all()
            result = []
            for row in rows:
                created_at = row.get("created_at", "")
                if isinstance(created_at, datetime):
                    created_at = created_at.isoformat()
                result.append(ConsumerIntervention(
                    intervention_id=row["id"],
                    branch_id=row["branch_id"],
                    simulation_id=row["simulation_id"],
                    intervention_type=row["intervention_type"],
                    payload=dict(row.get("payload", {}) or {}),
                    target_round=row.get("target_round"),
                    created_at=created_at,
                ))
            return result

    def get_branch_run_status(self, simulation_id: str, branch_id: str) -> Dict[str, Any]:
        with self._session() as session:
            row = session.execute(
                select(branches.c.data)
                .where(branches.c.id == branch_id)
                .where(branches.c.simulation_id == simulation_id)
            ).fetchone()
            if row and row[0]:
                data = row[0] if isinstance(row[0], dict) else {}
                saved = data.get("_run_status")
                if saved:
                    return dict(saved)
        return {"status": "idle", "branch_id": branch_id, "simulation_id": simulation_id}

    def update_branch_run_status(self, simulation_id: str, branch_id: str, status_data: Dict[str, Any]) -> None:
        with self._session() as session:
            row = session.execute(
                select(branches.c.data)
                .where(branches.c.id == branch_id)
                .where(branches.c.simulation_id == simulation_id)
            ).fetchone()
            data = dict(row[0]) if row and row[0] else {}
            data["_run_status"] = status_data
            session.execute(
                update(branches)
                .where(branches.c.id == branch_id)
                .where(branches.c.simulation_id == simulation_id)
                .values(data=data)
            )
            session.commit()

    def build_comparison_context(self, simulation_id: str, branch_id: str) -> Dict[str, Any]:
        branch = self.get_branch(simulation_id, branch_id)
        if branch is None:
            raise ValueError("Branch not found")
        interventions = self.list_interventions(simulation_id, branch_id=branch_id)
        return {
            "branch_id": branch.branch_id,
            "base_branch_id": branch.parent_branch_id,
            "fork_round": branch.fork_round,
            "branch_name": branch.name,
            "branch_description": branch.description,
            "interventions": [i.model_dump() for i in interventions],
            "base_summary": {"events_count": 0, "has_data": False},
            "branch_summary": {"events_count": 0, "has_data": False},
        }


class SQLAlchemyReportRepository(ReportRepository):
    def __init__(self, session_factory: Optional[sessionmaker] = None) -> None:
        self._session_factory = session_factory

    def _session(self):
        return self._session_factory()

    def _report_from_row(self, row: Any) -> Any:
        from ..services.report_agent import Report, ReportStatus, ReportOutline, ReportSection
        data = dict(row.get("data", {}) or {})
        outline = None
        outline_data = data.get("_outline")
        if outline_data:
            sections = []
            for s in outline_data.get("sections", []):
                sections.append(ReportSection(title=s.get("title", ""), content=s.get("content", "")))
            outline = ReportOutline(
                title=outline_data.get("title", ""),
                summary=outline_data.get("summary", ""),
                sections=sections,
            )
        return _attach_version(Report(
            report_id=row["id"],
            simulation_id=row["simulation_id"],
            graph_id=data.get("graph_id", ""),
            simulation_requirement=data.get("simulation_requirement", ""),
            status=ReportStatus(row["status"]) if row["status"] else ReportStatus.PENDING,
            project_type=data.get("project_type", "default"),
            outline=outline,
            markdown_content=data.get("markdown_content", ""),
            report_context=data.get("report_context"),
            created_at=data.get("created_at", ""),
            completed_at=data.get("completed_at", ""),
            error=data.get("error"),
        ), row["version"])

    def get_report(self, report_id: str) -> Optional[Any]:
        with self._session() as session:
            row = session.execute(
                select(reports).where(reports.c.id == report_id)
            ).mappings().fetchone()
            if row is None:
                return None
            return self._report_from_row(row)

    def get_report_by_simulation(self, simulation_id: str) -> Optional[Any]:
        with self._session() as session:
            row = session.execute(
                select(reports)
                .where(reports.c.simulation_id == simulation_id)
                .order_by(reports.c.created_at.desc())
            ).mappings().fetchone()
            if row is None:
                return None
            return self._report_from_row(row)

    def list_reports(self, simulation_id: Optional[str] = None, limit: int = 50) -> List[Any]:
        with self._session() as session:
            stmt = select(reports)
            if simulation_id is not None:
                stmt = stmt.where(reports.c.simulation_id == simulation_id)
            stmt = stmt.order_by(reports.c.created_at.desc()).limit(limit)
            rows = session.execute(stmt).mappings().all()
            return [self._report_from_row(row) for row in rows]

    def save_report(self, report: Any) -> None:
        data = report.to_dict()
        data.pop("report_id", None)
        data.pop("simulation_id", None)
        data.pop("status", None)
        data.pop("outline", None)
        # Preserve _outline and _progress if already stored
        with self._session() as session:
            existing = session.execute(
                select(reports.c.data, reports.c.version).where(reports.c.id == report.report_id)
            ).fetchone()
            if existing and existing.data:
                old = existing.data if isinstance(existing.data, dict) else {}
                for key in ("_outline", "_progress", "_sections"):
                    if key in old:
                        data.setdefault(key, old[key])
            if existing:
                expected = _expected_version(report, existing.version)
                result = session.execute(
                    update(reports)
                    .where(reports.c.id == report.report_id)
                    .where(reports.c.version == expected)
                    .values(
                        simulation_id=report.simulation_id,
                        run_id="base",
                        report_type=data.get("report_type"),
                        status=report.status.value if hasattr(report.status, "value") else str(report.status),
                        progress=data.get("progress", 0),
                        data=data,
                        version=expected + 1,
                    )
                )
                if result.rowcount == 0:
                    session.rollback()
                    _raise_version_conflict("report", report.report_id)
                _attach_version(report, expected + 1)
            else:
                session.execute(
                    insert(reports).values(
                        id=report.report_id,
                        simulation_id=report.simulation_id,
                        run_id="base",
                        report_type=data.get("report_type"),
                        status=report.status.value if hasattr(report.status, "value") else str(report.status),
                        progress=data.get("progress", 0),
                        data=data,
                        version=1,
                    )
                )
                _attach_version(report, 1)
            session.commit()

    def save_outline(self, report_id: str, outline: Any) -> None:
        outline_data = outline.to_dict()
        with self._session() as session:
            row = session.execute(
                select(reports.c.data).where(reports.c.id == report_id)
            ).fetchone()
            data = dict(row[0]) if row and row[0] else {}
            data["_outline"] = outline_data
            existing = session.execute(
                select(reports.c.id).where(reports.c.id == report_id)
            ).fetchone()
            if existing:
                session.execute(
                    update(reports).where(reports.c.id == report_id).values(data=data)
                )
            else:
                session.execute(
                    insert(reports).values(
                        id=report_id,
                        simulation_id="",
                        run_id="base",
                        data=data,
                    )
                )
            session.commit()

    def save_section(self, report_id: str, section_index: int, section: Any) -> str:
        with self._session() as session:
            # Remove existing section at this index
            session.execute(
                delete(report_sections)
                .where(report_sections.c.report_id == report_id)
                .where(report_sections.c.section_index == section_index)
            )
            session.execute(
                insert(report_sections).values(
                    id=_generate_id(),
                    simulation_id="",
                    run_id="base",
                    report_id=report_id,
                    section_index=section_index,
                    title=section.title,
                    content={"text": section.content},
                )
            )
            session.commit()
        return f"section_{section_index:02d}"

    def update_progress(
        self,
        report_id: str,
        status: str,
        progress: int,
        message: str,
        current_section: Optional[str] = None,
        completed_sections: Optional[List[str]] = None,
    ) -> None:
        progress_data = {
            "status": status,
            "progress": progress,
            "message": message,
            "current_section": current_section,
            "completed_sections": completed_sections or [],
            "updated_at": _now_iso(),
        }
        with self._session() as session:
            row = session.execute(
                select(reports.c.data).where(reports.c.id == report_id)
            ).fetchone()
            data = dict(row[0]) if row and row[0] else {}
            data["_progress"] = progress_data
            existing = session.execute(
                select(reports.c.id).where(reports.c.id == report_id)
            ).fetchone()
            if existing:
                session.execute(
                    update(reports).where(reports.c.id == report_id).values(
                        status=status,
                        progress=progress,
                        data=data,
                    )
                )
            else:
                session.execute(
                    insert(reports).values(
                        id=report_id,
                        simulation_id="",
                        run_id="base",
                        status=status,
                        progress=progress,
                        data=data,
                    )
                )
            session.commit()

    def get_progress(self, report_id: str) -> Optional[Dict[str, Any]]:
        with self._session() as session:
            row = session.execute(
                select(reports.c.data).where(reports.c.id == report_id)
            ).fetchone()
            if row is None or row[0] is None:
                return None
            data = row[0] if isinstance(row[0], dict) else {}
            return data.get("_progress")

    def assemble_full_report(self, report_id: str, outline: Any) -> str:
        from ..services.report_agent import ReportOutline, ReportSection
        with self._session() as session:
            section_rows = session.execute(
                select(report_sections)
                .where(report_sections.c.report_id == report_id)
                .order_by(report_sections.c.section_index)
            ).mappings().all()
            md_content = f"# {outline.title}\n\n"
            md_content += f"> {outline.summary}\n\n"
            md_content += "---\n\n"
            for row in section_rows:
                content = row.get("content", {}) or {}
                text = content.get("text", "")
                title = row.get("title", "")
                if title:
                    md_content += f"## {title}\n\n"
                if text:
                    md_content += f"{text}\n\n"
            # Store assembled markdown
            rep_row = session.execute(
                select(reports.c.data).where(reports.c.id == report_id)
            ).fetchone()
            data = dict(rep_row[0]) if rep_row and rep_row[0] else {}
            data["markdown_content"] = md_content
            existing = session.execute(
                select(reports.c.id).where(reports.c.id == report_id)
            ).fetchone()
            if existing:
                session.execute(
                    update(reports).where(reports.c.id == report_id).values(data=data)
                )
            session.commit()
            return md_content

    def delete_report(self, report_id: str) -> bool:
        with self._session() as session:
            # Delete sections first
            session.execute(
                delete(report_sections).where(report_sections.c.report_id == report_id)
            )
            result = session.execute(
                delete(reports).where(reports.c.id == report_id)
            )
            session.commit()
            return result.rowcount > 0

    def get_agent_log(self, report_id: str, from_line: int = 0) -> Dict[str, Any]:
        return {"logs": [], "total_lines": 0, "from_line": from_line, "has_more": False}

    def get_console_log(self, report_id: str, from_line: int = 0) -> Dict[str, Any]:
        return {"logs": [], "total_lines": 0, "from_line": from_line, "has_more": False}


class SQLAlchemyBenchmarkRepository(BenchmarkRepository):
    def __init__(self, session_factory: Optional[sessionmaker] = None) -> None:
        self._session_factory = session_factory

    def _session(self):
        return self._session_factory()

    def register_benchmark(
        self,
        name: str,
        source_pack_lineage: str,
        expected_signals: Dict[str, Any],
        simulation_context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        benchmark_id = _generate_id("bench_")
        created_at = _now_iso()
        with self._session() as session:
            session.execute(
                insert(benchmarks).values(
                    id=benchmark_id,
                    name=name,
                    source_pack_lineage=source_pack_lineage,
                    expected_signals=expected_signals,
                    simulation_context=simulation_context or {},
                )
            )
            session.commit()
        return {
            "benchmark_id": benchmark_id,
            "name": name,
            "source_pack_lineage": source_pack_lineage,
            "created_at": created_at,
            "simulation_context": simulation_context or {},
            "expected_signals": expected_signals,
        }

    def list_benchmarks(self) -> List[Dict[str, Any]]:
        with self._session() as session:
            rows = session.execute(
                select(benchmarks).order_by(benchmarks.c.created_at.desc())
            ).mappings().all()
            return [
                {
                    "benchmark_id": row["id"],
                    "name": row["name"],
                    "source_pack_lineage": row.get("source_pack_lineage"),
                    "created_at": row.get("created_at", ""),
                    "simulation_context": row.get("simulation_context") or {},
                    "expected_signals": row.get("expected_signals") or {},
                }
                for row in rows
            ]

    def get_benchmark(self, benchmark_id: str) -> Optional[Dict[str, Any]]:
        with self._session() as session:
            row = session.execute(
                select(benchmarks).where(benchmarks.c.id == benchmark_id)
            ).mappings().fetchone()
            if row is None:
                return None
            return {
                "benchmark_id": row["id"],
                "name": row["name"],
                "source_pack_lineage": row.get("source_pack_lineage"),
                "created_at": row.get("created_at", ""),
                "simulation_context": row.get("simulation_context") or {},
                "expected_signals": row.get("expected_signals") or {},
            }

    def delete_benchmark(self, benchmark_id: str) -> bool:
        with self._session() as session:
            session.execute(
                delete(benchmark_replays).where(benchmark_replays.c.benchmark_id == benchmark_id)
            )
            result = session.execute(
                delete(benchmarks).where(benchmarks.c.id == benchmark_id)
            )
            session.commit()
            return result.rowcount > 0

    def replay_benchmark(
        self,
        benchmark_id: str,
        report_context: Dict[str, Any],
        project_id: Optional[str] = None,
        simulation_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        from ..services.consumer.benchmark_replay import (
            extract_stable_signals,
            compare_replay_result,
        )
        benchmark = self.get_benchmark(benchmark_id)
        if benchmark is None:
            raise ValueError(f"Benchmark not found: {benchmark_id}")
        expected_signals = benchmark.get("expected_signals", {})
        actual_signals = extract_stable_signals(report_context)
        comparison = compare_replay_result(expected_signals, actual_signals)
        replay_id = _generate_id("replay_")
        replay_result = {
            "replay_id": replay_id,
            "benchmark_id": benchmark_id,
            "project_id": project_id,
            "simulation_id": simulation_id,
            "replayed_at": _now_iso(),
            "expected_signals": expected_signals,
            "actual_signals": actual_signals,
            "alignment_status": comparison["alignment_status"],
            "metric_deltas": comparison["metric_deltas"],
            "drift_signals": comparison["drift_signals"],
            "overall_score": comparison["overall_score"],
            "replay_summary": comparison["summary"],
        }
        gatekeeping_summary = report_context.get("evidence_gatekeeping_summary")
        if gatekeeping_summary is not None:
            replay_result["evidence_gatekeeping_summary"] = gatekeeping_summary
        with self._session() as session:
            session.execute(
                insert(benchmark_replays).values(
                    id=replay_id,
                    benchmark_id=benchmark_id,
                    replay_result=replay_result,
                )
            )
            session.commit()
        return replay_result

    def get_replay_result(self, replay_id: str) -> Optional[Dict[str, Any]]:
        with self._session() as session:
            row = session.execute(
                select(benchmark_replays).where(benchmark_replays.c.id == replay_id)
            ).mappings().fetchone()
            if row is None:
                return None
            result = dict(row.get("replay_result", {}) or {})
            return result

    def list_replay_results(self, benchmark_id: str) -> List[Dict[str, Any]]:
        with self._session() as session:
            rows = session.execute(
                select(benchmark_replays)
                .where(benchmark_replays.c.benchmark_id == benchmark_id)
                .order_by(benchmark_replays.c.created_at.desc())
            ).mappings().all()
            return [dict(row.get("replay_result", {}) or {}) for row in rows]


__all__ = [
    "metadata",
    "projects",
    "consumer_briefs",
    "simulations",
    "simulation_runs",
    "society_agents",
    "persona_packs",
    "round_snapshots",
    "consumer_events",
    "branches",
    "interventions",
    "reports",
    "report_sections",
    "research_assets",
    "benchmarks",
    "benchmark_replays",
    "memory_entries",
    "tasks",
    "task_attempts",
    "dead_letters",
    "locks",
    "SQLAlchemyProjectRepository",
    "SQLAlchemyConsumerStateRepository",
    "SQLAlchemyConsumerProjectResearchProvider",
    "SQLAlchemySimulationRepository",
    "SQLAlchemyBranchRepository",
    "SQLAlchemyReportRepository",
    "SQLAlchemyBenchmarkRepository",
]
