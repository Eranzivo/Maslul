# Session startup — Maslul (paste to a new session)  ·  refreshed 2026-07-14

Run `/prime`. Then read, in order: `context/README.md` (the map) → `context/impact-map.md`
(**NEW — the dual-engine parity/coupling map; read before touching any cross-engine rule/knob/column**)
→ `context/knobs.md` (tenant-rule registry) → `context/design-system.md` (before any UI work).
Memories: `cross-tenant-brain`, `knob-registry-parity`, `ui-redesign-port`, `feedback_engine-first-priority`.

## Where things stand (2026-07-14, all LIVE + verified through `0935ed9`)
Suites: **282 sched + 65 zones JS · 193 py** (all green). Deploy = GitHub Pages (app + `/landing/`),
backend = Railway (`v1.3.0`). `HEAD == origin/main`, clean tree. Advisors clean.

### Shipped this session (newest first)
- **Impact map** (`context/impact-map.md`) — the "Neurons brain": the JS↔Py parity table (15 pairs +
  their golden fixtures), config-key→consumers, DB-table→readers/writers, "change X → verify Y".
  The safety net for the real-data ramp. Update it same-commit as any cross-engine change.
- **Cross-tenant brain — the big one this session** (vision: `outputs/cross-tenant-brain-design_2026-07-14.md`,
  memory `cross-tenant-brain`). Two-tier learning brain, **human-in-the-loop at every tier**:
  - **P0** — `route_cache.time_bucket` (PK now from/to/bucket; existing rows `static`) + `routing.traffic_mode`
    knob (off/rush_hour/live, PureWater=off) with JS↔Py parity (`traffic-cases.json`). Zero behavior change.
  - **P1** — `route_observations` (tenant-scoped, append-only). `logLegObservation` fire-and-forget on a
    task's FIRST arrival logs the real leg (`arrived − en_route`, bucketed). Fed by E4-lite timestamps.
  - **P2 APPROVAL GATE (Eran's rule: learned data NEVER auto-changes routing)** — `route_learned_approved`
    is the ONLY thing routing reads (`get_learned_legs` reads it, not raw observations). Master knob
    `routing.learned_durations` (default OFF). Optimizer prefers approved legs over cache/Google/haversine.
    **Verified E2E live** (fable review): inserted an observation + an approval, ran `get_learned_legs`'s
    query → returned only the approved leg; the observation was invisible to routing. Probe cleaned up.
  - **P3 groundwork** — 🧠 מוח המערכת card on מנהל מאסטר (super_admin): observed trends → PROPOSALS with
    context → **✓ אשר** (writes approved leg) → applies on next optimize; approved list with **↩ בטל**;
    **🌐 flag** when ≥2 tenants approved the same leg (global-rule candidate).
- **E4-lite** — `en_route_at`/`arrived_at`/`completed_at` on tasks (first-write-wins, stamped in
  `setStatus`/`techSetStatus`) + per-category duration-accuracy insight in reports + CSV export.
- **Weekly schedule rework** — Google-Calendar solid blocks (adaptive ink), distinct tech colors
  (מיכאל purple→rose `#DB2777`), per-block tech avatar+name, `לקוח` placeholder dropped, address shown.
- **Landing** — hero background REMOVED entirely (Eran: waste of resources); clean text hero. Old hero
  assets kept on disk (Eran will do a unified version later). Leads inbox + one-front-door still live.

## OPEN — Geo self-healing (Slices 1-3 SHIPPED 2026-07-14; Slices 4-5 next)
Design `outputs/geo-selfheal-design_2026-07-14.md`. Eran chose the read-only Health view first (A),
then expanded scope to the full correction loop. Memory `geo-selfheal-slices`.
- **Slice 1 LIVE on main** — `/geo-health` (read-only, fail-open) + super_admin home tile
  (🧠 בריאות גאוגרפית: unresolved + out-of-zone task-cities). Verified live (flags חרב + ~9 settlements).
- **Slice 2** — `backend/geo_suggest.py` confidence engine (backend-only, golden fixture).
- **Slice 3 DEPLOYED DARK** — `/geo-suggest` + 4 doors wired behind **`features.geo_suggest` (OFF)**.
  Enable on a tenant via `jsonb_set(config,'{features,geo_suggest}','true')` → **browser-QA the 4 doors**
  (dispatch/add-task/bulk/zone) before trusting. Auto-fixes `נהרייה`→`נהריה`; asks on `קרת שמה`.
- **Rule (Eran):** field-level auto-fix OK; **brain writes (aliases/places) need coordinator approval** (P2 page). Slice 3 writes nothing to the brain.
→ **Next:** Slice 4 add-city→pick-zone (nearest-member suggest); Slice 5 seed the ~9 real settlements
  (already have coords — only need zone assignment) + חרב. Then the P2 approval page.

## Deferred (documented, not lost)
- **Cross-tenant brain P2.5** — time-dependent rush-hour matrix (rush_hour × per-departure-time buckets);
  hard with a static OR-Tools matrix. Data already bucketed; only consumption deferred. Stays approval-gated.
- **Cross-tenant brain P3 promotion job** — automated quorum→global `route_cache` via a super_admin
  service-key endpoint + confirm/rollback. Today promotion is manual (the 🌐 flag surfaces candidates).
- Other engine/data items (mostly done): boundary engine + mandatory tech config (#2.10/2.11), bulk region
  creation, geo GPS-healing (P6), in-app demand dashboard, CRM structured fields, lead email-notify.

## Big context
**Eran will iterate on REAL Israel schedules/data very soon** — mirroring/creating schedules himself to
validate route logic before pushing PureWater to use it. When he does, P1→P3 should "surface and catch"
his activity (observations log → brain card → approve → optimizer). Techs CAN already submit
בדרך/הגיע/הושלם (tech view + coordinator modal) — both stamp E4-lite timestamps + log observations.

## Standing rules (unchanged)
Approval gate doctrine: learned data never auto-applies — surface → business owner approves → then engine
uses it · one engine door per action · a per-tenant rule = knobs.md row + BOTH readers (or documented n/a)
+ test/fixture, same commit · commit per slice + doc row same commit · parse-check inline JS + run both
suites before commit · verify deploys by observing the live surface + Railway `/health` · answer Eran in
English · SQL as a chat code block, never a file link · back up before any live-calendar write.
