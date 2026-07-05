"""
Batch scheduler — assigns all pending tasks for a tenant to technicians
across a date range, respecting zone rotation, fill-first, and equal city
distribution. Runs the OR-Tools optimizer per tech-day to get arrival times
and service windows. Writes results directly to Supabase via service key.
"""
import os
from datetime import date, timedelta
from typing import Optional
import httpx
from optimizer import solve_route_v2, build_matrix_local
from cities import resolve_coords
import geo_resolver

SUPABASE_URL = os.getenv("SUPABASE_URL", "https://pxpqcdfxogaajwstwdtk.supabase.co")

# ── Supabase helpers ──────────────────────────────────────────────────────────

def _sb_headers(service_key: str) -> dict:
    return {
        "apikey": service_key,
        "Authorization": f"Bearer {service_key}",
        "Content-Type": "application/json",
    }

async def _sb_get(path: str, params: dict, key: str) -> list:
    async with httpx.AsyncClient(timeout=15) as c:
        r = await c.get(
            f"{SUPABASE_URL}/rest/v1/{path}",
            headers=_sb_headers(key),
            params=params,
        )
        r.raise_for_status()
        return r.json()

async def _sb_patch(task_id: str, body: dict, key: str):
    async with httpx.AsyncClient(timeout=10) as c:
        r = await c.patch(
            f"{SUPABASE_URL}/rest/v1/tasks",
            headers={**_sb_headers(key), "Prefer": "return=minimal"},
            params={"id": f"eq.{task_id}"},
            json=body,
        )
        r.raise_for_status()


# ── City normalization (mirrors JS normalizeCity) ─────────────────────────────

_CITY_ALIASES = {
    'ב"ש': 'באר שבע', "ב'ש": 'באר שבע',
    'ראשל"צ': 'ראשון לציון',
    'פ"ת': 'פתח תקווה', "פ'ת": 'פתח תקווה',
    'ק"ג': 'קרית גת', 'קריית גת': 'קרית גת',
    'ק"מ': 'קרית מלאכי', 'קריית מלאכי': 'קרית מלאכי',
    'ת"א': 'תל אביב',
    'נהריה': 'נהרייה',
    'נהרייה': 'נהרייה',
    # Kiryat Shmona — bare/abbrev forms map to the zone's stored spelling קריית שמונה
    'קש': 'קריית שמונה', 'ק"ש': 'קריית שמונה', 'קרית שמונה': 'קריית שמונה',
    # Zichron — bare "זכרון"/"זיכרון" map to the zone's city זכרון יעקב
    'זכרון': 'זכרון יעקב', 'זיכרון': 'זכרון יעקב', 'זיכרון יעקב': 'זכרון יעקב',
}

def _norm(city: str) -> str:
    c = city.strip()
    return _CITY_ALIASES.get(c, c)


# ── Date helpers ──────────────────────────────────────────────────────────────

def _dow(d: date) -> int:
    """Israeli day-of-week: 0=Sun … 5=Fri. Saturday returns 6."""
    return (d.weekday() + 1) % 7

def _time_to_min(t: str) -> int:
    h, m = map(int, t.split(':'))
    return h * 60 + m

def _min_to_time(m: int) -> str:
    m = max(0, min(m, 23 * 60 + 59))
    return f"{m // 60:02d}:{m % 60:02d}"


# ── Engine wiring (pure, testable) ────────────────────────────────────────────

def resolve_route_strategy(config: Optional[dict]) -> str:
    """Mirror of the JS resolveRouteStrategy — absent config NEVER defaults to
    far_to_near (that is PureWater-specific tenant config, not a global default)."""
    sched = (config or {}).get("scheduling") or {}
    rs = sched.get("route_strategy")
    if rs:
        return rs
    if sched.get("route_logic"):  # legacy boolean flag
        return "far_to_near"
    return "flexible"


def tenant_works_day(dow: int, config: Optional[dict]) -> bool:
    """Is `dow` (0=Sun … 6=Sat) a tenant working day? Reads
    `config.defaults.work_days` (array of weekday ints). Absent/empty ⇒ today's
    behavior: Saturday (6) off, every other day on. Per-tech `weekly_schedule.work`
    and `day_offs` are applied separately (AND). Mirrors JS `isTenantWorkDay`."""
    wd = ((config or {}).get("defaults") or {}).get("work_days")
    if not isinstance(wd, list) or not wd:
        return dow != 6
    return dow in wd


