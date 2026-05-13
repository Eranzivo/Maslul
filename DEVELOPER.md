# Maslul — Developer Onboarding

## What This Is

Maslul (מסלול) is a Hebrew-first SaaS scheduling engine for Israeli SMBs with field workers (technicians, cleaners, couriers, etc.). It handles intelligent job dispatch, technician calendars, zone management, and task tracking.

**Live URL:** https://eranzivo.github.io/Maslul/  
**Stack:** Single `index.html` + Supabase backend + GitHub Pages hosting  
**Owner:** Eran Zivo (solo founder, non-technical)

---

## Local Setup

No build step. No npm. No toolchain.

1. Clone the repo
2. Open `index.html` in a browser — done for demo mode
3. For real data: you need Supabase credentials (ask Eran)

> Demo mode is controlled by `CONFIG.DEMO_MODE = true` at the top of the `<script>` block. It bypasses all auth and Supabase calls entirely.

---

## File Map

| File | Purpose |
|---|---|
| `index.html` | Entire application — HTML, CSS, and JS all inline |
| `schema.sql` | Complete Supabase DDL, RLS policies, onboarding SQL |
| `CLAUDE.md` | AI assistant context (not for humans) |
| `DEVELOPER.md` | This file |

Everything lives in `index.html`. It's ~2900 lines. The internal structure is:

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
      #page-technicians
      #page-zones
      #page-categories
      #page-settings
      #page-admin     (super_admin only)
      #page-techview  (tech's own calendar view)
    #mob-bar      Mobile bottom tab nav (hidden on desktop)
    modals        All modal dialogs (id="mo-*")
<script>          All JS (~1400–2900)
```

---

## Architecture

### Multi-tenant

Every table has a `tenant_id` UUID column. Supabase Row Level Security (RLS) enforces that users only see their own tenant's data via a `get_tenant_id()` SQL function that reads the JWT.

`currentTenantId` is set at login by `loadTenantFromUser()` and used in every query. If it's `null`, the app is in demo mode or unauthenticated — all Supabase writes are blocked.

### Auth flow

1. User enters email + password → `doLogin()` → `supabase.auth.signInWithPassword()`
2. On success → `loadTenantFromUser()` fetches the user's row from `users` table → sets `currentTenantId`, `currentRole`, user name
3. `applyFeatureVisibility()` shows/hides nav items based on `tenantConfig.features`
4. `load()` fetches all data for this tenant (technicians, tasks, zones, categories, packages, dayoffs, settings)

### Data flow

All entities live in memory (JS arrays: `technicians`, `tasks`, `zones`, etc.) and are synced to Supabase on every write. On login, all data is loaded once into memory. There is no reactive state system — renders are triggered manually by calling `renderX()` functions.

---

## Supabase Schema

See `schema.sql` for the full DDL. Key tables:

| Table | Purpose |
|---|---|
| `tenants` | One row per client company. `config` JSONB holds labels, defaults, features. |
| `users` | App users. `role` = `'admin'` or `'tech'`. Links to `auth.users` via UUID. |
| `technicians` | Field workers. Has availability, zone rotation, skill/category limits. |
| `tasks` | Jobs/calls. Has status lifecycle, scheduling, assignment. |
| `zones` | Named groups of cities. Controls which tech works where each day. |
| `categories` | Job types with duration in minutes. |
| `packages` | Multi-item bundles. `items` is a JSONB array of `{category_id, qty}`. |
| `day_offs` | Technician absences. Full day or time-range. |

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
    "whatsapp_enabled": false, "demo_mode": false,
    "google_maps_enabled": false
  }
}
```

---

## Adding a New Tenant (Client)

Run this in the Supabase SQL editor (fill in the UUIDs and details):

```sql
-- 1. Create the tenant
INSERT INTO tenants (id, name, plan, config) VALUES (
  'xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx',
  'Client Name',
  'starter',
  '{"labels":{"worker":"טכנאי","workers":"טכנאים","task":"קריאה","tasks":"קריאות","zone":"אזור","zones":"אזורים","dispatch":"שיבוץ קריאה"},"defaults":{"regular_job_minutes":30,"package_job_minutes":45,"arrival_window_hours":3,"max_daily_jobs":9,"lookahead_days":30,"work_start":"07:00","work_end":"18:00"},"features":{"crm_enabled":false,"reports_enabled":false,"files_enabled":false,"checklists_enabled":false,"whatsapp_enabled":false}}'
);

-- 2. Create the app user row (after creating the auth user in Supabase dashboard)
INSERT INTO users (id, tenant_id, role, name) VALUES (
  'auth-user-uuid-here',
  'tenant-uuid-here',
  'admin',
  'Manager Name'
);
```

Then in the Supabase dashboard → Authentication → Users → Invite user (or create manually with email + password).

---

## Feature Flags

Feature flags live in `tenants.config.features`. They control nav visibility and page access.

`applyFeatureVisibility()` runs after login and reads the flags to show/hide nav items. Toggling is done via:
- **Eran (super_admin):** Admin panel → enter tenant session → "תכונות" (features) section
- **SQL:** `UPDATE tenants SET config = jsonb_set(config, '{features,crm_enabled}', 'true') WHERE id = '...'`

Current flags: `crm_enabled`, `reports_enabled`, `files_enabled`, `checklists_enabled`, `whatsapp_enabled`, `google_maps_enabled`, `demo_mode`

---

## Labels System

