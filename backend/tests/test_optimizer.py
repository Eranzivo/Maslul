"""
pytest suite for backend/optimizer.py and backend/cities.py

Run from backend/ directory:
    pip install pytest pytest-asyncio
    pytest tests/ -v

All tests run in local (no Google Maps key) mode.
"""
import math
import logging
import pytest
import asyncio
from unittest.mock import patch

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from optimizer import (
    haversine_km, km_to_minutes, time_to_min, min_to_time,
    build_matrix_local, solve_route, optimize_routes,
)
from cities import get_coords, CITY_COORDS


# ── Helpers ───────────────────────────────────────────────────────────────────

def make_tech(id="t1", name="Test", base="תל אביב", tasks=None):
    from main import Technician, Task as TTask
    return Technician(
        id=id, name=name, base_city=base,
        start_time="07:00", end_time="17:00",
        tasks=tasks or [],
    )

def make_task(id, city, duration=30):
    from main import Task as TTask
    return TTask(id=id, city=city, duration_minutes=duration)


# ── Unit: distance / time helpers ─────────────────────────────────────────────

def test_haversine_same_point():
    assert haversine_km(32.08, 34.78, 32.08, 34.78) == pytest.approx(0.0)

def test_haversine_tel_aviv_jerusalem():
    # ~55 km straight-line
    d = haversine_km(32.0853, 34.7818, 31.7683, 35.2137)
    assert 50 < d < 65, f"Expected ~55 km, got {d:.1f}"

def test_haversine_tel_aviv_eilat():
    # ~330 km straight-line
    d = haversine_km(32.0853, 34.7818, 29.5569, 34.9519)
    assert 300 < d < 360, f"Expected ~330 km, got {d:.1f}"

def test_km_to_minutes_minimum():
    assert km_to_minutes(0.1) == 3  # clamps to minimum

def test_km_to_minutes_realistic():
    # 35 km at 35 km/h = 60 min
    assert km_to_minutes(35.0) == 60

def test_time_to_min():
    assert time_to_min("07:00") == 420
    assert time_to_min("17:30") == 1050
    assert time_to_min("00:00") == 0

def test_min_to_time():
    assert min_to_time(420) == "07:00"
    assert min_to_time(1050) == "17:30"
    assert min_to_time(0) == "00:00"

def test_min_to_time_clamps():
    assert min_to_time(-1) == "00:00"
    assert min_to_time(99999) == "23:59"


# ── Unit: city coords ─────────────────────────────────────────────────────────

def test_known_city_returns_correct_coords():
    lat, lon = get_coords("תל אביב")
    assert lat == pytest.approx(32.0853, abs=0.01)
    assert lon == pytest.approx(34.7818, abs=0.01)

def test_partial_match_returns_coords():
    # "תל" is a substring of "תל אביב"
    lat, lon = get_coords("יפו תל אביב")
    assert lat != 0 and lon != 0

def test_unknown_city_falls_back_to_tel_aviv(caplog):
    with caplog.at_level(logging.WARNING):
        lat, lon = get_coords("עיר_לא_קיימת_xyz_9999")
    assert lat == pytest.approx(32.0853, abs=0.01)
    assert lon == pytest.approx(34.7818, abs=0.01)
    assert "Unknown city" in caplog.text

def test_city_coords_has_minimum_coverage():
    assert len(CITY_COORDS) >= 50, "Need at least 50 cities in coords dict"


# ── Unit: distance matrix ─────────────────────────────────────────────────────

def test_matrix_diagonal_is_zero():
    locations = ["תל אביב", "חיפה", "ירושלים"]
    matrix = build_matrix_local(locations)
    for i in range(len(locations)):
        assert matrix[i][i] == 0

def test_matrix_is_square():
    locations = ["תל אביב", "ראשון לציון", "חולון", "בת ים"]
    matrix = build_matrix_local(locations)
    assert len(matrix) == 4
    for row in matrix:
        assert len(row) == 4

def test_matrix_travel_time_realistic():
    # Tel Aviv → Jerusalem ≈ 55 km ≈ 94 min at 35 km/h
    locs = ["תל אביב", "ירושלים"]
    matrix = build_matrix_local(locs)
    assert 60 < matrix[0][1] < 130, f"TA→Jer travel unexpected: {matrix[0][1]} min"


# ── Unit: solve_route edge cases ──────────────────────────────────────────────

def test_solve_route_empty():
    ordered, arrivals = solve_route("תל אביב", [], [], [], "07:00", "17:00")
    assert ordered == []
    assert arrivals == []

def test_solve_route_single_task():
    locs = ["תל אביב", "חיפה"]
    matrix = build_matrix_local(locs)
    ordered, arrivals = solve_route("תל אביב", ["חיפה"], [30], matrix, "07:00", "17:00")
    assert ordered == [0]
    assert len(arrivals) == 1
    # Arrival must be after start + depot travel
    assert arrivals[0] >= time_to_min("07:00")

