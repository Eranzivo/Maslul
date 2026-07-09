"""Route-intelligence P1 wiring: optimize_routes must attach an id-mapped health
block computed from the solve it already performed, and build_audit_rows must
package results into route_audits rows (skipping unauditable days, clamping the
trigger to the DB check constraint). No network: local matrix via lat/lon tasks.
"""
import asyncio
import os
import sys
from types import SimpleNamespace

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import optimizer  # noqa: E402
import route_health as rh  # noqa: E402


def _task(id_, lat, lon, sched, dur=30):
    return SimpleNamespace(id=id_, city=f"c-{id_}", address=None, lat=lat, lon=lon,
                           duration_minutes=dur, scheduled_time=sched,
                           window_start=None, window_end=None, locked=False)


def _tech(tasks):
    return SimpleNamespace(id="t-1", name="tech", base_city="31.6,34.6",
                           return_city=None, start_time="08:00", end_time="17:00",
                           breaks=[], tasks=tasks)


def _run(coro):
    # Own loop: e2e tests near the pytest-asyncio suites must not share the
    # thread default loop (test_optimizer closes it).
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


def test_optimize_routes_attaches_id_mapped_health():
    # Far stop (Dimona-ish) scheduled LAST under far_to_near -> backtrack finding
    # must carry the task id, and better_order_exists a task-id solver order.
    tasks = [_task("near", 31.61, 34.61, "08:30"),
             _task("far", 31.06, 35.03, "10:00")]
    res = _run(optimizer.optimize_routes([_tech(tasks)], None, service_key="",
                                         route_strategy="far_to_near"))
    h = res[0]["health"]
    assert h is not None and h["score"] is not None
    assert h["actual_order_ids"] == ["near", "far"]
    types = {f["type"] for f in h["findings"]}
    assert "backtrack" in types, f"expected backtrack, got {h['findings']}"
    bt = next(f for f in h["findings"] if f["type"] == "backtrack")
    assert bt["task_id"] == "far"
    bo = [f for f in h["findings"] if f["type"] == "better_order_exists"]
    if bo:  # fires only when the saving clears the noise threshold
        assert set(bo[0]["data"]["solver_order"]) == {"near", "far"}


def test_optimize_routes_empty_day_health_none():
    res = _run(optimizer.optimize_routes([_tech([])], None, service_key="",
                                         route_strategy="far_to_near"))
    assert res[0]["health"] is None


def test_build_audit_rows_packages_and_skips():
    tasks = [_task("a", 31.61, 34.61, "08:30")]
    tech = _tech(tasks)
    results = [{"technician_id": "t-1", "ordered_tasks": ["a"], "total_drive_minutes": 12,
                "health": {"score": 92, "band": "healthy", "partial": False,
                           "components": {"idle_min": 20}, "findings": [],
                           "actual_order_ids": ["a"]}}]
    rows = rh.build_audit_rows("tenant-x", "2026-07-09", [tech], results, "bogus-trigger")
    assert len(rows) == 1
    row = rows[0]
    assert row["tenant_id"] == "tenant-x"
    assert row["technician_id"] == "t-1"
    assert row["trigger"] == "manual"  # clamped to the DB check constraint
    assert row["score"] == 92
    assert row["route_snapshot"] == [{"task_id": "a", "city": "c-a", "time": "08:30"}]
    assert row["solver_best"] == {"order": ["a"], "drive_min": 12}

    # Unauditable days produce NO row (health None or score None).
    for h in (None, {"score": None, "band": None, "partial": False,
                     "components": {}, "findings": [], "actual_order_ids": []}):
        results[0]["health"] = h
        assert rh.build_audit_rows("tenant-x", "2026-07-09", [tech], results, "change") == []
