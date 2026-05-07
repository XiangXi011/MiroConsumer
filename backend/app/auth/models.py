"""认证授权模型"""
from dataclasses import dataclass, field
from typing import Optional, Set
import hashlib
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
    key_hash: str  # sha256 of the actual key
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


def generate_api_key() -> tuple:
    """生成 API Key，返回 (raw_key, key_id, key_hash)"""
    raw_key = f"mk_{secrets.token_urlsafe(32)}"
    key_id = f"key_{secrets.token_hex(8)}"
    key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
    return raw_key, key_id, key_hash


def verify_api_key(raw_key: str, key_hash: str) -> bool:
    """验证 API Key"""
    return hashlib.sha256(raw_key.encode()).hexdigest() == key_hash