def test_solve_route_fallback_arrivals_include_depot_travel():
    """Regression: fallback route (no OR-Tools solution) must include depot→task0 travel."""
    # Use cities far apart so depot travel is significant
    locs = ["אילת", "חיפה", "נהריה"]  # Eilat → Haifa is ~330 km
    matrix = build_matrix_local(locs)
    depot_to_task0 = matrix[0][1]
    assert depot_to_task0 > 0, "Depot travel must be non-zero for far cities"

    # Force fallback by mocking routing to return None
    import optimizer as opt_module
    import ortools.constraint_solver.pywrapcp as pywrapcp

    original_solve = pywrapcp.RoutingModel.SolveWithParameters

    def mock_solve(self, params):
        return None  # force fallback

    with patch.object(pywrapcp.RoutingModel, 'SolveWithParameters', mock_solve):
        ordered, arrivals = solve_route(
            "אילת", ["חיפה", "נהריה"], [30, 30], matrix, "07:00", "18:00"
        )

    assert len(arrivals) == 2
    # First task arrival must include depot travel (not just start_min = 420)
    assert arrivals[0] >= time_to_min("07:00") + depot_to_task0, (
        f"Fallback arrival {arrivals[0]} should include depot travel {depot_to_task0}"
    )

def test_solve_route_arrivals_monotonically_increasing():
    """Consecutive arrivals must be non-decreasing (no time-travel)."""
    locs = ["תל אביב", "ראשון לציון", "רחובות", "יבנה", "אשדוד"]
    matrix = build_matrix_local(locs)
    cities = [l for l in locs[1:]]
    durations = [30] * len(cities)
    ordered, arrivals = solve_route("תל אביב", cities, durations, matrix, "07:00", "17:00")
    for i in range(len(arrivals) - 1):
        assert arrivals[i] <= arrivals[i + 1], (
            f"Arrival at step {i} ({arrivals[i]}) > step {i+1} ({arrivals[i+1]})"
        )

def test_solve_route_all_arrivals_within_work_hours():
    locs = ["תל אביב", "הרצליה", "נתניה", "חדרה"]
    matrix = build_matrix_local(locs)
    cities = locs[1:]
    durations = [30] * len(cities)
    ordered, arrivals = solve_route("תל אביב", cities, durations, matrix, "07:00", "17:00")
    start = time_to_min("07:00")
    end = time_to_min("17:00")
    for arr in arrivals:
        assert start <= arr <= end, f"Arrival {arr} outside work hours [{start}, {end}]"


# ── Integration: optimize_routes ─────────────────────────────────────────────

@pytest.mark.asyncio
async def test_optimize_routes_single_tech():
    tech = make_tech(tasks=[
        make_task("t1", "ראשון לציון"),
        make_task("t2", "רחובות"),
        make_task("t3", "יבנה"),
    ])
    results = await optimize_routes([tech], google_maps_api_key=None)
    assert len(results) == 1
    r = results[0]
    assert r["technician_id"] == "t1"
    assert len(r["ordered_tasks"]) == 3
    assert set(r["ordered_tasks"]) == {"t1", "t2", "t3"}
    assert len(r["estimated_times"]) == 3
    assert r["total_drive_minutes"] >= 0
    assert r["mode"] == "local"

@pytest.mark.asyncio
async def test_optimize_routes_empty_tech():
    tech = make_tech(tasks=[])
    results = await optimize_routes([tech], google_maps_api_key=None)
    assert results[0]["ordered_tasks"] == []
    assert results[0]["total_drive_minutes"] == 0

@pytest.mark.asyncio
async def test_optimize_routes_two_techs():
    tech1 = make_tech("t1", "Tech North", "חיפה", tasks=[
        make_task("n1", "נהריה"),
        make_task("n2", "עכו"),
    ])
    tech2 = make_tech("t2", "Tech South", "ראשון לציון", tasks=[
        make_task("s1", "אשדוד"),
        make_task("s2", "אשקלון"),
    ])
    results = await optimize_routes([tech1, tech2], google_maps_api_key=None)
    assert len(results) == 2
    ids = {r["technician_id"] for r in results}
    assert ids == {"t1", "t2"}
    for r in results:
        assert len(r["ordered_tasks"]) == 2

@pytest.mark.asyncio
async def test_optimize_routes_all_task_ids_preserved():
    """Every input task ID must appear exactly once in the output."""
    task_ids = ["a", "b", "c", "d", "e"]
    tech = make_tech(tasks=[make_task(tid, "תל אביב") for tid in task_ids])
    results = await optimize_routes([tech], google_maps_api_key=None)
    assert sorted(results[0]["ordered_tasks"]) == sorted(task_ids)
