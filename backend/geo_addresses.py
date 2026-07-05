"""Shared address-level knowledge base ("City cords") — Geo Slice B.

Global Layer-A table `geo_addresses` (like route_cache: tenant-independent, deny-all RLS,
service-key only). Holds street+city → coordinates, nothing else — an address is public
geography; client names/phones NEVER enter this table (the Layer-A privacy boundary).

Flow: /geocode checks here FIRST (repeat addresses cost zero Google spend, across ALL
tenants), falls back to Google on miss, and stores trusted results so the KB grows with
every client's real calls. Lookup tiers:
  exact  — same city + same normalized street incl. house number
  street — same city + same street name: reuse the NEAREST known house number
           (same street ⇒ same block area — right for routing, never a cross-street guess)
Everything here is best-effort / fail-open: a KB outage must never break geocoding.
"""
import os
import re
import httpx

from canonicalize import normalize_place_key

SUPABASE_URL = os.getenv("SUPABASE_URL", "https://pxpqcdfxogaajwstwdtk.supabase.co")

_NUM_RE = re.compile(r"(\d+)")


# ── Pure helpers ──────────────────────────────────────────────────────────────

def street_keys(street):
    """(full_key, street_name_key, house_number) — normalized via the same noise rules
    as place names (gershayim/hyphen/whitespace), house number extracted for the
    nearest-house tier."""
    k = normalize_place_key(street)
    if not k:
        return "", "", None
    m = _NUM_RE.search(k)
    num = int(m.group(1)) if m else None
    name = _NUM_RE.sub(" ", k)
    name = re.sub(r"\s+", " ", name).strip()
    return k, name, num


def city_key(city) -> str:
    """Canonical city key — the SAME chain zone matching uses (_match_key), so
    'ק"ש' and 'קריית שמונה' share one address namespace."""
    from batch_schedule import _match_key
    import geo_resolver
    return _match_key(city or "", geo_resolver.alias_map())


def plausible_il(lat, lon) -> bool:
    """Trust bound for storing: inside the Israel bounding box. A geocode that landed in
    Paris is returned to the caller (their problem to spot) but NEVER poisons the KB."""
    if lat is None or lon is None:
        return False
    return 29.0 <= lat <= 33.5 and 33.8 <= lon <= 36.0


# ── Supabase REST I/O (service key; best-effort, fail-open) ──────────────────

def _headers(key: str) -> dict:
    return {"apikey": key, "Authorization": f"Bearer {key}", "Content-Type": "application/json"}


def _fetch(params: dict, key: str) -> list:
    with httpx.Client(timeout=10) as c:
        r = c.get(f"{SUPABASE_URL}/rest/v1/geo_addresses", headers=_headers(key), params=params)
        r.raise_for_status()
        return r.json()


def lookup(street, city, service_key):
    """(lat, lon, tier) or None. tier ∈ {'exact', 'street'}."""
    if not service_key:
        return None
    full, name, num = street_keys(street)
    ck = city_key(city)
    if not full or not ck:
        return None
    try:
        rows = _fetch({"city_key": f"eq.{ck}", "street_key": f"eq.{full}",
                       "select": "lat,lon,house_number"}, service_key)
        if rows:
            return (rows[0]["lat"], rows[0]["lon"], "exact")
        if name:
            rows = _fetch({"city_key": f"eq.{ck}", "street_name_key": f"eq.{name}",
                           "select": "lat,lon,house_number"}, service_key)
            if rows:
                if num is not None:
                    rows.sort(key=lambda r: abs((r.get("house_number") or 10**6) - num))
                return (rows[0]["lat"], rows[0]["lon"], "street")
    except Exception:
        return None  # fail-open — caller proceeds to Google
    return None


def store(street, city, lat, lon, service_key) -> None:
    """Upsert one geocoded address. Best-effort; trust-checked by the caller."""
    if not service_key:
        return
    full, name, num = street_keys(street)
    ck = city_key(city)
    if not full or not ck:
        return
    try:
        with httpx.Client(timeout=10) as c:
            c.post(f"{SUPABASE_URL}/rest/v1/geo_addresses",
                   headers={**_headers(service_key), "Prefer": "resolution=merge-duplicates"},
                   json=[{"city_key": ck, "street_key": full, "street_name_key": name,
                          "house_number": num, "lat": lat, "lon": lon, "source": "google"}])
    except Exception:
        pass


# ── Google Geocoding (moved here so the endpoint stays thin/testable) ─────────

async def google_geocode(street, city, api_key):
    """(lat, lon) via Google, or None. Raises nothing — None on any failure."""
    full_address = f"{street}, {city}, ישראל"
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.get(
                "https://maps.googleapis.com/maps/api/geocode/json",
                params={"address": full_address, "key": api_key, "region": "il", "language": "he"},
            )
        data = resp.json()
    except Exception:
        return None
    if data.get("status") == "OK":
        loc = data["results"][0]["geometry"]["location"]
        return (loc["lat"], loc["lng"])
    return None
