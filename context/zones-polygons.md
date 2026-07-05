# Zones & Polygon Context — Maslul

## What Zones Are

A zone is a named geographic area with a list of cities. Technicians are assigned to zones by day-of-week rotation (`technicians.rotation` JSONB). The scheduling engine only offers a tech for a task if the task's city is in that tech's zone for that day.

---

## Zone Data Model

```
zones.id        — UUID
zones.tenant_id — multi-tenant isolation
zones.name      — display name (e.g. "אזור צפון")
zones.cities    — text[] — city names (normalized)
zones.polygon   — JSONB — array of {lat, lng} vertices (nullable — only set if drawn on map)
```

**City names are normalized** via `normalizeCity()` before storage and lookup. The `CITY_ALIASES` map handles Hebrew spelling variants (e.g., `קריית גת` → `קרית גת`).

### canonicalCity guard (Task input / city add)

`canonicalCity(input)` is a higher-level guard used when persisting a city entered by a user (task form or zone city-add). It returns `{city, suggestion}`:

1. Calls `normalizeCity()` (alias lookup + trim).
2. Applies a rule-based collapse: `קריית → קרית` for any city name.
3. Looks up the result in `CITY_COORDS_JS`. If found → `{city: normalized, suggestion: null}`.
4. If not found, runs Levenshtein against all known city names. If the closest match is within 1–2 characters → `{city: input_normalized, suggestion: closest}`, so the UI can prompt "האם התכוונת ל…?".
5. If no close match → `{city: input_normalized, suggestion: null}` — city is stored as typed (unknown city, no crash).

---

## Zone Assignment Logic — the `resolveZone` seam

All zone matching goes through **one** function:

```javascript
resolveZone(city, lat, lon, conf, zonesList) → { zoneId|null, matched, reason }
```

It switches on the per-tenant **`tenants.config.scheduling.zone_match`** axis (separate from `scheduling.mode`):

| `zone_match` | How it matches | `reason` when no match |
|---|---|---|
| `city_list` (default) | canonical city is in a zone's `cities[]` | `city_not_in_zone` |
| `polygon` | the geocoded point falls inside a zone's `polygons[]` (`_pointInPolygon`) | `outside_all_polygons`, or `not_geocoded` if no lat/lon |

`city_list` matching **canonicalizes both sides** — the input city *and* each stored zone city run through `canonicalCity` — so a zone that stored a variant spelling (e.g. `קריית גת`) still matches a canonical input (`קרית גת`). This fixed a latent bug where only the input was normalized.

The live helpers `getCityZone(city)` and `isCityInTechZone(tech, city, dateStr)` both **delegate to `resolveZone`** (passing the globals `tenantConfig`, `zones`). PureWater is `city_list`, so behavior is unchanged but more robust. Polygon-mode callers pass real coordinates; until geocoding is wired for a polygon tenant, `null` coords correctly yield `not_geocoded`.

`resolveZone` is pure and lives inside the `// <zone-logic>` markers, covered by `tests/zones.test.js` (including tenant-separation cases proving two tenants with different `zone_match` resolve independently).

**Mode-aware UI:** the entire zone surface (settings **אזורים** tab, tech rotation grid, city-in-zone gate, zone error copy, batch "תקן אזורים" CTA) is gated by `appUsesZones()` / `body[data-zone-mode]` — hidden for `open`/`radius` tenants. See `context/architecture.md` → Mode-Aware UI.

---

## Polygon Drawing Flow

