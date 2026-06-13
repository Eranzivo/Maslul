# Maslul — Backlog & History

> **North star + reprioritized roadmap (2026-06-13):** `outputs/product-vision-roadmap_2026-06-13.md`
> — *Maslul is an AI dispatch cockpit, not a calendar.* Buckets below mirror it.

## 🟢 NOW — UI/UX pass (cockpit reframe)
- [ ] **Pass 1 — design system + shell / side-panel redesign.** Tokens (whitespace, status→colour, typography, buttons); Linear-style side panel; dashboard reframed as a cockpit (pending/in-progress/completed/today + per-tech utilization); extract reusable components. Then Pass 2 (planner), Pass 3 (other screens).
- [ ] **Explainability v1** — "why this tech" panel on the assignment recommendation from signals the engine already computes (same zone · km saved · uses active day · avoids new route · load impact) + hover tooltips.

## 🟠 Next
- [x] **Out-of-zone drop safeguard** ✅ 2026-06-13 — `confirmZoneDrop`/`zoneDropMismatch` on all three placement paths warn (fail-soft) when a call's city is in a different zone than the tech's day zone; ⚠ flag via `taskOutOfZone`. Config `scheduling.zone_drop_guard` (default ON, zone-mode). Needs browser QA.
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
