# Architecture Context — Maslul

## Current State
- Single `index.html` — all HTML, CSS, JS inline (~4000 lines)
- Supabase (PostgreSQL + Auth + RLS) — direct from browser
- GitHub Pages (static hosting): https://eranzivo.github.io/Maslul/
- FastAPI backend on Railway: https://maslul-production-77fa.up.railway.app
- No build step, no npm, no toolchain

## Target Stack (Roadmap)
- **Frontend:** Modular ES modules, Vercel (trigger: 2+ paying clients or 2nd developer)
- **Backend:** FastAPI (Python) on Railway — scheduling engine first, CRUD later
- **Keep vanilla JS** — no React, Vue, TypeScript

## Hard Rules
- Do NOT use React, Vue, or TypeScript
- Do NOT break any existing functionality
- Every Supabase table must have tenant_id with RLS
- Do NOT make Supabase calls when DEMO_MODE is true
- Single HTML file until architecture trigger is hit

## File Map
| File | Purpose |
|---|---|
| `index.html` | Entire frontend — HTML, CSS, JS inline |
| `schema.sql` | Complete Supabase DDL, RLS policies, onboarding SQL |
| `CLAUDE.md` | AI assistant context (working rule, clients, backlog) |
| `context/style.md` | CSS tokens, component classes, spacing, RTL conventions |
| `context/architecture.md` | This file — stack, schema, hard rules, features |
| `context/scheduling-rules.md` | Scheduling engine rules and invariants |
| `DEVELOPER.md` | Developer onboarding, gotchas, infrastructure |
| `PRODUCT_GUIDE.md` | Section-by-section product brief + 15-min demo script |
| `backend/main.py` | FastAPI app — /health and /optimize endpoints |
| `backend/optimizer.py` | OR-Tools TSP solver + Google Maps / haversine distance matrix |
| `backend/cities.py` | 200+ Israeli city coordinates (haversine fallback, logs unknown cities) |

## Internal HTML Structure
```
<style>              CSS
<body>
  #login-screen      Login form
  #reset-screen      Password reset
  #app-shell         Main app
    .sidebar         Left nav
    .content
      #page-home
      #page-dispatch
      #page-tasks
      #page-planner
      #page-reports
      #page-clients
      #page-users
      #page-technicians
      #page-zones
      #page-categories
      #page-settings
      #page-admin      (super_admin only)
      #page-techview   (tech's own schedule)
      #page-wizard     (super_admin only)
    #mob-bar         Mobile bottom nav
    modals           id="mo-*"
<script>             All JS
```

## Multi-Tenant Architecture
- Every table has `tenant_id` UUID column with Supabase RLS
- `currentTenantId` set at login via `loadTenantFromUser()`
- `if (!currentTenantId) return` blocks all Supabase writes in demo mode or unauth state
- `DEMO_MODE: true` in CONFIG bypasses auth and Supabase entirely

## Role System
| Role | Access |
|---|---|
| `admin` | Full access to all pages in their tenant |
| `coordinator` | Ops pages (home, dispatch, tasks, planner) — controlled by `users.permissions.views[]` |
| `tech` | Tech view only — their own schedule |
| `super_admin` | Eran only — cross-tenant admin, wizard, enter-as-tenant |

## Route Optimization Backend
- POST `/optimize` — builds distance matrix, runs OR-Tools TSP solver, returns ordered tasks with arrival times
- Distance matrix: Google Maps Distance Matrix API if key set, else haversine
- Location priority per task: **geocoded lat/lon** → **street + city string** → **city name only**
- `_parse_loc(loc)` in optimizer.py handles `"lat,lon"` strings and city name strings uniformly
- 5-second solver time limit
- "🔀 מסלול מיטבי" button on home when tech has 2+ tasks today

## Geocoding (Google Geocoding API)
- POST `/geocode` — accepts `{street, city}`, returns `{lat, lon}` via Google Geocoding API (same key as Distance Matrix)
- Frontend calls this inside `confirmAssign()` (button press, not blur) when `features.geocoding_enabled = true`
- Result cached in `tasks.lat / tasks.lon / tasks.geocoded_at` — geocode once, reuse forever
- `_pendingGeocode` JS var holds result until `confirmAssign()` writes it to the task
- `_geocodeCache` JS object caches within the session by `"street|city"` key
- Cost: ~$0.005 per unique address; within $200/month Google Maps free credit
- **Israel**: `geocoding_enabled: true` (enabled 2026-06-07)

