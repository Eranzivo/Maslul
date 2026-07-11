"""window_semantics knob (Eran decision 2026-07-11): what the customer window
promises. 'finish' (default, conservative) = job must END inside the window —
today's solver behavior. 'arrive' = tech must START (arrive) by window end;
service may run past it — Israel's real operation, PureWater's setting. Opens
the last [duration] minutes of every window (~17% more arrival capacity).

One resolver both doors (batch mirror of JS resolveWindowSemantics); the solver
is the enforcement point. route_health already audits with arrival semantics.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import batch_schedule as bs  # noqa: E402
from optimizer import solve_route_v2  # noqa: E402


def test_resolver_default_and_values():
    assert bs.resolve_window_semantics(None) == "finish"
    assert bs.resolve_window_semantics({}) == "finish"
    assert bs.resolve_window_semantics({"scheduling": {}}) == "finish"
    assert bs.resolve_window_semantics({"scheduling": {"window_semantics": "arrive"}}) == "arrive"
    assert bs.resolve_window_semantics({"scheduling": {"window_semantics": "finish"}}) == "finish"
    # Unknown value -> conservative default, never crashes
    assert bs.resolve_window_semantics({"scheduling": {"window_semantics": "banana"}}) == "finish"


# One task, 30 min, window ends 13:00. Depot->task drive 340 min from a 07:00
# start -> earliest possible arrival 12:40. finish: latest start is 12:30 ->
# infeasible -> dropped. arrive: latest start is 13:00 -> placed at 12:40.
_MATRIX = [[0, 340], [340, 0]]
_TASK = [{"duration": 30, "window_start": None, "window_end": "13:00",
          "locked": False, "scheduled_time": None}]


def test_finish_semantics_drops_last_half_hour_arrival():
    r = solve_route_v2(_MATRIX, _TASK, "07:00", "17:00", breaks=[],
                       window_semantics="finish")
    assert r["dropped"] == [0], f"finish must drop (can't END by 13:00): {r}"


def test_arrive_semantics_books_last_half_hour():
    r = solve_route_v2(_MATRIX, _TASK, "07:00", "17:00", breaks=[],
                       window_semantics="arrive")
    assert r["dropped"] == [], f"arrive must place it: {r}"
    assert r["ordered"] == [0]
    # Arrival 07:00 + 340 = 12:40 — inside the window under arrival semantics.
    assert r["arrivals"][0] == 7 * 60 + 340


def test_default_is_finish_backcompat():
    # Omitting the param must behave exactly like today (finish).
    r = solve_route_v2(_MATRIX, _TASK, "07:00", "17:00", breaks=[])
    assert r["dropped"] == [0]


def test_arrive_still_respects_window_start():
    task = [{"duration": 30, "window_start": "13:00", "window_end": "16:00",
             "locked": False, "scheduled_time": None}]
    m = [[0, 10], [10, 0]]
    r = solve_route_v2(m, task, "07:00", "17:00", breaks=[], window_semantics="arrive")
    assert r["dropped"] == []
    assert r["arrivals"][0] >= 13 * 60, "window_start stays a hard floor"
