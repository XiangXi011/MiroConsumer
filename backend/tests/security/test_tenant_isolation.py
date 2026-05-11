from dataclasses import dataclass

import pytest

from app.auth.tenant_guard import TenantAccessDenied, TenantGuard


@dataclass
class FakeUser:
    user_id: str
    role: str
    tenant_id: str


def test_admin_cannot_cross_tenant():
    user = FakeUser("user_admin", "admin", "tenant_a")

    assert TenantGuard.can_access_tenant(user, "tenant_b") is False
    with pytest.raises(TenantAccessDenied):
        TenantGuard.require_same_tenant("tenant_b", user, target_type="project", target_id="proj_b")


def test_researcher_same_tenant_allowed():
    user = FakeUser("user_researcher", "researcher", "tenant_a")

    TenantGuard.require_same_tenant("tenant_a", user, target_type="simulation", target_id="sim_a")


def test_super_admin_can_cross_tenant():
    user = FakeUser("user_super", "super_admin", "tenant_a")

    assert TenantGuard.can_access_tenant(user, "tenant_b") is True
    TenantGuard.require_same_tenant("tenant_b", user, target_type="report", target_id="report_b")
