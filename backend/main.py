import asyncio
import os
from datetime import date
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
import httpx
from pydantic import BaseModel
from typing import Optional
from dotenv import load_dotenv
from optimizer import optimize_routes
import optimizer as optimizer_module
from batch_schedule import run_batch_schedule, resolve_learned_durations, _match_key, _sb_get
from batch_auth import resolve_effective_tenant, AuthzError
import route_observations
import geo_resolver
import geo_health
import geo_addresses
import route_health
import audit_sweep

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL", "https://pxpqcdfxogaajwstwdtk.supabase.co")


async def _introspect_user_token(token: str, service_key: str) -> Optional[str]:
    """Validate a Supabase user JWT by asking GoTrue who it belongs to.
    Returns the auth user id (uid) if the token is valid, else None. Fail-closed."""
    if not token:
        return None
    try:
        async with httpx.AsyncClient(timeout=8) as c:
            r = await c.get(
                f"{SUPABASE_URL}/auth/v1/user",
                headers={"apikey": service_key, "Authorization": f"Bearer {token}"},
            )
        if r.status_code != 200:
            return None
        return r.json().get("id")
    except Exception:
        return None


async def _get_user_row(uid: str, service_key: str) -> Optional[dict]:
    """Read the caller's tenant + role from public.users using the service key
    (server-side, RLS-bypassing). Returns {tenant_id, role, super_admin} or None."""
    if not uid:
        return None
    try:
        async with httpx.AsyncClient(timeout=8) as c:
            r = await c.get(
                f"{SUPABASE_URL}/rest/v1/users",
                headers={"apikey": service_key, "Authorization": f"Bearer {service_key}"},
                params={"id": f"eq.{uid}", "select": "tenant_id,role,super_admin"},
            )
        if r.status_code != 200:
            return None
        rows = r.json()
        return rows[0] if rows else None
    except Exception:
        return None

app = FastAPI(title="Maslul Optimizer", version="1.0.0")

allowed_origins = os.getenv("ALLOWED_ORIGINS", "https://eranzivo.github.io").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_methods=["POST", "GET"],
    allow_headers=["Content-Type", "Authorization"],
)

# ── Daily element counter ─────────────────────────────────────────────────────
# Prevents runaway Google Maps spend. Resets automatically each UTC day.
# Limit is configurable via GMAPS_DAILY_ELEMENT_LIMIT env var (default 1 200).
# 1 200 elements/day ≈ 15 full-team optimizations (4 techs × 7 stops = 196 elements each).
# Free tier is 40 000 elements/month → 1 200/day uses at most ~36 000/month, well within free.

_DAILY_LIMIT = int(os.getenv("GMAPS_DAILY_ELEMENT_LIMIT", "1200"))
_counter: dict = {"day": None, "elements": 0}
# NOTE: _counter is per-process. With multiple Railway workers each worker enforces
# the limit independently, so effective daily limit = _DAILY_LIMIT × worker_count.
# Hobby plan runs 1 worker by default; set RAILWAY_NUMREPLICAS=1 to be explicit.

def _gmaps_quota_ok(elements_needed: int, charge: bool = True) -> bool:
    """charge=True consumes quota; charge=False only checks headroom (peek).
    The cache path peeks first and charges ACTUAL Google fetches afterwards —
    cache hits must not consume quota."""
    today = str(date.today())
    if _counter["day"] != today:
        _counter["day"] = today
        _counter["elements"] = 0
    if _counter["elements"] + elements_needed > _DAILY_LIMIT:
        return False
    if charge:
        _counter["elements"] += elements_needed
    return True

def _total_elements(technicians) -> int:
    """N locations per tech → N² elements in the distance matrix."""
    total = 0
    for tech in technicians:
        n = len(tech.tasks) + 1  # tasks + base city
        total += n * n
    return total


# Per-day /optimize call counter — visibility for resource/load planning (auto-sequence
# fires one call per touched tech-day, debounced). Resets each UTC day, per-process.
_opt_calls = {"day": None, "calls": 0, "tech_days": 0, "tasks": 0}

def _track_optimize(technicians) -> None:
    today = str(date.today())
    if _opt_calls["day"] != today:
        _opt_calls.update(day=today, calls=0, tech_days=0, tasks=0)
    _opt_calls["calls"] += 1
    _opt_calls["tech_days"] += len(technicians)
    _opt_calls["tasks"] += sum(len(t.tasks) for t in technicians)


# ── Models ────────────────────────────────────────────────────────────────────

