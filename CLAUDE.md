# Maslul — Claude Code Context

## What This Is
Hebrew-first SaaS scheduling engine for Israeli SMBs with field workers.
Deployed as a single HTML file: https://eranzivo.github.io/Maslul/

## Tech Stack (Current)
- **Frontend:** Single `index.html` — all JS and CSS inline, no build step
- **Backend:** Supabase (PostgreSQL + Auth + RLS) — direct from browser
- **Hosting:** GitHub Pages (static)
- **Font:** Heebo (Google Fonts)

## Tech Stack (Roadmap)
- **Frontend:** Modular ES modules, Vercel (when 2+ paying clients or 2nd developer)
- **Backend:** FastAPI (Python) on Railway — scheduling engine first, CRUD later
- **Keep vanilla JS** — no React/Vue/TypeScript

## Architecture Principles
- Multi-tenant: every table row has `tenant_id`, enforced by Supabase RLS
- Adding a client: 1 SQL insert into `tenants` + 1 Supabase Auth user + 1 insert into `users`
- `currentTenantId` set at login via `loadTenantFromUser()`, used in every query
- localStorage is fallback only — Supabase is source of truth
- `DEMO_MODE: true` in CONFIG bypasses auth and Supabase entirely
- Single HTML file until 2+ paying clients

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

Demo mode: bypasses auth, loads `DEMO_PRESETS[type]`, shows purple banner,
blocks all localStorage writes and Supabase calls (null `currentTenantId` prevents writes).

## Supabase Tables
See `schema.sql` for complete DDL, RLS policies, and onboarding SQL.

| Table | Key columns |
|---|---|
| `tenants` | `id`, `name`, `plan`, `config` (JSONB) |
| `users` | `id`, `tenant_id`, `role`, `name` |
| `technicians` | `id`, `tenant_id`, `name`, `phone`, `base_city`, `color`, `min_daily`, `max_daily`, `start_time`, `end_time`, `blocked_cities` (array), `skills` (array), `cat_limits` (JSONB), `rotation` (JSONB) |
| `tasks` | `id`, `tenant_id`, `assign_id`, `client_name`, `client_phone`, `city`, `street`, `category_id`, `category_name`, `technician_id`, `status`, `scheduled_date`, `scheduled_time`, `notes`, `cancelled_at` |
| `zones` | `id`, `tenant_id`, `name`, `cities` (array) |
| `categories` | `id`, `tenant_id`, `name`, `duration_minutes` |
| `packages` | `id`, `tenant_id`, `name`, `items` (JSONB) |
| `day_offs` | `id`, `tenant_id`, `technician_id`, `date`, `type`, `from_time`, `to_time`, `reason` |

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
All entities use insert-or-update keyed on `_dbId`:
```js
async function saveXToSupabase(x) {
  if (!currentTenantId) return; // guards demo mode and unauth state
  const row = { tenant_id: currentTenantId, ...fields };
  if (x._dbId) {
    await sb.from('table').update(row).eq('id', x._dbId);
  } else {
    const { data } = await sb.from('table').insert(row).select().single();
    x._dbId = data.id;
  }
}
```
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
- `DEMO_MODE` must never make Supabase calls

## Clients
| Client | tenant_id | Business |
|---|---|---|
| Israel (pilot) | `00000000-0000-0000-0000-000000000001` | Garbage disposal + water systems, 4 technicians |

## Files
| File | Purpose |
|---|---|
| `index.html` | Entire application |
| `schema.sql` | Complete Supabase DDL, RLS, onboarding SQL |
| `CLAUDE.md` | This file |
