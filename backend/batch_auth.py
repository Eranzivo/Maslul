"""Authorization for the /batch-schedule endpoint.

Two caller types are supported:

  1. **Service-key Bearer** (cron / Eran's admin tooling) — full trust; the request's
     `tenant_id` is used as-is. This is the original behaviour.
  2. **User-JWT Bearer** (browser coordinator/admin) — the token is introspected against
     Supabase Auth, the user's row is read with the service key, and the tenant is FORCED
     to the user's own tenant so a caller can never batch another tenant's tasks. Techs are
     denied. This keeps the engine generic: any tenant's admin/coordinator batches their own
     pending tasks — nothing is special-cased per client.

The network pieces (token introspection, user lookup) live in `main.py`; the pure
authorization decision lives here so it is unit-testable without network or secrets.
"""
from typing import Optional

# Roles permitted to run a batch schedule for their own tenant.
_DISPATCH_ROLES = {"admin", "coordinator"}


class AuthzError(Exception):
    """Raised when a user-JWT caller is not allowed to run the requested batch."""

    def __init__(self, status: int, detail: str):
        self.status = status
        self.detail = detail
        super().__init__(detail)


def resolve_effective_tenant(user_row: Optional[dict], requested_tenant_id: str) -> str:
    """Decide which tenant a user-JWT caller may batch-schedule.

    Args:
        user_row: ``{tenant_id, role, super_admin}`` from public.users, or ``None`` if the
            token was invalid / the user has no row.
        requested_tenant_id: tenant_id from the request body. Only honoured for super_admin
            (who impersonates other tenants); ignored for everyone else.

    Returns:
        The tenant_id the batch must run for.

    Raises:
        AuthzError: 401 for an invalid token, 403 for a disallowed role / missing tenant.
    """
    if not user_row:
        raise AuthzError(401, "Invalid or expired session")

    own_tenant = user_row.get("tenant_id")
    role = user_row.get("role")
    is_super = bool(user_row.get("super_admin"))

    if is_super:
        # Super admin (Eran) may target any tenant (impersonation); fall back to own tenant.
        return requested_tenant_id or own_tenant

    if role in _DISPATCH_ROLES:
        if not own_tenant:
            raise AuthzError(403, "No tenant for this user")
        # Force own tenant — a coordinator can never batch another tenant's tasks,
        # regardless of what tenant_id the request body claims.
        return own_tenant

    # tech / unknown role
    raise AuthzError(403, "This account is not allowed to run batch scheduling")
