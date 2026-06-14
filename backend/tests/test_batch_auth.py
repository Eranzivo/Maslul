import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
import pytest
from batch_auth import resolve_effective_tenant, AuthzError

OWN = "00000000-0000-0000-0000-000000000001"
OTHER = "99999999-9999-9999-9999-999999999999"
ADMIN_TENANT = "642ad6e6-a093-46a4-8489-ce49a966d77c"


def test_invalid_token_rejected():
    with pytest.raises(AuthzError) as e:
        resolve_effective_tenant(None, OWN)
    assert e.value.status == 401


def test_coordinator_forced_to_own_tenant():
    row = {"tenant_id": OWN, "role": "coordinator", "super_admin": False}
    # Even if the request body asks for another tenant, the coordinator gets their own.
    assert resolve_effective_tenant(row, OTHER) == OWN


def test_admin_forced_to_own_tenant():
    row = {"tenant_id": OWN, "role": "admin", "super_admin": False}
    assert resolve_effective_tenant(row, OWN) == OWN


def test_tech_denied():
    row = {"tenant_id": OWN, "role": "tech", "super_admin": False}
    with pytest.raises(AuthzError) as e:
        resolve_effective_tenant(row, OWN)
    assert e.value.status == 403


def test_unknown_role_denied():
    row = {"tenant_id": OWN, "role": "viewer", "super_admin": False}
    with pytest.raises(AuthzError) as e:
        resolve_effective_tenant(row, OWN)
    assert e.value.status == 403


def test_super_admin_may_target_other_tenant():
    row = {"tenant_id": ADMIN_TENANT, "role": "admin", "super_admin": True}
    assert resolve_effective_tenant(row, OTHER) == OTHER


def test_super_admin_defaults_to_own_when_none_requested():
    row = {"tenant_id": ADMIN_TENANT, "role": "admin", "super_admin": True}
    assert resolve_effective_tenant(row, "") == ADMIN_TENANT


def test_user_without_tenant_denied():
    row = {"tenant_id": None, "role": "coordinator", "super_admin": False}
    with pytest.raises(AuthzError) as e:
        resolve_effective_tenant(row, OWN)
    assert e.value.status == 403
