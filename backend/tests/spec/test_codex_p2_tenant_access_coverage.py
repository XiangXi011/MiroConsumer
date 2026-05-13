"""SPEC-P2-028 explicit cross-tenant access coverage."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass

import pytest

from app.auth.tenant_guard import TenantAccessDenied, TenantGuard


@dataclass
class FakeUser:
    user_id: str
    role: str
    tenant_id: str


@dataclass
class FakeResource:
    resource_id: str
    tenant_id: str | None

    @property
    def project_id(self) -> str:
        return self.resource_id

    @property
    def simulation_id(self) -> str:
        return self.resource_id

    @property
    def report_id(self) -> str:
        return self.resource_id


@pytest.mark.parametrize("role", ["viewer", "researcher", "analyst", "admin"])
@pytest.mark.parametrize("resource_type", ["project", "simulation", "report"])
def test_tenant_scoped_roles_cannot_cross_tenant_by_resource_type(role: str, resource_type: str):
    user = FakeUser(user_id=f"{role}_tenant_a", role=role, tenant_id="tenant_a")
    resource = FakeResource(resource_id=f"{resource_type}_tenant_b", tenant_id="tenant_b")

    with pytest.raises(TenantAccessDenied):
        if resource_type == "project":
            TenantGuard.assert_project_access(resource, user)
        elif resource_type == "simulation":
            TenantGuard.assert_simulation_access(resource, user)
        else:
            TenantGuard.assert_report_access(resource, user)


@pytest.mark.parametrize("resource_type", ["project", "simulation", "report"])
def test_super_admin_can_cross_tenant_for_all_resource_types(resource_type: str):
    user = FakeUser(user_id="super_tenant_a", role="super_admin", tenant_id="tenant_a")
    resource = FakeResource(resource_id=f"{resource_type}_tenant_b", tenant_id="tenant_b")

    if resource_type == "project":
        TenantGuard.assert_project_access(resource, user)
    elif resource_type == "simulation":
        TenantGuard.assert_simulation_access(resource, user)
    else:
        TenantGuard.assert_report_access(resource, user)


@pytest.mark.parametrize("resource_type", ["project", "simulation", "report"])
def test_legacy_resources_without_tenant_id_remain_readable(resource_type: str):
    user = FakeUser(user_id="researcher_tenant_a", role="researcher", tenant_id="tenant_a")
    resource = FakeResource(resource_id=f"{resource_type}_legacy", tenant_id=None)

    if resource_type == "project":
        TenantGuard.assert_project_access(resource, user)
    elif resource_type == "simulation":
        TenantGuard.assert_simulation_access(resource, user)
    else:
        TenantGuard.assert_report_access(resource, user)


def test_concurrent_tenant_checks_do_not_leak_between_tenants():
    tenant_a = FakeUser(user_id="researcher_a", role="researcher", tenant_id="tenant_a")
    tenant_b = FakeUser(user_id="researcher_b", role="researcher", tenant_id="tenant_b")
    own_a = FakeResource(resource_id="sim_a", tenant_id="tenant_a")
    own_b = FakeResource(resource_id="sim_b", tenant_id="tenant_b")
    cross_b = FakeResource(resource_id="sim_cross_b", tenant_id="tenant_b")

    def check(index: int) -> bool:
        if index % 2 == 0:
            TenantGuard.assert_simulation_access(own_a, tenant_a)
            with pytest.raises(TenantAccessDenied):
                TenantGuard.assert_simulation_access(cross_b, tenant_a)
        else:
            TenantGuard.assert_simulation_access(own_b, tenant_b)
        return True

    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(check, range(50)))

    assert all(results)
