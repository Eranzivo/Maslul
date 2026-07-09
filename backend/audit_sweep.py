"""Nightly route-audit sweep — route-intelligence P1, slice 5.

Audits the NEXT `days` days for every tenant whose `config.audit.enabled` knob
is on: assembles each tech-day's assigned calls into the same payload shape the
live `/optimize` path uses, runs the solver CACHE-ONLY (api_key None — zero
Google spend by construction; uncached legs degrade to haversine and the audit
row is marked partial-quality by its own numbers), and stores route_audits rows
with trigger='nightly'. This is the safety net for days changed by paths that
never hit the optimizer (manual placement with auto-sequence off).

Reuses batch_schedule's fetch + rule helpers (one implementation per rule):
`_sb_get`, `resolve_route_strategy`, `_effective_duration`, `tech_breaks`,
`_clamp_blocks`, `_dow`. Payload assembly is pure (`build_day_payloads`) and
unit-tested; only the fetch/persist shell touches the network. Fail-open per
tenant: one tenant's bad data never stops the sweep for the rest.
"""
import asyncio
from datetime import date, timedelta
from types import SimpleNamespace
from typing import Optional

import httpx

from batch_schedule import (_sb_get, _clamp_blocks, _dow, _effective_duration,
                            resolve_route_strategy, tech_breaks)
from optimizer import optimize_routes
import route_health

SWEEP_DAYS = 7
_ACTIVE_STATUSES = "in.(assigned,en_route,arrived)"


def _tech_hours(tech: dict, d: date) -> tuple:
    """Mirror of the batch closure tech_hours (weekly_schedule day override →
    tech default hours). Kept identical on purpose — a divergent copy here would
    audit against the wrong workday."""
    ws = tech.get("weekly_schedule") or {}
    day_cfg = ws.get(str(_dow(d)), {})
    if isinstance(day_cfg, dict) and day_cfg.get("work"):
        start = day_cfg.get("start") or tech.get("start_time", "07:00")
        end = day_cfg.get("end") or tech.get("end_time", "18:00")
        return start, end
    return tech.get("start_time", "07:00"), tech.get("end_time", "18:00")


def build_day_payloads(tasks_raw: list, techs_raw: list, cats_raw: list,
                       dayoffs_raw: list, config: Optional[dict]) -> dict:
    """Group assigned tasks into optimize_routes payloads: {date_str: [tech_ns]}.

    Only tech-days that HAVE assigned calls are audited (an empty day needs no
    audit); day-off eligibility is therefore irrelevant here — if calls are on
    the day, the day is real. Durations use the shared _effective_duration chain."""
    cat_dur = {c["id"]: c.get("duration_minutes") for c in (cats_raw or [])}
    techs_by_id = {t["id"]: t for t in (techs_raw or [])}
    partials: dict = {}
    for o in (dayoffs_raw or []):
        if o.get("type") == "partial":
            partials.setdefault((o["technician_id"], o["date"]), []).append(o)

    grouped: dict = {}
    for t in (tasks_raw or []):
        tid, ds = t.get("technician_id"), t.get("scheduled_date")
        if not tid or not ds or tid not in techs_by_id:
            continue
        grouped.setdefault((tid, ds), []).append(t)

    payloads: dict = {}
    for (tid, ds), day_tasks in grouped.items():
        tech = techs_by_id[tid]
        d = date.fromisoformat(ds)
        start_t, end_t = _tech_hours(tech, d)
        breaks = _clamp_blocks(
            tech_breaks(tech, config, partials.get((tid, ds), [])), start_t, end_t)
        task_ns = [SimpleNamespace(
            id=str(x["id"]), city=x.get("city") or "",
            address=x.get("street"), lat=x.get("lat"), lon=x.get("lon"),
            duration_minutes=_effective_duration(x.get("category_id"), tech, cat_dur, config),
            scheduled_time=(x.get("scheduled_time") or "")[:5] or None,
            window_start=(x.get("scheduled_window_start") or "")[:5] or None,
            window_end=(x.get("scheduled_window_end") or "")[:5] or None,
            locked=bool(x.get("locked")),
        ) for x in day_tasks]
        payloads.setdefault(ds, []).append(SimpleNamespace(
            id=str(tid), name=tech.get("name") or "",
            base_city=tech.get("base_city") or "",
            return_city=tech.get("return_city"),
            start_time=start_t, end_time=end_t,
            breaks=breaks, tasks=task_ns,
        ))
    return payloads


