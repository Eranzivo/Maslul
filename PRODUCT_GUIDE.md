# Maslul — Product Guide

_The single, current reference for what every part of Maslul does. Use it for onboarding, support, demos, and as the map for client conversations._

> **Last verified:** 2026-06-29 — rewritten against the live `index.html` source and PureWater's live Supabase config. Supersedes the May 2026 demo-script version.
>
> **What it is:** A Hebrew-first, RTL, mobile-friendly scheduling engine for Israeli SMBs with field workers. One `index.html` (no build step) talking directly to Supabase (Postgres + Auth + RLS), plus a FastAPI + OR-Tools optimizer on Railway. Multi-tenant: every business is one `tenant_id` with its own config; **rules live in `tenants.config`, never hardcoded.**
>
> **The mental model:** Maslul is **not a calendar — it is an AI dispatcher.** The coordinator enters a city + service type; the engine decides *who, when, and why* using zones, routes, capacity, and customer windows. The screens are mostly a window onto that engine.

---

## How to read this guide
- **Part 1** — the sections a user clicks (keyed to the real navigation).
- **Part 2** — the engine and systems working behind those screens.
- **Part 3** — feature flags, config model, roles.
- Each section: **What it is · What you can do · Current behavior / notes.**
- 🆕 marks things added or materially changed since the May guide.

---

# Part 1 — The Sections (navigation)

Desktop: left sidebar. Mobile: bottom tab bar. Visibility depends on **role**, **feature flags**, and **scheduling mode** (zone-only items hide for non-zone tenants).

| Nav (Hebrew) | Internal page | Who sees it |
|---|---|---|
| דף הבית | `home` | everyone |
| שיבוץ קריאה | `dispatch` | admin, coordinator |
| קריאות | `tasks` | admin, coordinator |
| יומן | `planner` | admin, coordinator |
| דוחות | `reports` | flag-gated |
| לקוחות | `clients` (CRM) | flag-gated |
| טכנאים | `technicians` | admin |
| אזורים | `zones` | admin (zone mode only) |
| קטגוריות | `categories` | admin |
| הגדרות | `settings` | admin |
| הרשאות גישה | `users` | admin |
| מנהל מאסטר | `admin` | super_admin (Eran) |
| היום שלי | `techview` | tech role |
| (אשף לקוח חדש) | `wizard` | super_admin |

---

## 🏠 דף הבית — Home
**What it is:** The daily command center — first screen after login.

