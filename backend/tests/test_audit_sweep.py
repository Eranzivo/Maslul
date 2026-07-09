"""Nightly-sweep payload assembly (pure part of audit_sweep): assigned tasks
grouped into per-date optimize_routes payloads, durations via the shared
_effective_duration chain, hours from weekly_schedule overrides, breaks
clamped, unassigned/unknown-tech rows skipped.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from audit_sweep import build_day_payloads  # noqa: E402

TECHS = [{
    "id": "t1", "name": "בני", "base_city": "אשקלון", "return_city": None,
    "start_time": "07:00", "end_time": "18:00",
    # 2026-07-12 is a Sunday -> dow 0; override that day's hours
    "weekly_schedule": {"0": {"work": True, "start": "08:00", "end": "16:00"},
                        "_break": {"mode": "custom", "start": "12:00", "end": "12:30"}},
    "duration_overrides": {"cat-fix": 45},
}]
CATS = [{"id": "cat-fix", "duration_minutes": 60},
        {"id": "cat-srv", "duration_minutes": 30}]
CONFIG = {"defaults": {"regular_job_minutes": 30}}


def _t(id_, ds, time, cat, tid="t1"):
    return {"id": id_, "city": "אשקלון", "street": None, "lat": None, "lon": None,
            "category_id": cat, "technician_id": tid, "scheduled_date": ds,
            "scheduled_time": time, "scheduled_window_start": "08:00:00",
            "scheduled_window_end": "11:00:00", "locked": False}


def test_grouping_hours_durations_breaks():
    tasks = [_t("a", "2026-07-12", "08:30:00", "cat-fix"),
             _t("b", "2026-07-12", "10:00:00", "cat-srv"),
             _t("c", "2026-07-13", "09:00:00", None),
             _t("skip-unassigned", "2026-07-12", "09:00:00", None, tid=None),
             _t("skip-unknown-tech", "2026-07-12", "09:00:00", None, tid="ghost")]
    p = build_day_payloads(tasks, TECHS, CATS, [], CONFIG)
    assert sorted(p.keys()) == ["2026-07-12", "2026-07-13"]

    sun = p["2026-07-12"][0]
    assert (sun.start_time, sun.end_time) == ("08:00", "16:00")   # weekly override wins
    assert sun.breaks == [{"from": "12:00", "to": "12:30"}]       # custom break, clamped
    by_id = {t.id: t for t in sun.tasks}
    assert set(by_id) == {"a", "b"}                               # skips dropped
    assert by_id["a"].duration_minutes == 45                      # tech override > category
    assert by_id["b"].duration_minutes == 30                      # category
    assert by_id["a"].scheduled_time == "08:30"                   # HH:MM:SS -> HH:MM
    assert by_id["a"].window_start == "08:00" and by_id["a"].window_end == "11:00"

    mon = p["2026-07-13"][0]
    assert (mon.start_time, mon.end_time) == ("07:00", "18:00")   # no override that dow
    assert mon.tasks[0].duration_minutes == 30                    # no cat -> tenant regular


def test_partial_dayoff_becomes_break():
    tasks = [_t("a", "2026-07-12", "08:30:00", None)]
    dayoffs = [{"technician_id": "t1", "date": "2026-07-12", "type": "partial",
                "from_time": "14:00", "to_time": "15:00"}]
    p = build_day_payloads(tasks, TECHS, CATS, dayoffs, CONFIG)
    assert {"from": "14:00", "to": "15:00"} in p["2026-07-12"][0].breaks


def test_empty_inputs():
    assert build_day_payloads([], TECHS, CATS, [], CONFIG) == {}
    assert build_day_payloads(None, None, None, None, None) == {}
