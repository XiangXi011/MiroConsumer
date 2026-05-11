"""Tenant isolation helpers for project, simulation, and report access."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

from flask import g, has_request_context, request

from .models import ROLE_PERMISSIONS
from ..security.audit_log import audit_event


@dataclass
class TenantAccessDenied(Exception):
    target_tenant_id: str
    actor_tenant_id: Optional[str] = None
    target_type: str = "resource"
    target_id: Optional[str] = None

    def __str__(self) -> str:
        return "Access denied: tenant mismatch"


class TenantGuard:
    """Centralized tenant checks.

    Missing target tenant IDs are treated as legacy data and remain readable for
    backward compatibility. Admin is tenant-scoped; only super_admin can cross
    tenant boundaries, and those accesses are audited.
    """

    @staticmethod
    def can_access_tenant(user: Any, target_tenant_id: Optional[str]) -> bool:
        if not target_tenant_id:
            return True
        if user is None:
            return False
        actor_tenant_id = getattr(user, "tenant_id", None)
        if actor_tenant_id == target_tenant_id:
            return True
        role = getattr(user, "role", "")
        permissions = ROLE_PERMISSIONS.get(role, set())
        return role == "super_admin" or "tenant.cross_access" in permissions

    @staticmethod
    def require_same_tenant(
        target_tenant_id: Optional[str],
        user: Any = None,
        *,
        target_type: str = "resource",
        target_id: Optional[str] = None,
    ) -> None:
        actor = user or (getattr(g, "current_user", None) if has_request_context() else None)
        if TenantGuard.can_access_tenant(actor, target_tenant_id):
            if target_tenant_id and actor and getattr(actor, "tenant_id", None) != target_tenant_id:
                TenantGuard._audit(
                    "tenant.cross_access",
                    actor,
                    target_type,
                    target_id,
                    target_tenant_id,
                    success=True,
                    reason="super_admin_cross_tenant",
                )
            return

        TenantGuard._audit(
            "tenant.access_denied",
            actor,
            target_type,
            target_id,
            target_tenant_id,
            success=False,
            reason="tenant_mismatch",
        )
        raise TenantAccessDenied(
            target_tenant_id=target_tenant_id or "",
            actor_tenant_id=getattr(actor, "tenant_id", None) if actor else None,
            target_type=target_type,
            target_id=target_id,
        )

    @staticmethod
    def assert_project_access(project: Any, user: Any = None) -> None:
        TenantGuard.require_same_tenant(
            getattr(project, "tenant_id", None),
            user,
            target_type="project",
            target_id=getattr(project, "project_id", None),
        )

    @staticmethod
    def assert_simulation_access(simulation: Any, user: Any = None) -> None:
        TenantGuard.require_same_tenant(
            getattr(simulation, "tenant_id", None),
            user,
            target_type="simulation",
            target_id=getattr(simulation, "simulation_id", None),
        )

    @staticmethod
    def assert_report_access(report: Any, user: Any = None) -> None:
        TenantGuard.require_same_tenant(
            getattr(report, "tenant_id", None),
            user,
            target_type="report",
            target_id=getattr(report, "report_id", None),
        )

    @staticmethod
    def _audit(event_type: str, actor: Any, target_type: str, target_id: Optional[str], target_tenant_id: Optional[str], *, success: bool, reason: str) -> None:
        audit_event(
            event_type=event_type,
            actor_user_id=getattr(actor, "user_id", None) if actor else None,
            actor_tenant_id=getattr(actor, "tenant_id", None) if actor else None,
            target_type=target_type,
            target_id=target_id,
            ip=request.remote_addr if has_request_context() else None,
            user_agent=request.headers.get("User-Agent") if has_request_context() else None,
            success=success,
            reason=reason,
            details={"target_tenant_id": target_tenant_id},
        )


def tenant_forbidden_response():
    return {"success": False, "error": "FORBIDDEN", "message": "Access denied: tenant mismatch"}, 403
