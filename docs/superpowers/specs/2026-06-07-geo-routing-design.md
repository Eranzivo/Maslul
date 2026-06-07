# Geo-Intelligence Layer — Design Spec

**Date:** 2026-06-07  
**Status:** Approved — implementing  
**Scope:** Street-level routing accuracy + polygon zone support for all tenants

---

## Problem

The routing optimizer currently uses city centers as locations (e.g., all tasks in "תל אביב" collapse to one point). This produces suboptimal routes when a technician has multiple jobs in the same city, because the distance matrix cannot distinguish between "הרצל 15" and "ויצמן 30".

---

## Solution: Two-Layer Geo Architecture

### Layer 1 — Address-level Distance Matrix (immediate)
The `/optimize` request already sends `address: t.street`. The backend already has an `address` field in the `Task` model but ignores it. Changing `optimizer.py` to use `"{street}, {city}"` when available immediately improves route accuracy with zero new DB columns or API calls — Google Distance Matrix geocodes the full address string server-side.

### Layer 2 — Cached Geocoding (Phase 2)
A `/geocode` backend endpoint accepts `{street, city}` and returns `{lat, lon}` using the Google Geocoding API (same key as Distance Matrix, same $200/month free credit). The frontend caches lat/lon in `tasks.lat` / `tasks.lon` after the first geocode. Subsequent optimize calls pass `"{lat},{lon}"` directly — no re-geocoding needed.

---

## Data Model

### `tasks` table (new columns)
| Column | Type | Notes |
|---|---|---|
| `lat` | `DOUBLE PRECISION` | Geocoded latitude. NULL = not yet geocoded, use city fallback |
| `lon` | `DOUBLE PRECISION` | Geocoded longitude |
| `geocoded_at` | `TIMESTAMPTZ` | When geocoded. Audit only — not used in logic |

### `zones` table (new column)
| Column | Type | Notes |
|---|---|---|
| `polygon` | `JSONB` | Array of `{lat, lng}` vertices drawn by client. NULL = city-list zone (no polygon) |

---

## API Call Budget

| User action | API calls | Cost |
|---|---|---|
| "מצא שיבוץ" (find slot) | **0** — pure JS engine | Free |
| "שבץ" (confirm assign) | **0 or 1** Geocoding call | ~$0.005 per new address; 0 if cached |
| "🔀 מסלול מיטבי" (optimize) | **1** Distance Matrix call | ~$0.002 per tech per run |

Geocoding fires **once per unique address**, then cached in `tasks.lat/lon` forever.

---

## Backend Changes

### `optimizer.py`
- Add `_parse_loc(loc)` — parses `"lat,lon"` string or falls back to `get_coords(city_name)`
- Add `_task_location(t)` — returns `"{lat},{lon}"` if geocoded, else `"{street}, {city}"`, else `city`
- Update `build_matrix_local()` — use `_parse_loc()` instead of `get_coords()` directly
- Update `optimize_routes()` — use `_task_location(t)` when building the locations array

### `main.py`
- `Task` model: add `lat: Optional[float] = None`, `lon: Optional[float] = None`
- New endpoint: `POST /geocode` — accepts `{street, city}`, calls Google Geocoding API, returns `{lat, lon}`

---

## Frontend Changes (`index.html`)

- Add `_pendingGeocode = null` and `_geocodeCache = {}` module-level vars
- Add `async _triggerGeocode()` — fires when `s-street` loses focus (both city + street filled + `geocoding_enabled` flag)
- Task load mapping: add `lat`, `lon`, `geocodedAt` from Supabase row
- Zones load mapping: add `polygon` from Supabase row
- `saveTaskToSupabase()`: include `lat`, `lon`, `geocoded_at` in row
- `confirmAssign()`: include `_pendingGeocode` coords in new task object
- `optimizeDay()`: include `lat`, `lon` in task payload to backend
- `clearDispatch()`: reset `_pendingGeocode = null`

---

## Multi-Tenant Architecture

All geo features are controlled by `tenants.config.features`:

| Flag | Default | Meaning |
|---|---|---|
| `geocoding_enabled` | `false` | Activates Geocoding API call at dispatch |

Routing accuracy improvement (address-level DM) applies to all tenants automatically because it only requires `t.address` being non-null — no flag needed.

---

## General vs Israel-Specific

| Logic | Scope |
|---|---|
| Address-level Distance Matrix | **General** — all tenants benefit automatically |
| Geocoding API + `lat/lon` caching | **General** — per-tenant flag (`geocoding_enabled`) |
| `far_to_near` route strategy | **Israel-specific** — controlled by `scheduling.route_strategy` |
| Zone rotation (Sun/Mon/Tue/Wed/Thu) | **Israel-specific** — PureWater config only |
| Polygon draw UI (already exists) | **General** — any tenant can use it |

---

## Rollout Plan

1. DB migration — add columns (backward-compatible, all nullable)
2. Backend deploy — new `/geocode` endpoint + optimizer improvements
3. Frontend deploy — geocoding function + payload updates
4. Enable per-tenant — set `geocoding_enabled: true` for Israel when ready