async def persist_rows(rows: list, service_key: str, supabase_url: str) -> int:
    """Insert route_audits rows with the service key. Fail-open (0 on error)."""
    if not rows:
        return 0
    try:
        async with httpx.AsyncClient(timeout=8) as c:
            r = await c.post(
                f"{supabase_url}/rest/v1/route_audits",
                headers={"apikey": service_key,
                         "Authorization": f"Bearer {service_key}",
                         "Content-Type": "application/json",
                         "Prefer": "return=minimal"},
                json=rows,
            )
        if r.status_code not in (200, 201, 204):
            print(f"[sweep] persist failed {r.status_code}: {r.text[:200]}")
            return 0
        return len(rows)
    except Exception as e:
        print(f"[sweep] persist error: {e}")
        return 0


async def run_audit_sweep(service_key: str, supabase_url: str,
                          days: int = SWEEP_DAYS, only_tenant: Optional[str] = None) -> dict:
    """Sweep every audit-enabled tenant (or one). Returns a per-tenant summary."""
    date_from = date.today().isoformat()
    date_to = (date.today() + timedelta(days=days - 1)).isoformat()
    tenants = await _sb_get("tenants", {"select": "id,config"}, service_key)
    summary = {"from": date_from, "to": date_to, "tenants": {}}

    for row in tenants:
        tenant_id = row["id"]
        config = row.get("config") or {}
        audit_cfg = config.get("audit") or {}
        if only_tenant and tenant_id != only_tenant:
            continue
        if not audit_cfg.get("enabled"):
            continue
        try:
            tasks_raw = await _sb_get("tasks", {
                "tenant_id": f"eq.{tenant_id}", "status": _ACTIVE_STATUSES,
                "and": f"(scheduled_date.gte.{date_from},scheduled_date.lte.{date_to})",
                "select": "id,city,street,lat,lon,category_id,technician_id,"
                          "scheduled_date,scheduled_time,scheduled_window_start,"
                          "scheduled_window_end,locked",
            }, service_key)
            techs_raw = await _sb_get("technicians", {
                "tenant_id": f"eq.{tenant_id}",
                "select": "id,name,base_city,return_city,weekly_schedule,start_time,"
                          "end_time,duration_overrides",
            }, service_key)
            cats_raw = await _sb_get("categories", {
                "tenant_id": f"eq.{tenant_id}", "select": "id,duration_minutes",
            }, service_key)
            dayoffs_raw = await _sb_get("day_offs", {
                "tenant_id": f"eq.{tenant_id}",
                "and": f"(date.gte.{date_from},date.lte.{date_to})",
                "select": "*",
            }, service_key)

            payloads = build_day_payloads(tasks_raw, techs_raw, cats_raw, dayoffs_raw, config)
            strategy = resolve_route_strategy(config)
            weights = audit_cfg.get("health_weights") or None
            stored = audited = 0
            for ds, techs in sorted(payloads.items()):
                results = await optimize_routes(techs, None, service_key=service_key,
                                                route_strategy=strategy,
                                                health_weights=weights)
                rows = route_health.build_audit_rows(tenant_id, ds, techs, results, "nightly")
                stored += await persist_rows(rows, service_key, supabase_url)
                audited += len(rows)
            summary["tenants"][tenant_id] = {"tech_days": audited, "stored": stored}
        except Exception as e:
            print(f"[sweep] tenant {tenant_id} failed: {e}")
            summary["tenants"][tenant_id] = {"error": str(e)[:200]}
    return summary


async def nightly_loop(service_key: str, supabase_url: str, hour_utc: int = 2, minute: int = 30):
    """In-process scheduler: run the sweep once per UTC day at hour:minute.
    Single Railway worker ⇒ single loop; a worker restart just re-arms it."""
    from datetime import datetime, timezone
    while True:
        now = datetime.now(timezone.utc)
        nxt = now.replace(hour=hour_utc, minute=minute, second=0, microsecond=0)
        if nxt <= now:
            nxt += timedelta(days=1)
        await asyncio.sleep((nxt - now).total_seconds())
        try:
            s = await run_audit_sweep(service_key, supabase_url)
            print(f"[sweep] nightly done: {s}")
        except Exception as e:
            print(f"[sweep] nightly failed: {e}")