All user-visible entity names are tenant-configurable (a cleaning company uses "מנקה" not "טכנאי").

- `tenantLabels` — in-memory object, loaded from `tenants.config.labels` at login
- `L('key')` — returns the label for a key, falls back to the default Hebrew value
- HTML elements with `data-label="key"` are updated automatically by `applyLabels()` on init

When adding new UI text that names an entity, use `L('worker')` / `L('task')` etc. rather than hardcoding Hebrew.

---

## Scheduling Engine

The core business logic. Lives in `findBestSlot()`.

**Rules (do not break these):**
1. **Zone-strict:** A technician only receives jobs in their scheduled zone for that day. Zone assignment rotates weekly per technician (`tech.rotation` JSONB).
2. **Far-to-near routing:** Cities within a zone are ordered by `getCityIndexInZone()`. Earlier jobs go to cities further from base.
3. **Fill existing days first:** When multiple valid slots exist, prefer days where the tech already has jobs in that zone (`fillScore = existingInZone * 100 + currentLoad`).
4. **Category limits:** Each tech can have per-category daily caps (`tech.catLimits[catId]`).
5. **Day-off awareness:** Slots on days marked as off (full day or overlapping time) are skipped.

---

## Supabase Write Pattern

Every entity follows this pattern (never deviate from it):

```js
async function saveXToSupabase(x) {
  if (!currentTenantId) return;  // demo mode / unauth guard
  const row = { tenant_id: currentTenantId, field1: x.field1, ... };
  if (x._dbId) {
    const { error } = await sb.from('table').update(row).eq('id', x._dbId);
    if (error) { console.error(error); showToast('שגיאה בשמירה', 'error'); return; }
  } else {
    const { data, error } = await sb.from('table').insert(row).select().single();
    if (error) { console.error(error); showToast('שגיאה בשמירה', 'error'); return; }
    x._dbId = data.id;
  }
  showToast('נשמר ✓');
}
```

---

## ID Strategy

This is subtle — read carefully.

- In-memory objects start with integer `id` values (assigned locally on creation)
- After a Supabase INSERT, `_dbId` is set to the returned UUID
- For technicians specifically: after insert, `tech.id` is also promoted to the UUID, and all in-memory tasks referencing the old integer id are updated (see `saveTechToSupabase`)
- Tech IDs from Supabase are UUIDs — always quote them in `onclick` handlers: `onclick="editTech('${tech.id}')"` (unquoted UUIDs are parsed as arithmetic and silently fail)
- Never use `parseInt()` on a tech ID — UUID → NaN

---

## Adding a New Page

1. Add the HTML section: `<div id="page-yourpage" class="page hidden">...</div>` inside `#app-shell .content`
2. Add a nav button in the sidebar: `<button id="nav-yourpage" class="ni-btn" onclick="goPage('yourpage')">...</button>`
3. Add a mobile tab or "more" sheet item if it should be accessible on mobile
4. Add `'yourpage'` to the pages array in `goPage()`
5. Add `if(page==='yourpage') renderYourPage();` in `goPage()`
6. Write `renderYourPage()` — it should always call `document.getElementById('page-yourpage').innerHTML = ...`

---

## Navigation & Routing

There is no router library. `goPage(page)` is the entire routing system:
- Hides all pages, shows the target page
- Removes `.active` from all sidebar nav buttons, adds it to the matching one
- Syncs the mobile bottom tab bar active state
- Calls the appropriate render function

---

## Deployment

GitHub Pages serves `index.html` directly from the `main` branch.

To deploy: `git push origin main` — live in ~1 minute.

No CI, no build step, no environment variables (Supabase credentials are hardcoded in the script — acceptable for this stage, revisit before scaling).

---

## Access Control

| Role | Access |
|---|---|
| `admin` | Full access to their tenant's data |
| `tech` | Read-only calendar view (`page-techview`) of their own tasks |
| `super_admin` | Eran only. Cross-tenant admin panel, feature flag control, enter-as-tenant |

`super_admin` is a boolean on the `users` table row, checked at login.

---

## Current Clients

| Client | tenant_id | Business | Status |
|---|---|---|---|
| PureWater Israel | `00000000-0000-0000-0000-000000000001` | Garbage disposal + water systems, 4 technicians | Pilot — live |

---

## Known Gotchas

- **UUID onclick quoting** — always `onclick="fn('${id}')"` not `onclick="fn(${id})"`
- **No parseInt on UUIDs** — use `.value` directly from DOM selects for tech IDs
- **Supabase config column** — settings live in `tenants.config` JSONB, not a separate `settings` column
- **Template literals in PowerShell** — use `[System.IO.File]::ReadAllText` + `.Replace()` when editing JS template literals via PowerShell scripts; `-replace` regex mangles `${}`
- **Demo mode guard** — `if (!currentTenantId) return` is the single guard for all Supabase writes; null currentTenantId = demo or unauth
- **cancelOnly / confirmReplace** — both must call `saveTaskToSupabase(t)` after updating status in memory

---

## Roadmap (as of May 2026)

**Short term (post-pilot feedback):**
- Mobile layout fixes (nav bar added, page layouts need testing)
- Task history on client card (CRM linkage)
- Cross-tenant RLS (required before client #2)

**Medium term:**
- FastAPI backend on Railway (scheduling engine first)
- Google Maps + route optimization
- WhatsApp integration

**Architecture trigger:** Move from single HTML to modular ES modules + Vercel when there are 2+ paying clients or a second developer joins.
