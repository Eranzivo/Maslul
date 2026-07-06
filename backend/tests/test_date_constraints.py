"""Structured per-task date constraints (fixed/earliest/latest) — golden parity fixture
(tests/fixtures/datecons-cases.json) run by BOTH this suite and tests/sched.test.js,
plus batch e2e via the FakeSB harness."""
import asyncio
import io
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.dirname(__file__))

from batch_schedule import date_constraint_allows  # noqa: E402
import batch_schedule as bs  # noqa: E402
import test_batch_correctness as tc  # noqa: E402

_FX = json.load(io.open(os.path.join(os.path.dirname(__file__), "..", "..",
                                     "tests", "fixtures", "datecons-cases.json"),
                        encoding="utf-8"))


def test_fixture_cases():
    for c in _FX["cases"]:
        assert date_constraint_allows(c["cons"], c["date"]) == c["allow"], c["why"]


def test_none_task_allows():
    assert date_constraint_allows(None, "2026-07-12") is True


def _await(coro):
    # Own fresh loop — pytest-asyncio suites close the thread default (see test_pref_windows).
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


def _pending_with(i, city, **fields):
    t = tc._pending(i, city)
    t.update(fields)
    return t


def test_fixed_date_lands_exactly_there(monkeypatch):
    # Tech covers דרום Sunday+Wednesday; fixed_date=Wednesday ⇒ must land Wednesday.
    fake = tc.FakeSB(
        pending=[_pending_with(0, "באר שבע", fixed_date=tc.WED)],
        zones=tc._ZONES, techs=[tc._tech("t1", "אלירן", tc._ROT_SOUTH)], cats=tc._CATS)
    fake.install(monkeypatch)
    _await(bs.run_batch_schedule("tenant-1", tc.SUN, tc.THU, False, "svc-key"))
    assert dict(fake.patches)["p0"]["scheduled_date"] == tc.WED


def test_fixed_date_on_uncovered_day_reports_reason(monkeypatch):
    # fixed_date=Monday but the tech never covers דרום on Monday ⇒ fixed_date_unavailable.
    fake = tc.FakeSB(
        pending=[_pending_with(0, "באר שבע", fixed_date=tc.MON)],
        zones=tc._ZONES, techs=[tc._tech("t1", "אלירן", tc._ROT_SOUTH)], cats=tc._CATS)
    fake.install(monkeypatch)
    r = _await(bs.run_batch_schedule("tenant-1", tc.SUN, tc.THU, True, "svc-key"))
    assert r["unassigned_tasks"][0]["reason"] == "fixed_date_unavailable", r


def test_earliest_pushes_past_first_covering_day(monkeypatch):
    # earliest=Monday excludes the Sunday covering day ⇒ lands Wednesday.
    fake = tc.FakeSB(
        pending=[_pending_with(0, "באר שבע", earliest_date=tc.MON)],
        zones=tc._ZONES, techs=[tc._tech("t1", "אלירן", tc._ROT_SOUTH)], cats=tc._CATS)
    fake.install(monkeypatch)
    _await(bs.run_batch_schedule("tenant-1", tc.SUN, tc.THU, False, "svc-key"))
    assert dict(fake.patches)["p0"]["scheduled_date"] == tc.WED


def test_latest_before_all_covering_days_reports_reason(monkeypatch):
    # latest=Monday: Sunday is covered and allowed... Sunday <= Monday, so it lands Sunday.
    # Use earliest=Monday AND latest=Tuesday: no covering day inside ⇒ date-constraints reason.
    fake = tc.FakeSB(
        pending=[_pending_with(0, "באר שבע", earliest_date=tc.MON, latest_date=tc.TUE)],
        zones=tc._ZONES, techs=[tc._tech("t1", "אלירן", tc._ROT_SOUTH)], cats=tc._CATS)
    fake.install(monkeypatch)
    r = _await(bs.run_batch_schedule("tenant-1", tc.SUN, tc.THU, True, "svc-key"))
    assert r["unassigned_tasks"][0]["reason"] == "no_slot_within_date_constraints", r
