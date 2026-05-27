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
| `CLAUDE.md` | AI assistant context (architecture rules, invariants) |
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
- 5-second solver time limit
- "🔀 מסלול מיטבי" button on home when tech has 2+ tasks today

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
