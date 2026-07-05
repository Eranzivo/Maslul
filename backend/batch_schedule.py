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

    # 1. Fetch all required data
    tasks_raw = await _sb_get("tasks", {
        "tenant_id": f"eq.{tenant_id}",
        "status": "eq.pending",
        "select": "id,city,street,lat,lon,category_id",
    }, service_key)

    zones_raw = await _sb_get("zones", {
        "tenant_id": f"eq.{tenant_id}",
        "select": "id,name,cities",
    }, service_key)

    techs_raw = await _sb_get("technicians", {
        "tenant_id": f"eq.{tenant_id}",
        "select": "id,name,base_city,return_city,rotation,weekly_schedule,start_time,end_time,max_daily",
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
    arrival_window_h = config.get("arrival_window_hours", 3)
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

    def tech_is_working(tech: dict, d: date) -> bool:
        if not tenant_works_day(_dow(d), config):  # tenant-level off-day (Sat off by default)
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

    # 3. Greedy task → tech+day assignment
    # day_slots: {(tech_id, date_str): [task_dict, ...]}
    day_slots: dict[tuple, list] = {}
    # city_counts per tech (for equal city distribution penalty)
    city_counts: dict[str, dict[str, int]] = {t["id"]: {} for t in techs_raw}

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

        cur = d_start
        while cur <= d_end:
            for tech in techs_raw:
                if not tech_is_working(tech, cur):
                    continue
                if tech_zone_for_day(tech, cur) != zone_id:
                    continue
                key = (tech["id"], cur.isoformat())
                count = len(day_slots.get(key, []))
                if count >= tech_max_daily(tech):
                    continue

                nc = _norm(task["city"])
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

        task["_duration"] = cat_duration.get(task.get("category_id"), 30)
        day_slots.setdefault(best_key, []).append(task)
        nc = _norm(task["city"])
        tech_id_key = best_key[0]
        city_counts[tech_id_key][nc] = city_counts[tech_id_key].get(nc, 0) + 1

    # 4. Optimize each tech+day and write results
    assignments = []

    for (tech_id, date_str), day_tasks in sorted(day_slots.items(), key=lambda x: (x[0][1], x[0][0])):
        tech = next(t for t in techs_raw if t["id"] == tech_id)
        start_t, end_t = tech_hours(tech, date.fromisoformat(date_str))
        start_min = _time_to_min(start_t)
        base = tech.get("base_city") or "אשקלון"
        ret  = tech.get("return_city") or ""
        return_loc = ret if (ret and ret != base) else ""

        task_locs = [
            f"{t['lat']},{t['lon']}" if t.get("lat") and t.get("lon")
            else (f"{t['street']}, {t['city']}" if t.get("street") else t["city"])
            for t in day_tasks
        ]
        locations = [base] + task_locs + ([return_loc] if return_loc else [])
        durations = [t["_duration"] for t in day_tasks]

        # Tasks at city-level only (no street/coords) — haversine is equivalent
        # to Google Maps for city-center→city-center and avoids burning API quota.
        # Real drive-time refinement happens later via the live cache-backed sequencer.
        matrix = build_matrix_local(locations)

        ordered_idx, arrivals, dropped_idx = optimize_day(
            matrix=matrix,
            durations=durations,
            start_t=start_t,
            end_t=end_t,
            return_node=bool(return_loc),
            route_strategy=route_strategy,
        )

        # Over-full day: the solver dropped these rather than fail — leave them
        # pending and surface them so the coordinator can re-place or extend hours.
        for di in dropped_idx:
            dt = day_tasks[di]
            unassigned.append({"id": dt["id"], "city": dt["city"], "reason": "day_over_capacity"})

        win_mins = arrival_window_h * 60
        for i, arr in zip(ordered_idx, arrivals):
            task = day_tasks[i]
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
        "dry_run":         dry_run,
        "by_tech":         summary,
    }
