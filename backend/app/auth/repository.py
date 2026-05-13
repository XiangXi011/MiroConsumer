"""Authentication persistence repositories."""

from abc import ABC, abstractmethod
from dataclasses import replace
from typing import Dict, List, Optional

from sqlalchemy import (
    Boolean,
    Column,
    Float,
    ForeignKey,
    Integer,
    Index,
    JSON,
    MetaData,
    String,
    Table,
    delete,
    insert,
    select,
    update,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import sessionmaker

from .models import APIKey, User


auth_metadata = MetaData()


def _json_type():
    return JSON().with_variant(JSONB, "postgresql")


auth_users = Table(
    "auth_users",
    auth_metadata,
    Column("user_id", String(64), primary_key=True),
    Column("username", String(255), nullable=False),
    Column("email", String(255), nullable=False),
    Column("role", String(50), nullable=False),
    Column("tenant_id", String(255), nullable=False),
    Column("workspace_id", String(255), nullable=False),
    Column("password_hash", String(255), nullable=False, default=""),
    Column("password_changed_at", Float),
    Column("failed_login_count", Integer, nullable=False, default=0),
    Column("locked_until", Float),
    Column("is_active", Boolean, nullable=False, default=True),
    Column("created_at", Float, nullable=False),
    Index("ix_auth_users_user_id", "user_id"),
    Index("ix_auth_users_username", "username"),
    Index("ix_auth_users_email", "email"),
    Index("ix_auth_users_tenant_id", "tenant_id"),
)


auth_api_keys = Table(
    "auth_api_keys",
    auth_metadata,
    Column("key_id", String(64), primary_key=True),
    Column("key_hash", String(255), nullable=False),
    Column(
        "user_id",
        String(64),
        ForeignKey("auth_users.user_id", ondelete="CASCADE"),
        nullable=False,
    ),
    Column("tenant_id", String(255), nullable=False),
    Column("scopes", _json_type(), nullable=False, default=list),
    Column("is_active", Boolean, nullable=False, default=True),
    Column("created_at", Float, nullable=False),
    Column("expires_at", Float),
    Index("ix_auth_api_keys_user_id", "user_id"),
    Index("ix_auth_api_keys_tenant_id", "tenant_id"),
    Index("ix_auth_api_keys_key_hash", "key_hash"),
)


class AuthRepository(ABC):
    """Abstract authentication persistence interface."""

    @abstractmethod
    def save_user(self, user: User) -> None:
        """Persist a user."""

    @abstractmethod
    def get_user(self, user_id: str) -> Optional[User]:
        """Return a user by id, or None."""

    @abstractmethod
    def get_user_by_username(self, username: str) -> Optional[User]:
        """Return a user by username, or None."""

    @abstractmethod
    def get_user_by_email(self, email: str) -> Optional[User]:
        """Return a user by email, or None."""

    @abstractmethod
    def save_api_key(self, api_key: APIKey) -> None:
        """Persist an API key."""

    @abstractmethod
    def get_api_key_by_id(self, key_id: str) -> Optional[APIKey]:
        """Return an API key by id, or None."""

    @abstractmethod
    def get_api_keys_by_user(self, user_id: str) -> List[APIKey]:
        """Return all API keys owned by a user."""

    @abstractmethod
    def delete_api_key(self, key_id: str) -> bool:
        """Delete an API key. Returns True when a row was removed."""

    @abstractmethod
    def clear_all(self) -> None:
        """Clear all auth state. Intended for tests."""


def _copy_user(user: User) -> User:
    return replace(user)


def _copy_api_key(api_key: APIKey) -> APIKey:
    return replace(api_key, scopes=set(api_key.scopes or set()))


class MemoryAuthRepository(AuthRepository):
    """In-memory auth repository used as the fallback and in tests."""

    def __init__(self) -> None:
        self._users: Dict[str, User] = {}
        self._api_keys: Dict[str, APIKey] = {}

    def save_user(self, user: User) -> None:
        self._users[user.user_id] = _copy_user(user)

    def get_user(self, user_id: str) -> Optional[User]:
        user = self._users.get(user_id)
        return _copy_user(user) if user else None

    def get_user_by_username(self, username: str) -> Optional[User]:
        normalized = (username or "").strip().lower()
        for user in self._users.values():
            if user.username.lower() == normalized:
                return _copy_user(user)
        return None

    def get_user_by_email(self, email: str) -> Optional[User]:
        normalized = (email or "").strip().lower()
        for user in self._users.values():
            if user.email.lower() == normalized:
                return _copy_user(user)
        return None

    def save_api_key(self, api_key: APIKey) -> None:
        self._api_keys[api_key.key_id] = _copy_api_key(api_key)

    def get_api_key_by_id(self, key_id: str) -> Optional[APIKey]:
        api_key = self._api_keys.get(key_id)
        return _copy_api_key(api_key) if api_key else None

    def get_api_keys_by_user(self, user_id: str) -> List[APIKey]:
        return [
            _copy_api_key(api_key)
            for api_key in self._api_keys.values()
            if api_key.user_id == user_id
        ]

    def delete_api_key(self, key_id: str) -> bool:
        return self._api_keys.pop(key_id, None) is not None

    def clear_all(self) -> None:
        self._api_keys.clear()
        self._users.clear()


class SqlAlchemyAuthRepository(AuthRepository):
    """SQLAlchemy Core auth repository for shared persistent storage."""

    def __init__(self, session_factory: sessionmaker) -> None:
        if session_factory is None:
            raise ValueError("session_factory is required")
        self._session_factory = session_factory

    def _session(self):
        return self._session_factory()

    def save_user(self, user: User) -> None:
        values = {
            "user_id": user.user_id,
            "username": user.username,
            "email": user.email,
            "role": user.role,
            "tenant_id": user.tenant_id,
            "workspace_id": user.workspace_id,
            "password_hash": user.password_hash,
            "password_changed_at": user.password_changed_at,
            "failed_login_count": user.failed_login_count,
            "locked_until": user.locked_until,
            "is_active": user.is_active,
            "created_at": user.created_at,
        }
        with self._session() as session:
            existing = session.execute(
                select(auth_users.c.user_id).where(auth_users.c.user_id == user.user_id)
            ).fetchone()
            if existing:
                session.execute(
                    update(auth_users)
                    .where(auth_users.c.user_id == user.user_id)
                    .values(**values)
                )
            else:
                session.execute(insert(auth_users).values(**values))
            session.commit()

    def get_user(self, user_id: str) -> Optional[User]:
        with self._session() as session:
            row = session.execute(
                select(auth_users).where(auth_users.c.user_id == user_id)
            ).mappings().fetchone()
            return self._user_from_row(row) if row else None

    def get_user_by_username(self, username: str) -> Optional[User]:
        with self._session() as session:
            row = session.execute(
                select(auth_users).where(auth_users.c.username == username)
            ).mappings().fetchone()
            return self._user_from_row(row) if row else None

    def get_user_by_email(self, email: str) -> Optional[User]:
        with self._session() as session:
            row = session.execute(
                select(auth_users).where(auth_users.c.email == email)
            ).mappings().fetchone()
            return self._user_from_row(row) if row else None

    def save_api_key(self, api_key: APIKey) -> None:
        values = {
            "key_id": api_key.key_id,
            "key_hash": api_key.key_hash,
            "user_id": api_key.user_id,
            "tenant_id": api_key.tenant_id,
            "scopes": sorted(api_key.scopes or set()),
            "is_active": api_key.is_active,
            "created_at": api_key.created_at,
            "expires_at": api_key.expires_at,
        }
        with self._session() as session:
            existing = session.execute(
                select(auth_api_keys.c.key_id).where(auth_api_keys.c.key_id == api_key.key_id)
            ).fetchone()
            if existing:
                session.execute(
                    update(auth_api_keys)
                    .where(auth_api_keys.c.key_id == api_key.key_id)
                    .values(**values)
                )
            else:
                session.execute(insert(auth_api_keys).values(**values))
            session.commit()

    def get_api_key_by_id(self, key_id: str) -> Optional[APIKey]:
        with self._session() as session:
            row = session.execute(
                select(auth_api_keys).where(auth_api_keys.c.key_id == key_id)
            ).mappings().fetchone()
            return self._api_key_from_row(row) if row else None

    def get_api_keys_by_user(self, user_id: str) -> List[APIKey]:
        with self._session() as session:
            rows = session.execute(
                select(auth_api_keys)
                .where(auth_api_keys.c.user_id == user_id)
                .order_by(auth_api_keys.c.created_at.asc())
            ).mappings().all()
            return [self._api_key_from_row(row) for row in rows]

    def delete_api_key(self, key_id: str) -> bool:
        with self._session() as session:
            result = session.execute(
                delete(auth_api_keys).where(auth_api_keys.c.key_id == key_id)
            )
            session.commit()
            return result.rowcount > 0

    def clear_all(self) -> None:
        with self._session() as session:
            session.execute(delete(auth_api_keys))
            session.execute(delete(auth_users))
            session.commit()

    @staticmethod
    def _user_from_row(row) -> User:
        return User(
            user_id=row["user_id"],
            username=row["username"],
            email=row["email"],
            role=row["role"],
            tenant_id=row["tenant_id"],
            workspace_id=row["workspace_id"],
            password_hash=row.get("password_hash", ""),
            password_changed_at=row.get("password_changed_at"),
            failed_login_count=int(row.get("failed_login_count") or 0),
            locked_until=row.get("locked_until"),
            is_active=bool(row["is_active"]),
            created_at=float(row["created_at"]),
        )

    @staticmethod
    def _api_key_from_row(row) -> APIKey:
        return APIKey(
            key_id=row["key_id"],
            key_hash=row["key_hash"],
            user_id=row["user_id"],
            tenant_id=row["tenant_id"],
            scopes=set(row["scopes"] or []),
            is_active=bool(row["is_active"]),
            created_at=float(row["created_at"]),
            expires_at=row["expires_at"],
        )



class CachedAuthRepository(AuthRepository):
    """Auth repository decorator that caches user lookups in Redis."""

    USER_TTL_SECONDS = 600

    def __init__(self, wrapped: AuthRepository, cache) -> None:
        self.wrapped = wrapped
        self.cache = cache

    @staticmethod
    def _user_key(user_id: str) -> str:
        return f"auth:user:{user_id}"

    @staticmethod
    def _user_to_cache(user: User) -> dict:
        return dict(user.__dict__)

    @staticmethod
    def _user_from_cache(payload: dict) -> User:
        return User(**payload)

    def save_user(self, user: User) -> None:
        self.wrapped.save_user(user)
        self.cache.set(self._user_key(user.user_id), self._user_to_cache(user), ttl=self.USER_TTL_SECONDS)

    def get_user(self, user_id: str) -> Optional[User]:
        cached = self.cache.get(self._user_key(user_id))
        if isinstance(cached, dict):
            return self._user_from_cache(cached)

        user = self.wrapped.get_user(user_id)
        if user is not None:
            self.cache.set(self._user_key(user_id), self._user_to_cache(user), ttl=self.USER_TTL_SECONDS)
        return user

    def get_user_by_username(self, username: str) -> Optional[User]:
        return self.wrapped.get_user_by_username(username)

    def get_user_by_email(self, email: str) -> Optional[User]:
        return self.wrapped.get_user_by_email(email)

    def save_api_key(self, api_key: APIKey) -> None:
        self.wrapped.save_api_key(api_key)

    def get_api_key_by_id(self, key_id: str) -> Optional[APIKey]:
        return self.wrapped.get_api_key_by_id(key_id)

    def get_api_keys_by_user(self, user_id: str) -> List[APIKey]:
        return self.wrapped.get_api_keys_by_user(user_id)

    def delete_api_key(self, key_id: str) -> bool:
        return self.wrapped.delete_api_key(key_id)

    def clear_all(self) -> None:
        self.wrapped.clear_all()


def _wrap_auth_cache_if_configured(repository: AuthRepository, config) -> AuthRepository:
    redis_url = getattr(config, "REDIS_URL", "")
    if not redis_url:
        return repository
    from ..services.application.redis_cache import RedisCache
    return CachedAuthRepository(repository, RedisCache(redis_url=redis_url))

def create_auth_repository_from_config(config, create_schema: bool = True):
    """Create the configured auth repository and its owned DB engine."""
    from ..repositories.session import create_engine_from_config, create_session_factory

    engine = create_engine_from_config(config)
    if engine is None:
        return _wrap_auth_cache_if_configured(MemoryAuthRepository(), config), None

    if create_schema:
        auth_metadata.create_all(engine)

    session_factory = create_session_factory(engine)
    repository = SqlAlchemyAuthRepository(session_factory)
    return _wrap_auth_cache_if_configured(repository, config), engine



