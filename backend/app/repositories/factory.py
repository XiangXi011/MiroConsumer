"""Repository factory - returns the correct bundle based on DB_URL."""

from dataclasses import dataclass

from ..config import Config
from . import (
    ConsumerProjectResearchProvider,
    ProjectRepository,
    ConsumerStateRepository,
    SimulationRepository,
    BranchRepository,
    ReportRepository,
    BenchmarkRepository,
)
from .filesystem import (
    FilesystemProjectRepository,
    FilesystemConsumerStateRepository,
    FilesystemConsumerProjectResearchProvider,
    FilesystemSimulationRepository,
    FilesystemBranchRepository,
    FilesystemReportRepository,
    FilesystemBenchmarkRepository,
)


@dataclass
class RepositoryBundle:
    """Container for all repository implementations used by the app layer."""

    backend: str
    project_repo: ProjectRepository
    consumer_state_repo: ConsumerStateRepository
    consumer_research_provider: ConsumerProjectResearchProvider
    simulation_repo: SimulationRepository
    branch_repo: BranchRepository
    report_repo: ReportRepository
    benchmark_repo: BenchmarkRepository


def _wrap_cache_if_configured(bundle: RepositoryBundle, config: type[Config]) -> RepositoryBundle:
    redis_url = getattr(config, "REDIS_URL", "")
    if not redis_url:
        return bundle

    from ..services.application.redis_cache import RedisCache
    from .cache import CachedProjectRepository, CachedSimulationRepository

    cache = RedisCache(redis_url=redis_url)
    return RepositoryBundle(
        backend=bundle.backend,
        project_repo=CachedProjectRepository(bundle.project_repo, cache),
        consumer_state_repo=bundle.consumer_state_repo,
        consumer_research_provider=bundle.consumer_research_provider,
        simulation_repo=CachedSimulationRepository(bundle.simulation_repo, cache),
        branch_repo=bundle.branch_repo,
        report_repo=bundle.report_repo,
        benchmark_repo=bundle.benchmark_repo,
    )


def create_repository_bundle(config: type[Config] = Config) -> RepositoryBundle:
    """Create a RepositoryBundle based on Config.DB_URL.

    - Empty DB_URL  -> filesystem repositories
    - sqlite:///    -> SQLAlchemy repositories
    - postgresql+psycopg:// -> SQLAlchemy repositories
    - Anything else -> ValueError
    """
    db_url = config.DB_URL

    if not db_url:
        bundle = RepositoryBundle(
            backend="filesystem",
            project_repo=FilesystemProjectRepository(),
            consumer_state_repo=FilesystemConsumerStateRepository(),
            consumer_research_provider=FilesystemConsumerProjectResearchProvider(),
            simulation_repo=FilesystemSimulationRepository(),
            branch_repo=FilesystemBranchRepository(),
            report_repo=FilesystemReportRepository(),
            benchmark_repo=FilesystemBenchmarkRepository(),
        )
        return _wrap_cache_if_configured(bundle, config)

    valid_schemes = ("sqlite:///", "postgresql+psycopg://")
    if not any(db_url.startswith(scheme) for scheme in valid_schemes):
        raise ValueError(
            f"DB_URL unsupported scheme: {db_url.split('://')[0] if '://' in db_url else db_url}"
        )

    from .session import create_engine_from_config, create_session_factory
    from .sqlalchemy import (
        SQLAlchemyProjectRepository,
        SQLAlchemyConsumerStateRepository,
        SQLAlchemyConsumerProjectResearchProvider,
        SQLAlchemySimulationRepository,
        SQLAlchemyBranchRepository,
        SQLAlchemyReportRepository,
        SQLAlchemyBenchmarkRepository,
    )

    try:
        engine = create_engine_from_config(config)
        session_factory = create_session_factory(engine)
    except ImportError:
        session_factory = None

    bundle = RepositoryBundle(
        backend="sqlalchemy",
        project_repo=SQLAlchemyProjectRepository(session_factory=session_factory),
        consumer_state_repo=SQLAlchemyConsumerStateRepository(session_factory=session_factory),
        consumer_research_provider=SQLAlchemyConsumerProjectResearchProvider(session_factory=session_factory),
        simulation_repo=SQLAlchemySimulationRepository(session_factory=session_factory),
        branch_repo=SQLAlchemyBranchRepository(session_factory=session_factory),
        report_repo=SQLAlchemyReportRepository(session_factory=session_factory),
        benchmark_repo=SQLAlchemyBenchmarkRepository(session_factory=session_factory),
    )
    return _wrap_cache_if_configured(bundle, config)