class Task(BaseModel):
    id: str
    city: str
    address: Optional[str] = None
    lat: Optional[float] = None
    lon: Optional[float] = None
    duration_minutes: int = 30
    scheduled_time: Optional[str] = None
    window_start: Optional[str] = None   # hard customer window (e.g. "08:00")
    window_end: Optional[str] = None
    locked: bool = False                 # pinned by coordinator — never moved/dropped


class Technician(BaseModel):
    id: str
    name: str
    base_city: str
    return_city: Optional[str] = None
    start_time: str = "07:00"
    end_time: str = "18:00"
    breaks: list[dict] = []              # [{"from":"12:00","to":"13:00"}]
    tasks: list[Task] = []


class GeocodeRequest(BaseModel):
    street: str
    city: str


class SchedulingConfig(BaseModel):
    mode: str = "zone"
    zone_strict: bool = True
    fill_first: bool = True
    route_logic: bool = True
    route_strategy: str = "flexible"   # flexible | far_to_near | nearest_first
    window_semantics: str = "finish"   # finish | arrive (what the customer window promises)

class OptimizeRequest(BaseModel):
    date: str
    technicians: list[Technician]
    scheduling: Optional[SchedulingConfig] = None
    # Only honoured for super_admin / service-key callers (impersonation / cron);
    # everyone else is FORCED to their JWT's own tenant — see _resolve_audit_context.
    tenant_id: Optional[str] = None


class AuditDayRequest(OptimizeRequest):
    trigger: str = "manual"   # manual | nightly (change = the /optimize path)


# ── Route-audit persistence (route-intelligence P1) ──────────────────────────
# Health itself is computed inside optimize_routes from the solve it already
# performed; these helpers only decide WHO the audit belongs to and store it.
# Everything is fail-open: a persistence failure never breaks the optimize path.

async def _get_tenant_audit_cfg(tenant_id: str, service_key: str) -> dict:
    """config.audit for a tenant ({} when absent/unreadable)."""
    try:
        async with httpx.AsyncClient(timeout=8) as c:
            r = await c.get(
                f"{SUPABASE_URL}/rest/v1/tenants",
                headers={"apikey": service_key, "Authorization": f"Bearer {service_key}"},
                params={"id": f"eq.{tenant_id}", "select": "config"},
            )
        if r.status_code != 200 or not r.json():
            return {}
        return (r.json()[0].get("config") or {}).get("audit") or {}
    except Exception:
        return {}


async def _get_tenant_routing(tenant_id: str, service_key: str) -> dict:
    """config.routing for a tenant ({} when absent/unreadable) — the cross-tenant-brain knobs."""
    try:
        async with httpx.AsyncClient(timeout=8) as c:
            r = await c.get(
                f"{SUPABASE_URL}/rest/v1/tenants",
                headers={"apikey": service_key, "Authorization": f"Bearer {service_key}"},
                params={"id": f"eq.{tenant_id}", "select": "config"},
            )
        if r.status_code != 200 or not r.json():
            return {}
        return (r.json()[0].get("config") or {}).get("routing") or {}
    except Exception:
        return {}


async def _resolve_audit_context(request: Request, req_tenant_id: Optional[str],
                                 service_key: str) -> tuple[Optional[str], dict]:
    """(verified tenant_id, audit config) for an optionally-authenticated call.

    Bearer user-JWT → introspected, tenant FORCED to the user's own (super_admin
    may target req_tenant_id — impersonation). Bearer service-key → req_tenant_id
    trusted (nightly cron). No/invalid auth → (None, {}): health still computed
    and returned, nothing persisted. A tenant_id from the request body is NEVER
    trusted on its own — that would let an anonymous caller write another
    tenant's audit rows."""
    if not service_key:
        return None, {}
    auth = request.headers.get("Authorization", "")
    token = auth[7:] if auth.startswith("Bearer ") else ""
    if not token:
        return None, {}
    if token == service_key:
        tenant = req_tenant_id
    else:
        uid = await _introspect_user_token(token, service_key)
        row = await _get_user_row(uid, service_key)
        try:
            tenant = resolve_effective_tenant(row, req_tenant_id or "")
        except AuthzError:
            return None, {}
    if not tenant:
        return None, {}
    return tenant, await _get_tenant_audit_cfg(tenant, service_key)


