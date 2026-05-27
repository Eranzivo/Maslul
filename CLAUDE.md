# Maslul — Claude Code Context

## Working Rule
**Before every task — read all files in `context/` first:**
- `context/business.md` — what the product is, who it's for, the goal
- `context/architecture.md` — tech stack, file map, hard rules, gotchas
- `context/scheduling-rules.md` — the core scheduling logic (do not break)
- `context/client-israel.md` — current pilot client details and constraints

Never start coding without reading context first.

**New entity / new table rule:** Before adding any new Supabase table or entity, run every step in `context/new-entity-checklist.md`. All 8 steps are required. Do not ship without completing the checklist.

**Outputs rule:** Every command or generated artifact (summaries, reports, plans, drafts) must be saved to `outputs/[task-name]_[YYYY-MM-DD].md`. Never save in a random location.

**Connections:** See `connections/registry.json` for all external services. Secrets live only in `.env` (root) — never in `context/`, `connections/`, or `commands/`.

---

## What This Is
Hebrew-first SaaS scheduling engine for Israeli SMBs with field workers.
Deployed as a single HTML file: https://eranzivo.github.io/Maslul/

## Tech Stack (Current)
- **Frontend:** Single `index.html` — all JS and CSS inline, no build step
- **Backend (DB):** Supabase (PostgreSQL + Auth + RLS) — direct from browser
- **Backend (Optimizer):** FastAPI + OR-Tools in `backend/` — deployed to Railway
- **Hosting:** GitHub Pages (static HTML), Railway (FastAPI)
- **Font:** Heebo (Google Fonts)

## Tech Stack (Roadmap)
- **Frontend:** Modular ES modules, Vercel (when 2+ paying clients or 2nd developer)
- **Keep vanilla JS** — no React/Vue/TypeScript

## Backend — FastAPI Optimizer (`backend/`)
- `backend/main.py` — FastAPI app, `/optimize` POST endpoint, `/health` GET
- `backend/optimizer.py` — OR-Tools TSP solver with time windows; haversine fallback when no Google Maps key
- `backend/cities.py` — Hebrew city name → (lat, lon) lookup; ~50 Israeli cities; unknown city logs warning + falls back to Tel Aviv
- `backend/test_optimizer.py` — local smoke test (no pytest yet — see backlog)
- `backend/requirements.txt` — fastapi, uvicorn, ortools==9.10.4067, httpx, python-dotenv
- **Known gap:** No pytest suite yet. `test_optimizer.py` is a manual run script only.
- **Known gap:** `cities.py` has ~50 cities — any city not listed falls back silently to Tel Aviv coords (logs warning since 2026-05-22 fix).

## Architecture Principles
- Multi-tenant: every table row has `tenant_id`, enforced by Supabase RLS
- Adding a client: 1 SQL insert into `tenants` + 1 Supabase Auth user + 1 insert into `users`
- `currentTenantId` set at login via `loadTenantFromUser()`, used in every query
- localStorage is fallback only — Supabase is source of truth
- `DEMO_MODE: true` in CONFIG bypasses auth and Supabase entirely
- Single HTML file until 2+ paying clients
- **WAL (Write-Ahead Log):** `_walWrite` saves every payload to localStorage BEFORE Supabase call. `_walClear` removes on success. `_replayWAL` re-sends on next login. Key: `ml_wal_v1`.
- **All writes go through `dbUpsert` / `dbInsert`** — never raw `sb.from().insert()` directly. These handle WAL, save-counter, and error toast.
- **Schema validator:** `_validateSchema()` runs after every `loadFromSupabase()`, checks null/empty on required fields, sends to Sentry.
- **Connection monitor:** `_checkConnection()` pings Supabase every 60s. Distinguishes network failure (catch) from auth expiry (401/403 → calls showLogin).

