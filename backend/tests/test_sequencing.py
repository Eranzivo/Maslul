import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from optimizer import solve_route_v2, time_to_min, build_matrix_local

# 3-node toy matrix: 0=depot, 1=A, 2=B (minutes)
M = [
    [0, 10, 20],
    [10, 0, 15],
    [20, 15, 0],
]


def base_tasks():
    return [
        {"duration": 30, "window_start": None, "window_end": None, "locked": False, "scheduled_time": None},
        {"duration": 30, "window_start": None, "window_end": None, "locked": False, "scheduled_time": None},
    ]


def test_unconstrained_orders_all_tasks():
    r = solve_route_v2(M, base_tasks(), "07:00", "18:00", breaks=[])
    assert sorted(r["ordered"]) == [0, 1]
    assert r["dropped"] == []
    assert len(r["arrivals"]) == 2


def test_locked_task_is_pinned_to_its_time():
    tasks = base_tasks()
    tasks[1]["locked"] = True
    tasks[1]["scheduled_time"] = "09:00"
    r = solve_route_v2(M, tasks, "07:00", "18:00", breaks=[])
    i = r["ordered"].index(1)
    assert r["arrivals"][i] == time_to_min("09:00")  # exactly pinned


def test_window_is_honored_with_waiting():
    tasks = base_tasks()
    tasks[0]["window_start"] = "10:00"   # can't start before 10 even though day starts 07:00
    tasks[0]["window_end"] = "13:00"
    r = solve_route_v2(M, tasks, "07:00", "18:00", breaks=[])
    i = r["ordered"].index(0)
    assert r["arrivals"][i] >= time_to_min("10:00")  # solver waited — Time dimension, not accumulation


def test_overfull_day_drops_flexible_not_fail():
    # 60-minute day, two 45-min jobs → only one fits; must drop, not return no-solution
    tasks = base_tasks()
    tasks[0]["duration"] = 45
    tasks[1]["duration"] = 45
    r = solve_route_v2(M, tasks, "07:00", "08:00", breaks=[])
    assert len(r["ordered"]) == 1
    assert len(r["dropped"]) == 1


def test_locked_is_never_dropped():
    tasks = base_tasks()
    tasks[0]["duration"] = 45
    tasks[1]["duration"] = 45
    tasks[1]["locked"] = True
    tasks[1]["scheduled_time"] = "07:10"
    r = solve_route_v2(M, tasks, "07:00", "08:00", breaks=[])
    assert 1 in r["ordered"]          # locked survived
    assert r["dropped"] == [0]        # flexible was dropped


def test_far_to_near_counts_return_home_and_prefers_far_first():
    # far_to_near models the (unpaid) drive home: closed-tour costs are symmetric here
    # (near-first 10+20+30=60 == far-first 30+20+10=60), so the tie-break must pick FAR first.
    m = [[0, 10, 30], [10, 0, 20], [30, 20, 0]]
    tasks = base_tasks()
    r = solve_route_v2(m, tasks, "07:00", "18:00", breaks=[], route_strategy="far_to_near")
    assert r["ordered"][0] == 1  # farther-from-depot first


def test_far_to_near_never_drops_a_fitting_task_for_direction():
    # SPEC CHANGE (2026-06-15): direction is now ENFORCED (was a soft bias here — this test
    # previously asserted min-drive beat far-first; superseded by scheduling-rules #1 > #4,
    # see test_far_to_near_direction_beats_drive_savings). Direction stays FAIL-OPEN, though:
    # its penalty is below the drop penalty, so a task that fits in work-hours is never
    # dropped just to satisfy far→near.
    m = [[0, 10, 40], [10, 0, 35], [15, 35, 0]]
    tasks = base_tasks()
    r = solve_route_v2(m, tasks, "07:00", "18:00", breaks=[], route_strategy="far_to_near")
    assert r["dropped"] == []                 # both tasks fit → none dropped for direction
    assert sorted(r["ordered"]) == [0, 1]     # both visited
    assert r["ordered"][0] == 1               # far stop first (direction enforced)


# ── far_to_near: ENFORCES direction / no-backtrack (scheduling-rules priority #1) ──
# Per context/scheduling-rules.md, route direction & no-backtrack is the #1 priority,
# ABOVE fuel (#4): "better to start later than to create a far-near-far zigzag".
# far_to_near is PureWater's chosen, config-selected strategy — when selected it must
# truly enforce far→near, not merely nudge. These tests pin that contract on REAL data.

def _purewater_north_day():
    # Real bug fixture: אלירן's Tue north-zone day. Base אשקלון (far south), 4 clustered
    # northern cities, קרית ים twice. Live batch produced a backtrack:
    # חיפה → קרית ים → נהריה → קרית ים → קרית חיים (climbs out to נהריה, revisits קרית ים).
    base = "אשקלון"
    cities = ["חיפה", "קרית ים", "נהריה", "קרית ים", "קרית חיים"]
    m = build_matrix_local([base] + cities)
    tasks = [{"duration": 30, "window_start": None, "window_end": None,
              "locked": False, "scheduled_time": None} for _ in cities]
    return m, tasks, cities


def test_far_to_near_real_purewater_day_has_no_backtrack():
    m, tasks, cities = _purewater_north_day()
    r = solve_route_v2(m, tasks, "07:00", "18:00", breaks=[], route_strategy="far_to_near")
    # distance-from-base for each visited stop (matrix row 0 = base → node)
    d = [m[0][i + 1] for i in r["ordered"]]
    TOL = 20  # minutes — intra-cluster near-equidistant stops may swap; real backtracks are big
    for k in range(len(d) - 1):
        assert d[k] >= d[k + 1] - TOL, (
            f"backtrack: stop {k} '{cities[r['ordered'][k]]}' (d={d[k]}) → "
            f"'{cities[r['ordered'][k+1]]}' (d={d[k+1]}) climbs back out from base"
        )


