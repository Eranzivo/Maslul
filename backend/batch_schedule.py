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


def point_in_polygon(lat, lon, ring) -> bool:
    """Ray-casting point-in-polygon over [{lat, lng}] vertices — EXACT mirror of the JS
    _pointInPolygon (index.html <zone-logic>). Parity pair; shared fixture-tested."""
    if not ring or len(ring) < 3:
        return False
    inside = False
    j = len(ring) - 1
    for i in range(len(ring)):
        xi, yi = ring[i]["lat"], ring[i]["lng"]
        xj, yj = ring[j]["lat"], ring[j]["lng"]
        if ((yi > lon) != (yj > lon)) and (lat < (xj - xi) * (lon - yi) / (yj - yi) + xi):
            inside = not inside
        j = i
    return inside


def _match_key(name: str, alias_map: Optional[dict]) -> str:
    """ONE canonical matching key for a city name — the seam every city comparison goes
    through (zone matching). Chain (mirrors JS cityMatchKey exactly):
    legacy alias (_norm) → קריית→קרית collapse → normalize noise (gershayim/hyphens) →
    brain alias (place_aliases) → canonical key. With an empty alias_map this is still a
    strict superset of the old bare-_norm comparison — fail-open, never worse."""
    from canonicalize import resolve_place_key
    c = _norm(name or "").replace("קריית", "קרית")
    return resolve_place_key(c, alias_map or {})


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


def _pref_window_minutes(w) -> Optional[tuple]:
    """Parse one preferred-window dict to (from_min, to_min); None on malformed input —
    a broken window must FAIL OPEN (never block scheduling), mirroring the JS side."""
    try:
        fh, fm = map(int, str(w["from"]).split(":"))
        th, tm = map(int, str(w["to"]).split(":"))
        return fh * 60 + fm, th * 60 + tm
    except Exception:
        return None


def _pref_window_days(w) -> Optional[list]:
    """Window's day list (Sun=0…Sat=6, JS getDay convention). Absent/empty ⇒ None = every day."""
    days = w.get("days") if isinstance(w, dict) else None
    return days if isinstance(days, list) and days else None


def pref_allows_day(windows, dow: int) -> bool:
    """HARD day gate for customer availability (handover §8): with windows present, weekday
    `dow` is eligible only if some window covers it (hour-only window = every day).
    No/empty windows ⇒ unconstrained. Mirrors JS `prefWindowAllowsDay`; golden fixture
    tests/fixtures/prefwindow-cases.json asserts both sides."""
    if not windows:
        return True
    ok = False
    for w in windows:
        if _pref_window_minutes(w) is None:
            return True  # malformed ⇒ fail open
        days = _pref_window_days(w)
        if days is None or dow in days:
            ok = True
    return ok


def pref_allows_range(windows, dow: int, from_min: int, to_min: int) -> bool:
    """HARD time gate: does any window allowed on `dow` OVERLAP [from_min, to_min)?
    (Touching boundaries don't overlap.) Mirrors JS `prefWindowAllowsRange`."""
    if not windows:
        return True
    ok = False
    for w in windows:
        mins = _pref_window_minutes(w)
        if mins is None:
            return True  # malformed ⇒ fail open
        days = _pref_window_days(w)
        if days is not None and dow not in days:
            continue
        if from_min < mins[1] and to_min > mins[0]:
            ok = True
    return ok


def date_constraint_allows(task: Optional[dict], date_iso: str) -> bool:
    """Structured per-task date constraints (handover §10/§13): `fixed_date` pins the call
    to exactly one date (overriding the bounds); `earliest_date`/`latest_date` are inclusive
    bounds. Absent/empty fields are ignored. ISO strings compare lexicographically.
    Mirrors JS `dateConstraintAllows`; golden fixture tests/fixtures/datecons-cases.json."""
    t = task or {}
    fixed = t.get("fixed_date")
    if fixed:
        return date_iso == fixed
    earliest, latest = t.get("earliest_date"), t.get("latest_date")
    if earliest and date_iso < earliest:
        return False
    if latest and date_iso > latest:
        return False
    return True