## Safety Stack (added May 2026)
| Layer | What it does |
|---|---|
| WAL (`ml_wal_v1`) | Stores failed saves in localStorage, replays on next login |
| `dbUpsert` try/catch | Prevents `_savesInFlight` permanent leak if client throws |
| Schema validator | Post-load null/type checks on all entities, Sentry on drift |
| Audit log (DB triggers) | Every INSERT/UPDATE/DELETE written to `audit_log` table in Supabase |
| Connection monitor | 60s ping, red banner on network loss, re-login prompt on auth expiry |

## Terminology / Labels System
All user-visible entity names come from `tenantLabels` (not hardcoded).
Call `L('key')` anywhere in JS to get the current tenant's label.

Default keys and Hebrew values:
| Key | Default | Example override |
|---|---|---|
| `worker` | טכנאי | שליח / מנקה |
| `workers` | טכנאים | שליחים / מנקים |
| `task` | קריאה | משלוח / עבודה |
| `tasks` | קריאות | משלוחים / עבודות |
| `zone` | אזור | מסלול |
| `zones` | אזורים | מסלולים |
| `zones_title` | אזורי פעילות | מסלולי פעילות |
| `dispatch` | שיבוץ קריאה | משלוח חדש |

Labels are stored in `tenants.config.labels` in Supabase and loaded at login.
Static HTML elements use `data-label="key"` and are updated by `applyLabels()` on init.

## Demo Mode
Set `CONFIG.DEMO_MODE = true` and `CONFIG.DEMO_TYPE` to one of:
- `'general'` — field service (technicians, zones, service calls)
- `'cleaning'` — cleaning company (cleaners, areas, jobs)
- `'delivery'` — courier (drivers, routes, deliveries)

Also triggered by `?demo=1` (general), `?demo=cleaning`, `?demo=delivery` URL params.

Demo mode: bypasses auth, loads `DEMO_PRESETS[type]`, shows purple banner,
blocks all localStorage writes and Supabase calls (null `currentTenantId` prevents writes).

## Supabase Tables
See `schema.sql` for complete DDL, RLS policies, and onboarding SQL.

| Table | Key columns |
|---|---|
| `tenants` | `id`, `name`, `plan`, `config` (JSONB) |
| `users` | `id`, `tenant_id`, `role`, `name` |
| `technicians` | `id`, `tenant_id`, `name`, `phone`, `base_city`, `color`, `min_daily`, `max_daily`, `start_time`, `end_time`, `blocked_cities` (array), `skills` (array), `cat_limits` (JSONB), `rotation` (JSONB) |
| `tasks` | `id`, `tenant_id`, `assign_id`, `client_name`, `client_phone`, `city`, `street`, `category_id`, `category_name`, `technician_id`, `status`, `scheduled_date`, `scheduled_time`, `notes`, `cancelled_at`, `checklist_done` (JSONB) |
| `zones` | `id`, `tenant_id`, `name`, `cities` (array) |
| `categories` | `id`, `tenant_id`, `name`, `duration_minutes` |
| `packages` | `id`, `tenant_id`, `name`, `items` (JSONB) |
| `day_offs` | `id`, `tenant_id`, `technician_id`, `date`, `type`, `from_time`, `to_time`, `reason` |
| `clients` | `id`, `tenant_id`, `name`, `phone`, `email`, `city`, `address`, `notes`, `archived` |
| `audit_log` | `id`, `created_at`, `tenant_id`, `table_name`, `operation`, `record_id`, `old_data` (JSONB), `new_data` (JSONB) |

### `tenants.config` JSONB shape
```json
{
  "labels": { "worker": "טכנאי", "workers": "טכנאים", "task": "קריאה", "tasks": "קריאות",
              "zone": "אזור", "zones": "אזורים", "dispatch": "שיבוץ קריאה" },
  "defaults": { "regular_job_minutes": 30, "package_job_minutes": 45,
                "arrival_window_hours": 3, "max_daily_jobs": 9,
                "lookahead_days": 30, "monthly_volume": 300,
                "work_start": "07:00", "work_end": "18:00" },
  "features": { "whatsapp_enabled": true, "demo_mode": false,
                "google_maps_enabled": false, "odoo_integration": false }
}
```

