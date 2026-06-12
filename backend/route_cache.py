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


def is_trustworthy(google_min: int, haversine_min: int) -> bool:
    """Reject implausible Google legs that would poison the cache forever.
    A real drive can't beat the straight-line floor, and >10x it is absurd."""
    if google_min < max(1, int(haversine_min * 0.6)):
        return False
    if google_min > haversine_min * 10:
        return False
    return True


# ── Supabase REST I/O (best-effort, fail-open) ────────────────────────────────

def _headers(key: str) -> dict:
    return {"apikey": key, "Authorization": f"Bearer {key}", "Content-Type": "application/json"}


def get_cached(pairs: list, key: str) -> dict:
    """Fetch cached drive_minutes for the given directional (from_key, to_key) pairs.
    Returns {(from_key, to_key): minutes}. Missing table / errors → {} (fail-open)."""
    if not pairs or not key:
        return {}
    or_terms = ",".join(f'and(from_key.eq."{f}",to_key.eq."{t}")' for f, t in pairs)
    try:
        with httpx.Client(timeout=15) as c:
            r = c.get(
                f"{SUPABASE_URL}/rest/v1/route_cache",
                headers=_headers(key),
                params={"select": "from_key,to_key,drive_minutes", "or": f"({or_terms})"},
            )
            r.raise_for_status()
            rows = r.json()
    except Exception:
        return {}
    return {(row["from_key"], row["to_key"]): row["drive_minutes"] for row in rows}


def put_cached(rows: list, key: str) -> None:
    """Upsert cache rows: [{from_key, to_key, drive_minutes, source}]. Best-effort —
    a cache write failure must never break optimization."""
    if not rows or not key:
        return
    try:
        with httpx.Client(timeout=15) as c:
            c.post(
                f"{SUPABASE_URL}/rest/v1/route_cache",
                headers={**_headers(key), "Prefer": "resolution=merge-duplicates"},
                json=rows,
            )
    except Exception:
        pass


def split_hits_misses(locations: list, service_key: str) -> tuple:
    """For all directional non-self location pairs, return (hits {pair: minutes}, miss pairs)."""
    keys = [norm_key(l) for l in locations]
    pairs = [(keys[i], keys[j]) for i in range(len(keys)) for j in range(len(keys)) if i != j]
    hits = get_cached(pairs, service_key)
    misses = [p for p in pairs if p not in hits]
    return hits, misses
