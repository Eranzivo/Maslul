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
from optimizer import solve_route, build_matrix_local

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


# ── Main entry point ──────────────────────────────────────────────────────────

async def run_batch_schedule(
    tenant_id: str,
    date_from: str,
    date_to: str,
    dry_run: bool,
    service_key: str,
) -> dict:

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
        if _dow(d) == 6:  # Saturday — never work
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

        best_key: Optional[tuple] = None
        best_score = -999

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
                # fill_first: prefer days already active (count*100)
                # equal_city_distribution: penalize same-city overload (-50 per existing)
                score = count * 100 - city_load * 50

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
        matrix = build_matrix_local(locations)

        ordered_idx, arrivals = solve_route(
            base_city=base,
            task_cities=[t["city"] for t in day_tasks],
            task_durations=durations,
            matrix=matrix,
            start_time_str=start_t,
            end_time_str=end_t,
            return_city=return_loc,
        )

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