def _arrival_window_hours(config: Optional[dict]) -> int:
    """Customer service-window length. Real location: `config.defaults.arrival_window_hours`
    (the shape every other defaults knob uses). The old top-level read was a bug — kept only
    as a fallback so a tenant that was ever set that way keeps working."""
    cfg = config or {}
    d = (cfg.get("defaults") or {}).get("arrival_window_hours")
    if isinstance(d, (int, float)) and d > 0:
        return int(d)
    top = cfg.get("arrival_window_hours")
    if isinstance(top, (int, float)) and top > 0:
        return int(top)
    return 3


def _effective_duration(cat_id, tech: dict, cat_duration: dict, config: Optional[dict]) -> int:
    """Job duration, mirroring the live JS chain: tech duration_overrides →
    category default → tenant defaults.regular_job_minutes → 30."""
    ov = (tech.get("duration_overrides") or {}) if tech else {}
    if cat_id and ov.get(cat_id):
        return int(ov[cat_id])
    if cat_id and cat_duration.get(cat_id):
        return int(cat_duration[cat_id])
    reg = ((config or {}).get("defaults") or {}).get("regular_job_minutes")
    if isinstance(reg, (int, float)) and reg > 0:
        return int(reg)
    return 30


def tech_has_skill(tech: dict, cat_id) -> bool:
    """Mirror of JS techHasSkill: no category ⇒ allowed; otherwise the category must be
    in the tech's skills list (empty/absent skills ⇒ NOT allowed, same as JS)."""
    if not cat_id:
        return True
    return cat_id in (tech.get("skills") or [])


def cat_limit_ok(tech: dict, cat_id, current_count: int) -> bool:
    """Mirror of JS getCatLimitOk: no category or no limit configured ⇒ ok;
    otherwise the day's count for that category must stay below the limit."""
    if not cat_id:
        return True
    limit = (tech.get("cat_limits") or {}).get(cat_id)
    if not limit:
        return True
    try:
        return current_count < int(limit)
    except (TypeError, ValueError):
        return True


def city_blocked(tech: dict, city_norm: str) -> bool:
    """Is this (normalized) city in the tech's blocked_cities list?"""
    return city_norm in (tech.get("blocked_cities") or [])


def zone_blocked(tech: dict, zone_id) -> bool:
    """Is this zone in the tech's blocked_zones list?"""
    return zone_id in (tech.get("blocked_zones") or [])


def tech_breaks(tech: dict, config: Optional[dict], partial_dayoffs: list) -> list:
    """Blocked intervals for a tech-day as [{"from": "HH:MM", "to": "HH:MM"}] — the solver's
    `breaks` input. Mirror of JS getTechPartialBlocks: partial day_offs + the resolved break
    (tech weekly_schedule._break: 'none' ⇒ no break, 'custom' ⇒ its own hours, else the
    tenant defaults.break when enabled)."""
    blocks = [{"from": p["from_time"], "to": p["to_time"]}
              for p in (partial_dayoffs or []) if p.get("from_time") and p.get("to_time")]
    tb = ((tech or {}).get("weekly_schedule") or {}).get("_break")
    brk = None
    if tb:
        if tb.get("mode") == "none":
            return blocks
        if tb.get("mode") == "custom":
            brk = {"enabled": True, "start": tb.get("start"), "end": tb.get("end")}
    if brk is None:
        brk = ((config or {}).get("defaults") or {}).get("break") or {}
    if brk.get("enabled") and brk.get("start") and brk.get("end"):
        blocks.append({"from": brk["start"], "to": brk["end"]})
    return blocks


