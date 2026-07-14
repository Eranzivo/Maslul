"""
Cross-tenant brain Phase 2 — read tenant-learned travel legs from route_observations.
Backend-only (service key). Aggregates a tenant's own observed legs into a median duration
per (from_key, to_key), gated by a minimum sample count so a single fluke can't move a route.
Every operation is best-effort / fail-open: a missing table or network error returns {} and the
optimizer falls back to the global cache / Google / haversine exactly as before.

This is Tier-1 consumption (a tenant learning from ITS OWN history). Tier-2 cross-tenant
promotion into route_cache is a later phase (the supervisor). Design:
outputs/cross-tenant-brain-design_2026-07-14.md
"""
import os
import statistics
import httpx

SUPABASE_URL = os.getenv("SUPABASE_URL", "https://pxpqcdfxogaajwstwdtk.supabase.co")


# ── Pure aggregation (testable without network) ───────────────────────────────

def aggregate_legs(rows: list, min_samples: int = 3) -> dict:
    """Rows: [{from_key, to_key, observed_min}, …] → {(from_key, to_key): median_min}
    for every leg with at least `min_samples` observations. Median is robust to the odd
    slow/fast run. Bucket-agnostic in v1 (time-of-day weighting comes with rush-hour routing)."""
    buckets: dict = {}
    for r in rows or []:
        try:
            f, t, m = r["from_key"], r["to_key"], int(r["observed_min"])
        except (KeyError, TypeError, ValueError):
            continue
        if not f or not t or f == t or m <= 0:
            continue
        buckets.setdefault((f, t), []).append(m)
    out = {}
    for pair, mins in buckets.items():
        if len(mins) >= min_samples:
            out[pair] = int(round(statistics.median(mins)))
    return out


# ── Supabase REST I/O (best-effort, fail-open) ────────────────────────────────

def get_learned_legs(tenant_id: str, service_key: str, min_samples: int = 3) -> dict:
    """Fetch a tenant's observed legs and aggregate → {(from_key, to_key): median_min}.
    Missing table / errors / no service key → {} (fail-open — optimizer is unaffected)."""
    if not tenant_id or not service_key:
        return {}
    try:
        with httpx.Client(timeout=15) as c:
            r = c.get(
                f"{SUPABASE_URL}/rest/v1/route_observations",
                headers={"apikey": service_key, "Authorization": f"Bearer {service_key}"},
                params={"select": "from_key,to_key,observed_min", "tenant_id": f"eq.{tenant_id}"},
            )
            r.raise_for_status()
            rows = r.json()
    except Exception:
        return {}
    return aggregate_legs(rows, min_samples)
