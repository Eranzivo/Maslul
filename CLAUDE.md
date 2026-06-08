# Maslul — Claude Code Context

## Before Every Task — Read Context First
Read ALL files in `context/` before touching any code:
- `context/business.md` — product vision, target clients, goals
- `context/architecture.md` — stack, schema, hard rules, auth, safety, GPS, labels, features
- `context/scheduling-rules.md` — scheduling engine, zones, break time, configurable modes
- `context/style.md` — CSS tokens, component classes, spacing rules, RTL conventions
- `context/clients/purewater.md` — PureWater pilot: zones, techs, scheduling config, Odoo
- `context/auth-users.md` — roles, user management, technician↔user linkage, impersonation, RLS
- `context/zones-polygons.md` — zone system, city-list matching, polygon draw flow

**Adding a client:** Create `context/clients/[name].md` + SQL onboarding script. Each client's business rules live in `tenants.config` — never in shared code.

**New entity / table rule:** Run all steps in `context/new-entity-checklist.md` before adding any Supabase table.

**Proactive upgrade rule:** Suggest significant product improvements proactively: what it does, steps, cost estimate.

**Outputs rule:** Every artifact (reports, plans, migrations) → `outputs/[task-name]_[YYYY-MM-DD].[ext]`.

**Connections:** `connections/registry.json` — secrets only in `.env` (root), never in context/ or connections/.

---

## What This Is
Hebrew-first SaaS scheduling engine for Israeli SMBs with field workers.
- App: https://eranzivo.github.io/Maslul/
- Optimizer API: https://maslul-production-77fa.up.railway.app

## Tech Stack
| Layer | Tech |
|---|---|
| Frontend | Single `index.html` — all JS/CSS inline, no build step, vanilla JS only |
| DB | Supabase (PostgreSQL + Auth + RLS) — direct from browser |
| Optimizer | FastAPI + OR-Tools on Railway (`backend/`) |
| Hosting | GitHub Pages (frontend) + Railway (FastAPI) |

## Clients
| Client | tenant_id | Details |
|---|---|---|
| PureWater Israel (pilot) | `00000000-0000-0000-0000-000000000001` | Water systems, 3 techs, depot: אלי סיני 7 אשקלון. See `context/clients/purewater.md` |
| Maslul Admin (Eran) | `642ad6e6-a093-46a4-8489-ce49a966d77c` | Internal — cross-tenant management |

Eran (infomaslul@gmail.com) → Maslul Admin → 🔀 PureWater chip to impersonate. `super_admin=true` bypasses RLS.

## Deployment Checklist (every push)
1. `git push origin main`
2. Wait 60s → open incognito → `https://eranzivo.github.io/Maslul/`
3. Confirm: login < 3s, login succeeds, home loads
4. Stuck? `?clearall=1` resets localStorage. `?clearwal=1` clears WAL only.

---

## Active Backlog

### 🔴 Urgent
- [ ] **Railway upgrade** — trial expires **2026-06-12**. Upgrade to Hobby $5/mo at railway.app or optimizer goes down.
- [ ] **Dispatcher: assign 108 tasks** — 108 pending tasks with real cities seeded; coordinator dispatches via engine or batch optimizer

### 🟠 Next
- [ ] Israel fills in client details on 108 tasks (via ✏️ edit button)
- [ ] Israel testing — real dispatch scenarios, feedback collection
- [ ] Equal city distribution — config flag `scheduling.equal_city_distribution` to spread same-city tasks across techs
- [ ] Admin panel chips redesign — plan at `.claude/plans/ancient-plotting-prism.md`
- [ ] Web Push notifications — alert tech when task assigned

### 🟡 After Israel stabilizes
- [ ] Tech view redesign
- [ ] Dashboard & analytics — charts, KPIs (like timing.tech)
- [ ] Customer ETA portal — SMS/WhatsApp link → customer sees tech ETA + can rate

### 🟡 After Client #2
- [ ] Custom domain (maslul.co.il) + Cloudflare
- [ ] Client #2 onboarding — `context/clients/[name].md` + SQL script
- [ ] SMS auto-send (Twilio, ~$5/mo for 100 msgs)

### 🔵 Future
- [ ] AI call summary in tech view
- [ ] Customer self-booking portal
- [ ] Native mobile app (PWA first)
- [ ] WAL tenant isolation on replay

---

## Milestone Log
| Date | What shipped |
|---|---|
| 2026-05-27 | GPS tracking, photo upload, job history, polygon zone drawing, digital signature |
| 2026-05-28 | WhatsApp template, tenant separation (Eran ↔ Israel impersonation) |
| 2026-06-01 | Configurable scheduling engine (modes, route_strategy, duration overrides), recurring jobs, pending queue, cities autocomplete, Maps quota, break time, code review |
| 2026-06-04 | UI/UX overhaul — SVG sidebar, KPI cards, tech cards, two-column dispatch |
| 2026-06-06 | PureWater zone setup — 9 zones, 3-tech rotation, city normalization |
| 2026-06-07 | Dispatch UX, task edit modal, 108 tasks seeded, polygon fix, 255 cities, geo-intelligence layer |
| 2026-06-08 | Service windows (DB + dispatch), 72/48/24h slot release (PureWater config), backtrack detection, return_city OR-Tools end depot, calendar rebuilt (absolute grid, one-tech, all tasks visible), auth-users + zones-polygons context files, 108 real tasks seeded |
