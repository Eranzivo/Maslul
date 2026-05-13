# Maslul — Developer Onboarding

## What This Is

Maslul (מסלול) is a Hebrew-first SaaS scheduling engine for Israeli SMBs with field workers (technicians, cleaners, couriers, etc.). It handles intelligent job dispatch, technician calendars, zone management, route optimization, and task tracking.

**Live URL:** https://eranzivo.github.io/Maslul/  
**Optimizer API:** https://maslul-production-77fa.up.railway.app  
**Stack:** Single `index.html` + Supabase backend + GitHub Pages + Railway (FastAPI)  
**Owner:** Eran Zivo (solo founder, non-technical)

---

## Local Setup

No build step. No npm. No toolchain.

1. Clone the repo
2. Open `index.html` in a browser — done for demo mode
3. For real data: you need Supabase credentials (ask Eran)
4. For backend development: `cd backend && pip install -r requirements.txt && uvicorn main:app --reload`

> Demo mode is controlled by `CONFIG.DEMO_MODE = true` at the top of the `<script>` block. It bypasses all auth and Supabase calls entirely.

---

## File Map

| File | Purpose |
|---|---|
| `index.html` | Entire frontend — HTML, CSS, and JS all inline |
| `schema.sql` | Complete Supabase DDL, RLS policies, onboarding SQL |
| `CLAUDE.md` | AI assistant context (architecture rules, invariants) |
| `DEVELOPER.md` | This file |
| `backend/main.py` | FastAPI app — `/health` and `/optimize` endpoints |
| `backend/optimizer.py` | OR-Tools TSP solver + Google Maps / haversine distance matrix |
| `backend/cities.py` | 50 Israeli city coordinates (haversine fallback) |
| `backend/requirements.txt` | Python dependencies |
| `backend/railway.toml` | Railway deployment config (root dir, start command, healthcheck) |

Everything frontend lives in `index.html`. It's ~3500 lines. Internal structure:

```
<style>           CSS (lines ~10–240)
<body>
  #login-screen   Login form (shown before auth)
  #app-shell      Main app (hidden until logged in)
    .sidebar      Left-fixed nav
    .content      Page sections (one per route)
      #page-home
      #page-dispatch
      #page-tasks
      #page-planner
      #page-reports
      #page-clients
      #page-users       (admin only — user management)
      #page-technicians
      #page-zones
      #page-categories
      #page-settings
      #page-admin       (super_admin only)
      #page-techview    (tech's own schedule view)
      #page-wizard      (super_admin only — new client onboarding)
    #mob-bar      Mobile bottom tab nav (hidden on desktop)
    modals        All modal dialogs (id="mo-*", #modal-add-user, etc.)
<script>          All JS
```

---

## Architecture

### Multi-tenant

Every table has a `tenant_id` UUID column. Supabase Row Level Security (RLS) enforces that users only see their own tenant's data via a `get_tenant_id()` SQL function that reads the JWT.

`currentTenantId` is set at login by `loadTenantFromUser()` and used in every query. If it's `null`, the app is in demo mode or unauthenticated — all Supabase writes are blocked.

### Auth flow

1. User enters email + password → `doLogin()` → `supabase.auth.signInWithPassword()`
2. On success → `loadTenantFromUser()` fetches from `users` table → sets `currentTenantId`, `currentUserRole`, `currentUserPermissions`, `currentUserSuperAdmin`
3. `initApp()` loads all tenant data from Supabase into memory
4. `applyFeatureVisibility()` shows/hides nav items based on role + feature flags
5. If `currentUserRole === 'tech'` → `routeTechLogin()` redirects to tech view

### Role system

| Role | Access |
|---|---|
| `admin` | Full access to all pages in their tenant |
| `coordinator` | Ops pages only (home, dispatch, tasks, planner). Specific pages controlled by `users.permissions.views[]` |
| `tech` | Tech view only (`page-techview`) showing their own schedule |
| `super_admin` | Eran only. Cross-tenant admin panel, wizard, enter-as-tenant |

`coordinator` view permissions are stored as `{views: ['home','dispatch','tasks','planner','clients','reports']}` in the `users.permissions` JSONB column. Admins configure these per-user in the Users page.

`routeTechLogin()` matches the logged-in user to a technician via `technicians.user_id` (UUID FK). Falls back to name matching if `user_id` is null.

### Data flow

All entities live in memory (JS arrays: `technicians`, `tasks`, `zones`, etc.) and are synced to Supabase on every write. On login, all data is loaded once into memory. There is no reactive state system — renders are triggered manually by calling `renderX()` functions.

---

## Supabase Schema

See `schema.sql` for the full DDL. Key tables:

