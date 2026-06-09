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

## Zone Assignment Logic (current)

Zone matching is **city-list based**:

```javascript
function isCityInTechZone(tech, city, dateStr) {
  const zid = getTechZoneId(tech, dateStr); // from tech.rotation[dayOfWeek]
  const z = zones.find(x => x.id === zid);
  return z ? z.cities.includes(normalizeCity(city)) : false;
}
```

The polygon (`zones.polygon`) is **not used** for zone assignment — it exists as stored geometry for future point-in-polygon matching and for visual reference. All current routing uses city-list only.

---

## Polygon Drawing Flow

1. Admin clicks "🗺️ צייר" on a zone card → `openZoneDraw(zoneId)`
2. Modal opens after 80ms `setTimeout` (ensures `overflow-y:auto` parent has laid out before Leaflet initializes)
3. Leaflet map renders on OpenStreetMap tiles; existing zone cities shown as blue dots
4. User draws a polygon with the Leaflet.Draw polygon tool
5. `L.Draw.Event.CREATED` fires → `_drawnPolygon = latlngs`; `_updateDrawStatus()` shows city count
6. "✓ הוסף ערים לאזור" button calls `confirmZoneDraw()`
7. `confirmZoneDraw()`:
   - Runs `_detectCitiesInPolygon()` — ray-casting point-in-polygon for each of the ~255 known cities
   - Adds detected cities to `zone.cities` (no duplicates)
   - Sets `zone.polygon = _drawnPolygon.map(p => ({lat: p.lat, lng: p.lng}))` — serialized to plain objects
   - Calls `saveZoneToSupabase(zone)` — saves both `cities` and `polygon`

**`invalidateSize()` is called at 200ms and 600ms** after map init to handle container layout settling.

---

## CITY_COORDS_JS

`CITY_COORDS_JS` is a JS object in `index.html` with ~255 Israeli cities mapped to `[lat, lon]` arrays:
```javascript
const CITY_COORDS_JS = { 'תל אביב': [32.0853, 34.7818], ... };
```

Used for:
1. Polygon draw — detect which cities fall inside drawn polygon
2. Haversine fallback in the optimizer when no geocoded lat/lon exists
3. Zone city dots on the draw map

Separate from `cities.py` (backend), which has a similar list for the Python optimizer.

---

## Future: Polygon-Point Zone Assignment

**Not yet implemented.** Infrastructure is ready:
- `zones.polygon` column exists and is populated after drawing
- Tasks have `lat`/`lon` after geocoding
- `_pointInPolygon(lat, lon, polygon)` function already exists in `index.html`

When needed: modify `isCityInTechZone` to accept lat/lon, check polygon containment if both task coords and zone polygon exist, fall back to city-list otherwise. This enables sub-city zone splits (e.g., north Beer Sheva vs south Beer Sheva) without listing every neighborhood.

---

## PureWater Zone Setup (Israel)

9 zones covering Israel, 3 technicians, day-of-week rotation:

| Day | אלירן | בני | מיכאל |
|---|---|---|---|
| Sun | שפלה | שרון | ירושלים |
| Mon | ירושלים | שפלה | שרון |
| Tue | שרון | ירושלים | שפלה |
| Wed | נגב | מרכז | דן |
| Thu | דן | נגב | מרכז |

Setup SQL: `outputs/migration-purewater-zone-cities_2026-06-06.sql`

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
