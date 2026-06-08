# Maslul — Claude Code Context

## Before Every Task — Read Context First
Read ALL files in `context/` before touching any code:
- `context/business.md` — product vision, target clients, goals
- `context/architecture.md` — stack, schema, hard rules, auth, safety, GPS, labels, features
- `context/scheduling-rules.md` — scheduling engine, zones, break time, configurable modes
- `context/style.md` — CSS tokens, component classes, spacing rules, RTL conventions
- `context/client-israel.md` — pilot client details and constraints
- `context/auth-users.md` — roles, user management, technician↔user linkage, impersonation, RLS
- `context/zones-polygons.md` — zone system, city-list matching, polygon draw flow, future polygon-point assignment

**New entity / table rule:** Run all steps in `context/new-entity-checklist.md` before adding any Supabase table.

**Proactive upgrade rule:** If a significant product improvement is possible (like geocoding accuracy, a new API integration, or an architectural enhancement), proactively suggest it with: what it does, steps to implement, and cost estimate. Don't wait to be asked.

**Outputs rule:** Every artifact (reports, plans, summaries, migrations) → `outputs/[task-name]_[YYYY-MM-DD].md`.

**Connections:** `connections/registry.json` lists all external services. Secrets only in `.env` (root) — never in `context/`, `connections/`, or `commands/`.

---

## What This Is
Hebrew-first SaaS scheduling engine for Israeli SMBs with field workers.
- App: https://eranzivo.github.io/Maslul/
- Optimizer API: https://maslul-production-77fa.up.railway.app

## Tech Stack
| Layer | Tech |
|---|---|
| Frontend | Single `index.html` — all JS/CSS inline, no build step, vanilla JS only (no React/Vue/TS) |
| DB | Supabase (PostgreSQL + Auth + RLS) — direct from browser |
| Optimizer | FastAPI + OR-Tools on Railway (`backend/`) |
| Hosting | GitHub Pages (frontend) + Railway (FastAPI) |

## Deployment Checklist (every push)
1. `git push origin main`
2. Wait 60s → open incognito → `https://eranzivo.github.io/Maslul/`
3. Confirm: login screen < 3s, login succeeds, home page loads
4. Stuck? `?clearall=1` resets all localStorage. `?clearwal=1` clears WAL only.

## Clients
| Client | tenant_id | Business |
|---|---|---|
| Israel / PureWater (pilot) | `00000000-0000-0000-0000-000000000001` | Garbage disposal + water systems, 3 technicians (depot: אלי סיני 7, אשקלון) |
| Maslul Admin (Eran) | `642ad6e6-a093-46a4-8489-ce49a966d77c` | Internal admin tenant — cross-tenant management |

Eran (infomaslul@gmail.com) logs in to Maslul Admin → uses 🔀 PureWater sidebar chip to impersonate Israel's tenant. `super_admin = true` on Eran's user row bypasses RLS for any tenant.

## Known Backlog

### ✅ Done
- [x] GPS tracking + live coordinator map (2026-05-27)
- [x] Photo upload on task completion (2026-05-27)
- [x] Tech job history (2026-05-27)
- [x] Polygon zone drawing (2026-05-27)
- [x] Digital signature capture (2026-05-27)
- [x] WhatsApp message template (2026-05-28)
- [x] Tenant separation — Eran ↔ Israel impersonation (2026-05-28)
- [x] Configurable scheduling engine — wizard, modes, route_strategy, duration_overrides (2026-06-01)
- [x] Recurring jobs (2026-06-01)
- [x] Pending queue panel on dispatch (2026-06-01)
- [x] Israeli cities autocomplete (2026-06-01)
- [x] Google Maps daily quota + /health reporting (2026-06-01)
- [x] Break time system — tenant default + per-tech override (2026-06-01)
- [x] Code review — 15 findings fixed (2026-06-01)
- [x] UI/UX overhaul — home + dispatch pages (2026-06-04): SVG sidebar, KPI cards, tech cards, header cleanup, two-column dispatch
- [x] PureWater zone setup — 9 zones, cities arrays, 3-tech rotation, city normalization (2026-06-06)
- [x] Dispatch form UX — client name/phone/notes moved to top of form, one-step flow (2026-06-07)
- [x] Task detail modal — "ערוך ✏" button added, MSL assign_id hidden from UI (2026-06-07)
- [x] Week of Jun 7–11 seeded — 108 placeholder tasks for PureWater via SQL (2026-06-07)
- [x] Polygon draw modal fixed — map renders, scroll works (2026-06-07)
- [x] CITY_COORDS_JS expanded 45 → 255 cities (2026-06-07)
- [x] Geo-intelligence layer — street-level routing via Google Geocoding API + lat/lon caching on tasks; polygon vertices saved on zones; optimizer uses best available coords (2026-06-07)
- [x] Floor / apartment / entrance notes fields — added to tasks table + dispatch form; optional; don't affect geocoding (2026-06-08)
- [x] Geocoding trigger → confirmAssign() button only — zero automatic API calls (2026-06-08)
- [x] Users management → "הרשאות גישה" — renamed, filtered to admin/coordinator only; techs managed from טכנאים page (2026-06-08)
- [x] Dropped redundant `users_admin_all` RLS policy — fixed "טוען..." loading bug on users page (2026-06-08)
- [x] Context files: auth-users.md + zones-polygons.md created (2026-06-08)
- [x] PureWater scheduling overhaul — service windows persisted to DB, 72/48/24h slot release (PureWater-only config), backtrack detection, return_city as OR-Tools end depot (2026-06-08)
- [x] Calendar daily view rebuilt — absolute-positioned grid (1px/min), one-tech-at-a-time with tech tabs, all tasks visible incl. unscheduled below grid (2026-06-08)

### 🔴 Urgent
- [ ] **Railway upgrade** — trial expires **2026-06-12**. Upgrade to Hobby $5/mo at railway.app or the optimizer goes down.
- [ ] **Re-dispatch 108 PureWater tasks** — run `outputs/reset-purewater-tasks_2026-06-08.sql` in Supabase, then coordinator re-dispatches via new engine

### 🟠 Next
- [ ] Israel fills in client details on 108 seeded tasks (via ערוך ✏ button)
- [ ] Israel testing — real scenarios, feedback collection
- [ ] Admin panel chips redesign — plan exists at `.claude/plans/ancient-plotting-prism.md`
- [ ] Web Push notifications — alert tech when new task assigned (Medium)
- [ ] pytest backend suite (Low, ~30min)

### 🟡 After Israel stabilizes
- [ ] Tech view redesign — after Israel confirms scheduling engine is solid
- [ ] Dashboard & analytics — proper charts, KPIs, donut charts (like timing.tech)
- [ ] Customer ETA portal — SMS/WhatsApp link → customer sees tech ETA + can rate service (timing.tech's #1 differentiator)

### 🟡 After Client #2
- [ ] Custom domain (maslul.co.il) + Cloudflare
- [ ] Client #2 onboarding — new `context/client-[name].md` + SQL onboarding script
- [ ] SMS auto-send (Twilio, ~$5/mo for 100 msgs)

### 🔵 Future
- [ ] AI call summary in tech view
- [ ] Customer self-booking portal
- [ ] Native mobile app (PWA first)
- [ ] min_daily enforcement for past underfull days
- [ ] WAL tenant isolation on replay