## Supabase Write Pattern
```js
async function saveXToSupabase(x) {
  if (!currentTenantId) return; // demo mode / unauth guard
  const row = { tenant_id: currentTenantId, ...fields };
  if (x._dbId) {
    await sb.from('table').update(row).eq('id', x._dbId);
  } else {
    const { data } = await sb.from('table').insert(row).select().single();
    x._dbId = data.id;
  }
}
```

## ID Strategy
- `id` = in-memory identity (integer for locally-created, UUID after Supabase insert)
- `_dbId` = Supabase row UUID, used for update/delete
- Technicians from Supabase: `id === _dbId === UUID`
- Always quote IDs in onclick handlers: `onclick="fn('${tech.id}')"` — unquoted UUIDs parse as arithmetic
- Never use `parseInt()` on a tech ID — UUIDs become NaN

## Known Gotchas
- UUID onclick quoting — always `onclick="fn('${id}')"` not `onclick="fn(${id})"`
- No parseInt on UUIDs — use `String(t.techId) === String(tech.id)`
- Template literals in PowerShell — use `[System.IO.File]::ReadAllText` + `.Replace()`; `-replace` mangles `${}`
- Demo mode guard — `if (!currentTenantId) return` blocks all Supabase writes
- Email confirmation — disable in Supabase Auth so techs can log in immediately

## Infrastructure
| Service | Purpose |
|---|---|
| GitHub Pages | Frontend hosting |
| Supabase | DB + Auth + RLS |
| Railway | FastAPI optimizer backend (trial expires June 12 2026 — upgrade to Hobby $5/mo) |
| Google Cloud | Distance Matrix API |
| Sentry | Error tracking (EU region) |
| UptimeRobot | Uptime monitoring |

---

## Supabase Schema

### Tables
| Table | Key columns |
|---|---|
| `tenants` | `id`, `name`, `plan`, `config` (JSONB) |
| `users` | `id`, `tenant_id`, `role`, `name` |
| `technicians` | `id`, `tenant_id`, `name`, `phone`, `base_city`, `color`, `min_daily`, `max_daily`, `start_time`, `end_time`, `blocked_cities` (array), `skills` (array), `cat_limits` (JSONB), `rotation` (JSONB), `duration_overrides` (JSONB), `weekly_schedule` (JSONB), `last_lat`, `last_lon`, `last_seen` |
| `tasks` | `id`, `tenant_id`, `assign_id`, `client_name`, `client_phone`, `city`, `street`, `floor` (TEXT), `apartment` (TEXT), `entrance_notes` (TEXT), `category_id`, `category_name`, `technician_id`, `status`, `scheduled_date`, `scheduled_time`, `notes`, `cancelled_at`, `checklist_done` (JSONB), `recurring_template_id` (UUID FK), `lat` (DOUBLE PRECISION), `lon` (DOUBLE PRECISION), `geocoded_at` (TIMESTAMPTZ) |
| `zones` | `id`, `tenant_id`, `name`, `cities` (array), `polygon` (JSONB — array of `{lat,lng}` vertices, nullable) |
| `categories` | `id`, `tenant_id`, `name`, `duration_minutes` |
| `packages` | `id`, `tenant_id`, `name`, `items` (JSONB) |
| `day_offs` | `id`, `tenant_id`, `technician_id`, `date`, `type`, `from_time`, `to_time`, `reason` |
| `clients` | `id`, `tenant_id`, `name`, `phone`, `email`, `city`, `address`, `notes`, `archived` |
| `recurring_templates` | `id`, `tenant_id`, `client_name`, `client_phone`, `city`, `street`, `category_id`, `category_name`, `notes`, `day_of_week`, `scheduled_time`, `interval_weeks` (1/2/4), `preferred_technician_id`, `lookahead_weeks`, `active`, `last_generated_date`, `created_at` |
| `audit_log` | `id`, `created_at`, `tenant_id`, `table_name`, `operation`, `record_id`, `old_data` (JSONB), `new_data` (JSONB) |

### DB Migrations (run in order on fresh Supabase)
```
outputs/migration-gps-columns_2026-05-27.sql          — last_lat/lon/seen on technicians
outputs/migration-duration-overrides_2026-06-01.sql   — duration_overrides JSONB on technicians
outputs/migration-recurring-jobs_2026-06-01.sql       — recurring_templates table + tasks FK
outputs/migration-geocoding_2026-06-07.sql            — lat/lon/geocoded_at on tasks; polygon on zones
outputs/migration-purewater-zone-cities_2026-06-06.sql — Israel's 9 zones + city lists seeded
(applied via Supabase MCP 2026-06-08): floor/apartment/entrance_notes on tasks; drop redundant users_admin_all policy
```