1. Admin clicks "🗺️ צייר" on a zone card → `openZoneDraw(zoneId)`
2. Modal opens after 80ms `setTimeout` (ensures `overflow-y:auto` parent has laid out before Leaflet initializes)
3. Leaflet map renders on OpenStreetMap tiles; existing zone cities shown as blue dots
4. User draws a polygon with the Leaflet.Draw polygon tool
5. `L.Draw.Event.CREATED` fires → `_drawnPolygon = latlngs`; `_updateDrawStatus()` shows city count
6. "✓ הוסף ערים לאזור" button calls `confirmZoneDraw()`
7. **WYSIWYG multi-polygon editor** (rebuilt twice 2026-07-05; final after Eran's live QA):
   - The zone's SAVED rings load INTO the Leaflet.draw edit `FeatureGroup` — every ring
     (old or new) is **vertex-editable and deletable** with the toolbar. Drawing ADDS a ring.
   - **ALL brain places** render as small grey dots (the zone's own cities bigger, indigo);
     dots inside any ring turn **green live** on every draw/edit/delete (`_refreshZoneDrawCapture`),
     and the status line recounts (`N פוליגונים · נתפסו X ערים · Y חדשות`). The coordinator
     literally sees what is and isn't captured before confirming.
   - Detection universe = `_geoPlaceEntries()`: `GEO_BRAIN.places` (500+, grows with every
     client); static `CITY_COORDS_JS` only as offline fallback. (The old static-only scan was
     the "didn't capture all cities" root cause.)
   - `confirmZoneDraw()` saves **exactly what's on the map**: `zone.polygons = all rings`
     (no append/replace prompts); cities added with canonical dedup (`cityMatchKey`) — cities
     are only ever ADDED, ring deletion never auto-removes them; an empty map offers polygon
     removal; a sub-city ring capturing no city-centers saves after an explicit confirm.
     `zone.polygon = polygons[0]` stays as the legacy mirror; `resolveZone` matches ANY ring.

**`invalidateSize()` is called at 200ms and 600ms** after map init to handle container layout settling. The draw modal is enlarged (`min(96vw,1000px)` box, `min(70vh,620px)` map) for precise drawing.

**Manual city-add guard:** typing/pasting cities (`addCities()`) runs each through `canonicalCity()` — if the input isn't an exact known city but is a near-duplicate, it prompts *"האם התכוונת ל…?"* before storing the canonical form (prevents קרית/קריית duplicates).

---

## Geo brain in the frontend (one source of truth — 2026-07-05)

`GEO_BRAIN` (`{places: {key:[lat,lon]}, aliases: {variant:key}}`) is loaded once per session
from **`geo_places` + `place_aliases`** (read-only RLS SELECT for authenticated; public
geography only, PII-free) via `loadGeoBrain()` — fire-and-forget after login, lazy-retried in
`openZoneDraw`. **FAIL-OPEN:** if the fetch fails (or the policy isn't applied), every consumer
falls back to the static lists — exactly the old behavior.

**The matching seam is `cityMatchKey(name, brain)`** (in `<zone-logic>`, tested): legacy
alias + קריית collapse (`canonicalCity`) → `normalizePlaceKeyJS` (gershayim/hyphen noise) →
brain alias → canonical key. Mirrors Python `_match_key` (batch_schedule) exactly; both are
asserted against the same golden fixture `tests/fixtures/geo-cases.json` (JS harness + pytest)
so ק"ש / קרית שמונה / קריית שמונה resolve identically everywhere — drift = failing test.
Consumers: `resolveZone` city_list matching (both sides), `_cityDistKm` → `geoCityCoords()`
(brain-first coords — this also sharpens far→near ordering for cities the static list lacks),
polygon detection, zone-draw dots.

## CITY_COORDS_JS (offline fallback only)

`CITY_COORDS_JS` (~255 cities) remains in `index.html` strictly as the offline fallback when
the brain isn't loaded. `outputs/migration-geo-superset_2026-07-05.sql` backfills the 83
static-only entries into `geo_places` so the brain is a strict superset. Same role for
`cities.py` on the backend (via `geo_resolver`). **Never add a city to the static lists —
add it to `geo_places`.**

---

## Future: Polygon-Point Zone Assignment

**Not yet implemented.** Infrastructure is ready:
- `zones.polygon` column exists and is populated after drawing
- Tasks have `lat`/`lon` after geocoding
- `_pointInPolygon(lat, lon, polygon)` function already exists in `index.html`

When needed: modify `isCityInTechZone` to accept lat/lon, check polygon containment if both task coords and zone polygon exist, fall back to city-list otherwise. This enables sub-city zone splits (e.g., north Beer Sheva vs south Beer Sheva) without listing every neighborhood.

---

## PureWater Zone Setup (Israel)

9 zones covering Israel, 3 technicians, day-of-week rotation. **The authoritative rotation table lives in `context/clients/purewater.md`** (single source — keep one copy only). Re-link SQL if zones are ever re-created: `outputs/migration-purewater-rotation_2026-06-11.sql`. City lists: `outputs/migration-purewater-zone-cities_2026-06-06.sql`

---

## Zone Management UI

- `page-zones` — lists all zones with city tags
- Each zone card has: rename input, city tags (with × remove), "⊕ הוסף עיר" button, "🗺️ צייר" button
- Adding a city: `openAddCityModal(zoneId)` → free-text input with Israeli cities datalist → `saveZoneToSupabase(zone)`
- Deleting a city: `removeCity(zoneId, cityIndex)` → splice + save
- Zone save is **per-zone queued** (`_zoneSaveQueues`) — rapid edits serialize, no race conditions

---

## Dispatch: Zone Enforcement

Zone enforcement happens **in the engine** (`buildCandidates` → `_candidatesZone`), not in the city input field. The city input is a free-text field with datalist suggestions. An invalid city (not in any zone) will simply find no candidates when `zone_strict = true`.

`mode = 'zone'` (Israel default): only techs whose rotation zone contains the task city are offered.
`mode = 'open'`: any tech, any city — no zone check.
`mode = 'radius'`: city within X km of tech's base.

### No-Match Blocked Message (mode-aware)

When `buildCandidates` returns an empty list, `findBestSlot` calls `resolveZone(city, lat, lon, tenantConfig, zones)` to determine *why* no zone matched, then calls `showNoResult(city, reason)` which renders a mode-aware amber alert in `#d-alert`:

| `reason` | Message shown | CTA button |
|---|---|---|
| `outside_all_polygons` | "הכתובת מחוץ לאזור השירות." | "🗺️ ערוך אזור על המפה" → `goPage('zones')` |
| `not_geocoded` | "לא ניתן לאתר את הכתובת — בדוק רחוב ועיר." | none |
| `city_not_in_zone` (or undefined) | "העיר '…' אינה משויכת לאף אזור עם טכנאי זמין." | "➕ שייך עיר לאזור" → `goPage('zones')` |

Coordinates passed to `resolveZone` come from `_pendingGeocode` (set by `_triggerGeocode()` when the dispatcher form is submitted), or `null` if geocoding hasn't run yet.

### Per-Technician Zone Exclusions (`blockedZones`)

Each technician has a `blockedZones` field (array of zone IDs, stored in `technicians.blocked_zones` TEXT[] in Supabase). If a tech's rotation zone for a given day is in their `blockedZones`, `_candidatesZone` skips them for that date regardless of city match.

- Set via the **"אזורים חסומים"** multi-select in the tech edit/add drawer (`ti-blocked-zones`).
- The multi-select is populated with all zones when the drawer opens (both new-tech and edit-tech paths).
- On save, `data.blockedZones` is built from selected options and merged into the tech object via `Object.assign` (edit) or spread (new), then persisted by `saveTechToSupabase`.