| Table | Key columns |
|---|---|
| `tenants` | `id`, `name`, `plan`, `config` (JSONB) |
| `users` | `id`, `tenant_id`, `role`, `name`, `email`, `permissions` (JSONB), `super_admin` |
| `technicians` | `id`, `tenant_id`, `name`, `user_id` (FK → auth.users), `rotation` (JSONB), `skills`, `cat_limits`, etc. |
| `tasks` | `id`, `tenant_id`, `assign_id`, `status`, `technician_id`, `scheduled_date`, `cancelled_at`, etc. |
| `zones` | `id`, `tenant_id`, `name`, `cities` (array) |
| `categories` | `id`, `tenant_id`, `name`, `duration_minutes` |
| `day_offs` | `id`, `tenant_id`, `technician_id`, `date`, `type` (`full`/`partial`) |
| `clients` | `id`, `tenant_id`, `name`, `phone`, `archived`, `archived_at` |

### `tenants.config` shape

```json
{
  "labels": {
    "worker": "טכנאי", "workers": "טכנאים",
    "task": "קריאה", "tasks": "קריאות",
    "zone": "אזור", "zones": "אזורים",
    "dispatch": "שיבוץ קריאה"
  },
  "defaults": {
    "regular_job_minutes": 30, "package_job_minutes": 45,
    "arrival_window_hours": 3, "max_daily_jobs": 9,
    "lookahead_days": 30, "work_start": "07:00", "work_end": "18:00"
  },
  "features": {
    "crm_enabled": false, "reports_enabled": false,
    "files_enabled": false, "checklists_enabled": false,
    "whatsapp_enabled": false, "google_maps_enabled": false
  }
}
```

---

## Adding a New Tenant (Client)

**Preferred:** Use the onboarding wizard in the app (הגדרות → 🧙 אשף לקוח חדש, super_admin only). The wizard creates the tenant, technicians, zones, categories, and rotation automatically.

**Manual SQL fallback:**

```sql
INSERT INTO tenants (id, name, plan, config) VALUES (
  'xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx',
  'Client Name', 'starter',
  '{"labels":{"worker":"טכנאי","workers":"טכנאים","task":"קריאה","tasks":"קריאות","zone":"אזור","zones":"אזורים","dispatch":"שיבוץ קריאה"},"defaults":{"regular_job_minutes":30,"package_job_minutes":45,"arrival_window_hours":3,"max_daily_jobs":9,"lookahead_days":30,"work_start":"07:00","work_end":"18:00"},"features":{"crm_enabled":false,"reports_enabled":false}}'
);

INSERT INTO users (id, tenant_id, role, name, email) VALUES (
  'auth-user-uuid-here', 'tenant-uuid-here', 'admin', 'Manager Name', 'email@company.com'
);
```

**Creating users in-app (no Supabase dashboard needed):**  
הגדרות → 👤 משתמשים → + משתמש חדש. This calls `supabase.auth.signUp()`, captures and restores the admin session, then inserts the `users` row. For tech-role users, select which technician profile they map to — this writes `technicians.user_id`.

---

## Route Optimization Backend

**URL:** `https://maslul-production-77fa.up.railway.app`  
**Deployed from:** `backend/` subfolder of this repo, via Railway  
**Triggered by:** `CONFIG.OPTIMIZER_URL` in `index.html` (empty = disabled, set to Railway URL = active)

The frontend calls `optimizeDay(techId, date)` which POSTs to `/optimize`. The backend:
1. Builds a distance matrix — Google Maps Distance Matrix API if `GOOGLE_MAPS_API_KEY` env var is set, otherwise haversine between city coordinates × 35km/h speed factor
2. Runs OR-Tools TSP solver with time dimension (5-second limit)
3. Returns ordered task list with estimated arrival times

`runOptimize(techId)` applies the result back to tasks in memory and Supabase. A "🔀 מסלול מיטבי" button appears on home tech cards when `OPTIMIZER_URL` is set and the tech has 2+ tasks today.

**Railway env vars:**
| Variable | Value |
|---|---|
| `PORT` | `8080` |
| `ALLOWED_ORIGINS` | `https://eranzivo.github.io` |
| `GOOGLE_MAPS_API_KEY` | (add when Google Cloud account is set up) |

---

## Feature Flags

Feature flags live in `tenants.config.features`. They control nav visibility and page access.

`applyFeatureVisibility()` runs after login and reads the flags + current user role/permissions to show/hide nav items.

Toggling: Admin panel → enter tenant session → "תכונות" section, OR direct SQL update.

Current flags: `crm_enabled`, `reports_enabled`, `files_enabled`, `checklists_enabled`, `whatsapp_enabled`, `google_maps_enabled`

---

## Labels System

All user-visible entity names are tenant-configurable (a cleaning company uses "מנקה" not "טכנאי").

- `tenantLabels` — in-memory object, loaded from `tenants.config.labels` at login
- `L('key')` — returns the label for a key, falls back to the default Hebrew value
- HTML elements with `data-label="key"` are updated automatically by `applyLabels()` on init

