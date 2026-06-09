# Zones & Polygons — Design Spec

**Date:** 2026-06-09
**Workstream:** 1 of 4 (Zones & Polygons) — foundation before Scheduling engine, Roles/backoffice, UI
**Status:** Design — awaiting user review before implementation plan

---

## 1. Goal & Scope

Make zone definition and zone→tech matching **reliable, configurable per-tenant, and ready for any business type** — while keeping the build focused on what PureWater needs *now*.

PureWater runs `mode: zone` + `zone_match: city_list`. A future Client #2 (unknown) must slot in by **config, not a rewrite** — including a polygon-based client, a no-geo client, or a high-volume client. We build the seam and data model for all of it; we fully build the city-list path PureWater uses today and the polygon **authoring** tool, and we leave polygon **runtime matching** as a config-ready seam (light build) until a polygon client onboards.

**In scope:** per-tenant matching model, `resolveZone` seam, zone authoring (city batch + polygon draw), map-render reliability fix, canonical-city guard, bulk task import, tech zone exclusions, no-match UX with fix-it CTA, data integrity, tests.

**Out of scope (other workstreams):** intra-city / address-level route ordering, traffic, and the OR-Tools sequencing fixes → **Scheduling engine** workstream. Roles/backoffice and UI polish → their own workstreams.

---

## 2. Architecture — Two Axes + One Seam

The codebase already has an assignment-strategy axis. We reuse it and add one orthogonal sub-setting. **No duplicate concepts.**