def resolve_pref_windows_mode(config: Optional[dict]) -> str:
    """`scheduling.preferred_windows_mode`: 'hard' (default — availability is a hard
    constraint per Israel's handover §8) | 'soft' (highlight-only, the pre-2026-07-06
    behavior). Unknown values ⇒ 'hard'. Mirrors JS `resolvePrefWindowsMode`."""
    mode = (((config or {}).get("scheduling") or {}).get("preferred_windows_mode"))
    return mode if mode in ("hard", "soft") else "hard"


def _arrival_window_hours(config: Optional[dict]) -> float:
    """Customer service-window length. Real location: `config.defaults.arrival_window_hours`
    (the shape every other defaults knob uses). The old top-level read was a bug — kept only
    as a fallback so a tenant that was ever set that way keeps working. Fractional hours
    (Israel's real cards show 1.5h windows) are preserved — minutes math rounds, never
    truncates."""
    cfg = config or {}
    d = (cfg.get("defaults") or {}).get("arrival_window_hours")
    if isinstance(d, (int, float)) and not isinstance(d, bool) and d > 0:
        return float(d)
    top = cfg.get("arrival_window_hours")
    if isinstance(top, (int, float)) and not isinstance(top, bool) and top > 0:
        return float(top)
    return 3.0


def _clamp_blocks(blocks: list, start_t: str, end_t: str) -> list:
    """Clamp break/partial blocks to the tech's work hours. A block entirely outside
    the day is dropped — sending it to the solver as a mandatory pinned node would make
    the whole model infeasible and cascade-drop every flexible call."""
    s, e = _time_to_min(start_t), _time_to_min(end_t)
    out = []
    for b in blocks:
        lo, hi = max(_time_to_min(b["from"]), s), min(_time_to_min(b["to"]), e)
        if lo < hi:
            out.append({"from": _min_to_time(lo), "to": _min_to_time(hi)})
    return out


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


def resolve_placement_policy(config: Optional[dict]) -> str:
    """ONE placement philosophy per tenant — 'consolidate' | 'spread' — read identically
    by the live JS path (resolvePlacementPolicy) and this batch. Decided by Israel's
    handover (2026-07-06): consolidate = "fill the best nearby technician route first;
    avoid creating multiple half-empty days" (his Scenario D). spread = fluid even split
    across covering tech-days, for tenants that want balanced load over tight routes.

    Legacy mapping: explicit `scheduling.placement_policy` wins; the old
    `balance.enabled:true` flag maps to 'spread' (its batch semantics); absent ⇒
    'consolidate' (today's fill-first default). Golden fixture: tests/fixtures/policy-cases.json."""
    sched = (config or {}).get("scheduling") or {}
    pp = sched.get("placement_policy")
    if pp in ("consolidate", "spread"):
        return pp
    if (sched.get("balance") or {}).get("enabled"):
        return "spread"
    return "consolidate"