### `tenants.config` JSONB Shape
```json
{
  "labels":    { "worker": "טכנאי", "workers": "טכנאים", "task": "קריאה", "tasks": "קריאות",
                 "zone": "אזור", "zones": "אזורים", "dispatch": "שיבוץ קריאה" },
  "defaults":  { "regular_job_minutes": 30, "package_job_minutes": 45,
                 "arrival_window_hours": 3, "max_daily_jobs": 9,
                 "lookahead_days": 30, "monthly_volume": 300,
                 "work_start": "07:00", "work_end": "18:00",
                 "break": { "enabled": true, "start": "12:00", "end": "13:00" } },
  "scheduling": { "mode": "zone", "zone_strict": true, "fill_first": true,
                  "route_logic": true, "route_strategy": "far_to_near" },
  "features":  { "whatsapp_enabled": true, "demo_mode": false,
                 "google_maps_enabled": false, "odoo_integration": false,
                 "tech_duration_overrides": false,
                 "geocoding_enabled": false }
}
```

---

## CDN + Supabase Key Rules
- **Always use the JWT anon key** (`eyJ...` format) — never `sb_publishable_...` with supabase-js@2
- **Pin every CDN library to an exact version** — never `@2` or `latest`; use `@2.49.4` etc.
- **Always use jsDelivr** (`cdn.jsdelivr.net`) — never unpkg (unpkg can silently change build artifacts)
- **Never add `integrity=` attributes** to CDN tags — version pinning is sufficient; hashes go stale
- Supabase JS pinned to `2.49.4`. Leaflet pinned to `1.9.4`. Do not change without testing.

---

## Auth Flow Rules (hard-learned — do not break)
- **Never use `Promise.race` to cancel a Supabase auth call.** The underlying fetch keeps running and holds supabase-js's lock. Any subsequent auth call queues behind it and hangs indefinitely.
- **`createClient()` uses a no-op auth lock** — `auth: { lock: async (_n, _t, fn) => fn() }`. Default Web Locks API is shared across tabs — one tab holds the lock, all others hang. Do not remove this option.
- **Pre-flight runs BEFORE `createClient()`** — clears sessions expiring within 5 minutes. Do not move inside `initAuth()` — by then the lock is already held.
- **`initAuth` watchdog** — `authDone = true` is the FIRST line in the watchdog callback. Without it, a late `getSession()` result calls `showLogin()` on top of the live app.
- **`loadTenantFromUser()` must `throw` on failure** — must: (1) call `showLogin()`, (2) set error text AFTER `showLogin`, (3) fire-and-forget `signOut()`, (4) `throw`. Never `return` after error — caller still calls `showApp()`.
- **`SIGNED_OUT` handler skips `showLogin()` if login is already visible** — prevents fire-and-forget `signOut()` from clearing errors set by `loadTenantFromUser()`.

---

## Supabase SECURITY DEFINER Function Rules (hard-learned — do not break)
- **`SET search_path = ''` requires `public.` prefix on ALL table references.** Bare `users` fails with `42P01: relation "users" does not exist` — silently breaks ALL RLS policies.
- **Supabase auto-creates** `current_tenant_id()` and `current_user_role()` startup functions. After any security advisor run, check and fix:
  ```sql
  SELECT proname, prosrc FROM pg_proc
  WHERE pronamespace = 'public'::regnamespace AND proconfig @> ARRAY['search_path=""']
  ORDER BY proname;
  ```
- **Our four functions** that query `public.users`: `get_tenant_id()`, `is_super_admin()`, `current_tenant_id()`, `current_user_role()`. All must have `public.` prefix.

---

## Data Persistence Rules (CRITICAL)
1. Verify `currentTenantId` is not null before any Supabase write — if null, show error and stop
2. `await` all `saveXToSupabase()` calls in user-facing flows — never fire-and-forget on a confirmed action
3. Show explicit error toast if save returns false/null — never silent failure
4. For new entities (no `_dbId`): the WAL does NOT cover them — they rely on the Supabase call completing
5. **Supabase user row invariant:** Every auth user MUST have a row in `public.users` with correct `tenant_id`. Missing row = `currentTenantId` stays null = all saves silently fail. Verify: `SELECT id, tenant_id, role FROM users WHERE id = '<auth_user_id>'`