def test_far_to_near_visits_farthest_city_first():
    m, tasks, cities = _purewater_north_day()
    r = solve_route_v2(m, tasks, "07:00", "18:00", breaks=[], route_strategy="far_to_near")
    first_city = cities[r["ordered"][0]]
    assert first_city == "נהריה", f"far→near must start at the farthest city נהריה, got {first_city}"


def test_far_to_near_keeps_same_city_jobs_adjacent():
    m, tasks, cities = _purewater_north_day()
    r = solve_route_v2(m, tasks, "07:00", "18:00", breaks=[], route_strategy="far_to_near")
    # the two קרית ים jobs are input indices 1 and 3 — never leave and return to a city
    pos_a, pos_b = r["ordered"].index(1), r["ordered"].index(3)
    assert abs(pos_a - pos_b) == 1, (
        f"same-city קרית ים jobs split across the day (positions {pos_a}, {pos_b})"
    )


def test_far_to_near_direction_beats_drive_savings():
    # SPEC CHANGE (2026-06-15): direction (#1) outranks fuel (#4). depot→A=10 (near),
    # depot→B=40 (far). Near-first is cheaper to drive, but the rule requires far (B) first.
    m = [[0, 10, 40], [10, 0, 35], [15, 35, 0]]
    r = solve_route_v2(m, base_tasks(), "07:00", "18:00", breaks=[], route_strategy="far_to_near")
    assert r["ordered"][0] == 1, "far_to_near must visit the farther stop first, even at higher drive cost"


def test_flexible_keeps_open_end_semantics():
    # flexible (default) ends at the last client: near-first open cost 10+20=30 beats far-first 30+20=50
    m = [[0, 10, 30], [10, 0, 20], [30, 20, 0]]
    tasks = base_tasks()
    r = solve_route_v2(m, tasks, "07:00", "18:00", breaks=[], route_strategy="flexible")
    assert r["ordered"][0] == 0


def test_break_blocks_time():
    # 12:00-13:00 break: no task may overlap the break window
    tasks = base_tasks()
    r = solve_route_v2(M, tasks, "07:00", "18:00", breaks=[{"from": "12:00", "to": "13:00"}])
    for i, arr in zip(r["ordered"], r["arrivals"]):
        dur = tasks[i]["duration"]
        assert not (arr < time_to_min("13:00") and arr + dur > time_to_min("12:00"))


# ── nearest_first enforcement (Slice 4 — mirror of far_to_near, 2026-07-05) ──
# Before this slice the solver treated nearest_first as flexible: the knob was honest
# at JS-assignment level but cosmetic at the authoritative sequencing layer.

def test_nearest_first_visits_nearest_city_first():
    m, tasks, cities = _purewater_north_day()
    r = solve_route_v2(m, tasks, "07:00", "18:00", breaks=[], route_strategy="nearest_first")
    d = [m[0][i + 1] for i in r["ordered"]]
    assert d[0] == min(d), f"nearest_first must start closest to base, got order {[cities[i] for i in r['ordered']]}"

def test_nearest_first_never_moves_back_inward():
    m, tasks, cities = _purewater_north_day()
    r = solve_route_v2(m, tasks, "07:00", "18:00", breaks=[], route_strategy="nearest_first")
    d = [m[0][i + 1] for i in r["ordered"]]
    TOL = 20
    for k in range(len(d) - 1):
        assert d[k] <= d[k + 1] + TOL, (
            f"inward backtrack: '{cities[r['ordered'][k]]}' (d={d[k]}) → "
            f"'{cities[r['ordered'][k+1]]}' (d={d[k+1]})")

def test_nearest_first_keeps_same_city_jobs_adjacent():
    m, tasks, cities = _purewater_north_day()
    r = solve_route_v2(m, tasks, "07:00", "18:00", breaks=[], route_strategy="nearest_first")
    pos = {i: k for k, i in enumerate(r["ordered"])}
    assert abs(pos[1] - pos[3]) == 1, "the two קרית ים jobs must stay adjacent"

def test_nearest_first_never_drops_for_direction():
    # Fail-open: direction penalty must stay below the drop penalty.
    m, tasks, cities = _purewater_north_day()
    r = solve_route_v2(m, tasks, "07:00", "18:00", breaks=[], route_strategy="nearest_first")
    assert r["dropped"] == [], "direction must never force a drop"

def test_nearest_first_direction_beats_drive_savings():
    # Two-branch geometry: A near (10), B far on branch 1 (100), C far on branch 2 (110),
    # branches connected only via the base area (d(B,C)=210). Pure min-drive prefers
    # B→A→C (300 min) which starts FAR; nearest_first must force A→B→C (315 min) —
    # direction over fuel, mirroring the far_to_near enforcement.
    pairs = {(0,1):10,(0,2):100,(0,3):110,(1,2):95,(1,3):105,(2,3):210}
    n = 4; m = [[0]*n for _ in range(n)]
    for (i,j),v in pairs.items(): m[i][j] = v; m[j][i] = v
    tasks = [{"duration": 30, "window_start": None, "window_end": None,
              "locked": False, "scheduled_time": None} for _ in range(3)]
    r = solve_route_v2(m, tasks, "07:00", "23:00", breaks=[], route_strategy="nearest_first")
    d = [m[0][i + 1] for i in r["ordered"]]
    assert d == sorted(d), f"nearest_first must move strictly outward, got distances {d}"
    assert r["dropped"] == [], "direction must never force a drop"