async def _persist_audits(tenant_id: str, date_str: str, techs, results,
                          trigger: str, service_key: str) -> int:
    rows = route_health.build_audit_rows(tenant_id, date_str, techs, results, trigger)
    if not rows:
        return 0
    try:
        async with httpx.AsyncClient(timeout=8) as c:
            r = await c.post(
                f"{SUPABASE_URL}/rest/v1/route_audits",
                headers={"apikey": service_key,
                         "Authorization": f"Bearer {service_key}",
                         "Content-Type": "application/json",
                         "Prefer": "return=minimal"},
                json=rows,
            )
        if r.status_code not in (200, 201, 204):
            print(f"[audit] persist failed {r.status_code}: {r.text[:200]}")
            return 0
        return len(rows)
    except Exception as e:
        print(f"[audit] persist error: {e}")
        return 0


# ── Endpoints ─────────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    gmaps_key = os.getenv("GOOGLE_MAPS_API_KEY")
    today = str(date.today())
    used = _counter["elements"] if _counter["day"] == today else 0
    oc = _opt_calls if _opt_calls["day"] == today else {"calls": 0, "tech_days": 0, "tasks": 0}
    return {
        "status": "ok",
        "service": "maslul-optimizer",
        "version": "1.3.0",
        # In-memory brain size: 0 until the first optimize/geocode warms it; once warm it
        # must match geo_places row count (1,310 after the 2026-07-06 national import) —
        # a lower number means the paged loader regressed.
        "geo_brain_places": len(geo_resolver._brain["places"]),
        "gmaps": "configured" if gmaps_key else "missing — using haversine fallback",
        "route_cache": "configured" if os.getenv("SUPABASE_SERVICE_KEY") else "missing SUPABASE_SERVICE_KEY — optimizer works but never caches",
        "daily_elements_used": used,
        "daily_elements_limit": _DAILY_LIMIT,
        "daily_elements_remaining": max(0, _DAILY_LIMIT - used),
        "optimize_calls_today": oc["calls"],
        "tech_days_sequenced_today": oc["tech_days"],
        "tasks_sequenced_today": oc["tasks"],
    }


@app.post("/geocode")
async def geocode(req: GeocodeRequest):
    """Geocode a street address. Returns {lat, lon, source}.

    Cache-first via the shared address KB (`geo_addresses`, Geo Slice B): a repeat
    address — from ANY tenant — costs zero Google spend and zero quota. Only a real
    Google call is metered (10 elements). Trusted results (inside the IL bbox) are
    stored so the KB grows with every client's calls."""
    api_key = os.getenv("GOOGLE_MAPS_API_KEY")
    service_key = os.getenv("SUPABASE_SERVICE_KEY", "")

    # 0. Shared address KB first (fail-open — a KB outage degrades to plain Google)
    if service_key:
        await geo_resolver.ensure_loaded(service_key)  # city aliases for the key chain
        hit = geo_addresses.lookup(req.street, req.city, service_key)
        if hit:
            lat, lon, tier = hit
            return {"lat": lat, "lon": lon, "source": f"cache-{tier}"}

    if not api_key:
        raise HTTPException(status_code=503, detail="Maps key not configured")
    # Meter geocoding under the same daily counter (counts as 10 elements per call) so an
    # unauthenticated caller can't burn unbounded Google spend (CORS doesn't stop server-to-server).
    if not _gmaps_quota_ok(10):
        raise HTTPException(status_code=429, detail="Daily geocoding quota reached")

    coords = await geo_addresses.google_geocode(req.street, req.city, api_key)
    if coords is None:
        raise HTTPException(status_code=404, detail="Address not found")
    lat, lon = coords
    # Store only plausible-IL results — a bad geocode must never poison the shared KB.
    if service_key and geo_addresses.plausible_il(lat, lon):
        geo_addresses.store(req.street, req.city, lat, lon, service_key)
    return {"lat": lat, "lon": lon, "source": "google"}


