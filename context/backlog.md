# Maslul — Backlog & History

> **North star + reprioritized roadmap (2026-06-13):** `outputs/product-vision-roadmap_2026-06-13.md`
> — *Maslul is an AI dispatch cockpit, not a calendar.* Buckets below mirror it.

## 🟢 NOW — coordinator flow redesign (Israel demo feedback 2026-06-14)
> Full triage: `outputs/israel-feedback-triage_2026-06-14.md`. Theme: dead-simple dispatcher flow, optimization behind the scenes.

> **✅ UI redesign port SHIPPED & DEPLOYED 2026-06-15** (7 slices on `md-*` design system, pushed to live):
> detail side-panel, weekly 3h window-blocks, daily grid polish, coordinator **3-card chooser** (additive over `showCandidate`),
> home dashboard, nav sidebar. All handlers preserved, 61+18 tests green. Source: `mockups/claude-design/`, log: `mockups/DESIGN-LOG.md`.
- [ ] **⭐ Manual E2E/QA pass — every section** (Eran request 2026-06-15; small fixes expected, nothing broken so far). Click through + verify each: home (KPI + tech→weekly), dispatch/coordinator (search→3 cards→reveal→confirm→back-home), task detail (assign/transfer, lock, status, save), weekly board (window-blocks, drag, optimize), daily grid (drop geometry, now-line, tray), nav + role/tenant switch, calls tab, reports, technicians, zones, clients, settings. Log each fix as found.
- [ ] **Simplified scheduling flow (Feedback #3 + 1.4/1.6/1.7)** — Search (city/address) → **3 recommendation cards** (Day · Date · Time-window only, no tech/route/scores) → confirm. Reveal tech/route/existing-day-jobs only *after* a card is picked. Replaces the current multi-slot `showCandidate`. **(card chooser shipped 2026-06-15; remaining: "check specific date" calendar view, auto-return-home polish.)**
  - [ ] **"Find Another Date"** → next-best optimized option (then 3rd…), all still rule-compliant.
  - [ ] **"Check Specific Date"** → run the same engine against a coordinator-chosen date; show that day's open windows calendar-style (#1.7/2.5).
  - [ ] After confirm: **"נקבע ✓" → auto-return to home/search** (#1.9/2.9).
- [ ] **Home = technician names only (#1.10)** — click a tech → structured weekly view (days · windows · cities · addresses · service types · status). Replaces current task/city dashboard.
- [ ] **Chronological ordering audit (#1.8/2.8)** — never 10:00 before 07:00; weekly sort fixed, audit all views. Calendar shows **only confirmed/completed**, never drafts/candidates.
- [ ] **Pass 1 — design system + shell / side-panel redesign.** Tokens, Linear-style side panel, cockpit dashboard, reusable components. (In progress.)
- [ ] **Explainability v1** — "why this tech" panel from signals the engine already computes (same zone · km saved · uses active day · avoids new route · load impact) + hover tooltips. (Now deferred behind the card flow — shown *after* selection per #3.)

## 🟠 Next
### Scheduling-engine capabilities (Israel feedback 2026-06-14)
- [ ] **Fill-first over balance (#1.5/2.3/2.7)** — Israel wants consolidation (pack one tech's day to max before opening another), NOT even-spread. Flip PureWater `scheduling.balance.enabled` → OFF. Re-validate `_assignment_score` fill-first path. ⚠ reverses the 2026-06-13 balance-ON decision.
- [ ] **⭐ Bulk-import → batch engine ("fill a week at once")** — `runBulkImport()`/`importCsvRows()` currently create calls as `status:'pending'` only (no engine). Wire them to the batch scheduler (`/batch-schedule` + `batch_schedule.py`) so an import is placed in ONE optimal pass instead of call-by-call re-sequencing. Eran flagged this as mandatory (2026-06-15). Writes live data → do deliberately, after backups.
- [ ] **Strict daily-region HARD block in dispatch UI (#1.3/1.11)** — batch engine already blocks cross-region (`batch_schedule.py:251`); the live `_candidatesZone`/drag path is fail-soft (warn). Make region violations a hard exclude when `scheduling.zone_strict` (+ remove N/S boundary, #1.2/2.11).
- [ ] **Technician skills / categories (#2.1)** — required `technicians.skills[]`; candidate engine filters techs by skill. Not every tech does every job type.
- [ ] **Per-category daily limits (#2.4)** — `technicians.category_limits` (e.g. ≤2 service calls, ≤5 installs/day); assigner respects them.
- [ ] **Rotation variety + busy-zone coverage (#2.2)** — up to 5 weekly regions/tech, ensure a tech isn't stuck in one area all week; **give under-covered busy zones a 3rd covering day** (תל אביב = 27 calls vs 2 covering tech-days is the current overflow cause).
- [ ] **Mandatory tech config + real boundary engine (#2.10/2.11)** — can't create a tech without regions, skills, hours, durations, max-daily, categories; recommendations never exceed the defined operating range (region/coords based, not N/S).
- [ ] **Bulk region creation (#2.12)** — paste a list of ~100 cities into a region at once (zone authoring; pairs with `canonicalCity` guard).
- [ ] **45-min "package" category (#1.1)** — add the DB category; durations already flow through the engine (standard 30 / package 45).
- [x] **Out-of-zone drop safeguard** ✅ 2026-06-13 — `confirmZoneDrop`/`zoneDropMismatch` on all three placement paths warn (fail-soft) when a call's city is in a different zone than the tech's day zone; ⚠ flag via `taskOutOfZone`. Config `scheduling.zone_drop_guard` (default ON, zone-mode). Needs browser QA. **→ upgrade to hard-block per #1.3.**
- [ ] **Calculate/batch-schedule PureWater's 108 tasks** — DEFERRED until all scheduling changes land (mode-aware UI + Plan B). Prereqs: (1) re-run rotation SQL so tech rotations re-link to current zone IDs; (2) verify Israel's tech-zone-per-day division (confirmed 2026-06-10 = `migration-purewater-zones-rotation_2026-06-05.sql`); (3) city aliases קש→קריית שמונה, זכרון→זכרון יעקב (added 2026-06-10, JS + backend). Then run batch assignment respecting the rotation.
- [ ] Israel fills in client details on 108 tasks (via ✏️ edit button)
- [ ] Israel testing — real dispatch scenarios, feedback collection
- [ ] Equal city distribution — config flag `scheduling.equal_city_distribution` to spread same-city tasks across techs
- [ ] Admin panel chips redesign — plan at `.claude/plans/ancient-plotting-prism.md`
- [ ] Web Push notifications — alert tech when task assigned

## 🟡 After Israel stabilizes
- [ ] **Per-task scheduling constraints** (from Israel's real cards) — structured `earliest`/`latest`/`forbidden_times`, `fixed_date`, `requires_approval`, `contact_person`; optimizer must honor them. Today buried in free-text `notes`.
- [ ] **"Call N min before arrival"** per-task notification rule (WhatsApp).
- [ ] **Variable window length per task** (not hardcoded 3h — saw 1.5h/3h/4h in real data).
- [ ] **Basic CRM structured fields** (the next-client direction; already needed by Israel): `product`/model, `price`/quote, `job_type` (לקחת/לספק/להתקין/לתקן), `contact`. Schema accurate + connected end-to-end. See `context/clients/purewater.md` → "Signals from Israel's real calendar".
- [ ] Tech view redesign
- [ ] **Geo corrections loop / self-healing place brain** — additive, does NOT touch routing. Phases: (1) write `place_resolution_log` + `confidence` on `geo_places`; (2) super_admin Geo Health page (see→fix→save→re-assign→log, reversible); (3) on-demand digest output; (4) typeahead-constrained city input at all entry doors; (5) bulk-door fuzzy+centroid ladder; (6) technician-GPS ground-truth healing. Two-store confidence model (high bar to enter the brain, below-bar surfaces as work). Fail-soft, never blocks. Full design: `outputs/geo-corrections-loop-design_2026-06-13.md`.
- [ ] **UI/UX design pass** — clean friendly SaaS look (colour-coded calendar + side panel, KPI strip), operable by a non-technical user. Refs: `outputs/ui-references_2026-06-13.md`. After the editable-calendar engine slices.
- [ ] Dashboard & analytics — charts, KPIs (like timing.tech)
- [ ] Customer ETA portal — SMS/WhatsApp link → customer sees tech ETA + can rate

## 🟢 Foundations / infra ("on me")
- [ ] **⭐ Supabase Free → Pro (~$25/mo) — at PureWater go-live.** Driver is data safety + reliability: Free **pauses after 7d inactivity** and has **no auto-backups** (we've had data-loss incidents). The first real foundational spend. Full plan: `outputs/infra-cost-roadmap_2026-06-14.md`.
- _Client-driven costs (storage/photos, SMTP, Twilio/WhatsApp, domain, higher Maps budget) = "on the way", added per client need and covered by their price — see the infra-cost-roadmap doc._

## 🟡 After Client #2
- [ ] Custom domain (maslul.co.il) + Cloudflare
- [ ] Client #2 onboarding — `context/clients/[name].md` + SQL script
- [ ] SMS auto-send (Twilio, ~$5/mo for 100 msgs)

## 🔵 Future
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
| 2026-06-08 (cont.) | Batch scheduler (`/batch-schedule` + `batch_schedule.py`) — 108 PureWater tasks auto-assigned from Jun 7 with zone rotation verified (16 tech-day combos ✅); weekly calendar shows all tasks (no +N truncation); professional block styling (accent border + shadow) |
| 2026-06-09/10 | **Zones & Polygons foundation** (branch `zones-polygons`) — two-axis model (`scheduling.mode` × `zone_match` city_list/polygon) via `resolveZone()` seam; `canonicalCity` duplicate-spelling guard; Leaflet self-hosted in `vendor/` (fixes recurring map-load failure) + lazy fallback; zone authoring (canonical guard + larger draw map + `polygons[]`); per-tech `blocked_zones`; mode-aware no-match block + fix-it CTA; bulk task import; dependency-free Node test harness (`tests/zones.test.js`, 18 tests) + `/test-zones` command; `context/clients/` profile layer + doc-sync discipline. Migration applied. ⏳ needs browser QA before merge to main |
| 2026-06-13 | **Editable calendar + geo foundation (Opus session)** — daily within-grid drag (drop a call onto a 3-hour window band, `windowAtOffset` snap + dashed indicator, re-sequences); weekly cells sort window-first (fixes dragged-call float-to-top); lock/unlock pin toggle (`toggleTaskLock`) in task-detail modal. Geo brain wired into live resolution (`geo_resolver`, fail-safe) — optimizer/batch resolve through `geo_places`+`place_aliases` then `cities.py`. PureWater `auto_sequence` + `balance` turned **ON** (live-verified). Geo-corrections-loop design doc (later phase, routing untouched). 61/61 JS + 64/64 backend. Outputs folder tidied (`outputs/archive/`). ⏳ later QA: drop re-sequence round-trip, cross-tech drag, out-of-zone drop safeguard. |
| 2026-06-09→13 | **Scheduling engine B1→B3 (Fable session)** — B1 drive-time cache (global `route_cache`, cache-first matrix, physics trust-bounds, honest quota → `gmaps-cached` mode; **verified live: 0-quota cache hit**); B2 authoritative auto-sequencing (`markDayDirty`→debounced→epoch-guarded `sequenceDay`→awaited persists, flag-gated `features.auto_sequence`); B3 route-strategy physics (cost/time-callback split so far→near *emerges*), weekly balance, gap-fill on cancel, shadow-compare modal (PureWater go/no-go gate), optimistic versioning. Plus a fresh-eyes product audit that fixed a 🔴 WAL cross-tenant write bug, unmetered `/geocode`, and per-row `auth.uid()` RLS. All flag-gated → PureWater untouched. 45/45 backend + 41 JS tests. Retro + lessons → `outputs/fable-session-retro_2026-06-13.md` |
