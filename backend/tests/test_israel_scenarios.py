"""Israel's dispatcher scenarios frozen as engine law (context/scheduling-scenarios.md).

These are REGRESSION anchors: the engine already passes them — the tests exist so no
future refactor/knob can silently break the behaviors Israel described in words.
Geometry note (base אשקלון): דימונה ≈ farthest, באר שבע ≈ mid, אשקלון = base/closest.
"""
import asyncio
import sys, os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.dirname(__file__))

import batch_schedule as bs  # noqa: E402
import test_batch_correctness as tc  # noqa: E402


def _await(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


def _t_min(patch):
    t = patch["scheduled_time"]
    return int(t[:2]) * 60 + int(t[3:5])


def test_window_stacking_three_nearby_calls_share_one_day(monkeypatch):
    """Israel's window-stacking principle ("several calls at the same general time when
    they fit geographically"): three Be'er Sheva calls for a Be'er-Sheva-based tech must
    all land on ONE day inside working hours — the 3h window holds multiple jobs, the day
    is not split unnecessarily (consolidate). Same-city ⇒ ~3min travel, so this isolates
    stacking from depot-distance physics (the far→near ordering is covered separately).

    NB: Israel's worked example assumes the tech STARTS near the work area at 07:00. Modelled
    here by basing the tech in Be'er Sheva — a call's 07:00 window is unreachable if the tech
    must first drive 2h from a distant depot, which is itself correct engine physics."""
    fake = tc.FakeSB(
        pending=[tc._pending(i, "באר שבע") for i in range(3)],
        techs=[tc._tech("t1", "אלירן", tc._ROT_SOUTH, base_city="באר שבע", return_city="באר שבע")],
        zones=tc._ZONES, cats=tc._CATS)
    fake.install(monkeypatch)
    r = _await(bs.run_batch_schedule("tenant-1", tc.SUN, tc.THU, False, "svc-key"))
    assert r["unassigned"] == 0, r
    patches = dict(fake.patches)
    days = {patches[f"p{i}"]["scheduled_date"] for i in range(3)}
    assert len(days) == 1, f"3 nearby calls must stack on ONE day, not split: {days}"
    for i in range(3):
        assert 7 * 60 <= _t_min(patches[f"p{i}"]) <= 17 * 60, patches[f"p{i}"]


def test_three_city_far_to_near_monotonic_day(monkeypatch):
    """Far/mid/close on one day ⇒ arrival order must be דימונה → באר שבע → אשקלון
    (mid-distance placed in the middle — scenarios B3)."""
    fake = tc.FakeSB(
        pending=[tc._pending(0, "אשקלון"), tc._pending(1, "דימונה"), tc._pending(2, "באר שבע")],
        zones=tc._ZONES, techs=[tc._tech("t1", "אלירן", tc._ROT_SOUTH)], cats=tc._CATS)
    fake.install(monkeypatch)
    r = _await(bs.run_batch_schedule("tenant-1", tc.SUN, tc.SUN, False, "svc-key"))
    assert r["unassigned"] == 0, r
    patches = dict(fake.patches)
    t_far, t_mid, t_close = _t_min(patches["p1"]), _t_min(patches["p2"]), _t_min(patches["p0"])
    assert t_far < t_mid < t_close, (
        f"far→near violated: דימונה={t_far} באר שבע={t_mid} אשקלון={t_close}")