---

## Scheduling Engine

The core business logic lives in `findBestSlot()` / `buildCandidates()`.

**Rules (do not break):**
1. **Zone-strict:** A tech only receives jobs in their scheduled zone for that day. Zone assignment rotates weekly (`tech.rotation` JSONB keys 0–5 = Sun–Fri)
2. **Far-to-near routing:** Cities within a zone are ordered by `getCityIndexInZone()`. Earlier jobs go to farther cities
3. **Fill existing days first:** Prefer days where the tech already has jobs in that zone (`fillScore = existingInZone * 100 + currentLoad`)
4. **Category limits:** Per-tech daily caps (`tech.catLimits[catId]`)
5. **Day-off awareness:** `isTechAvailable()` checks `dayoffs` array before adding candidate

---

## Supabase Write Pattern

```js
async function saveXToSupabase(x) {
  if (!currentTenantId) return;  // demo mode / unauth guard
  const row = { tenant_id: currentTenantId, field1: x.field1, ... };
  if (x._dbId) {
    await sb.from('table').update(row).eq('id', x._dbId);
  } else {
    const { data } = await sb.from('table').insert(row).select().single();
    x._dbId = data.id;
  }
}
```

---

## ID Strategy

- In-memory objects start with integer `id` values (locally assigned)
- After a Supabase INSERT, `_dbId` is set to the returned UUID
- Technicians: after insert, `tech.id` is promoted to the UUID and all in-memory tasks are updated
- **Always quote IDs in onclick handlers:** `onclick="fn('${tech.id}')"` — unquoted UUIDs parse as arithmetic and silently fail
- **Never use `parseInt()` on a tech ID** — UUIDs become NaN

---

## Adding a New Page

1. Add HTML: `<div id="page-yourpage" class="page hidden">...</div>` in `#app-shell .content`
2. Add nav button in sidebar: `<button id="nav-yourpage" class="ni-btn" onclick="goPage('yourpage')">...</button>`
3. Add `'yourpage'` to the pages array in `goPage()`
4. Add `if(page==='yourpage') renderYourPage();` in `goPage()`
5. Add visibility control in `applyFeatureVisibility()` if role/feature-gated
6. Write `renderYourPage()`

---

## Deployment

**Frontend:** `git push origin main` → GitHub Pages live in ~1 min. No build step.

**Backend:** Railway auto-deploys from `backend/` on every push to `main`. Takes ~2–3 min (OR-Tools is large). Monitor at railway.app.

**Supabase credentials** are hardcoded in `index.html` (acceptable for this stage — revisit before scaling or adding devs).

---

## Known Gotchas

- **UUID onclick quoting** — always `onclick="fn('${id}')"` not `onclick="fn(${id})"`
- **No parseInt on UUIDs** — use string comparison: `String(t.techId) === String(tech.id)`
- **Template literals in PowerShell** — use `[System.IO.File]::ReadAllText` + `.Replace()` when editing JS via PowerShell; `-replace` mangles `${}`
- **Demo mode guard** — `if (!currentTenantId) return` blocks all Supabase writes; null = demo or unauth
- **Tech login** — matched by `technicians.user_id` FK first, then name fallback. Link via Users page → tech role → pick technician dropdown
- **Email confirmation** — disable in Supabase Auth → Email → Confirm sign up, so techs can log in immediately with temp passwords
- **OR-Tools on Railway** — first deploy takes 2–3 min (large library). Health check at `/health`
- **Port 8080** — Railway domain must be configured to route to port 8080. Check Networking → domain → pencil icon if 502

---

## Current Clients

| Client | tenant_id | Business | Status |
|---|---|---|---|
| PureWater Israel | `00000000-0000-0000-0000-000000000001` | Garbage disposal + water systems, 4 technicians | Pilot |

---

## Roadmap (May 2026)

**Done:**
- ✅ Zone-based scheduling engine
- ✅ Multi-tenant RLS
- ✅ Tech individual logins (user_id FK)
- ✅ In-app user management (no Supabase dashboard needed)
- ✅ Coordinator role with per-user view permissions
- ✅ FastAPI + OR-Tools optimizer on Railway
- ✅ Route optimization UI (home card button)
- ✅ WhatsApp click-to-send (zero cost)
- ✅ Recurring tasks
- ✅ Client archive, reports, planner view
- ✅ Onboarding wizard (super_admin, hidden until client #2)

**Next:**
- ⬜ Google Maps Distance Matrix API (real drive times)
- ⬜ Mobile page layouts (deferred until Israel feedback)
- ⬜ Cross-tenant RLS hardening (before client #2)
- ⬜ WhatsApp API automation via GreenAPI (~$20/month)

**Architecture trigger:** Move to modular ES modules + Vercel when 2+ paying clients or a second developer joins.