---

## Safety Stack
| Layer | What it does |
|---|---|
| WAL (`ml_wal_v1`) | Stores failed saves in localStorage, replays on next login |
| `dbUpsert` try/catch | Prevents `_savesInFlight` permanent leak if client throws |
| Schema validator | Post-load null/type checks on all entities, Sentry on drift |
| Audit log (DB triggers) | Every INSERT/UPDATE/DELETE written to `audit_log` table |
| Connection monitor | 60s ping, red banner on network loss, re-login prompt on auth expiry |

All writes go through `dbUpsert` / `dbInsert` — never raw `sb.from().insert()`. These handle WAL, save-counter, error toast, Sentry logging.

---

## Terminology / Labels System
All user-visible entity names come from `tenantLabels` — never hardcoded. Call `L('key')` anywhere in JS.

| Key | Default | Example override |
|---|---|---|
| `worker` / `workers` | טכנאי / טכנאים | שליח / מנקה |
| `task` / `tasks` | קריאה / קריאות | משלוח / עבודה |
| `zone` / `zones` | אזור / אזורים | מסלול |
| `dispatch` | שיבוץ קריאה | משלוח חדש |

Labels stored in `tenants.config.labels`. Static HTML elements use `data-label="key"`, updated by `applyLabels()` on init.

---

## Demo Mode
Set `CONFIG.DEMO_MODE = true` (or `?demo=1`, `?demo=cleaning`, `?demo=delivery` URL params).
- `DEMO_TYPE`: `'general'` / `'cleaning'` / `'delivery'`
- Bypasses auth, loads `DEMO_PRESETS[type]`, shows purple banner
- `currentTenantId` is null → all Supabase calls blocked automatically
- `DEMO_MODE` must never make Supabase calls

---

## GPS + Live Map
- Leaflet.js from CDN (free, no API key) — OpenStreetMap tiles
- **Tech route map**: `toggleTechMap()` — numbered stop pins, home base marker, GPS dot
- **GPS tracking**: `startGpsTracking()` / `stopGpsTracking()` — `navigator.geolocation.watchPosition`, throttled to 1 DB write per 30s
- **Coordinator live map**: `toggleCoordinatorMap()` — all techs with last GPS + today's tasks
- **Supabase Realtime**: channel `ml-tech-gps-{tenantId}` — coordinator map updates live as techs move
- GPS columns: `last_lat`, `last_lon`, `last_seen` on `technicians` — migration: `outputs/migration-gps-columns_2026-05-27.sql`

---

## Feature Architecture (June 2026)

### Recurring Jobs
- `recurring_templates` table — one row per pattern (day_of_week, interval_weeks 1/2/4, scheduled_time, preferred_technician_id)
- `_generateRecurringInstances()` runs on every login — idempotent, silent, client-side
- **ID safety:** `nextTaskId++` only after confirmed `dbInsert` — never pre-consume on network failure
- **Frontier safety:** `lastGenerated` only advances after confirmed insert — failures retry on next login
- Tasks link to template via nullable `recurring_template_id` FK; deleting template sets FK to NULL (preserves history)
- Migration: `outputs/migration-recurring-jobs_2026-06-01.sql`

### Pending Queue Panel
- Dispatch page — 15 nearest upcoming `status==='pending'` tasks, sorted by date ASC
- Overdue tasks highlighted red; "שבץ →" button pre-fills dispatch form
- `queueAssign(id)` pre-fills form + sets `window._queueTask`
- `confirmAssign()` detects `_queueTask` and updates existing task in-place (not create new)
- On save failure: rolls back task object to previous state — no silent phantom assignment
- Filter is `status==='pending'` only — do NOT add `!t.techId` (recurring tasks with preferred tech must still appear)

### Israeli Cities Autocomplete
- `<datalist id="il-cities-list">` with 250+ Israeli cities, shared across dispatch `s-city` and add-task `at-city`
- Both are `<input list="il-cities-list">`, not `<select>` — zone enforcement is engine-side, not input-side

### Google Maps Daily Quota
- `backend/main.py` tracks elements used per UTC day in `_counter` (per-process)
- Limit via `GMAPS_DAILY_ELEMENT_LIMIT` env var (default 1200 elements/day ≈ 15 optimizations for 4 techs)
- Falls back to haversine silently when limit hit; `/health` endpoint reports usage
- Free tier: 40,000 elements/month → 1200/day uses ~36,000/month, within free