def _assignment_score(count: int, city_load: int, balance_conf: Optional[dict]) -> float:
    """Score a candidate (tech, day) for one task — higher is better.

    Default (balance off / absent): fill active days first (`count*100`), penalise
    over-concentration of one city. This is today's behaviour — absent config = unchanged.

    Balance on (`scheduling.balance.enabled`): fluid even workload spread — prefer the
    LEAST-loaded covering tech-day (negative count), with a same-city nudge so identical-
    city jobs split across the covering days. Greedy-applied this yields 8→4-4, 7→4-3,
    6→3-3, adapting to each week's actual count. Soft (never a hard cap); still bounded by
    max_daily and customer date/window requests. Tunable via `balance.weight`."""
    bal = balance_conf or {}
    if bal.get("enabled"):
        w = bal.get("weight", 50)
        return -count * w - city_load * (w // 2)
    return count * 100 - city_load * 50


def solve_day_with_existing(matrix, existing_v2, new_v2, start_t, end_t, breaks,
                            return_node, route_strategy):
    """Order one tech-day containing EXISTING calls (already promised) + NEW calls.

    Policy (approved 2026-07-05): existing calls keep their customer window as a hard
    constraint — their internal time may re-flow within it; locked calls are pinned at
    their exact time; an existing call is NEVER dropped in favor of a new one. If the
    first solve drops any existing call, re-solve with ALL existing pinned at their
    current times so only new calls can drop (attempt 2).

    Node order: 0 = depot, 1..n_e = existing, n_e+1.. = new (matrix must match).
    Returns {"ordered": [combined_idx...], "arrivals": [abs-minute...],
             "dropped_new": [combined_idx...], "pinned_fallback": bool}.
    """
    n_e = len(existing_v2)
    tasks = list(existing_v2) + list(new_v2)
    res = solve_route_v2(matrix, tasks, start_t, end_t, breaks=breaks,
                         return_node=return_node, route_strategy=route_strategy)
    pinned_fallback = False
    if any(i < n_e for i in res["dropped"]):
        # Existing commitments outrank new placements: pin them all, retry.
        pinned = [dict(t, locked=True) for t in existing_v2]
        res = solve_route_v2(matrix, pinned + list(new_v2), start_t, end_t, breaks=breaks,
                             return_node=return_node, route_strategy=route_strategy)
        pinned_fallback = True
    dropped_new = [i for i in res["dropped"] if i >= n_e]
    # An existing call still dropped here (e.g. locked-vs-locked conflict) is left
    # untouched in the DB — the caller must not unassign it.
    return {"ordered": res["ordered"], "arrivals": res["arrivals"],
            "dropped_new": dropped_new, "pinned_fallback": pinned_fallback}


def optimize_day(matrix, durations, start_t, end_t, return_node, route_strategy):
    """Order one tech-day with the authoritative v2 solver (the same engine the
    live path uses) so the batch reflects route_strategy physics (far→near),
    hard work-hours, and drop-if-overfull. Returns (ordered_idx, arrivals, dropped_idx)."""
    tasks_v2 = [{"duration": d, "window_start": None, "window_end": None,
                 "locked": False, "scheduled_time": None} for d in durations]
    res = solve_route_v2(matrix, tasks_v2, start_t, end_t, breaks=[],
                         return_node=return_node, route_strategy=route_strategy)
    return res["ordered"], res["arrivals"], res["dropped"]


# ── Main entry point ──────────────────────────────────────────────────────────

async def run_batch_schedule(
    tenant_id: str,
    date_from: str,
    date_to: str,
    dry_run: bool,
    service_key: str,
) -> dict:

    await geo_resolver.ensure_loaded(service_key)  # load the shared geo brain (fail-open)

    # 1. Fetch all required data — including the LIVE calendar state. All fetches happen
    # before any write and raise on failure (fail-closed: no partial batch).
    tasks_raw = await _sb_get("tasks", {
        "tenant_id": f"eq.{tenant_id}",
        "status": "eq.pending",
        "select": "id,city,street,lat,lon,category_id",
    }, service_key)

    # Existing calls in range: they occupy capacity and shape every day's route.
    existing_raw = await _sb_get("tasks", {
        "tenant_id": f"eq.{tenant_id}",
        "status": "in.(assigned,en_route,arrived)",
        "and": f"(scheduled_date.gte.{date_from},scheduled_date.lte.{date_to})",
        "select": "id,city,street,lat,lon,category_id,technician_id,scheduled_date,"
                  "scheduled_time,scheduled_window_start,scheduled_window_end,locked",
    }, service_key)

    dayoffs_raw = await _sb_get("day_offs", {
        "tenant_id": f"eq.{tenant_id}",
        "and": f"(date.gte.{date_from},date.lte.{date_to})",
        "select": "technician_id,date,type,from_time,to_time",
    }, service_key)

    zones_raw = await _sb_get("zones", {
        "tenant_id": f"eq.{tenant_id}",
        "select": "id,name,cities",
    }, service_key)

    techs_raw = await _sb_get("technicians", {
        "tenant_id": f"eq.{tenant_id}",
        "select": "id,name,base_city,return_city,rotation,weekly_schedule,start_time,end_time,"
                  "max_daily,skills,cat_limits,blocked_zones,blocked_cities,duration_overrides",
    }, service_key)

    cats_raw = await _sb_get("categories", {
        "tenant_id": f"eq.{tenant_id}",
        "select": "id,duration_minutes",
    }, service_key)

    tenant_rows = await _sb_get("tenants", {
        "id": f"eq.{tenant_id}",
        "select": "config",
    }, service_key)

    config = tenant_rows[0]["config"] if tenant_rows else {}
    arrival_window_h = _arrival_window_hours(config)
    route_strategy = resolve_route_strategy(config)
    balance_conf = (config.get("scheduling") or {}).get("balance")  # None ⇒ today's fill-first packing

    # 2. Build lookup tables
    cat_duration = {c["id"]: c.get("duration_minutes", 30) for c in cats_raw}
    tech_name_map = {t["id"]: t["name"] for t in techs_raw}

    # zone_map: {zone_id: {name, cities_normalized[]}}
    zone_map = {
        z["id"]: {"name": z["name"], "cities": [_norm(c) for c in (z.get("cities") or [])]}
        for z in zones_raw
    }

    def find_zone(city: str) -> Optional[str]:
        nc = _norm(city)
        for zid, z in zone_map.items():
            if nc in z["cities"]:
                return zid
        return None

    def tech_zone_for_day(tech: dict, d: date) -> Optional[str]:
        rotation = tech.get("rotation") or {}
        return rotation.get(str(_dow(d)))

    # Day-off lookups (mirror of the live path's isTechAvailable / getTechPartialBlocks)
    dayoffs_full = {(o["technician_id"], o["date"]) for o in dayoffs_raw
                    if o.get("type") == "full"}
    dayoffs_partial: dict[tuple, list] = {}
    for o in dayoffs_raw:
        if o.get("type") == "partial":
            dayoffs_partial.setdefault((o["technician_id"], o["date"]), []).append(o)

    def tech_is_working(tech: dict, d: date) -> bool:
        if not tenant_works_day(_dow(d), config):  # tenant-level off-day (Sat off by default)
            return False
        if (tech["id"], d.isoformat()) in dayoffs_full:  # vacation / full day off
            return False
        ws = tech.get("weekly_schedule") or {}
        day_cfg = ws.get(str(_dow(d)), {})
        if isinstance(day_cfg, dict):
            return day_cfg.get("work", True)
        return True

    def tech_hours(tech: dict, d: date) -> tuple[str, str]:
        ws = tech.get("weekly_schedule") or {}
        day_cfg = ws.get(str(_dow(d)), {})
        if isinstance(day_cfg, dict) and day_cfg.get("work"):
            start = day_cfg.get("start") or tech.get("start_time", "07:00")
            end   = day_cfg.get("end")   or tech.get("end_time",   "18:00")
            return start, end
        return tech.get("start_time", "07:00"), tech.get("end_time", "18:00")

    def tech_max_daily(tech: dict) -> int:
        v = tech.get("max_daily")
        if isinstance(v, int) and v > 0:
            return v
        return config.get("defaults", {}).get("max_daily_jobs", 9)

    # 3. Greedy task → tech+day assignment — seeded with the LIVE calendar so every
    # count (capacity, same-city, per-category) reflects reality, not an empty week.
    # day_slots: {(tech_id, date_str): [task_dict, ...]} — NEW placements only
    day_slots: dict[tuple, list] = {}
    # existing_slots: {(tech_id, date_str): [existing_task, ...]} — read-only occupancy
    existing_slots: dict[tuple, list] = {}
    # city_counts per tech (for equal city distribution penalty)
    city_counts: dict[str, dict[str, int]] = {t["id"]: {} for t in techs_raw}
    # cat_counts: {(tech_id, date_str, category_id): n} — for cat_limits
    cat_counts: dict[tuple, int] = {}

    for e in existing_raw:
        tid = e.get("technician_id")
        if tid is None or e.get("scheduled_date") is None:
            continue
        key = (tid, e["scheduled_date"])
        existing_slots.setdefault(key, []).append(e)
        nc = _norm(e.get("city") or "")
        if tid in city_counts:
            city_counts[tid][nc] = city_counts[tid].get(nc, 0) + 1
        if e.get("category_id"):
            ck = (tid, e["scheduled_date"], e["category_id"])
            cat_counts[ck] = cat_counts.get(ck, 0) + 1

    def occupancy(key: tuple) -> int:
        return len(day_slots.get(key, [])) + len(existing_slots.get(key, []))

    unassigned = []
    d_start = date.fromisoformat(date_from)
    d_end   = date.fromisoformat(date_to)

    for task in tasks_raw:
        zone_id = find_zone(task["city"])
        if not zone_id:
            unassigned.append({"id": task["id"], "city": task["city"], "reason": "city_not_in_zone"})
            continue

        # Location must be locatable for sane routing. If the task has no coords AND its
        # city can't be resolved by either its raw or normalized spelling (unknown
        # settlement / typo / new-client test data), DON'T guess — leave it pending and
        # flag it so the coordinator completes the address. Routing uses the raw city, so
        # the raw spelling resolving is sufficient (avoids false flags from alias rewrites).
        if (not (task.get("lat") and task.get("lon"))
                and geo_resolver.resolve(task["city"]) is None
                and geo_resolver.resolve(_norm(task["city"])) is None):
            unassigned.append({"id": task["id"], "city": task["city"], "reason": "needs_location"})
            continue

        best_key: Optional[tuple] = None
        best_score = float("-inf")  # balance-on scores are negative — never seed at a finite floor

        cat_id = task.get("category_id")
        nc = _norm(task["city"])
        cur = d_start
        while cur <= d_end:
            for tech in techs_raw:
                if not tech_is_working(tech, cur):
                    continue
                if tech_zone_for_day(tech, cur) != zone_id:
                    continue
                # Same eligibility gates as the live _candidatesZone path:
                if zone_blocked(tech, zone_id) or city_blocked(tech, nc):
                    continue
                if not tech_has_skill(tech, cat_id):
                    continue
                key = (tech["id"], cur.isoformat())
                count = occupancy(key)  # existing + newly placed
                if count >= tech_max_daily(tech):
                    continue
                if not cat_limit_ok(tech, cat_id,
                                    cat_counts.get((tech["id"], cur.isoformat(), cat_id), 0)):
                    continue

                city_load = city_counts[tech["id"]].get(nc, 0)
                # Balance off ⇒ fill-first packing (today's behavior); balance on ⇒ fluid
                # even spread across covering tech-days (8→4-4, 7→4-3). See _assignment_score.
                score = _assignment_score(count, city_load, balance_conf)

                if score > best_score:
                    best_score = score
                    best_key = key
            cur += timedelta(days=1)

        if best_key is None:
            unassigned.append({"id": task["id"], "city": task["city"], "reason": "no_slot_in_range"})
            continue

        tech_id_key = best_key[0]
        assigned_tech = next(t for t in techs_raw if t["id"] == tech_id_key)
        task["_duration"] = _effective_duration(cat_id, assigned_tech, cat_duration, config)
        day_slots.setdefault(best_key, []).append(task)
        city_counts[tech_id_key][nc] = city_counts[tech_id_key].get(nc, 0) + 1
        if cat_id:
            ck = (tech_id_key, best_key[1], cat_id)
            cat_counts[ck] = cat_counts.get(ck, 0) + 1

    # 4. Optimize each tech+day (existing + new together) and write results.
    # Only days that RECEIVE new calls are solved — days the batch doesn't touch stay as-is.
    assignments = []
    retimed_existing = 0

    def _loc(t: dict) -> str:
        if t.get("lat") and t.get("lon"):
            return f"{t['lat']},{t['lon']}"
        if t.get("street"):
            return f"{t['street']}, {t['city']}"
        return t["city"]

    for (tech_id, date_str), day_tasks in sorted(day_slots.items(), key=lambda x: (x[0][1], x[0][0])):
        tech = next(t for t in techs_raw if t["id"] == tech_id)
        start_t, end_t = tech_hours(tech, date.fromisoformat(date_str))
        start_min = _time_to_min(start_t)
        base = tech.get("base_city") or "אשקלון"
        ret  = tech.get("return_city") or ""
        return_loc = ret if (ret and ret != base) else ""

        day_existing = existing_slots.get((tech_id, date_str), [])
        locations = ([base] + [_loc(e) for e in day_existing] + [_loc(t) for t in day_tasks]
                     + ([return_loc] if return_loc else []))

        # Tasks at city-level only (no street/coords) — haversine is equivalent
        # to Google Maps for city-center→city-center and avoids burning API quota.
        # Real drive-time refinement happens later via the live cache-backed sequencer.
        matrix = build_matrix_local(locations)

        existing_v2 = [{
            "duration": _effective_duration(e.get("category_id"), tech, cat_duration, config),
            "window_start": e.get("scheduled_window_start"),
            "window_end": e.get("scheduled_window_end"),
            "locked": bool(e.get("locked")),
            "scheduled_time": (e.get("scheduled_time") or "")[:5] or None,
        } for e in day_existing]
        new_v2 = [{"duration": t["_duration"], "window_start": None, "window_end": None,
                   "locked": False, "scheduled_time": None} for t in day_tasks]
        brk = tech_breaks(tech, config, dayoffs_partial.get((tech_id, date_str), []))

        r = solve_day_with_existing(
            matrix, existing_v2, new_v2, start_t, end_t, breaks=brk,
            return_node=bool(return_loc), route_strategy=route_strategy)

        n_e = len(day_existing)
        # Over-full day: the solver dropped NEW calls rather than fail — leave them
        # pending and surface them so the coordinator can re-place or extend hours.
        # (Existing calls are never dropped/unassigned by the batch — see the solver policy.)
        for di in r["dropped_new"]:
            dt = day_tasks[di - n_e]
            unassigned.append({"id": dt["id"], "city": dt["city"], "reason": "day_over_capacity"})

        win_mins = arrival_window_h * 60
        for i, arr in zip(r["ordered"], r["arrivals"]):
            if i < n_e:
                # Existing call: window/date/tech/status untouchable; only the internal
                # time may re-flow (within its window — enforced by the solver).
                e = day_existing[i]
                new_time = _min_to_time(arr)
                if new_time != (e.get("scheduled_time") or "")[:5] and not e.get("locked"):
                    retimed_existing += 1
                    if not dry_run:
                        await _sb_patch(e["id"], {"scheduled_time": new_time}, service_key)
                continue
            task = day_tasks[i - n_e]
            slot_num   = max(0, (arr - start_min) // win_mins)
            slot_start = start_min + slot_num * win_mins
            payload = {
                "technician_id":          tech_id,
                "scheduled_date":         date_str,
                "scheduled_time":         _min_to_time(arr),
                "scheduled_window_start": _min_to_time(slot_start),
                "scheduled_window_end":   _min_to_time(slot_start + win_mins),
                "status":                 "assigned",
            }
            assignments.append({
                "task_id": task["id"],
                "tech":    tech_name_map.get(tech_id, tech_id),
                "date":    date_str,
                "city":    task["city"],
                "window":  f"{_min_to_time(slot_start)}–{_min_to_time(slot_start + win_mins)}",
            })
            if not dry_run:
                await _sb_patch(task["id"], payload, service_key)

    # Build a readable summary: tech → {date → [cities in order]}
    summary: dict[str, dict] = {}
    for a in assignments:
        summary.setdefault(a["tech"], {}).setdefault(a["date"], []).append(a["city"])

    return {
        "assigned":        len(assignments),
        "unassigned":      len(unassigned),
        "unassigned_tasks": unassigned,
        "retimed_existing": retimed_existing,
        "dry_run":         dry_run,
        "by_tech":         summary,
    }
