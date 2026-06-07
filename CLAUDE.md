# Maslul — Claude Code Context

## Before Every Task — Read Context First
Read ALL files in `context/` before touching any code:
- `context/business.md` — product vision, target clients, goals
- `context/architecture.md` — stack, schema, hard rules, auth, safety, GPS, labels, features
- `context/scheduling-rules.md` — scheduling engine, zones, break time, configurable modes
- `context/style.md` — CSS tokens, component classes, spacing rules, RTL conventions
- `context/client-israel.md` — pilot client details and constraints

**New entity / table rule:** Run all steps in `context/new-entity-checklist.md` before adding any Supabase table.

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
| Israel / PureWater (pilot) | `00000000-0000-0000-0000-000000000001` | Garbage disposal + water systems, 4 technicians |
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

### 🔴 Urgent
- [ ] **Railway upgrade** — trial expires **2026-06-12**. Upgrade to Hobby $5/mo at railway.app or the optimizer goes down.

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
