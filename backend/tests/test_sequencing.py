import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from optimizer import solve_route_v2, time_to_min

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


def test_break_blocks_time():
    # 12:00-13:00 break: no task may overlap the break window
    tasks = base_tasks()
    r = solve_route_v2(M, tasks, "07:00", "18:00", breaks=[{"from": "12:00", "to": "13:00"}])
    for i, arr in zip(r["ordered"], r["arrivals"]):
        dur = tasks[i]["duration"]
        assert not (arr < time_to_min("13:00") and arr + dur > time_to_min("12:00"))
