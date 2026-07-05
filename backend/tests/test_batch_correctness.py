"""Batch correctness pack (Slice 1) — spec: outputs/batch-correctness-design_2026-07-05.md.

The batch scheduler must read the live calendar and enforce the same tenant rules as
the live JS path. Helper semantics MIRROR the JS functions (techHasSkill, getCatLimitOk,
getTechPartialBlocks, isCityBlocked, blockedZones) — parity is the point.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from batch_schedule import (  # noqa: E402
    _arrival_window_hours,
    _effective_duration,
    tech_has_skill,
    cat_limit_ok,
    city_blocked,
    zone_blocked,
    tech_breaks,
)


# ── Task 1: config + eligibility helpers ─────────────────────────────────────

def test_arrival_window_reads_defaults_path():
    assert _arrival_window_hours({"defaults": {"arrival_window_hours": 2}}) == 2

def test_arrival_window_absent_defaults_to_3():
    assert _arrival_window_hours({}) == 3
    assert _arrival_window_hours(None) == 3

def test_arrival_window_legacy_toplevel_still_honored_as_fallback():
    # Old (buggy) location — keep as fallback so any tenant that was set that way keeps working.
    assert _arrival_window_hours({"arrival_window_hours": 4}) == 4
    # defaults wins over top-level
    assert _arrival_window_hours({"arrival_window_hours": 4,
                                  "defaults": {"arrival_window_hours": 2}}) == 2


def test_duration_chain_override_then_category_then_config_then_30():
    cat_duration = {"c1": 45}
    tech = {"duration_overrides": {"c1": 60}}
    config = {"defaults": {"regular_job_minutes": 25}}
    # tech override wins
    assert _effective_duration("c1", tech, cat_duration, config) == 60
    # category default next
    assert _effective_duration("c1", {}, cat_duration, config) == 45
    # tenant regular_job_minutes next
    assert _effective_duration("c2", {}, cat_duration, config) == 25
    # hardcoded 30 last
    assert _effective_duration("c2", {}, cat_duration, {}) == 30
    assert _effective_duration(None, {}, cat_duration, {}) == 30


def test_skill_semantics_mirror_js():
    # JS: if(!catId)return true; return (tech.skills||[]).includes(catId)
    assert tech_has_skill({}, None) is True
    assert tech_has_skill({"skills": ["c1"]}, "c1") is True
    assert tech_has_skill({"skills": ["c1"]}, "c2") is False
    # empty/absent skills with a category ⇒ False (exact JS mirror)
    assert tech_has_skill({}, "c1") is False
    assert tech_has_skill({"skills": []}, "c1") is False
    assert tech_has_skill({"skills": None}, "c1") is False


def test_cat_limit_ok_mirrors_js():
    # JS: no catId → ok; no limit for cat → ok; count < limit → ok
    assert cat_limit_ok({}, None, 5) is True
    assert cat_limit_ok({"cat_limits": {}}, "c1", 5) is True
    assert cat_limit_ok({"cat_limits": {"c1": 3}}, "c1", 2) is True
    assert cat_limit_ok({"cat_limits": {"c1": 3}}, "c1", 3) is False
    # string limits (JSONB from UI may hold strings — JS parseInt's them)
    assert cat_limit_ok({"cat_limits": {"c1": "2"}}, "c1", 2) is False


def test_city_and_zone_blocked():
    assert city_blocked({"blocked_cities": ["באר שבע"]}, "באר שבע") is True
    assert city_blocked({"blocked_cities": []}, "באר שבע") is False
    assert city_blocked({}, "באר שבע") is False
    assert zone_blocked({"blocked_zones": ["z1"]}, "z1") is True
    assert zone_blocked({}, "z1") is False
    assert zone_blocked({"blocked_zones": None}, "z1") is False


# ── Task 2: breaks + partial day-offs (mirror of JS getTechPartialBlocks) ────

_BRK_CONF = {"defaults": {"break": {"enabled": True, "start": "12:00", "end": "13:00"}}}

def test_break_tenant_default():
    assert tech_breaks({}, _BRK_CONF, []) == [{"from": "12:00", "to": "13:00"}]

def test_break_disabled_tenant():
    assert tech_breaks({}, {"defaults": {"break": {"enabled": False}}}, []) == []
    assert tech_breaks({}, {}, []) == []

def test_break_tech_mode_none_overrides_tenant():
    tech = {"weekly_schedule": {"_break": {"mode": "none"}}}
    assert tech_breaks(tech, _BRK_CONF, []) == []

def test_break_tech_mode_custom():
    tech = {"weekly_schedule": {"_break": {"mode": "custom", "start": "10:00", "end": "10:30"}}}
    assert tech_breaks(tech, _BRK_CONF, []) == [{"from": "10:00", "to": "10:30"}]

def test_partial_dayoffs_merge_with_break():
    partials = [{"from_time": "08:00", "to_time": "09:00"}]
    out = tech_breaks({}, _BRK_CONF, partials)
    assert {"from": "08:00", "to": "09:00"} in out
    assert {"from": "12:00", "to": "13:00"} in out
    assert len(out) == 2

def test_partial_dayoff_missing_times_skipped():
    assert tech_breaks({}, {}, [{"from_time": None, "to_time": "09:00"}]) == []


# ── Task 3: live-state fetch + seeded greedy enforcement (end-to-end) ────────
# run_batch_schedule against a fake in-memory Supabase. Dates: 2026-07-05 = Sunday.

import asyncio
import batch_schedule as bs

SUN, MON, TUE, WED, THU = "2026-07-05", "2026-07-06", "2026-07-07", "2026-07-08", "2026-07-09"

def _cfg(**over):
    cfg = {
        "defaults": {"arrival_window_hours": 3, "regular_job_minutes": 30,
                     "max_daily_jobs": 9, "work_days": [0, 1, 2, 3, 4]},
        "scheduling": {"mode": "zone", "route_strategy": "far_to_near"},
    }
    cfg.update(over)
    return cfg

def _tech(tid, name, rotation, **over):
    t = {"id": tid, "name": name, "base_city": "אשקלון", "return_city": "",
         "rotation": rotation, "weekly_schedule": {}, "start_time": "07:00",
         "end_time": "17:00", "max_daily": 9, "skills": ["c-water"],
         "cat_limits": {}, "blocked_zones": [], "blocked_cities": [],
         "duration_overrides": {}}
    t.update(over)
    return t

def _pending(i, city, cat="c-water"):
    return {"id": f"p{i}", "city": city, "street": None, "lat": None, "lon": None,
            "category_id": cat}

def _existing(i, tech_id, d, city, time="08:00", ws="07:00", we="10:00",
              locked=False, cat="c-water"):
    return {"id": f"e{i}", "city": city, "street": None, "lat": None, "lon": None,
            "category_id": cat, "technician_id": tech_id, "scheduled_date": d,
            "scheduled_time": time, "scheduled_window_start": ws,
            "scheduled_window_end": we, "locked": locked, "status": "assigned"}

class FakeSB:
    """Dispatches _sb_get by path (+ status filter for tasks); records patches."""
    def __init__(self, pending=(), existing=(), zones=(), techs=(), cats=(),
                 config=None, dayoffs=()):
        self.tables = {"pending": list(pending), "existing": list(existing),
                       "zones": list(zones), "technicians": list(techs),
                       "categories": list(cats),
                       "tenants": [{"config": config or _cfg()}],
                       "day_offs": list(dayoffs)}
        self.patches = []  # (task_id, body)

    def install(self, monkeypatch):
        async def fake_get(path, params, key):
            if path == "tasks":
                st = params.get("status", "")
                return self.tables["pending" if st == "eq.pending" else "existing"]
            return self.tables[path]
        async def fake_patch(task_id, body, key):
            self.patches.append((task_id, body))
        async def noop_load(key, force=False):
            return None
        monkeypatch.setattr(bs, "_sb_get", fake_get)
        monkeypatch.setattr(bs, "_sb_patch", fake_patch)
        monkeypatch.setattr(bs.geo_resolver, "ensure_loaded", noop_load)

_ZONES = [{"id": "z-south", "name": "דרום", "cities": ["דימונה", "באר שבע", "אשקלון"]},
          {"id": "z-north", "name": "צפון", "cities": ["חיפה", "עכו"]}]
_CATS = [{"id": "c-water", "duration_minutes": 30}]
# אלירן covers דרום on Sunday AND Wednesday (two covering days)
_ROT_SOUTH = {"0": "z-south", "3": "z-south"}

def _run(fake, monkeypatch, dry_run=True, date_from=SUN, date_to=THU):
    fake.install(monkeypatch)
    return asyncio.run(bs.run_batch_schedule("tenant-1", date_from, date_to,
                                             dry_run, "svc-key"))

def _new_per_day(result, tech_name):
    days = result["by_tech"].get(tech_name, {})
    return {d: len(cities) for d, cities in days.items()}


def test_existing_calls_count_toward_max_daily(monkeypatch):
    # 5 already assigned on Sunday; max_daily 9 ⇒ only 4 new fit Sunday, 2 spill to Wednesday.
    fake = FakeSB(
        pending=[_pending(i, "באר שבע") for i in range(6)],
        existing=[_existing(i, "t1", SUN, "אשקלון") for i in range(5)],
        zones=_ZONES, techs=[_tech("t1", "אלירן", _ROT_SOUTH)], cats=_CATS)
    r = _run(fake, monkeypatch)
    per_day = _new_per_day(r, "אלירן")
    assert per_day.get(SUN) == 4, f"Sunday should cap at 4 new (5 existing), got {per_day}"
    assert per_day.get(WED) == 2, f"2 should spill to Wednesday, got {per_day}"

def test_full_dayoff_blocks_batch_assignment(monkeypatch):
    fake = FakeSB(
        pending=[_pending(i, "באר שבע") for i in range(3)],
        zones=_ZONES, techs=[_tech("t1", "אלירן", _ROT_SOUTH)], cats=_CATS,
        dayoffs=[{"technician_id": "t1", "date": SUN, "type": "full",
                  "from_time": None, "to_time": None}])
    r = _run(fake, monkeypatch)
    per_day = _new_per_day(r, "אלירן")
    assert SUN not in per_day, f"Sunday is a day off — got {per_day}"
    assert per_day.get(WED) == 3

def test_cat_limits_count_existing_plus_new(monkeypatch):
    # limit 6 water/day; 5 existing water on Sunday ⇒ only 1 new water fits Sunday.
    tech = _tech("t1", "אלירן", _ROT_SOUTH, cat_limits={"c-water": 6})
    fake = FakeSB(
        pending=[_pending(i, "באר שבע") for i in range(3)],
        existing=[_existing(i, "t1", SUN, "אשקלון") for i in range(5)],
        zones=_ZONES, techs=[tech], cats=_CATS)
    r = _run(fake, monkeypatch)
    per_day = _new_per_day(r, "אלירן")
    assert per_day.get(SUN) == 1, f"cat limit 6 with 5 existing ⇒ 1 new, got {per_day}"
    assert per_day.get(WED) == 2

def test_skills_and_blocked_zones_filter(monkeypatch):
    no_skill = _tech("t1", "אלירן", _ROT_SOUTH, skills=["c-other"])
    fake = FakeSB(pending=[_pending(0, "באר שבע")],
                  zones=_ZONES, techs=[no_skill], cats=_CATS)
    r = _run(fake, monkeypatch)
    assert r["assigned"] == 0 and r["unassigned"] == 1
    assert r["unassigned_tasks"][0]["reason"] == "no_slot_in_range"

    blocked = _tech("t1", "אלירן", _ROT_SOUTH, blocked_zones=["z-south"])
    fake2 = FakeSB(pending=[_pending(0, "באר שבע")],
                   zones=_ZONES, techs=[blocked], cats=_CATS)
    r2 = _run(fake2, monkeypatch)
    assert r2["assigned"] == 0 and r2["unassigned"] == 1

def test_window_hours_from_defaults_in_output(monkeypatch):
    fake = FakeSB(pending=[_pending(0, "באר שבע")], zones=_ZONES,
                  techs=[_tech("t1", "אלירן", _ROT_SOUTH)], cats=_CATS,
                  config=_cfg(defaults={"arrival_window_hours": 2,
                                        "work_days": [0, 1, 2, 3, 4]}))
    fake.install(monkeypatch)
    r = asyncio.run(bs.run_batch_schedule("tenant-1", SUN, THU, True, "svc-key"))
    # 2-hour window: "07:00–09:00" style (width 120 min)
    win = None
    for tech_days in r["by_tech"].values():
        pass
    # windows aren't in by_tech; re-run non-dry to capture the patch body
    fake2 = FakeSB(pending=[_pending(0, "באר שבע")], zones=_ZONES,
                   techs=[_tech("t1", "אלירן", _ROT_SOUTH)], cats=_CATS,
                   config=_cfg(defaults={"arrival_window_hours": 2,
                                         "work_days": [0, 1, 2, 3, 4]}))
    fake2.install(monkeypatch)
    asyncio.run(bs.run_batch_schedule("tenant-1", SUN, THU, False, "svc-key"))
    body = dict(fake2.patches)[list(dict(fake2.patches))[0]]
    ws = bs._time_to_min(body["scheduled_window_start"])
    we = bs._time_to_min(body["scheduled_window_end"])
    assert we - ws == 120, f"expected 2h window, got {body}"


# ── Task 4: existing calls inside the day solve ──────────────────────────────
# Policy (approved): windows fixed, times may re-flow; locked pinned exactly;
# an existing call is NEVER dropped/unassigned in favor of a new one.

def _v2(duration=30, ws=None, we=None, locked=False, time=None):
    return {"duration": duration, "window_start": ws, "window_end": we,
            "locked": locked, "scheduled_time": time}

def _flat_matrix(n, minutes=10):
    return [[0 if i == j else minutes for j in range(n)] for i in range(n)]

def test_solve_day_existing_reflow_within_window():
    # 1 existing (window 07:00-10:00, currently 09:30) + 2 new; roomy day.
    existing = [_v2(ws="07:00", we="10:00", time="09:30")]
    new = [_v2(), _v2()]
    m = _flat_matrix(4)  # base + 1 existing + 2 new
    r = bs.solve_day_with_existing(m, existing, new, "07:00", "17:00",
                                   breaks=[], return_node=False,
                                   route_strategy="flexible")
    assert r["dropped_new"] == []
    assert set(r["ordered"]) == {0, 1, 2}
    # existing arrival stays inside its window (start early enough to finish by 10:00)
    e_arr = r["arrivals"][r["ordered"].index(0)]
    assert 7 * 60 <= e_arr <= 10 * 60 - 30

def test_solve_day_locked_existing_pinned_exactly():
    existing = [_v2(ws="07:00", we="10:00", time="08:00", locked=True)]
    new = [_v2()]
    m = _flat_matrix(3)
    r = bs.solve_day_with_existing(m, existing, new, "07:00", "17:00",
                                   breaks=[], return_node=False,
                                   route_strategy="flexible")
    e_arr = r["arrivals"][r["ordered"].index(0)]
    assert e_arr == 8 * 60

def test_solve_day_overload_drops_only_new():
    # 07:00-10:00 day (180 min), 60-min jobs, zero travel: 3 fit.
    # 2 existing + 4 new ⇒ both existing kept, drops come only from new.
    existing = [_v2(duration=60, ws="07:00", we="10:00", time="07:00"),
                _v2(duration=60, ws="07:00", we="10:00", time="08:00")]
    new = [_v2(duration=60) for _ in range(4)]
    m = _flat_matrix(7, minutes=0)
    r = bs.solve_day_with_existing(m, existing, new, "07:00", "10:00",
                                   breaks=[], return_node=False,
                                   route_strategy="flexible")
    assert 0 in r["ordered"] and 1 in r["ordered"], "existing must never be dropped"
    assert all(i >= 2 for i in r["dropped_new"] or [2]), "drops must be new-only"
    assert len(r["dropped_new"]) >= 1

def test_e2e_existing_patch_carries_time_only(monkeypatch):
    # Non-dry run: any patch to an existing call may contain scheduled_time ONLY.
    fake = FakeSB(
        pending=[_pending(i, "באר שבע") for i in range(3)],
        existing=[_existing(0, "t1", SUN, "דימונה", time="09:30",
                            ws="07:00", we="10:00")],
        zones=_ZONES, techs=[_tech("t1", "אלירן", _ROT_SOUTH)], cats=_CATS)
    _run(fake, monkeypatch, dry_run=False)
    for task_id, body in fake.patches:
        if task_id.startswith("e"):
            assert set(body.keys()) == {"scheduled_time"}, f"existing patch leaked fields: {body}"
    new_patches = [t for t, _ in fake.patches if t.startswith("p")]
    assert len(new_patches) == 3
