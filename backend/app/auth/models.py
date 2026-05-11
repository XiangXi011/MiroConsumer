"""认证授权模型"""
from dataclasses import dataclass, field
from typing import Optional, Set
import bcrypt
import secrets
import time


@dataclass
class User:
    user_id: str
    username: str
    email: str
    role: str  # owner/admin/researcher/viewer/auditor/service
    tenant_id: str
    workspace_id: str
    password_hash: str = ""
    password_changed_at: Optional[float] = None
    failed_login_count: int = 0
    locked_until: Optional[float] = None
    is_active: bool = True
    created_at: float = field(default_factory=time.time)


@dataclass
class APIKey:
    key_id: str
    key_hash: str  # bcrypt hash of the actual key
    user_id: str
    tenant_id: str
    scopes: Set[str] = field(default_factory=set)
    is_active: bool = True
    created_at: float = field(default_factory=time.time)
    expires_at: Optional[float] = None


# 角色权限映射
ROLE_PERMISSIONS = {
    "owner": {"project.read", "project.write", "simulation.read", "simulation.run",
              "report.read", "report.generate", "report.export", "asset.export",
              "admin.manage_users", "audit.read"},
    "admin": {"project.read", "project.write", "simulation.read", "simulation.run",
              "report.read", "report.generate", "report.export", "asset.export",
              "admin.manage_users"},
    "super_admin": {"project.read", "project.write", "simulation.read", "simulation.run",
                    "report.read", "report.generate", "report.export", "asset.export",
                    "admin.manage_users", "audit.read", "tenant.cross_access"},
    "analyst": {"project.read", "simulation.read", "report.read", "report.export"},
    "researcher": {"project.read", "project.write", "simulation.read", "simulation.run",
                   "report.read", "report.generate", "report.export"},
    "viewer": {"project.read", "simulation.read", "report.read"},
    "auditor": {"project.read", "simulation.read", "report.read", "audit.read"},
    "service": {"project.read", "project.write", "simulation.read", "simulation.run",
                "report.read", "report.generate", "report.export", "asset.export"},
}

# 端点权限映射
ENDPOINT_PERMISSIONS = {
    "GET /api/graph": "project.read",
    "POST /api/graph": "project.write",
    "GET /api/simulation": "project.read",
    "POST /api/simulation": "simulation.run",
    "GET /api/report": "report.read",
    "POST /api/report/generate": "report.read",
    "GET /api/report/*/export": "report.export",
    "GET /api/consumer": "project.read",
    "POST /api/consumer": "simulation.run",
}


def hash_api_key(raw_key: str, rounds: int = 12) -> str:
    """Hash an API key with bcrypt for storage."""
    if not raw_key:
        raise ValueError("raw_key is required")
    salt = bcrypt.gensalt(rounds=rounds)
    return bcrypt.hashpw(raw_key.encode("utf-8"), salt).decode("utf-8")


def extract_api_key_id(raw_key: str) -> Optional[str]:
    """Extract the embedded key id from a generated API key."""
    if not raw_key or not raw_key.startswith("mk_") or "." not in raw_key:
        return None
    key_id, _secret = raw_key[3:].split(".", 1)
    return key_id if key_id.startswith("key_") else None


def generate_api_key() -> tuple:
    """生成 API Key，返回 (raw_key, key_id, key_hash)"""
    key_id = f"key_{secrets.token_hex(8)}"
    raw_key = f"mk_{key_id}.{secrets.token_urlsafe(32)}"
    key_hash = hash_api_key(raw_key)
    return raw_key, key_id, key_hash


def verify_api_key(raw_key: str, key_hash: str) -> bool:
    """验证 API Key"""
    if not raw_key or not key_hash:
        return False
    try:
        return bcrypt.checkpw(raw_key.encode("utf-8"), key_hash.encode("utf-8"))
    except ValueError:
        return False


def validate_password_strength(password: str) -> Optional[str]:
    """Return a validation message when password policy fails."""
    if not password:
        return "password is required"
    if len(password) < 10:
        return "password must be at least 10 characters"
    has_alpha = any(ch.isalpha() for ch in password)
    has_digit = any(ch.isdigit() for ch in password)
    if not has_alpha or not has_digit:
        return "password must contain at least one letter and one number"
    return None


def hash_password(password: str, rounds: int = 12) -> str:
    """Hash a login password with bcrypt for storage."""
    error = validate_password_strength(password)
    if error:
        raise ValueError(error)
    salt = bcrypt.gensalt(rounds=rounds)
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    """Verify a login password against a stored bcrypt hash."""
    if not password or not password_hash:
        return False
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except ValueError:
        return False
