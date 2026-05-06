"""Database session helpers.

No DB connection is opened on import. All engine/session creation is deferred
to explicit helper calls.
"""

from typing import Optional

from sqlalchemy import create_engine, Engine
from sqlalchemy.orm import sessionmaker, Session

from ..config import Config


VALID_DB_SCHEMES = ("sqlite:///", "postgresql+psycopg://")


def validate_db_url(db_url: str) -> Optional[str]:
    """Return error message if db_url scheme is unsupported, else None.

    Empty db_url is valid (signals filesystem mode).
    """
    if not db_url:
        return None
    if not any(db_url.startswith(scheme) for scheme in VALID_DB_SCHEMES):
        return f"DB_URL unsupported scheme: {db_url.split('://')[0] if '://' in db_url else db_url}"
    return None


def create_engine_from_config(config: type[Config] = Config) -> Optional[Engine]:
    """Create a SQLAlchemy engine from Config settings.

    Returns None when DB_URL is empty (filesystem mode).
    Raises ValueError on unsupported DB_URL scheme.
    """
    db_url = config.DB_URL
    if not db_url:
        return None

    error = validate_db_url(db_url)
    if error:
        raise ValueError(error)

    kwargs = {}
    if db_url.startswith("postgresql+psycopg://"):
        kwargs["pool_size"] = config.DB_POOL_SIZE
        kwargs["max_overflow"] = config.DB_MAX_OVERFLOW
        kwargs["connect_args"] = {
            "options": f"-c statement_timeout={config.DB_STATEMENT_TIMEOUT_SECONDS * 1000}"
        }

    return create_engine(db_url, **kwargs)


def create_session_factory(engine: Optional[Engine] = None) -> Optional[sessionmaker]:
    """Return a sessionmaker bound to the given engine.

    If engine is None, returns None.
    """
    if engine is None:
        return None
    return sessionmaker(bind=engine, class_=Session)