**What you can do:**
- See KPI cards (today's tasks / completed / in-progress / unassigned).
- See one card per technician: today's load (X / max), today's zone, progress.
- Click a tech card → their schedule.
- 🆕 **"🔀 מסלול מיטבי"** appears when a tech has 2+ tasks today → runs the OR-Tools optimizer to reorder the day by real drive time.
- Search any client across all tasks.
- 🆕 **Coordinator live map** (`toggleCoordinatorMap`) — all techs' last GPS + today's jobs, updating live via Supabase Realtime (when GPS is in use).
- Manage day-offs / vacations (חופשות).

---

## 🎯 שיבוץ קריאה — Dispatch
**What it is:** The flow to create and assign a new service call. This is the heart of the product.

🆕 **Current flow is a simplified 3-card chooser** (shipped 2026-06-15), replacing the old multi-slot list:
1. Pick a **category** chip or a **package** (bundle).
2. Enter **city** (autocomplete from 250+ Israeli cities) + optional street/address.
3. Click search → the engine returns **3 recommendation cards: Day · Date · Time-window** (no tech/route/scores shown up front — kept simple).
4. Pick a card → *then* it reveals the tech, route context, and that day's existing jobs.
5. Fill client name / phone / notes → **Confirm** (`confirmAssign`) → saved with a 3-hour customer window.

**Additional:**
- 🆕 **Pending queue panel** — the 15 nearest upcoming pending calls; overdue ones flagged red; "שבץ →" pre-fills the form and assigns in place.
- "Find another date" cycles alternatives; "check specific date" runs the engine against a chosen day.
- 🆕 **Recurring series** — turn a call into weekly / biweekly / monthly (see Part 2).
- 🆕 On confirm, optional one-click **WhatsApp** to the client.
- **Smart draft:** navigate away mid-form and fields are restored.
- 🆕 **Geocoding:** on confirm, the address is geocoded once (Google) and cached on the task — used for routing precision.

---

## 📋 קריאות — Tasks
**What it is:** The full call log — every status, every date.

**What you can do:**
- Filter: הכל / ממתינות / משובצות / הושלמו / בוטלו.
- Click any task → 🆕 **detail side-panel**: client info, tech, time/window, status, history, **🔒 lock/unlock** (pin a call so the optimizer never moves it), and an **assign/transfer** panel (tech + date + window).
- Status flow: ממתין → שובץ → בדרך → הגיע → הושלם / תקלה.
- Cancel → 🆕 the engine suggests the nearest pending calls to fill the freed slot (gap-fill).
- 🆕 **Bulk task import** ("⇪ ייבוא מרובה") — paste `street, city` rows; matched cities become pending tasks; 🆕 **"⚡ שבץ אוטומטית"** runs the batch engine (dry-run preview → commit). Unmatched cities listed with a reason + "תקן אזורים" link.
- CSV import (file path exists; not wired to batch).

---

## 📅 יומן — Planner _(was "לוח תכנון")_
**What it is:** The visual schedule across technicians.

**Views:**
- **Weekly:** each tech a column, each day a row.
- 🆕 **Daily grid:** absolute-positioned timeline (1px/min). Each **3-hour window** is a block; overlapping windows lay out **side-by-side in columns** (no pile-up); now-line; tasks without windows show at exact time; unscheduled calls listed below.

🆕 **Editable calendar:**
- **Drag** a call between tech/day cells (weekly) or onto a time-window band (daily) → re-assigns and re-sequences.
- **Tap-to-place** (mobile + desktop) via the detail panel.
- **Needs-attention strip** at the top surfaces every pending call (no column), draggable/tappable — including flagged overflow (טבריה) and no-location (חרב).
- 🆕 **Out-of-zone safeguard:** for a zone-strict tenant, dropping a call outside the tech's zone-of-the-day is **hard-blocked** (error toast, no override); relaxed tenants get a soft warning. ⚠ marks out-of-zone calls.
- 🆕 **Auto-sequence:** when on, any change re-runs OR-Tools and re-orders the day (see Part 2).
- 🆕 Super-admin **"🔍 השוואת מסלול"** (shadow-compare) — current vs proposed route side-by-side with a fuel/time delta; one-click apply only if it saves time and drops nothing.

---

## 👷 טכנאים — Technicians
**What it is:** The technician roster and **all per-tech scheduling rules** — the core configuration surface.

**Per technician:**
- Name, phone, **base city** (departure), 🆕 **return city** (optional — day can end elsewhere), color.
- Work hours; **min / max calls per day**.
- 🆕 **Weekly schedule** (`weekly_schedule`): per-weekday on/off + hours; per-tech **break** override (default / custom / none).
- **Rotation:** which **zone** this tech covers each weekday (Sun–Thu) — the spine of zone scheduling.
- **Skills:** which categories the tech is qualified for.
- **Category limits:** max of a given category per day (e.g. max 2 service calls).
- **Blocked cities / blocked zones.**
- 🆕 **Per-category duration overrides** (when the flag is on).
- 🆕 GPS: `last_lat/lon/seen` populate the live map.

---

## 🗺️ אזורים — Zones
**What it is:** Geographic service areas. Visible only in **zone mode**.

**Structure:**
- Each zone = name + **ordered city list** (order sets far-to-near routing within a day).
- 🆕 Two matching modes (`zone_match`): **`city_list`** (match by city — PureWater) or **`polygon`** (point-in-polygon on the geocoded address). 🆕 Polygon drawing uses self-hosted Leaflet in `vendor/`.
- Rotation (set on each tech) maps weekday → one zone.

**Rule:** in zone mode, a call in city X only goes to the tech whose zone-of-that-day includes X. Enforced in dispatch search, batch, and manual placement.

---

## 📦 קטגוריות — Categories
**What it is:** Service types and bundles.
- **Categories:** name + duration (minutes) — drives slot math.
- **Packages:** a bundle of categories with a combined duration; appear as a chip in dispatch.

---

## ⚙️ הגדרות — Settings
**What it is:** Company-wide defaults + feature controls.

**Configurable:** company name, monthly volume target; global work hours; default durations (regular / package); arrival window (2h / 3h / 4h); lookahead days; 🆕 **working days** ("ימי עבודה") tenant default; 🆕 **break time** (enabled / start / end); export/import settings as JSON.

**Feature flags (admin):** CRM, Reports, WhatsApp, Google Maps, Geocoding, Files, Checklists, Odoo, Auto-sequence — per tenant.

> Note: these defaults are written into `tenants.config.defaults`. If that block is absent, the app falls back to code defaults (30-min jobs, **3h window**, max 9/day, 30-day lookahead, Saturday-off).

---

## 👤 הרשאות גישה — Users _(was "משתמשים")_
**What it is:** Access management.
- Create users (email invite) — role Admin / Coordinator / Tech.
- Per-coordinator page permissions (`users.permissions.views[]`).
- Link a tech-role user → a technician profile (they log in and see only their own day).
- Reset password; delete user.

---

## 📊 דוחות — Reports _(flag-gated; ON for PureWater)_
Business KPIs: task volume & completion, per-tech, per-zone, per-category breakdowns.

## 👥 לקוחות — CRM _(flag-gated; ON for PureWater)_
Client address book + service history. Add/edit clients (name, phone, email, city, address, notes); view history; archive (restorable).

## 📱 היום שלי — Tech View _(tech role)_
Stripped-down field view: today's + tomorrow's jobs ordered by time; per job category, client, phone, address, notes, window. Large status buttons (בדרך → הגעתי → הושלם); 🗺️ Waze; 📞 call; 💬 WhatsApp. 🆕 Route map + GPS tracking (throttled to 1 write / 30s). Sees nothing else.

## 🔧 מנהל מאסטר — Master Admin _(Eran only)_
Cross-tenant control: all tenants + flags; **enter any tenant's session** (impersonate); toggle features; 🆕 **onboarding wizard** (`אשף לקוח חדש`) — new client in one flow (tenant → scheduling mode → zones → techs → categories → rotation).

---

# Part 2 — The Engine & Systems Behind the Screens

This is what makes Maslul a dispatcher rather than a calendar. Almost all of it is **per-tenant config** in `tenants.config.scheduling`.

## The dispatcher north-star (universal)
Think like a seasoned coordinator. Optimize **in this priority order**: (1) correct route direction / no backtracking — *most important*; (2) full-day utilization; (3) no predictable lateness; (4) minimize fuel/travel; (5) most-appropriate tech — only after 1–4. The *specific knobs* below are how each tenant instantiates that north-star — they are **not** global defaults.

## Assignment model (`scheduling.mode`)
- **`zone`** (PureWater) — zone-strict: a tech only works their rotation zone that day; route ordered by `route_strategy`.
- **`open`** — no zones; balance by workload across techs.
- **`radius`** — assign nearest available tech to each city.
- The UI adapts: zone tabs/grids hide for `open`/`radius`.

## Route strategy (`scheduling.route_strategy`)
Resolved by `resolveRouteStrategy` — **absent ⇒ `flexible`** (safe default).
- **`flexible`** — no geographic ordering; fill by load.
- **`far_to_near`** (PureWater) — farthest city first, work toward base. 🆕 **Enforced in the backend solver** via a dominant outward-arc penalty (not just a bias) so the route can't zigzag; fail-open (never forces a drop); same-city stays adjacent.
- **`nearest_first`** — closest first (dense urban / delivery).

## Supporting rules (all config-gated)
- **`fill_first`** — fill a tech's partial active day before opening a new one.
- **`balance` `{enabled, weight}`** — intended as a soft load-distribution preference across the tech-days that cover a zone. _PureWater: ON._ ⚠ **Known inconsistency:** ON behaves **oppositely** in the two engines — the **batch** scheduler spreads evenly (8 → 4-4 via `_assignment_score`), while **live dispatch** mostly consolidates (`balanceAdjust` just rewards already-active days). OFF = both consolidate. Needs collapsing to one shared policy.
- **`equal_city_distribution`** — intended to spread same-city tasks across techs. _PureWater: ON._ ⚠ **Half-wired:** honored only in the **live** dispatch score (and there dominated by the +100 fill-first weight, so mostly a tie-breaker); the **batch** scheduler ignores the flag (it spreads same-city unconditionally via its `city_load` term).
- ⚠ **`balance` + `equal_city_distribution` + `fill_first` are three additive biases on one placement score** that partly cancel → emergent, hard-to-tune behavior. Planned fix: a single `placement_policy` (`consolidate`/`spread`) read identically by dispatch and batch.
- **`slot_release` (72/48/24h)** — hold early slots for farther cities; relaxes as the date nears. Only runs under `far_to_near`. _PureWater: ON._
- **`zone_strict`** — hard-block cross-zone placement (dispatch, batch, and manual drag). _PureWater: ON._
- **Break time** — tenant default + per-tech override; the optimizer treats it as a no-travel pinned block so no job overlaps it.
- **Working days** (`defaults.work_days`) — tenant operating week; absent ⇒ Saturday-off only. Combined (AND) with each tech's `weekly_schedule` and day-offs.
- **Category limits / skills** — per-tech caps and qualifications, enforced before a slot is offered.
- **Manual lock (`tasks.locked`)** — a pinned call the auto-sequencer must never move or drop.

## Route optimization backend (FastAPI + OR-Tools, Railway)
- **`/optimize`** — builds a distance matrix, runs the TSP solver (`solve_route_v2`), returns ordered tasks + arrival times, plus dropped-tasks (over-full day), conflict (locked-vs-locked), and a per-stop **decision trace** (prev city + drive minutes, shown as "🚗 X דק׳ מ-Y").
- 🆕 **Auto-sequence (`features.auto_sequence`)** — when on, every task change calls `markDayDirty` → debounced, epoch-guarded `sequenceDay` → re-optimizes and persists the day. OR-Tools becomes the single source of truth for order/time. Fail-open: on optimizer error the day keeps its heuristic order with a "טעון אופטימיזציה" badge. _PureWater: ON._
- 🆕 **Batch scheduler (`/batch-schedule`)** — auto-assigns all pending tasks across a date range: greedy zone-rotation assignment + per-tech-day `solve_route_v2`. `dry_run` previews without writing. Accepts the coordinator's own JWT (tenant forced to caller) or the service key.
- 🆕 **Drive-time cache (`route_cache`)** — global table; cached legs reused (even when Google is quota-blocked); only new pairs hit Google; physics-based trust bounds. Makes always-on real-drive sequencing cheap.
- **Geocoding (`/geocode`)** — `{street, city}` → lat/lon (Google), cached on the task forever. Metered under the same daily quota; falls back to haversine / city coords.
- **Unlocatable cities → flagged, never guessed** — a city with no coordinates is left pending with `needs_location` + a coordinator note, rather than silently stamped at Tel Aviv (which corrupted routes).

## Other systems
- 🆕 **Recurring jobs** — `recurring_templates` (day-of-week, interval 1/2/4 weeks, time, preferred tech). Instances generated idempotently on login.
- **GPS + live maps** — Leaflet/OSM; tech route map; coordinator live map via Supabase Realtime.
- **WhatsApp** — pre-written customer messages (primary channel for Israeli SMBs).
- **Safety stack** — WAL (replays failed saves), audit log (DB triggers on every write), schema validator, connection monitor, all writes through `dbUpsert`/`dbInsert`.

---

# Part 3 — Flags, Config Model, Roles

## `tenants.config` shape
```json
{
  "depot":     { "lat": .., "lon": .., "address": ".." },
  "labels":    { "worker": "טכנאי", "task": "קריאה", "zone": "אזור", ... },
  "defaults":  { "regular_job_minutes": 30, "package_job_minutes": 45,
                 "arrival_window_hours": 3, "max_daily_jobs": 9,
                 "lookahead_days": 30, "work_start": "07:00", "work_end": "18:00",
                 "work_days": [0,1,2,3,4],
                 "break": { "enabled": true, "start": "12:00", "end": "13:00" } },
  "scheduling": { "mode": "zone", "zone_match": "city_list", "zone_strict": true,
                  "fill_first": true, "route_strategy": "far_to_near",
                  "balance": { "enabled": true, "weight": 50 },
                  "equal_city_distribution": true,
                  "slot_release": { "enabled": true, "conservative_hours": 72,
                                    "moderate_hours": 48, "aggressive_hours": 24 } },
  "features":  { "whatsapp_enabled": true, "google_maps_enabled": false,
                 "geocoding_enabled": true, "auto_sequence": true,
                 "crm_enabled": true, "reports_enabled": true,
                 "files_enabled": true, "checklists_enabled": true,
                 "odoo_integration": false, "demo_mode": false } }
```
> **Terminology is tenant-configurable** via `labels` — call `LBL('worker')` etc. in code; never hardcode "טכנאי".

## Roles
| Role | Access |
|---|---|
| `admin` | All pages in their tenant |
| `coordinator` | Ops pages, controlled by `permissions.views[]` |
| `tech` | Own schedule only (`היום שלי`) |
| `super_admin` | Eran — cross-tenant, wizard, impersonate |

## Demo mode
`?demo=1` / `?demo=cleaning` / `?demo=delivery` bypasses auth + Supabase, loads presets, shows a purple banner. Never makes DB calls.

---

## What changed since the May guide (high level)
Simplified 3-card dispatch · editable drag/lock calendar + side-panel · daily window-block grid · auto-sequence (OR-Tools as source of truth) · honest route strategies + enforced far→near · balance / equal-city / slot-release / break / working-days config · batch scheduler + bulk import · drive-time cache · geocoding + geo foundation · recurring jobs · zone polygon mode (self-hosted Leaflet) · mode-aware UI · onboarding wizard · renamed nav (יומן, הרשאות גישה).
