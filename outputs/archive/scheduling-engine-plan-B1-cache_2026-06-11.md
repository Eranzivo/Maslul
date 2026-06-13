# Plan B1 — Drive-Time Cache Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans. Steps use checkbox (`- [ ]`).

**Goal:** Add a persistent drive-time cache so the optimizer reuses real Google drive times across calls instead of re-fetching every time — making authoritative auto-sequencing (Plan B2) quota-affordable.

**Architecture:** A global `route_cache` table (drive times are tenant-independent). The backend's `build_matrix_gmaps` reads cached legs first, requests only cache-misses from Google (still under the existing daily element cap), writes results back, and distrusts implausible values. Haversine remains the fallback. No frontend change.

**Tech Stack:** FastAPI backend (`backend/`, deployed on Railway), Supabase REST via service key, OR-Tools. Backend tests are plain `pytest` (`backend/tests/`, `backend/test_optimizer.py` pattern).

**Source spec:** `outputs/scheduling-engine-design_2026-06-10.md` §5 (cache). **Refinement:** cache is **global**, not per-tenant (drive times don't vary by tenant; backend-only access via service key, so no RLS/frontend exposure).

**Context the implementer needs:**
- `backend/optimizer.py` — `build_matrix_gmaps(locations, api_key)` (line 59) builds the full N×N matrix by calling Google Distance Matrix once for all origins×destinations. `build_matrix_local` is the haversine fallback. `_parse_loc` turns a location string (`"lat,lon"` or city name) into `(lat,lon)`.
- `backend/main.py` — `_gmaps_quota_ok(elements_needed)` (line 36) gates Google usage by a daily element counter (`GMAPS_DAILY_ELEMENT_LIMIT`, default 1200). `/health` reports usage.
- `backend/batch_schedule.py` — shows the Supabase REST pattern: `_sb_headers(key)`, `_sb_get(path, params, key)`, `_sb_patch(...)` against `{SUPABASE_URL}/rest/v1/{path}`. Service key from `os.getenv("SUPABASE_SERVICE_KEY")`.
- Migrations are run by Eran in Supabase (deliver SQL as a chat code block; never touch prod DB).
- Backend deploys to Railway on push; the implementer cannot verify the live deploy — tests must pass locally.

---

## File Structure

| File | Responsibility | Change |
|---|---|---|
| `backend/route_cache.py` | Cache read/write against Supabase REST; key normalization; trust sanity-bound. One clear responsibility. | Create |
| `backend/optimizer.py` | `build_matrix_gmaps` consults the cache: cached legs reused, only misses fetched, results written back. | Modify |
| `backend/tests/test_route_cache.py` | Unit tests for key normalization, trust bound, cache-hit/miss matrix assembly (Google + Supabase mocked). | Create |
| `outputs/migration-route-cache_2026-06-11.sql` | `route_cache` table DDL for Eran. | Create |
| `context/architecture.md`, `context/scheduling-rules.md` | living-docs. | Modify |

---

## Task 1: `route_cache` table

**Files:** Create `outputs/migration-route-cache_2026-06-11.sql`

- [ ] **Step 1: Write the migration file**

```sql
-- Global drive-time cache (tenant-independent). Backend-only (service key); frontend never reads it.
CREATE TABLE IF NOT EXISTS public.route_cache (
  from_key      TEXT NOT NULL,           -- normalized "lat,lon" (4 dp) or city name
  to_key        TEXT NOT NULL,           -- directional: A→B may differ from B→A
  drive_minutes INTEGER NOT NULL,
  drive_meters  INTEGER,
  source        TEXT NOT NULL DEFAULT 'google',  -- 'google' | 'haversine'
  updated_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (from_key, to_key)
);
-- Lock it down: only the service role (backend) touches it. No anon/authenticated access.
ALTER TABLE public.route_cache ENABLE ROW LEVEL SECURITY;
-- (No policies → RLS denies all non-service-role access. Service key bypasses RLS.)
```

- [ ] **Step 2: Deliver the SQL to Eran** as a chat code block (do not run it). Mention it must be run before the backend that reads it is deployed (the backend tolerates a missing table by falling back to Google/haversine, but the cache is a no-op until it exists).

- [ ] **Step 3: Commit**

```bash
git add outputs/migration-route-cache_2026-06-11.sql
git commit -m "feat(cache): route_cache table migration (global drive-time cache, service-role only)"
```

---

## Task 2: Cache module — key normalization + trust bound (pure, TDD)

**Files:** Create `backend/route_cache.py`; create `backend/tests/test_route_cache.py`

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_route_cache.py
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
import route_cache as rc

def test_norm_key_rounds_coords_to_4dp():
    assert rc.norm_key("32.1234567,34.7654321") == "32.1235,34.7654"

def test_norm_key_passes_city_names_through_trimmed():
    assert rc.norm_key("  תל אביב ") == "תל אביב"

def test_trust_rejects_below_haversine_floor():
    # google 2 min between points ~20 km apart (haversine floor ~34 min) → distrust
    assert rc.is_trustworthy(google_min=2, haversine_min=34) is False

def test_trust_rejects_absurdly_high():
    # > 10x the haversine floor → distrust (bad API row)
    assert rc.is_trustworthy(google_min=400, haversine_min=34) is False

def test_trust_accepts_plausible():
    assert rc.is_trustworthy(google_min=40, haversine_min=34) is True
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd backend && python -m pytest tests/test_route_cache.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'route_cache'`.

- [ ] **Step 3: Implement the pure helpers**

```python
# backend/route_cache.py
import os
import httpx

SUPABASE_URL = os.getenv("SUPABASE_URL", "https://pxpqcdfxogaajwstwdtk.supabase.co")

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
    """Reject implausible Google legs that would poison the cache.
    A real drive can't be faster than the straight-line floor, and >10x is absurd."""
    if google_min < max(1, int(haversine_min * 0.6)):
        return False
    if google_min > haversine_min * 10:
        return False
    return True
```

- [ ] **Step 4: Run to verify it passes**

Run: `cd backend && python -m pytest tests/test_route_cache.py -q`
Expected: PASS — 5 passed.

- [ ] **Step 5: Commit**

```bash
git add backend/route_cache.py backend/tests/test_route_cache.py
git commit -m "feat(cache): route_cache key normalization + trust sanity-bound (TDD)"
```

---

## Task 3: Cache read/write against Supabase REST

**Files:** Modify `backend/route_cache.py`; add tests to `backend/tests/test_route_cache.py`

- [ ] **Step 1: Write the failing test** (mock httpx so no network)

```python
def test_assemble_matrix_uses_cache_then_marks_misses(monkeypatch):
    # cache has only A→B; the rest are misses
    cached = {("A","B"): 12}
    def fake_get_many(keys, key):
        return {k: cached[k] for k in keys if k in cached}
    monkeypatch.setattr(rc, "get_cached", fake_get_many)
    locs = ["A","B","C"]
    hit, miss = rc.split_hits_misses(locs, service_key="x")
    assert hit[("A","B")] == 12
    assert ("A","C") in miss and ("B","A") in miss  # directional, self-pairs excluded
    assert ("A","A") not in miss
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd backend && python -m pytest tests/test_route_cache.py -q`
Expected: FAIL — `AttributeError: module 'route_cache' has no attribute 'split_hits_misses'`.

- [ ] **Step 3: Implement cache I/O**

```python
def _headers(key: str) -> dict:
    return {"apikey": key, "Authorization": f"Bearer {key}", "Content-Type": "application/json"}

def get_cached(pairs: list[tuple[str, str]], key: str) -> dict:
    """Fetch cached drive_minutes for the given directional key-pairs.
    Returns {(from_key,to_key): minutes}. Tolerates a missing table / errors by returning {}."""
    if not pairs:
        return {}
    or_terms = ",".join(f"and(from_key.eq.{f},to_key.eq.{t})" for f, t in pairs)
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

def put_cached(rows: list[dict], key: str) -> None:
    """Upsert cache rows: [{from_key,to_key,drive_minutes,drive_meters,source}]. Best-effort."""
    if not rows:
        return
    try:
        with httpx.Client(timeout=15) as c:
            c.post(
                f"{SUPABASE_URL}/rest/v1/route_cache",
                headers={**_headers(key), "Prefer": "resolution=merge-duplicates"},
                json=rows,
            )
    except Exception:
        pass  # cache write failures must never break optimization

def split_hits_misses(locations: list[str], service_key: str) -> tuple[dict, list[tuple[str, str]]]:
    """Return (cache hits {pair:minutes}, list of miss pairs) for all directional non-self pairs."""
    keys = [norm_key(l) for l in locations]
    pairs = [(keys[i], keys[j]) for i in range(len(keys)) for j in range(len(keys)) if i != j]
    hits = get_cached(pairs, service_key)
    misses = [p for p in pairs if p not in hits]
    return hits, misses
```

- [ ] **Step 4: Run to verify it passes**

Run: `cd backend && python -m pytest tests/test_route_cache.py -q`
Expected: PASS — all tests pass.

- [ ] **Step 5: Commit**

```bash
git add backend/route_cache.py backend/tests/test_route_cache.py
git commit -m "feat(cache): Supabase read/write + hit/miss split (best-effort, fail-open)"
```

---

## Task 4: Integrate the cache into `build_matrix_gmaps`

**Files:** Modify `backend/optimizer.py`

- [ ] **Step 1: Add a cache-aware matrix builder.** In `optimizer.py`, add `import route_cache` at the top and a new function that wraps the existing Google call so only misses are fetched and trusted results are written back:

```python
import route_cache

async def build_matrix_cached(locations: list[str], api_key: str, service_key: str) -> list[list[int]]:
    """Cache-first matrix: reuse cached legs, fetch only misses from Google (trust-checked),
    write trustworthy results back. Falls back to haversine for anything still missing."""
    keys = [route_cache.norm_key(l) for l in locations]
    hits, _misses = route_cache.split_hits_misses(locations, service_key)
    n = len(locations)
    matrix = [[0] * n for _ in range(n)]
    new_rows = []
    # Fetch a full Google matrix only if there are misses AND a key is available.
    gmatrix = None
    if _misses and api_key:
        gmatrix = await build_matrix_gmaps(locations, api_key)  # existing function
    for i in range(n):
        for j in range(n):
            if i == j:
                continue
            pair = (keys[i], keys[j])
            if pair in hits:
                matrix[i][j] = hits[pair]
                continue
            hav = km_to_minutes(haversine_km(*_parse_loc(locations[i]), *_parse_loc(locations[j])))
            if gmatrix is not None and route_cache.is_trustworthy(gmatrix[i][j], hav):
                matrix[i][j] = gmatrix[i][j]
                new_rows.append({"from_key": keys[i], "to_key": keys[j],
                                 "drive_minutes": gmatrix[i][j], "source": "google"})
            else:
                matrix[i][j] = hav
    route_cache.put_cached(new_rows, service_key)
    return matrix
```

- [ ] **Step 2: Use it from `optimize_routes`.** In `optimize_routes` (line 217), thread a `service_key` param and call `build_matrix_cached` when both keys are present:

Change the signature:
```python
async def optimize_routes(technicians: list, google_maps_api_key: Optional[str], service_key: str = "") -> list[dict]:
```
Replace the matrix selection block (lines 236–241):
```python
        if google_maps_api_key and service_key:
            matrix = await build_matrix_cached(locations, google_maps_api_key, service_key)
            mode = 'gmaps-cached'
        elif google_maps_api_key:
            matrix = await build_matrix_gmaps(locations, google_maps_api_key)
            mode = 'gmaps'
        else:
            matrix = build_matrix_local(locations)
            mode = 'local'
```

- [ ] **Step 3: Pass the service key from the endpoint.** In `backend/main.py` `/optimize` (line 149), pass the service key so the cache can be read/written:
```python
    result = await optimize_routes(
        req.technicians,
        google_maps_key if use_gmaps else None,
        service_key=os.getenv("SUPABASE_SERVICE_KEY", ""),
    )
```

- [ ] **Step 4: Verify existing optimizer tests still pass.**

Run: `cd backend && python -m pytest test_optimizer.py -q`
Expected: PASS (unchanged — `build_matrix_cached` is additive; existing paths intact).

- [ ] **Step 5: Commit**

```bash
git add backend/optimizer.py backend/main.py
git commit -m "feat(cache): cache-first matrix in optimizer (reuse legs, fetch+trust+store misses)"
```

---

## Task 5: Living-docs sync

**Files:** Modify `context/architecture.md`, `context/scheduling-rules.md`

- [ ] **Step 1:** In `context/architecture.md`, under the backend/optimizer section, add:

> **Drive-time cache (`route_cache`):** global table (drive times are tenant-independent), backend-only via service key (RLS denies all else). `backend/route_cache.py` normalizes keys (coords → 4 dp), reads cached legs, fetches only misses from Google (under the daily element cap), trust-checks them (reject < 0.6× or > 10× the haversine floor), and writes back. Optimizer uses `build_matrix_cached` (mode `gmaps-cached`); haversine remains the fallback. After warm-up most legs are cache hits → near-zero ongoing Google spend.

- [ ] **Step 2:** In `context/scheduling-rules.md`, under "Route Optimization Backend", add: "A global `route_cache` makes real-drive-time routing affordable — cached legs are reused; only new city/coord pairs hit Google (bounded by `GMAPS_DAILY_ELEMENT_LIMIT`)."

- [ ] **Step 3: Commit**

```bash
git add context/architecture.md context/scheduling-rules.md
git commit -m "docs(cache): document route_cache (global, backend-only, trust-bounded)"
```

---

## Verification (whole plan)

1. `cd backend && python -m pytest -q` → all tests pass (route_cache + optimizer).
2. Eran runs the `route_cache` migration → table exists with RLS on.
3. After backend deploy: `/health` still reports quota; an `/optimize` call returns `mode: "gmaps-cached"` when the key + service key are set; a second identical call performs **zero** Google fetches (all hits) — confirmed by `daily_elements_used` not increasing on the second call.
4. With the table absent or Supabase unreachable, `/optimize` still works (fails open to Google/haversine).

---

## What Plan B2+ will cover (separate plans)

- **B2:** authoritative `sequenceDay` + `markDayDirty` (debounced, epoch + version guards), window/break constraints in the TSP, overflow tray, `tasks.locked` honored as fixed nodes, `features.auto_sequence` flag.
- **B3:** weekly balance term (cross-tech fill-before-open), reactive gap-fill (cheapest-insertion), dry-run shadow compare + PureWater rollout.
