"""Runtime place→coordinate resolution backed by the shared geo brain (geo_places +
place_aliases), with a fail-safe fallback to the static cities.py.

Design: outputs/geo-foundation-design_2026-06-13.md. The brain is loaded into memory once
(TTL-refreshed) so the optimizer's hot path stays synchronous. FAIL-OPEN everywhere: if the
brain can't load, `resolve()` falls back to cities.py — i.e. exactly today's behavior — so
wiring this in can never break live scheduling. Resolution is conservative: a genuine miss
returns None (the caller flags `needs_location`), never a guess.
"""
import os
import time
import httpx
from canonicalize import normalize_place_key

_SB_URL = os.getenv("SUPABASE_URL", "https://pxpqcdfxogaajwstwdtk.supabase.co")
_TTL = 600  # seconds — refresh the in-memory brain at most this often

_brain = {"loaded_at": 0.0, "places": {}, "alias_to_key": {}}


def _headers(service_key: str) -> dict:
    return {"apikey": service_key, "Authorization": f"Bearer {service_key}"}


async def ensure_loaded(service_key: str, force: bool = False) -> None:
    """Load geo_places + place_aliases into memory (TTL-cached). Best-effort: on any error
    keep whatever we had — resolve() then falls back to cities.py."""
    if not service_key:
        return
    if not force and _brain["places"] and (time.time() - _brain["loaded_at"] < _TTL):
        return
    try:
        # PostgREST caps every response at 1000 rows — the brain holds 1,300+ places
        # (national OSM import 2026-07-06), so page until a short page or it silently truncates.
        page = 1000
        place_rows = []
        async with httpx.AsyncClient(timeout=10) as c:
            offset = 0
            while True:
                pr = await c.get(f"{_SB_URL}/rest/v1/geo_places",
                                 headers={**_headers(service_key),
                                          "Range": f"{offset}-{offset + page - 1}"},
                                 params={"select": "normalized_key,lat,lon"})
                pr.raise_for_status()
                chunk = pr.json()
                place_rows.extend(chunk)
                if len(chunk) < page:
                    break
                offset += page
            ar = await c.get(f"{_SB_URL}/rest/v1/place_aliases",
                             headers=_headers(service_key),
                             params={"select": "normalized_variant,geo_places(normalized_key)"})
            ar.raise_for_status()
        places = {r["normalized_key"]: (r["lat"], r["lon"])
                  for r in place_rows if r.get("lat") is not None and r.get("lon") is not None}
        alias_to_key = {}
        for r in ar.json():
            gp = r.get("geo_places")
            if gp and gp.get("normalized_key"):
                alias_to_key[r["normalized_variant"]] = gp["normalized_key"]
        if places:
            _brain.update(loaded_at=time.time(), places=places, alias_to_key=alias_to_key)
    except Exception:
        pass  # fail-open


def alias_map() -> dict:
    """The brain's curated alias map ({normalized_variant: canonical_key}) for callers
    that need name-identity (zone matching), not coordinates. {} when not loaded —
    callers must treat that as fail-open (normalize-only matching)."""
    return _brain["alias_to_key"]


def place_keys() -> list:
    """All canonical place keys currently in the brain — the candidate pool for fuzzy
    suggestion (geo_suggest). [] when not loaded ⇒ callers get no suggestion (fail-open)."""
    return list(_brain["places"].keys())


def lookup(name):
    """Resolve a name against the in-memory brain only. (lat, lon) or None — never guesses."""
    key = normalize_place_key(name)
    if not key:
        return None
    canon = _brain["alias_to_key"].get(key, key)
    return _brain["places"].get(canon)


def resolve(name):
    """Brain first, then the static cities.py (fail-safe). (lat, lon) or None."""
    hit = lookup(name)
    if hit is not None:
        return hit
    from cities import resolve_coords
    return resolve_coords(name)
