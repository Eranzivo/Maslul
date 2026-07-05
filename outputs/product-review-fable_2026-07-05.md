# Whole-Product Review — Engine First (Fable, 2026-07-05)

> Scope: §0 full context read (CLAUDE.md, all context/, roadmap + design docs, prior Fable review 2026-06-12) + deep code read of `backend/` (optimizer, batch_schedule, geo_resolver, canonicalize, route_cache, main, tests) + `index.html` scheduling path + read-only live-DB verification (Supabase MCP).
> Every finding below is verified against code and/or the live DB — file:line cited. Baseline: 79 backend + 96 JS tests green.
> Priority order honored: optimizer accuracy → data integrity/security → UI/UX.

## Verdict

The engine architecture is right (assign/sequence split, `solve_route_v2` as single solver, config-gated knobs, geo brain, cache). The dominant defect class is **the batch path (`/batch-schedule`) enforcing far fewer rules than the live JS path** — and the batch is what actually wrote PureWater's live calendar. Several per-tenant knobs are real on one door and cosmetic on the other. Second class: **the frontend still carries its own stale geo copy** (`CITY_COORDS_JS` + `CITY_ALIASES`), which is the root cause of the polygon bug and a standing parity hazard.

State correction vs the handoff: engine slices 3–7 are **substantially shipped** (route_cache, `sequenceDay`, balance, gap-fill, shadow-compare all exist and `auto_sequence` is ON for PureWater). Actually pending: `migration-tasks-updated-at` (optimistic versioning dormant), drag-to-pin UI, and cache warm-up (route_cache has only **6 rows** live — the "real drive times" layer is barely exercised; the live calendar's times are essentially haversine-batch output).

---

## A. Decision engine (crown jewel) — findings, prioritized

### 🔴 A1 — Batch scheduler is blind to already-assigned tasks (overbooking)
`run_batch_schedule` fetches only `status=eq.pending` tasks ([batch_schedule.py:151-155](../backend/batch_schedule.py)) and builds `day_slots`/`city_counts` from scratch. Tasks already **assigned** on a tech-day in the range are invisible: `count = len(day_slots.get(key, []))` counts only this run's placements. Consequences on any *incremental* run (the normal case now — 89 assigned + 20 pending live):
- `max_daily` can be exceeded (9 new on top of 5 existing).
- `optimize_day` sequences only the new tasks → arrival times/windows collide with existing ones.
- city-spread counters ignore existing same-city load.
The initial 108-task run was safe only because *everything* was pending.

### 🔴 A2 — Batch ignores `day_offs` (vacations)
`tech_is_working` checks tenant work-days + `weekly_schedule` only ([batch_schedule.py:203-210](../backend/batch_schedule.py)); `day_offs` is never fetched. A tech on vacation gets batch-assigned. Live path checks it (`isTechAvailable`, [index.html:4898](../index.html)) — same knob, opposite behavior by door.

### 🟠 A3 — Batch reads `arrival_window_hours` from the wrong config path
`config.get("arrival_window_hours", 3)` ([batch_schedule.py:178](../backend/batch_schedule.py)) reads **top-level**; the real key is `config.defaults.arrival_window_hours`. Verified live: top-level is NULL. PureWater gets the right answer **by coincidence** (their value = the fallback 3). Any tenant with a 2h/4h window silently gets 3h windows from batch. Israel's real cards already showed 1.5h/3h/4h variability.

### 🟠 A4 — Knobs enforced live but not in batch (the "cosmetic knob" audit)
The technicians select in batch ([batch_schedule.py:162-165](../backend/batch_schedule.py)) omits `skills`, `cat_limits`, `blocked_zones`, `blocked_cities`, `duration_overrides` — none are enforced there. Also: breaks are hard-passed empty (`breaks=[]`, [batch_schedule.py:133](../backend/batch_schedule.py)); task duration falls back to hardcoded 30 ([batch_schedule.py:284](../backend/batch_schedule.py)) instead of `defaults.regular_job_minutes`. Live `_candidatesZone` enforces all of these ([index.html:5433-5441](../index.html)). Full matrix:

| Knob | Live JS | Batch | Solver v2 |
|---|---|---|---|
| zone rotation | ✅ | ✅ | n/a |
| work_days | ✅ | ✅ | n/a |
| weekly_schedule hours | ✅ | ✅ | ✅ |
| max_daily | ✅ | ✅ (new-only, see A1) | n/a |
| day_offs full | ✅ | ❌ A2 | n/a |
| day_offs partial + break | ✅ | ❌ | ✅ (live path only) |
| cat_limits | ✅ | ❌ | n/a |
| skills | ✅ | ❌ | n/a |
| blocked_zones / blocked_cities | ✅ | ❌ | n/a |
| duration_overrides / regular_job_minutes | ✅ (zone mode) | ❌ | receives durations |
| arrival_window_hours | ✅ | ⚠ wrong path A3 | n/a |
| route_strategy far_to_near | ✅ guards | ✅ | ✅ enforced |
| route_strategy nearest_first | ✅ guards | ❌ (=flexible) | ❌ A5 |
| slot_release | ✅ (far_to_near only) | n/a by design | n/a |
| balance | ⚠ consolidates | ⚠ spreads (opposite!) | n/a |
| equal_city_distribution | ⚠ tie-breaker only | ❌ flag ignored (city-penalty always on) | n/a |
| fill_first | ⚠ partial (A8) | ⚠ not read | n/a |
| zone_strict | ✅ (hard block) | ✅ implicit | n/a |
| locked | ✅ | n/a (pending only) | ✅ |
| zone_match polygon | ✅ resolveZone | ❌ city-list only (B2) | n/a |

### 🟠 A5 — `nearest_first` is not implemented in `solve_route_v2`
The solver branches only on `far_to_near` ([optimizer.py:311-335](../backend/optimizer.py)); anything else gets flexible semantics. So for a `nearest_first` tenant: live candidate guards enforce near-first placement, then the *authoritative* sequencer (auto_sequence) re-orders the day min-drive with no near-first bias — knob honest at assignment, cosmetic at sequencing. No live client on this strategy today; still a "knob must truly enforce" violation and a documented-vs-real gap (scheduling-rules.md says it's "fully implemented" — true only for the JS guards).

### 🟠 A6 — Batch never retries optimizer-dropped tasks on another day
Greedy assigns by *count* capacity; `optimize_day` drops by *time* capacity; drops go straight to `unassigned` ([batch_schedule.py:325-327](../backend/batch_schedule.py)) without re-trying the next-best covering day that still has room. Some `day_over_capacity` flags are avoidable.

### 🟡 A7 — Placement policy contradiction (known, re-confirmed)
`balance.enabled` live (`balanceAdjust`, [index.html:5054](../index.html)) **rewards** active days = consolidate; batch `_assignment_score` ([batch_schedule.py:109](../backend/batch_schedule.py)) **prefers least-loaded** = spread. Same flag, opposite semantics; `equal_city_distribution` is a live-only tie-breaker while batch applies a same-city penalty unconditionally. Already in backlog (Sec 5B: collapse to one `placement_policy` + `same_city` read identically by both doors). Blocked on Israel's policy decision — the code fix should ride the same slice as A1/A4.

### 🟡 A8 — `fill_first` is partially cosmetic
Fill-first *scoring* (`existingInZone*100` / `count*100`) is unconditional in both paths; the flag only gates the JS min-underfull skip ([index.html:5442-5449](../index.html)) and is not read by batch at all. A tenant setting `fill_first:false` still gets fill-first packing.

### 🟡 A9 — `open`/`radius` modes ignore category durations
`_candidatesOpen`/`_candidatesRadius` use `settings.regularTime||30` ([index.html:5515](../index.html), [index.html:5680](../index.html)) — category durations and tech overrides only apply in zone mode. Wrong day-packing math for a future open/radius tenant.

### Parity infrastructure (structural, feeds the "neurons brain")
- **Alias drift is real today:** Python `_CITY_ALIASES` has `נהריה→נהרייה`, `ב"ש`, `ת"א`, `ראשל"צ`… ([batch_schedule.py:49-62](../backend/batch_schedule.py)); JS `CITY_ALIASES` has none of those but has hyphen variants + the `קריית→קרית` collapse (via `canonicalCity`) that Python lacks ([index.html:4822-4858](../index.html)). Concrete divergence: task "קריית טבעון" vs zone "קרית טבעון" → live dispatch matches, batch flags `city_not_in_zone`.
- **Four sources of geographic truth:** JS (`CITY_COORDS_JS`+`CITY_ALIASES`), Python (`cities.py`+`_CITY_ALIASES`), DB (`geo_places`+`place_aliases`). The geo-foundation design named single-authority as the goal; the frontend never got there.
- Fix direction: (1) golden shared fixtures — one `tests/fixtures/*.json` consumed by *both* the Node harness and pytest, asserting identical decisions (strategy resolution, work-day, zone match, placement score semantics); (2) serve the geo brain to the frontend (read-only RLS or endpoint) and shrink `CITY_COORDS_JS` to a bootstrap fallback; (3) `context/knobs.md` registry: config key → JS reader → Py reader → test (the impact-map lite).

---

## B. Zones

### 🔴 B1 — Polygon "didn't capture all cities" — root cause found
`_detectCitiesInPolygon` iterates **only the static `CITY_COORDS_JS`** (~255 entries, [index.html:8428-8432](../index.html)). The geo brain (`geo_places`, **423** rows incl. the ~266 PureWater cities added 06-30/07-01) is backend-only (RLS deny-all), so any city that exists only in the brain is invisible to the draw flow — it sits under the polygon and is never captured. Secondary defect: detection returns `CITY_COORDS_JS` key spellings, and `_updateZoneDrawStatus`/`confirmZoneDraw` compare raw strings against `zone.cities` — variant spellings (זיכרון יעקב vs זכרון יעקב) can duplicate. The ray-casting math itself (`_pointInPolygon`) is correct PNPOLY.
**Fix:** expose the brain read-only to the frontend (RLS `SELECT` policy for `authenticated` on `geo_places`+`place_aliases` — city coords are global, PII-free by design; or a backend `/geo/places` endpoint), detect against brain ∪ static fallback, canonicalize before comparing/adding, and add a marker-block test. Verified live: 0 polygons stored today, so the fix has no data migration.

### 🟠 B2 — Polygon mode exists only on the live JS path
Batch `find_zone` matches city-lists only ([batch_schedule.py:192-197](../backend/batch_schedule.py)); there is no Python point-in-polygon. A polygon-mode tenant's batch run would flag *everything* `city_not_in_zone`. Bulk import likewise passes null coords (documented). Polygon must be a first-class equal: mirror `resolveZone` (both axes) in Python and geocode-at-entry becomes a prerequisite for polygon tenants.

### B3 — "Do city-list + polygon together cover the whole business logic?" — Confirmed, with three caveats
As *boundary representations* the two are sufficient: city-list = discrete/manual/exact (right for PureWater's Israel-wide city service), polygon = continuous/sub-city/fringe (right for dense urban splits and the "fuzzy fringes" noted 06-27). No third geometry is needed — `radius` mode already covers the no-zones case. The caveats that must hold:
1. **Overlap determinism:** `resolveZone` returns the *first* match; PureWater's deliberate אשקלון dual-membership already makes single-answer resolution order-dependent and double-counts analytics. Need an explicit rule (e.g. rotation-day zone wins, else defined priority).
2. **Polygon ⇒ geocoding:** polygon matching is only as good as point coverage; geocode-at-entry must be on for polygon tenants (wizard should enforce the pairing).
3. **Cross-path parity:** B2 — both axes must exist in both engines.

---

## C. Tenant/tech settings + onboarding

### 🟠 C1 — The wizard configures ~40% of the knobs that exist
Wizard fields (`wc-*`): name/plan/type, labels, `mode`, route strategy, work hours, default duration, one category, admin user. **Not configurable at onboarding:** `work_days`, `arrival_window_hours`, `max_daily_jobs`, `break`, `zone_match`, `zone_strict`, `fill_first`, `balance`/placement policy, `equal_city_distribution`, `slot_release`, `lookahead`, feature flags, and all per-tech structure (rotation, weekly_schedule, skills, cat_limits, blocked, duration_overrides, base/return city). Today that gap is closed by hand-written SQL — exactly where "falls between the cracks" lives.
**Direction:** the knob matrix in A4 *is* the onboarding contract. Drive wizard + `_template.md` + onboarding SQL from one knob registry so they can't disagree (see ways-of-working: `/onboard-client` skill). Backlog items #2.10 (mandatory tech config) fold in here.

### 🟡 C2 — `_template.md` predates the current knob set
Missing rows: `work_days`, `break`, `balance`/placement, `slot_release`, `equal_city`, `zone_strict`, `fill_first`, depot coords, per-tech `min/max_daily`, `return_city`. Update alongside C1.

---

## D. Product flow & UI/UX (deliberately light this pass — engine first)
- The manual E2E/QA pass (backlog ⭐, requested 06-15) is still the top UI item — before any redesign work.
- Same-day dispatch is impossible: `getNextDates()` starts at tomorrow ([index.html:5700-5708](../index.html)). For a real dispatcher, "tech is in the area now, customer called" is a core scenario — worth a product decision.
- Explainability v1 (roadmap #2) is cheap now: the engine already returns a per-stop trace; the candidate cards could show "why this tech" from signals already computed.
- The design-system.md discipline + md-* namespace + timing.tech reference are the right frame; defer the visual pass until the engine slices above land (matches the priority order and the token budget).

---

## Security / integrity notes (no new criticals)
- Prior review's fixes verified still in place (WAL tenant stamping, `/geocode` metering, batch auth).
- `/optimize` remains unauthenticated (quota-bounded, known/accepted). Railway soft-cap 680 still pending (owner action).
- `route_cache` at 6 rows means optimizer accuracy currently rests on haversine city-centroids for nearly all legs — warming the cache (or batch-with-cache) is an *accuracy* investment, not just cost.

---

## Recommended slice order (engine first)
1. **Slice 1 — Batch correctness pack** (A1+A2+A3+A4+A6): make `/batch-schedule` enforce exactly what the live path enforces; TDD on real PureWater fixtures; dry-run diff before/after; no live writes without approval. Decision-free, pure accuracy, protects the next re-batch.
2. **Slice 2 — Polygon fix + geo brain to frontend** (B1, foundation for B2): RLS read policy + brain-backed detection + canonical add + tests.
3. **Slice 3 — Placement policy unification** (A7+A8): one `placement_policy` + `same_city` knob read identically by both doors — **after Israel's consolidate-vs-spread decision** (meeting-packet Sec 5B).
4. **Slice 4 — Honest `nearest_first` in solver** (A5) + open/radius duration fix (A9): completes "every knob truly enforces".
5. Then C1/C2 (onboarding configurator) and the D items.
