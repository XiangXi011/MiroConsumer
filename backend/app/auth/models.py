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
    "owner": {"project.read", "project.write", "simulation.run", "report.read",
              "report.export", "asset.export", "admin.manage_users", "audit.read"},
    "admin": {"project.read", "project.write", "simulation.run", "report.read",
              "report.export", "asset.export", "admin.manage_users"},
    "researcher": {"project.read", "project.write", "simulation.run", "report.read", "report.export"},
    "viewer": {"project.read", "report.read"},
    "auditor": {"project.read", "report.read", "audit.read"},
    "service": {"project.read", "project.write", "simulation.run", "report.read",
                "report.export", "asset.export"},
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
