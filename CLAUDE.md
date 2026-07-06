# Maslul — Claude Code Context

## Before Every Task — Read Context First
Read ALL files in `context/` before touching any code — **start with `context/README.md` (the top-down map: product → engine → knobs → clients)**:
- `context/business.md` — product vision, target clients, goals
- `context/architecture.md` — stack, schema, hard rules, auth, safety, GPS, labels, features
- `context/scheduling-rules.md` — scheduling engine, zones, break time, configurable modes
- `context/scheduling-scenarios.md` — use-case/edge-case catalog (principle → enforcing feature); check engine work against it
- `context/style.md` — CSS tokens, component classes, spacing rules, RTL conventions
- `context/clients/` — per-client profiles (`README.md` = global vs per-tenant model + source-of-truth rule; `_template.md`; `purewater.md` pilot)
- `context/auth-users.md` — roles, user management, technician↔user linkage, impersonation, RLS
- `context/zones-polygons.md` — zone system, city-list + polygon axes, geo one-source seam
- `context/knobs.md` — THE per-tenant rule registry (key → both engine readers → test)

**Adding a client:** Create `context/clients/[name].md` + SQL onboarding script. Each client's business rules live in `tenants.config` — never in shared code.

**Per-tenant scheduling rule:** Scheduling logic is tenant config, never a hardcoded default. **Far-to-near routing is PureWater/Israel-specific** — it is NOT the default for new clients; route strategy, zone-matching mode, durations, and windows are chosen per-tenant at onboarding. What's right for PureWater is not right for everyone.

**New entity / table rule:** Run all steps in `context/new-entity-checklist.md` before adding any Supabase table.

**Knob rule:** Every per-tenant rule lives in `context/knobs.md` (key → JS reader → batch reader → test). New knob = new row + BOTH readers + test, same commit. After any schema/policy change: run Supabase security advisors.

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

## 🔴 Urgent
- _(none — Railway `SUPABASE_SERVICE_KEY` resolved 2026-06-13: `/health` reports `route_cache:configured`, cache live.)_

Full backlog + milestone log → `context/backlog.md`