## Supabase Write Pattern
All entities use the unified write layer — never raw Supabase calls:
```js
// Update existing:
await dbUpsert('table', { id: entity._dbId, ...fields });
// Insert new:
const data = await dbInsert('table', { ...fields });
entity._dbId = data.id;
```
`dbUpsert` and `dbInsert` handle: WAL write-before, save counter, error toast, Sentry logging.

For technicians: after insert, `tech.id` is promoted to the Supabase UUID and all
in-memory tasks referencing the old local integer id are updated.

## ID Strategy
- `id` = in-memory identity (integer for locally-created, UUID after Supabase insert)
- `_dbId` = Supabase row UUID, used for update/delete
- Technicians from Supabase: `id === _dbId === UUID`

## Business Logic Invariants (do not change)
- Zone-strict scheduling: tech only receives jobs in their rotation zone for that day
- Far-to-near route: `getCityIndexInZone()` orders cities within a zone
- Fill-existing-days-first: `fillScore = existingInZone*100 + load`
- Category limits per technician per day: `catLimits[catId]` cap
- `min_daily` hard enforcement: if a tech has underfull days, don't open new days
- `DEMO_MODE` must never make Supabase calls

## Clients
| Client | tenant_id | Business |
|---|---|---|
| Israel (pilot) | `00000000-0000-0000-0000-000000000001` | Garbage disposal + water systems, 4 technicians |

## Files
| File | Purpose |
|---|---|
| `index.html` | Entire frontend application |
| `schema.sql` | Complete Supabase DDL, RLS, audit triggers, onboarding SQL |
| `backend/main.py` | FastAPI optimizer service |
| `backend/optimizer.py` | OR-Tools TSP solver |
| `backend/cities.py` | Hebrew city → coordinates lookup |
| `backend/test_optimizer.py` | Manual local smoke test for optimizer |
| `test/smoke.html` | Browser-based round-trip smoke tests (run against staging only) |
| `context/new-entity-checklist.md` | 8-step checklist for every new Supabase table |
| `CLAUDE.md` | This file |

## GPS + Live Map (added May 2026)
- **Leaflet.js** loaded from CDN (free, no API key) — renders OpenStreetMap tiles
- **Tech route map**: `toggleTechMap()` shows route map in tech view — numbered stop pins, home base marker, GPS dot
- **GPS tracking**: `startGpsTracking()` / `stopGpsTracking()` — `navigator.geolocation.watchPosition`, throttled to 1 DB write per 30s
- **Coordinator live map**: `toggleCoordinatorMap()` on home page — all techs with last GPS + today's tasks colored by tech
- **Supabase Realtime**: channel `ml-tech-gps-{tenantId}` — coordinator map updates in real-time as techs move
- **GPS columns**: `last_lat`, `last_lon`, `last_seen` on `technicians` table — run `outputs/migration-gps-columns_2026-05-27.sql`
- `CONFIG.GOOGLE_MAPS_KEY`: optional upgrade — leave empty to use free OpenStreetMap tiles

## Known Backlog / Open Items
- [x] **GPS migration done** — `last_lat`, `last_lon`, `last_seen` columns live on `technicians` table (applied 2026-05-27 via MCP)
- [ ] Add Google Maps API key to `CONFIG.GOOGLE_MAPS_KEY` (optional — app works without it)
- [ ] Photo upload on task completion (Supabase Storage, free 1GB tier)
- [ ] Digital signature capture (canvas-based, no library needed)
- [x] Tech job history — "📋 היסטוריה" toggle in tech view, groups by date, summary stats (done 2026-05-27)
- [x] Polygon zone drawing — "🗺️ צייר" button per zone, Leaflet.draw, ray-cast city detection (done 2026-05-27)
- [ ] Break time management (lunch block on tech schedule)
- [ ] pytest suite: tests written — run `cd backend && pytest tests/ -v`
- [ ] min_daily enforcement: currently only checks future dates; past underfull days not visible to `buildCandidates`
- [ ] WAL tenant isolation: replay does not re-verify tenant_id (low risk at single-tenant pilot stage)