@app.post("/optimize")
async def optimize(req: OptimizeRequest, request: Request):
    if not req.technicians:
        raise HTTPException(status_code=400, detail="No technicians provided")
    _track_optimize(req.technicians)

    google_maps_key = os.getenv("GOOGLE_MAPS_API_KEY") or None
    service_key = os.getenv("SUPABASE_SERVICE_KEY", "")

    # Route-audit context (optional Bearer): who this audit belongs to + knobs.
    # Anonymous callers still get routes + health in the response, never a DB write.
    audit_tenant, audit_cfg = await _resolve_audit_context(request, req.tenant_id, service_key)

    # Cross-tenant brain P2: tenant-learned leg durations (flag-gated, fail-open). Only for a
    # verified tenant with routing.learned_durations ON; otherwise None ⇒ today's behavior exactly.
    learned_legs = None
    if audit_tenant and service_key:
        try:
            if resolve_learned_durations({"routing": await _get_tenant_routing(audit_tenant, service_key)}):
                learned_legs = route_observations.get_learned_legs(audit_tenant, service_key)
        except Exception:
            learned_legs = None

    # Only use Google Maps if key is set AND daily quota has headroom.
    # Cache path: PEEK here, charge actual fetches after (cache hits are free).
    # Legacy path (no service key): pre-charge as before.
    use_gmaps = False
    if google_maps_key:
        needed = _total_elements(req.technicians)
        use_gmaps = _gmaps_quota_ok(needed, charge=not service_key)
        if not use_gmaps:
            print(f"[quota] daily limit reached ({_DAILY_LIMIT} elements) — falling back to haversine")

    result = await optimize_routes(
        req.technicians,
        google_maps_key if use_gmaps else None,
        service_key=service_key,
        route_strategy=(req.scheduling.route_strategy if req.scheduling else "flexible"),
        health_weights=(audit_cfg.get("health_weights") or None),
        window_semantics=(req.scheduling.window_semantics if req.scheduling else "finish"),
        learned_legs=learned_legs,
    )
    if service_key and optimizer_module.LAST_GOOGLE_ELEMENTS:
        _gmaps_quota_ok(optimizer_module.LAST_GOOGLE_ELEMENTS)  # charge real spend

    if audit_tenant and audit_cfg.get("enabled"):
        await _persist_audits(audit_tenant, req.date, req.technicians, result,
                              "change", service_key)

    return {
        "date": req.date,
        "mode": "gmaps" if use_gmaps else "local",
        "optimized": result,
    }


@app.post("/audit-day")
async def audit_day(req: AuditDayRequest, request: Request):
    """Audit-only pass: same payload shape as /optimize, NEVER consumes Google
    quota (cache-only matrix) and never proposes task writes to the caller —
    the response is health blocks only. Requires an authorized session (user
    JWT or service key); persists when the tenant's audit.enabled knob is on."""
    if not req.technicians:
        raise HTTPException(status_code=400, detail="No technicians provided")
    service_key = os.getenv("SUPABASE_SERVICE_KEY", "")
    audit_tenant, audit_cfg = await _resolve_audit_context(request, req.tenant_id, service_key)
    if not audit_tenant:
        raise HTTPException(status_code=401, detail="Audit requires an authorized session")

    result = await optimize_routes(
        req.technicians,
        None,  # cache-only: zero Google spend by construction
        service_key=service_key,
        route_strategy=(req.scheduling.route_strategy if req.scheduling else "flexible"),
        health_weights=(audit_cfg.get("health_weights") or None),
        window_semantics=(req.scheduling.window_semantics if req.scheduling else "finish"),
    )
    stored = 0
    if audit_cfg.get("enabled"):
        stored = await _persist_audits(audit_tenant, req.date, req.technicians, result,
                                       req.trigger, service_key)
    return {
        "date": req.date,
        "stored": stored,
        "audits": [{"technician_id": r["technician_id"], "health": r.get("health")}
                   for r in result],
    }


@app.post("/audit-sweep")
async def audit_sweep_endpoint(request: Request):
    """Manually run the nightly sweep (service-key or super_admin only —
    it walks every audit-enabled tenant)."""
    service_key = os.getenv("SUPABASE_SERVICE_KEY", "")
    if not service_key:
        raise HTTPException(status_code=503, detail="Service key not configured")
    auth = request.headers.get("Authorization", "")
    token = auth[7:] if auth.startswith("Bearer ") else ""
    if token != service_key:
        uid = await _introspect_user_token(token, service_key)
        row = await _get_user_row(uid, service_key)
        if not row or not row.get("super_admin"):
            raise HTTPException(status_code=403, detail="Not allowed")
    return await audit_sweep.run_audit_sweep(service_key, SUPABASE_URL)


@app.on_event("startup")
async def _arm_audit_sweep():
    # In-process nightly audit (02:30 UTC). Only armed when the backend can
    # actually persist (service key present); AUDIT_SWEEP_DISABLED=1 opts out.
    service_key = os.getenv("SUPABASE_SERVICE_KEY", "")
    if service_key and os.getenv("AUDIT_SWEEP_DISABLED") != "1":
        asyncio.create_task(audit_sweep.nightly_loop(service_key, SUPABASE_URL))


class BatchScheduleRequest(BaseModel):
    tenant_id: str
    date_from: str   # "YYYY-MM-DD" — first day to assign tasks to
    date_to: str     # "YYYY-MM-DD" — last day allowed
    dry_run: bool = False