def _assignment_score(count: int, city_load: int, policy, weight: int = 50) -> float:
    """Score a candidate (tech, day) for one task — higher is better.

    consolidate: fill active days first (`count*100`); same-city stays a mild tie-break
    penalty (grouping same-area work is a PLUS per the handover; the penalty only splits
    ties between equally-active days).
    spread: prefer the LEAST-loaded covering tech-day, same-city nudged apart — greedy-
    applied this yields 8→4-4, 7→4-3, 6→3-3, adapting to each week's count. Soft; always
    bounded by max_daily / cat_limits / windows.

    `policy` may also be a legacy balance-conf dict (older callers/tests) — mapped with
    the same semantics as resolve_placement_policy."""
    if isinstance(policy, dict) or policy is None:  # legacy balance_conf calling shape
        bal = policy or {}
        weight = bal.get("weight", 50)
        policy = "spread" if bal.get("enabled") else "consolidate"
    if policy == "spread":
        return -count * weight - city_load * (weight // 2)
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
    """(Test/back-compat wrapper — the production path is solve_day_with_existing.)
    Order one tech-day with the authoritative v2 solver (the same engine the
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
        "select": "id,city,street,lat,lon,category_id,preferred_windows,"
                  "earliest_date,latest_date,fixed_date",
    }, service_key)

    # Existing calls in range: they occupy capacity and shape every day's route.
    existing_raw = await _sb_get("tasks", {
        "tenant_id": f"eq.{tenant_id}",
        "status": "in.(assigned,en_route,arrived)",
        "and": f"(scheduled_date.gte.{date_from},scheduled_date.lte.{date_to})",
        "select": "id,city,street,lat,lon,category_id,technician_id,scheduled_date,"
                  "scheduled_time,scheduled_window_start,scheduled_window_end,locked",
    }, service_key)

    # select * — the live table currently lacks the type/from_time/to_time columns the
    # docs describe (migration not applied); the JS load path defaults a missing type to
    # 'full'. Mirror that: tolerate either schema, absent type ⇒ full day off.
    dayoffs_raw = await _sb_get("day_offs", {
        "tenant_id": f"eq.{tenant_id}",
        "and": f"(date.gte.{date_from},date.lte.{date_to})",
        "select": "*",
    }, service_key)

    zones_raw = await _sb_get("zones", {
        "tenant_id": f"eq.{tenant_id}",
        "select": "id,name,cities,polygons",
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
    sched_conf = config.get("scheduling") or {}
    placement_policy = resolve_placement_policy(config)
    placement_weight = (sched_conf.get("balance") or {}).get("weight", 50)
    pref_mode = resolve_pref_windows_mode(config)

    # 2. Build lookup tables
    cat_duration = {c["id"]: c.get("duration_minutes", 30) for c in cats_raw}
    tech_name_map = {t["id"]: t["name"] for t in techs_raw}

    # zone_map keyed by canonical match keys — BOTH sides (task city + zone cities) go
    # through the same _match_key seam (brain aliases + normalize), mirroring the JS
    # resolveZone chain. ק"ש / קרית שמונה / קריית שמונה all land in the same zone.
    brain_aliases = geo_resolver.alias_map()  # {} when brain not loaded → fail-open
    zone_map = {
        z["id"]: {"name": z["name"],
                  "keys": {_match_key(c, brain_aliases) for c in (z.get("cities") or [])}}
        for z in zones_raw
    }

    def find_zone(city: str) -> Optional[str]:
        k = _match_key(city, brain_aliases)
        for zid, z in zone_map.items():
            if k in z["keys"]:
                return zid
        return None

    # Two-axis zone matching — mirror of the JS resolveZone seam. city_list (default)
    # matches canonical city keys; polygon matches the task's geocoded point against any
    # ring in zones.polygons (same reasons: not_geocoded / outside_all_polygons).
    zone_match = ((config.get("scheduling") or {}).get("zone_match")) or "city_list"

    def find_zone_for(task) -> tuple:
        """(zone_id, fail_reason). fail_reason set only when zone_id is None."""
        if zone_match == "polygon":
            lat, lon = task.get("lat"), task.get("lon")
            if not (lat and lon):
                return None, "not_geocoded"
            for z in zones_raw:
                if any(point_in_polygon(lat, lon, ring) for ring in (z.get("polygons") or [])):
                    return z["id"], None
            return None, "outside_all_polygons"
        zid = find_zone(task["city"])
        return zid, (None if zid else "city_not_in_zone")

    def tech_zone_for_day(tech: dict, d: date) -> Optional[str]:
        rotation = tech.get("rotation") or {}
        return rotation.get(str(_dow(d)))

    # Day-off lookups (mirror of the live path's isTechAvailable / getTechPartialBlocks).
    # Missing type ⇒ 'full' (same default the JS load mapper applies).
    dayoffs_full = {(o["technician_id"], o["date"]) for o in dayoffs_raw
                    if (o.get("type") or "full") == "full"}
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

    # Per-task exclusion set of (tech, date) keys already tried and dropped —
    # bounds the retry loop (each task tries each covering day at most once).
    excluded: dict[str, set] = {}

    def place_task(task) -> Optional[tuple]:
        """Greedy best (tech, day) for one task, honoring every eligibility gate the
        live _candidatesZone path enforces. Books the placement and returns its key,
        or None when no eligible slot remains."""
        zone_id = task["_zone_id"]
        cat_id = task.get("category_id")
        nc = _norm(task["city"])
        best_key: Optional[tuple] = None
        best_score = float("-inf")  # balance-on scores are negative — never seed at a finite floor
        cur = d_start
        while cur <= d_end:
            # Structured date constraints (fixed/earliest/latest) are HARD — same gate
            # as the live buildCandidates date filter.
            if not date_constraint_allows(task, cur.isoformat()):
                task["_datecons_blocked"] = True
                cur += timedelta(days=1)
                continue
            # Customer availability is HARD (handover §8): a window with days:[0,2]
            # keeps the call off every other weekday — same gate as the live door.
            if pref_mode == "hard" and not pref_allows_day(
                    task.get("preferred_windows"), _dow(cur)):
                task["_pref_day_blocked"] = True
                cur += timedelta(days=1)
                continue
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
                if key in excluded.get(task["id"], set()):
                    continue
                count = occupancy(key)  # existing + newly placed
                if count >= tech_max_daily(tech):
                    continue
                if not cat_limit_ok(tech, cat_id,
                                    cat_counts.get((tech["id"], cur.isoformat(), cat_id), 0)):
                    continue

                city_load = city_counts[tech["id"]].get(nc, 0)
                # ONE placement policy for both doors — see resolve_placement_policy.
                score = _assignment_score(count, city_load, placement_policy, placement_weight)

                if score > best_score:
                    best_score = score
                    best_key = key
            cur += timedelta(days=1)

        if best_key is None:
            return None
        tech_id_key = best_key[0]
        assigned_tech = next(t for t in techs_raw if t["id"] == tech_id_key)
        task["_duration"] = _effective_duration(cat_id, assigned_tech, cat_duration, config)
        day_slots.setdefault(best_key, []).append(task)
        city_counts[tech_id_key][nc] = city_counts[tech_id_key].get(nc, 0) + 1
        if cat_id:
            ck = (tech_id_key, best_key[1], cat_id)
            cat_counts[ck] = cat_counts.get(ck, 0) + 1
        return best_key

    def unbook(key: tuple, task) -> None:
        """Reverse a booking after the day solver dropped the task (time capacity)."""
        day_slots[key].remove(task)
        nc = _norm(task["city"])
        city_counts[key[0]][nc] = max(0, city_counts[key[0]].get(nc, 0) - 1)
        cat_id = task.get("category_id")
        if cat_id:
            ck = (key[0], key[1], cat_id)
            cat_counts[ck] = max(0, cat_counts.get(ck, 0) - 1)

    # Eligibility pass: zone membership + locatability. Failures here are terminal.
    pool = []
    for task in tasks_raw:
        zone_id, zone_fail = find_zone_for(task)
        if not zone_id:
            unassigned.append({"id": task["id"], "city": task["city"], "reason": zone_fail})
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

        task["_zone_id"] = zone_id
        pool.append(task)

    # 4. Assign + optimize in bounded retry rounds. Only days that RECEIVE new calls
    # are solved — days the batch doesn't touch stay exactly as they are. A new call
    # the solver drops (time capacity) is un-booked, that day excluded for it, and it
    # retries the next-best covering day in the following round.
    assignments = []
    retimed_existing = 0

    def _loc(t: dict) -> str:
        if t.get("lat") and t.get("lon"):
            return f"{t['lat']},{t['lon']}"
        if t.get("street"):
            return f"{t['street']}, {t['city']}"
        return t["city"]

    def solve_day(key: tuple):
        """Solve one tech-day (existing + new). Returns (result, existing snapshot,
        new-tasks snapshot, start_min) — snapshots pin the index space of the result."""
        tech_id, date_str = key
        tech = next(t for t in techs_raw if t["id"] == tech_id)
        start_t, end_t = tech_hours(tech, date.fromisoformat(date_str))
        base = tech.get("base_city") or "אשקלון"
        ret  = tech.get("return_city") or ""
        return_loc = ret if (ret and ret != base) else ""

        day_existing = list(existing_slots.get(key, []))
        day_tasks = list(day_slots.get(key, []))
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
        # HARD time gate: a new call with preferred windows gets the day's earliest
        # tech-hours-overlapping window as its solver window (window_start/end are hard
        # in solve_route_v2). v1: one window per task — earliest overlapping wins.
        day_dow = _dow(date.fromisoformat(key[1]))
        day_start_min, day_end_min = _time_to_min(start_t), _time_to_min(end_t)

        def _pref_solver_window(t):
            if pref_mode != "hard":
                return None, None
            wins = t.get("preferred_windows") or []
            best = None
            for w in wins:
                mins = _pref_window_minutes(w)
                if mins is None:
                    return None, None  # malformed ⇒ fail open, no narrowing
                days = _pref_window_days(w)
                if days is not None and day_dow not in days:
                    continue
                if mins[0] < day_end_min and mins[1] > day_start_min:
                    if best is None or mins[0] < best[0]:
                        best = mins
            if best is None:
                return None, None  # day already passed pref_allows_day; only hours clash ⇒ open
            return _min_to_time(max(best[0], day_start_min)), _min_to_time(min(best[1], day_end_min))

        new_v2 = []
        for t in day_tasks:
            ws, we = _pref_solver_window(t)
            new_v2.append({"duration": t["_duration"], "window_start": ws, "window_end": we,
                           "locked": False, "scheduled_time": None})
        brk = _clamp_blocks(tech_breaks(tech, config, dayoffs_partial.get(key, [])),
                            start_t, end_t)

        r = solve_day_with_existing(
            matrix, existing_v2, new_v2, start_t, end_t, breaks=brk,
            return_node=bool(return_loc), route_strategy=route_strategy)
        return r, day_existing, day_tasks, _time_to_min(start_t)

    # day_results holds the FINAL solve per day: (result, existing, new, start_min).
    day_results: dict[tuple, tuple] = {}
    MAX_ROUNDS = max(6, (d_end - d_start).days + 1)  # >= covering days any task can try
    rounds = 0
    while pool and rounds < MAX_ROUNDS:
        rounds += 1
        dirty: set = set()
        for task in pool:
            key = place_task(task)
            if key is None:
                # Dropped earlier ⇒ it HAD a covering day that ran out of time budget;
                # never placeable at all ⇒ no slot in range (distinguish the case where
                # the customer's preferred-window DAYS are what eliminated the range —
                # the dispatcher then knows to renegotiate days, not capacity).
                if task.get("_dropped_once"):
                    reason = "day_over_capacity"
                elif task.get("fixed_date") and task.get("_datecons_blocked"):
                    reason = "fixed_date_unavailable"
                elif task.get("_datecons_blocked") and not task.get("_pref_day_blocked"):
                    reason = "no_slot_within_date_constraints"
                elif task.get("_pref_day_blocked"):
                    reason = "no_preferred_window_day"
                else:
                    reason = "no_slot_in_range"
                unassigned.append({"id": task["id"], "city": task["city"], "reason": reason})
            else:
                dirty.add(key)
        next_pool = []
        for key in sorted(dirty):
            r, day_existing, day_tasks, start_min = solve_day(key)
            n_e = len(day_existing)
            for di in r["dropped_new"]:
                dt = day_tasks[di - n_e]
                dt["_dropped_once"] = True
                excluded.setdefault(dt["id"], set()).add(key)
                unbook(key, dt)
                next_pool.append(dt)
            day_results[key] = (r, day_existing, day_tasks, start_min)
        pool = next_pool
    for task in pool:  # rounds exhausted — treat like any other capacity failure
        unassigned.append({"id": task["id"], "city": task["city"], "reason": "day_over_capacity"})

    # 5. Emit results from the final day snapshots (dropped tasks are not in `ordered`).
    win_mins = int(round(arrival_window_h * 60))
    for (tech_id, date_str), (r, day_existing, day_tasks, start_min) in sorted(day_results.items()):
        n_e = len(day_existing)
        if not any(i >= n_e for i in r["ordered"]):
            continue  # no new call survived on this day — leave its existing times alone
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
