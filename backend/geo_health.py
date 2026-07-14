"""Geo Health report — READ-ONLY diagnostics for the self-healing geo brain (Slice 1).

Pure computation, no network: given a tenant's task-cities with call counts, the set of
zone-covered canonical keys, and the backend's authoritative `resolve` + `match_key` seams,
it classifies each DISTINCT city as OK / unresolved / out-of-zone. The network shell
(fetch tasks + zones, call this, return JSON) lives in main.py.

Resolution authority stays in the backend — this module is handed the same `geo_resolver.resolve`
and `batch_schedule._match_key` the optimizer/batch use, so the frontend never re-implements
resolution (the נהריה/נהרייה false-flag lesson). Fail-open by construction: it
never raises on normal data; the endpoint wraps it so any upstream error degrades to an all-clear
report, never a 500 into the UI.

Design: outputs/geo-selfheal-design_2026-07-14.md.
"""
from typing import Callable, Iterable, Optional, Tuple


def build_health_report(
    cities_with_counts: Iterable[Tuple[str, int]],
    zone_keys: set,
    resolve: Callable[[str], Optional[Tuple[float, float]]],
    match_key: Callable[[str], str],
) -> dict:
    """Classify each distinct task-city.

    Args:
        cities_with_counts: iterable of ``(city_str, call_count)``.
        zone_keys: set of canonical match-keys covered by at least one zone. An EMPTY set
            means coverage is unknown (no zones loaded / brain absent) → out_of_zone is NOT
            flagged (fail-open: never invent a coverage gap we can't actually verify).
        resolve: ``city_str -> (lat, lon) | None`` — authoritative (`geo_resolver.resolve`).
        match_key: ``city_str -> canonical key`` — the same seam zone membership is built with.

    Returns:
        ``{"unresolved":[{city,calls}...], "out_of_zone":[{city,calls,lat,lon}...],
           "summary":{unresolved,out_of_zone,attention,checked_cities}}`` — both lists sorted
        by call count descending (most-impactful first).
    """
    unresolved = []
    out_of_zone = []
    checked = 0
    for city, count in cities_with_counts:
        city = (city or "").strip()
        if not city:
            continue
        checked += 1
        coords = resolve(city)
        if coords is None:
            unresolved.append({"city": city, "calls": int(count)})
            continue
        # Only flag out-of-zone when we actually know the coverage set.
        if zone_keys and match_key(city) not in zone_keys:
            lat, lon = coords
            out_of_zone.append({"city": city, "calls": int(count), "lat": lat, "lon": lon})
    unresolved.sort(key=lambda r: -r["calls"])
    out_of_zone.sort(key=lambda r: -r["calls"])
    return {
        "unresolved": unresolved,
        "out_of_zone": out_of_zone,
        "summary": {
            "unresolved": len(unresolved),
            "out_of_zone": len(out_of_zone),
            "attention": len(unresolved) + len(out_of_zone),
            "checked_cities": checked,
        },
    }
