"""
Global drive-time cache (tenant-independent — a road takes the same time for everyone).
Backend-only: reads/writes public.route_cache via the Supabase service key (RLS denies all
other roles). Every operation is best-effort / fail-open: a missing table or network error
must never break optimization — callers fall back to Google or haversine.
"""
import os
import httpx

SUPABASE_URL = os.getenv("SUPABASE_URL", "https://pxpqcdfxogaajwstwdtk.supabase.co")


# ── Pure helpers ──────────────────────────────────────────────────────────────

def norm_key(loc: str) -> str:
    """Normalize a location into a stable cache key.
    'lat,lon' → rounded to 4 decimal places (~11 m); city names → trimmed."""
    s = (loc or "").strip()
    parts = s.split(",", 1)
    if len(parts) == 2:
        try:
            lat = round(float(parts[0].strip()), 4)
            lon = round(float(parts[1].strip()), 4)
            return f"{lat},{lon}"
        except ValueError:
            pass
    return s


def is_trustworthy(google_min: int, straight_km: float) -> bool:
    """Reject implausible Google legs that would poison the cache forever.
    Floor: nobody covers the straight-line distance faster than ~110 km/h highway driving.
    Cap: more than 10x the conservative 35 km/h estimate is absurd (bad API row).
    NOTE: the floor must be physics-based (highway speed), NOT the 35 km/h city heuristic —
    real intercity legs are routinely much faster than that heuristic."""
    floor = max(1, int(straight_km / 110 * 60))
    cap = max(3, int(straight_km / 35 * 60)) * 10
    return floor <= google_min <= cap


# ── Supabase REST I/O (best-effort, fail-open) ────────────────────────────────

def _headers(key: str) -> dict:
    return {"apikey": key, "Authorization": f"Bearer {key}", "Content-Type": "application/json"}


def get_cached(pairs: list, key: str, bucket: str = "static") -> dict:
    """Fetch cached drive_minutes for the given directional (from_key, to_key) pairs, for ONE
    time_bucket (default 'static' = today's behavior). Returns {(from_key, to_key): minutes}.
    Missing table / errors → {} (fail-open). Cross-tenant brain P0: the bucket is the time-of-day
    seam; default keeps reads on the existing rows."""
    if not pairs or not key:
        return {}
    or_terms = ",".join(f'and(from_key.eq."{f}",to_key.eq."{t}")' for f, t in pairs)
    try:
        with httpx.Client(timeout=15) as c:
            r = c.get(
                f"{SUPABASE_URL}/rest/v1/route_cache",
                headers=_headers(key),
                params={"select": "from_key,to_key,drive_minutes",
                        "time_bucket": f"eq.{bucket}", "or": f"({or_terms})"},
            )
            r.raise_for_status()
            rows = r.json()
    except Exception:
        return {}
    return {(row["from_key"], row["to_key"]): row["drive_minutes"] for row in rows}


def put_cached(rows: list, key: str, bucket: str = "static") -> None:
    """Upsert cache rows: [{from_key, to_key, drive_minutes, source}]. Stamps the time_bucket
    (default 'static') so callers need not know about buckets yet. Best-effort — a cache write
    failure must never break optimization."""
    if not rows or not key:
        return
    payload = [{**row, "time_bucket": row.get("time_bucket", bucket)} for row in rows]
    try:
        with httpx.Client(timeout=15) as c:
            c.post(
                f"{SUPABASE_URL}/rest/v1/route_cache",
                headers={**_headers(key), "Prefer": "resolution=merge-duplicates"},
                json=payload,
            )
    except Exception:
        pass


def split_hits_misses(locations: list, service_key: str, bucket: str = "static") -> tuple:
    """For all directional non-self location pairs, return (hits {pair: minutes}, miss pairs)
    for ONE time_bucket (default 'static')."""
    keys = [norm_key(l) for l in locations]
    pairs = [(keys[i], keys[j]) for i in range(len(keys)) for j in range(len(keys)) if i != j]
    hits = get_cached(pairs, service_key, bucket)
    misses = [p for p in pairs if p not in hits]
    return hits, misses
