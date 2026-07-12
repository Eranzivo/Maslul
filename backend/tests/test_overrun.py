# Window-overrun policy (Eran 2026-07-12): scheduling.auto_overrun_min.
# Automatic paths (this batch — no coordinator) may book a service spill of up
# to tol minutes past the promised window end under 'arrive' semantics; beyond
# that they take the next window/day. The live door always asks (popup).
# Parity contract with the JS door: tests/fixtures/overrun-cases.json.
import json
import os

from batch_schedule import (
    resolve_auto_overrun_min,
    overrun_decision,
    narrow_window_for_overrun,
    promote_spilled_window,
)

_FX = json.load(open(os.path.join(os.path.dirname(__file__), "..", "..",
                     "tests", "fixtures", "overrun-cases.json"), encoding="utf-8"))


def test_resolver_golden_fixture_parity():
    for c in _FX["resolver_cases"]:
        sc = c["sc"]
        config = None if sc is None else {"scheduling": sc}
        assert resolve_auto_overrun_min(config) == c["expect"], f"case {c}"


def test_decision_golden_fixture_parity():
    for c in _FX["decision_cases"]:
        got = overrun_decision(c["semantics"], c["overrun"], c["auto"], c["tol"])
        assert got == c["expect"], f"case {c} → {got}"


# ── narrow_window_for_overrun (pref-window NEW calls: solver-hard cap) ──

def test_narrow_arrive_caps_spill_at_tolerance():
    # window 10:00–13:00 (600–780), 30-min job, tol 15 → latest start 765 (12:45)
    assert narrow_window_for_overrun(600, 780, 30, "arrive", 15) == 765


def test_narrow_short_job_within_tolerance_unchanged():
    # 10-min job, tol 15 → duration ≤ tol ⇒ window end untouched (start ≤ end)
    assert narrow_window_for_overrun(600, 780, 10, "arrive", 15) == 780


def test_narrow_strict_zero_tolerance_equals_finish_bound():
    # tol 0 → latest start = end − duration (finish-equivalent for booking)
    assert narrow_window_for_overrun(600, 780, 30, "arrive", 0) == 750


def test_narrow_never_below_window_start():
    # 45-min job in a 30-min window, tol 0 → clamps to window start (books at
    # start, minimizing the spill; model stays solvable)
    assert narrow_window_for_overrun(600, 630, 45, "arrive", 0) == 600


def test_narrow_finish_semantics_untouched():
    # finish: solver already subtracts duration — no double narrowing
    assert narrow_window_for_overrun(600, 780, 30, "finish", 15) == 780


# ── promote_spilled_window (free NEW calls: derived-window promise) ──

def test_promote_spill_within_tolerance_keeps_window():
    # window 07:00–10:00 (420–600), arr 09:50 (590), 25-min job → spill 15 ≤ 15
    assert promote_spilled_window(590, 25, 420, 180, 1080, 15) == 420


def test_promote_spill_beyond_tolerance_promises_next_window():
    # arr 09:50 (590), 30-min job → spill 20 > 15 → promise 10:00–13:00
    assert promote_spilled_window(590, 30, 420, 180, 1080, 15) == 600


def test_promote_fail_open_when_day_has_no_next_window():
    # last window of the day (15:00–18:00, day ends 18:00): spilled promise kept
    assert promote_spilled_window(1070, 30, 900, 180, 1080, 15) == 900


def test_promote_no_spill_untouched():
    assert promote_spilled_window(430, 30, 420, 180, 1080, 15) == 420