| Axis | Field | Values | Status |
|---|---|---|---|
| Assignment strategy | `tenants.config.scheduling.mode` | `zone` / `open` / `radius` | Exists — [buildCandidates:4709](../index.html#L4709) |
| Zone boundary (only when `mode='zone'`) | `tenants.config.scheduling.zone_match` | `city_list` (default) / `polygon` | **New** |

Mapping of the real business cases:
- **No geo logic** → `mode: open` (already works, no zones enforced)
- **City-list zones (PureWater)** → `mode: zone` + `zone_match: city_list` (today's behavior)
- **Polygon zones (future)** → `mode: zone` + `zone_match: polygon` (runtime point-in-polygon)

**Backward-compatible by construction:** absent `mode` → `zone`; absent `zone_match` → `city_list` = exactly today's behavior. New tenants choose explicitly at onboarding (never silently assumed — same principle as far-to-near being PureWater-specific, not a global default).

### The seam: `resolveZone(city, lat, lon, tenantConfig) → { zoneId | null, matched, reason }`

A single pure function that every caller goes through (dispatch, bulk import, tech-zone checks). It centralizes what is today scattered across `isCityInTechZone` ([:4581](../index.html#L4581)) and `getCityZone` ([:4527](../index.html#L4527)).

```
resolveZone(city, lat, lon, conf):
  match = conf.scheduling.zone_match || 'city_list'
  if match == 'city_list':
      c = canonicalCity(city)
      zone = zones.find(z => z.cities.includes(c))
      return zone ? {zoneId: zone.id, matched: true}
                  : {zoneId: null, matched: false, reason: 'city_not_in_zone'}
  if match == 'polygon':
      if !(lat && lon): return {matched:false, reason:'not_geocoded'}
      zone = zones.find(z => (z.polygons||[]).some(p => pointInPolygon(lat, lon, p)))
      return zone ? {zoneId: zone.id, matched: true}
                  : {zoneId: null, matched: false, reason: 'outside_all_polygons'}
```

Existing `isCityInTechZone(tech, city, date)` is rewritten to call `resolveZone` and compare the result against the tech's rotation zone for that day. Polygons are **exclusive / non-overlapping** (enforced at draw time), so at most one zone ever matches — no tie-break needed.

---

## 3. Data Model & Migration

All changes **additive and reversible**.

1. **`tenants.config.scheduling.zone_match`** — `'city_list' | 'polygon'`, tenant-level. JSON only; no DDL. Set per-tenant at onboarding. PureWater = `city_list`.

2. **`zones.polygons`** (JSONB) — array of polygons, each an array of `{lat, lng}`. Replaces the single `zones.polygon`.
   - Migration: `UPDATE zones SET polygons = jsonb_build_array(polygon) WHERE polygon IS NOT NULL;`
   - Keep `polygon` column for one release as a fallback, then drop.
   - Update both save paths: `dbUpsert('zones', …)` ([:2910](../index.html#L2910)) and the wizard insert ([:3465](../index.html#L3465), which currently writes no polygon at all), and the load mapper ([:2456](../index.html#L2456)).

3. **`technicians.blocked_zones`** (text[] of zone ids) — alongside existing `blocked_cities`. Default `'{}'`.

4. **DB constraints (integrity, cheap):** `CHECK` that `zone_match` ∈ allowed set is enforced app-side (config is free-form JSON); add a `NOT NULL DEFAULT '{}'` on `blocked_zones`. No unique constraint changes here.

---

## 4. Component — Zone Authoring + Map Reliability *(PureWater now)*

### 4a. New empty zone → two ways to fill it
`addZone()` ([:6310](../index.html#L6310)) already creates an empty zone. The zone card gets two clear actions:
- **➕ הוסף ערים** — type/paste cities (comma/newline), each passed through the **canonical-city guard** (§5) before being added. Replaces raw `addCities` ([:6324](../index.html#L6324)).
- **🗺️ צייר על מפה** — open the draw modal, draw a polygon, cities inside are auto-captured into `cities[]`.

For `city_list` tenants the polygon is purely an **authoring aid** that fills `cities[]` (and is stored in `polygons[]` for reference). For `polygon` tenants the same geometry is the runtime boundary.

### 4b. Map-render fix — root cause, not a band-aid
**Cause (verified):** Leaflet + Leaflet.draw load via plain synchronous `<script>` from jsDelivr ([:19, :22](../index.html#L19)). When that CDN fetch fails (network/blocked/slow), `window.L` is never defined, the guard at [:7186](../index.html#L7186) shows *"ספריית מפות לא נטענה"*, and it stays broken for the whole session — the "recurring" symptom.

**Fix — self-host (primary):** vendor `leaflet@1.9.4` (leaflet.js, leaflet.css, and its `images/` marker/sprite assets) and `leaflet-draw@1.0.4` (js, css, and the draw toolbar sprite images) into `vendor/` in the repo; reference via relative paths. GitHub Pages serves them; no third-party fetch can fail. Versions stay pinned (honors the CDN-pinning rule in architecture.md).

**Fix — lazy fallback (belt & suspenders):** if `window.L` is still missing when the modal opens, dynamically inject the script, `await` load (with a visible spinner) and one retry, before showing any error. So even a vendored-asset miss self-heals instead of dead-ending.

### 4c. Editable / redrawable / bigger view
Edit + delete are already wired ([:7216–7234](../index.html#L7216)); redraw clears prior layers cleanly. Enlarge the modal map (`mo-zone-draw` is 720px×400px today, [:1722](../index.html#L1722)) and add a fullscreen toggle for precise drawing.

### 4d. Reliable save
Saves stay on WAL-backed `dbUpsert` ([:2799](../index.html#L2799) — writes WAL first, clears on success, retains for replay on failure). `confirmZoneDraw` writes `polygons[]` + `cities[]`, awaited, with a success/fail toast. No fire-and-forget.

---

## 5. Component — Canonical-City Guard *(the קרית שמונה / קריית שמונה problem)*

`normalizeCity` today is alias-lookup only ([:4526](../index.html#L4526)) — it cannot catch near-duplicates that aren't in `CITY_ALIASES`. New `canonicalCity(input)`:

1. **Rule-based normalization** — collapse known Hebrew spelling variants (e.g. `קריית→קרית`, double-yud forms), trim, plus the existing `CITY_ALIASES`.
2. **Exact match** against the known dictionary `CITY_COORDS_JS` (the canonical city set, ~255 keys) → accept.
3. **Fuzzy fallback** — if no exact match, compute Levenshtein distance to dictionary keys; if the closest is within a small threshold (≤2, length-aware), prompt *"האם התכוונת ל'קרית שמונה'?"* before adding. User confirms or keeps their spelling.
4. **Store only the canonical form** — so a city can never live in two zones under two spellings, and matching never silently fails.

Also fix `isCityBlocked` ([:4565](../index.html#L4565)) to compare on `canonicalCity` (today it compares raw strings, so a blocked city under a variant spelling wouldn't match).

---

## 6. Component — Bulk Task Import *(the "200 tasks next week" scenario)*

A coordinator pastes/uploads rows of `(street, city, [category])`. For each row:
1. `canonicalCity(city)`.
2. `resolveZone` — `city_list`: city must be in some zone. `polygon`: geocode `(street, city)` via the existing `/geocode` endpoint (throttled to respect Google quota), then point-in-polygon.
3. **Matched** rows → created as `status: pending` tasks, ready for the scheduling engine.
4. **Unmatched** rows → a **review tray** listing each with its reason and a one-click fix CTA (§8): "add city to a zone" / "open the polygon to redraw". Re-running resolves the fixed rows.

Writes go through `dbInsert`/`dbUpsert` so partial failures are caught and retried; nothing is silently dropped.

---

## 7. Component — Technician Zone Exclusions

A tech must never receive a call in a zone they're excluded from. Add `technicians.blocked_zones` (zone ids). The candidate builder (`_candidatesZone`, [:4741](../index.html#L4741)) filters: skip a tech if the resolved zone is in their `blocked_zones` (mirrors the existing `blocked_cities` check at [:4752](../index.html#L4752)). Surfaced in the tech edit UI as a multi-select of zones, alongside the existing blocked-cities field.

---

## 8. Component — No-Match UX (block + prompt + fix-it CTA)

When `resolveZone` returns `matched: false`, dispatch shows the block at the existing `showNoResult` hook ([:5166](../index.html#L5166)), upgraded to be **mode-aware** and **actionable**:
- `city_list` / `city_not_in_zone` → *"העיר '{city}' אינה משויכת לאף אזור."* + button **"➕ שייך עיר לאזור"** → opens the zones page focused on adding that city.
- `polygon` / `outside_all_polygons` → *"הכתובת מחוץ לאזור השירות."* + button **"🗺️ ערוך אזור על המפה"** → opens the draw modal to extend a polygon.
- `polygon` / `not_geocoded` → *"לא ניתן לאתר את הכתובת — בדוק רחוב ועיר."*

Intake is **blocked** (never silently misrouted), but the coordinator is one click from fixing it. Same tray + CTA used by bulk import (§6).

---

## 9. Data Integrity & Reliability

- All zone/tech writes via WAL-backed `dbUpsert`/`dbInsert`, **awaited**, with success/fail toasts.
- Migration additive + reversible; `polygon` retained one release before drop.
- `blocked_zones` defaults to empty array (no migration risk to existing techs).
- Polygon non-overlap enforced at draw time (warn/block on intersection with another zone's polygon) so runtime resolution is unambiguous.

---

## 10. Testing

**Unit (`resolveZone` + helpers):**
- city in a city-list zone → matched; city absent → `city_not_in_zone`
- point inside a polygon → matched; outside all → `outside_all_polygons`; missing coords → `not_geocoded`
- `canonicalCity`: variant spelling collapses to canonical; near-duplicate triggers "did you mean"
- `blocked_zones` excludes the tech; non-overlap guarantees single match

**Manual QA checklist:**
- Draw a zone on the map (verify map renders reliably after a forced CDN failure / offline) → cities captured → saved → reload persists
- Add a city with a near-duplicate spelling → prompt appears → canonical stored
- Bulk import a batch with some unmatched rows → tray + CTA resolve them
- Dispatch a city outside any zone → block + correct CTA → fix → re-dispatch succeeds

---

## 11. Build Now vs Config-Ready Seam

**Fully built now (PureWater + foundation):** two-axis config + `resolveZone`, city-list path, polygon **authoring** (draw → capture cities), map-reliability fix, canonical-city guard, bulk import, tech exclusions, no-match CTA, integrity, tests.

**Seam built, runtime light until a polygon client onboards:** `zone_match: polygon` runtime point-in-polygon + mandatory geocoding. The data model (`polygons[]`), `resolveZone` polygon branch, and `_pointInPolygon` ([:7260](../index.html#L7260)) all exist; we wire and test the branch but don't force it on any current tenant.

---

## 12. Open Decisions (resolved)

- Match model → polygon first-class, per-tenant; city-list retained. ✔
- No-match → block + prompt + fix-it CTA. ✔
- Polygon overlap → none (exclusive); a zone may be multiple disjoint polygons. ✔
- Map fix → self-host (primary) + lazy fallback. ✔
- Focus → PureWater now; Client #2 via config. ✔