@app.post("/batch-schedule")
async def batch_schedule(req: BatchScheduleRequest, request: Request):
    """
    Auto-assign all pending tasks for a tenant across a date range.
    Respects zone rotation, fill-first, equal city distribution, and
    runs OR-Tools per tech-day to produce service windows.

    Auth — two accepted Bearer tokens:
      • SUPABASE_SERVICE_KEY  → full-trust admin/cron path; req.tenant_id is used as-is.
      • A Supabase user JWT    → introspected; the batch is FORCED to the caller's own
        tenant (super_admin may target another via req.tenant_id). Techs are denied.
    Use dry_run=true to preview the schedule without writing to the DB.
    """
    service_key = os.getenv("SUPABASE_SERVICE_KEY", "")
    if not service_key:
        raise HTTPException(status_code=503, detail="Scheduler not configured")

    auth = request.headers.get("Authorization", "")
    token = auth[7:] if auth.startswith("Bearer ") else ""

    if token and token == service_key:
        # Full-trust service path (cron / Eran admin tooling).
        effective_tenant = req.tenant_id
    else:
        # Browser user-JWT path — verify the session, then force the tenant.
        uid = await _introspect_user_token(token, service_key)
        user_row = await _get_user_row(uid, service_key) if uid else None
        try:
            effective_tenant = resolve_effective_tenant(user_row, req.tenant_id)
        except AuthzError as e:
            raise HTTPException(status_code=e.status, detail=e.detail)

    result = await run_batch_schedule(
        tenant_id=effective_tenant,
        date_from=req.date_from,
        date_to=req.date_to,
        dry_run=req.dry_run,
        service_key=service_key,
    )
    return result


class GeoHealthRequest(BaseModel):
    # Only honoured for super_admin / service-key callers (impersonation / cron);
    # everyone else is FORCED to their JWT's own tenant.
    tenant_id: Optional[str] = None


# Active (schedulable) statuses whose cities are worth a geo-health check.
_GEOHEALTH_STATUSES = "pending,assigned,en_route,arrived"


@app.post("/geo-health")
async def geo_health_report(req: GeoHealthRequest, request: Request):
    """READ-ONLY geo diagnostics for the caller's tenant (Slice 1): which active task-cities
    don't resolve to coordinates (`unresolved`), and which resolve but aren't in any zone
    (`out_of_zone`), each with an affected-call count. Never writes.

    Auth mirrors /batch-schedule: SUPABASE_SERVICE_KEY Bearer (full trust; req.tenant_id as-is)
    OR a Supabase user JWT (introspected; tenant FORCED to the caller's own — super_admin may
    target another via req.tenant_id; techs denied). Fail-open: any data/brain error returns an
    all-clear report rather than a 500 into the UI."""
    service_key = os.getenv("SUPABASE_SERVICE_KEY", "")
    if not service_key:
        raise HTTPException(status_code=503, detail="Not configured")

    auth = request.headers.get("Authorization", "")
    token = auth[7:] if auth.startswith("Bearer ") else ""
    if token and token == service_key:
        tenant = req.tenant_id
    else:
        uid = await _introspect_user_token(token, service_key)
        user_row = await _get_user_row(uid, service_key) if uid else None
        try:
            tenant = resolve_effective_tenant(user_row, req.tenant_id or "")
        except AuthzError as e:
            raise HTTPException(status_code=e.status, detail=e.detail)
    if not tenant:
        raise HTTPException(status_code=400, detail="No tenant")

    empty = {"tenant_id": tenant, "unresolved": [], "out_of_zone": [],
             "summary": {"unresolved": 0, "out_of_zone": 0, "attention": 0, "checked_cities": 0}}
    try:
        await geo_resolver.ensure_loaded(service_key)  # shared brain (fail-open)
        tasks = await _sb_get("tasks", {
            "tenant_id": f"eq.{tenant}",
            "status": f"in.({_GEOHEALTH_STATUSES})",
            "select": "city",
        }, service_key)
        zones = await _sb_get("zones", {
            "tenant_id": f"eq.{tenant}",
            "select": "cities",
        }, service_key)
    except Exception:
        return empty

    # Distinct city → active-call count.
    counts: dict = {}
    for t in tasks:
        c = (t.get("city") or "").strip()
        if c:
            counts[c] = counts.get(c, 0) + 1

    alias_map = geo_resolver.alias_map()          # {} when brain not loaded → fail-open
    match_key = lambda name: _match_key(name, alias_map)  # noqa: E731  (same zone seam batch uses)
    zone_keys = {match_key(c) for z in zones for c in (z.get("cities") or [])}

    report = geo_health.build_health_report(
        counts.items(), zone_keys, geo_resolver.resolve, match_key)
    report["tenant_id"] = tenant
    return report
