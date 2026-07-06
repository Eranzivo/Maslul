"""Preferred-windows day/time gates — golden parity fixture (tests/fixtures/prefwindow-cases.json)
run by BOTH this suite and tests/sched.test.js, plus the knob resolver. Customer availability
is a HARD constraint (Israel's handover §8): a window with days:[0,2] means the call may only
land on Sunday/Tuesday inside those hours — on BOTH engines."""
import io
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from batch_schedule import (  # noqa: E402
    pref_allows_day,
    pref_allows_range,
    resolve_pref_windows_mode,
)

_FX = json.load(io.open(os.path.join(os.path.dirname(__file__), "..", "..",
                                     "tests", "fixtures", "prefwindow-cases.json"),
                        encoding="utf-8"))


def test_day_cases_fixture():
    for c in _FX["day_cases"]:
        assert pref_allows_day(c["windows"], c["dow"]) == c["allow"], c["why"]


def test_range_cases_fixture():
    for c in _FX["range_cases"]:
        got = pref_allows_range(c["windows"], c["dow"], c["from_min"], c["to_min"])
        assert got == c["allow"], c["why"]


def test_mode_resolver():
    assert resolve_pref_windows_mode(None) == "hard"                       # absent config
    assert resolve_pref_windows_mode({}) == "hard"
    assert resolve_pref_windows_mode({"scheduling": {}}) == "hard"          # default
    assert resolve_pref_windows_mode(
        {"scheduling": {"preferred_windows_mode": "soft"}}) == "soft"
    assert resolve_pref_windows_mode(
        {"scheduling": {"preferred_windows_mode": "nonsense"}}) == "hard"   # unknown ⇒ default


def test_none_windows_allow():
    assert pref_allows_day(None, 3) is True
    assert pref_allows_range(None, 3, 0, 1440) is True


# ── End-to-end: the batch engine honors day-limited windows (FakeSB harness) ──
sys.path.insert(0, os.path.dirname(__file__))
import asyncio  # noqa: E402
import test_batch_correctness as tc  # noqa: E402  (shared fixture harness)
import batch_schedule as bs  # noqa: E402


def _await(coro):
    # Own fresh loop per call — tc._LOOP is the thread's default loop and pytest-asyncio
    # suites (test_optimizer) CLOSE it during teardown; this file runs after them
    # alphabetically, so borrowing tc._await breaks in full-suite order.
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


def _pending_with_windows(i, city, windows):
    t = tc._pending(i, city)
    t["preferred_windows"] = windows
    return t


def test_day_limited_window_lands_on_allowed_day_with_narrowed_window(monkeypatch):
    # Tech covers דרום on Sunday(0) + Wednesday(3). Customer: Wednesdays 10:00-13:00 only
    # ⇒ must land Wednesday, and the written window must be 10:00-13:00 (not tenant default).
    fake = tc.FakeSB(
        pending=[_pending_with_windows(0, "באר שבע",
                                       [{"from": "10:00", "to": "13:00", "days": [3]}])],
        zones=tc._ZONES, techs=[tc._tech("t1", "אלירן", tc._ROT_SOUTH)], cats=tc._CATS)
    fake.install(monkeypatch)
    _await(bs.run_batch_schedule(
        "tenant-1", tc.SUN, tc.THU, False, "svc-key"))
    body = dict(fake.patches)["p0"]
    assert body["scheduled_date"] == tc.WED, body
    assert body["scheduled_window_start"] == "10:00", body
    assert body["scheduled_window_end"] == "13:00", body
    t_min = int(body["scheduled_time"][:2]) * 60 + int(body["scheduled_time"][3:5])
    assert 600 <= t_min < 780, f"time outside preferred window: {body}"


def test_uncoverable_days_yield_pref_reason(monkeypatch):
    # Customer only available Monday(1) — tech never covers דרום on Monday ⇒ unassigned
    # with the actionable reason (renegotiate days, not capacity).
    fake = tc.FakeSB(
        pending=[_pending_with_windows(0, "באר שבע",
                                       [{"from": "09:00", "to": "12:00", "days": [1]}])],
        zones=tc._ZONES, techs=[tc._tech("t1", "אלירן", tc._ROT_SOUTH)], cats=tc._CATS)
    fake.install(monkeypatch)
    r = _await(bs.run_batch_schedule("tenant-1", tc.SUN, tc.THU, True, "svc-key"))
    assert r["unassigned"] == 1, r
    assert r["unassigned_tasks"][0]["reason"] == "no_preferred_window_day", r


def test_soft_mode_keeps_old_behavior(monkeypatch):
    # preferred_windows_mode=soft ⇒ the Monday-only customer still gets placed (highlight-only
    # semantics), and the window is NOT narrowed.
    cfg = tc._cfg(scheduling={"mode": "zone", "route_strategy": "far_to_near",
                              "preferred_windows_mode": "soft"})
    fake = tc.FakeSB(
        pending=[_pending_with_windows(0, "באר שבע",
                                       [{"from": "09:00", "to": "12:00", "days": [1]}])],
        zones=tc._ZONES, techs=[tc._tech("t1", "אלירן", tc._ROT_SOUTH)], cats=tc._CATS,
        config=cfg)
    fake.install(monkeypatch)
    _await(bs.run_batch_schedule(
        "tenant-1", tc.SUN, tc.THU, False, "svc-key"))
    body = dict(fake.patches)["p0"]
    assert body["scheduled_date"] in (tc.SUN, tc.WED), body
