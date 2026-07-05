# Geo One-Stop-Shop — Design Spec (Slice A approved; Slice B designed)

> Approved by Eran 2026-07-05: "Names+coords first, addresses next." Source findings: `outputs/product-review-fable_2026-07-05.md` §A-parity + B1/B2.
> Requirement (Eran): the system must never fall because of drifting geo copies; converge on ONE source of truth; ק"ש / קרית שמונה / קריית שמונה = the same city everywhere; future calls log real addresses so fallbacks can use the nearest real address we hold.

## End state

**`geo_places` + `place_aliases` (Supabase, global, PII-free) are the single authority for place identity and coordinates.** All four current sources converge:

| Source today | Role after Slice A |
|---|---|
| `geo_places` / `place_aliases` (DB) | **The** source of truth (names, aliases, coords) |
| `CITY_COORDS_JS` + `CITY_ALIASES` (index.html) | Offline last-resort fallback only (brain fetch failed) |
| `cities.py` + `_CITY_ALIASES` (backend) | Offline last-resort fallback only (already the case for coords via `geo_resolver`; extends to *zone matching*) |

Resolution chain, identical in JS and Python: **normalize noise** (gershayim/quotes/hyphens/whitespace — `normalize_place_key` and its tested JS twin) → **DB alias** → **canonical key** → **coords**. `ק"ש` → `קש` → alias → `קריית שמונה` in dispatch, batch zone-matching, polygon draw, and analytics alike.

## Slice A (approved, build after Slice 1)

1. **Frontend read access:** RLS `SELECT` policy for role `authenticated` on `geo_places` + `place_aliases` (public geography, no PII by design — the Layer-A privacy boundary). App loads the brain once per session on login (~423 rows ≈ 20KB), caches in memory as `GEO_BRAIN`; fetch failure ⇒ silent fallback to the static lists (system never falls). Migration SQL delivered as chat code block for approval.
2. **JS resolution:** `normalizePlaceKeyJS` (marker-tested twin of `canonicalize.normalize_place_key`) + brain-alias lookup wired into `canonicalCity` (static alias map + קריית-collapse retained as fallback tier). `resolveZone` city_list matching therefore uses brain-canonical names on both sides.
3. **Python zone matching:** `find_zone`/`_norm` in `batch_schedule.py` resolve through `geo_resolver`-style brain aliases (normalize → alias → canonical), with `_CITY_ALIASES` demoted to fallback. Kills the live drift (e.g. "קריית טבעון" matching live but flagging `city_not_in_zone` in batch).
4. **Polygon draw fixed:** `_detectCitiesInPolygon` iterates brain places ∪ static fallback; returns canonical names; `confirmZoneDraw`/`_updateZoneDrawStatus` compare canonically. + marker test. (Root cause B1: detection previously scanned only the static 255-city list, invisible to the 423-row brain.)
5. **Superset audit:** one-time SQL inserting any static-only entries (JS or Python) into `geo_places` so the brain strictly contains the fallbacks.
6. **Golden parity fixtures:** `tests/fixtures/geo-cases.json` (ק"ש variants, קריית collapse, נהריה/נהרייה, hyphen/quote noise, unknown city) asserted by BOTH the Node harness and pytest. Drift = failing test.

## Slice B (designed, separate approval — the "City cords" address KB)

- New global table `geo_addresses` (`city_key`, `street_key` normalized, `lat`, `lon`, `source`, `confidence`, timestamps; unique on (city_key, street_key)); PII boundary: street+city only, never client names/phones.
- **Geocode-on-save:** when a task with a street geocodes (existing `/geocode` flow), write coords to the task AND upsert `geo_addresses` — every client's calls grow the shared KB; repeat addresses cost nothing.
- **Fallback ladder (final):** task explicit coords → `geo_addresses` exact (city+street) → nearest known address in that city (only when unambiguous) → `geo_places` city centroid → static lists → `needs_location` flag. Never a TLV guess for routing decisions.
- Optimizer unchanged — it already prefers explicit task coords.

## Risks / rejected alternatives
- RLS read exposes global city coords to any authenticated user of any tenant — acceptable (public geography; the deliberate Layer-A boundary). Rejected: backend `/geo/places` endpoint (extra hop, Railway coupling for near-static data); build-time sync (no build step).
- Brain TTL: frontend per-session load vs backend 600s TTL — a just-added alias may take one refresh to appear everywhere; acceptable (additive data, fail-open).
