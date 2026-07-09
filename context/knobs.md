# Knob Registry — every per-tenant rule, who reads it, who proves it

> **The onboarding contract.** A business rule exists in Maslul only if it has a row here.
> Every row must be enforced by BOTH engine doors (live JS + Python batch) or explicitly
> marked why not. **Adding a knob = adding a row in the same commit** (living-docs rule),
> wiring both readers, and adding a test. The `/onboard-client` flow walks this table so
> nothing falls between the cracks. Seeded from the 2026-07-05 enforcement audit
> (`outputs/product-review-fable_2026-07-05.md` §A4).

Legend: ✅ enforced · ⚠ caveat (see note) · n/a not applicable to that layer.

## tenants.config.scheduling
| Knob | Meaning | Live JS reader | Batch reader | Solver | Test |
|---|---|---|---|---|---|
| `mode` (zone/open/radius) | assignment strategy | `buildCandidates` | zone-only today (⚠ open/radius batch unsupported) | n/a | zones.test.js |
| `zone_match` (city_list/polygon) | zone boundary type | `resolveZone` | `find_zone_for` — both axes ✅ 2026-07-05 (`point_in_polygon` mirror; reasons `not_geocoded`/`outside_all_polygons`) | n/a | zones.test.js + test_batch_correctness.py + shared polygon fixture |
| `zone_strict` | hard cross-zone block | `_candidatesZone` + `zoneDropDecision` | implicit (rotation filter) | n/a | zones.test.js |
| `route_strategy` (flexible/far_to_near/nearest_first) | day route direction | `resolveRouteStrategy` + guards | `resolve_route_strategy` | ✅ both non-flexible enforced (direction penalty) | sched.test.js + test_sequencing.py |
| **`placement_policy`** (consolidate/spread) | THE placement philosophy (Israel handover 07-06: consolidate) | `resolvePlacementPolicy`+`placementScore` (zone+open) | `resolve_placement_policy`+`_assignment_score` | n/a | policy-cases.json fixture BOTH suites + e2e ✅ 2026-07-06 |
| `balance {enabled,weight}` | LEGACY → maps to `spread` (weight kept as tunable) | via resolver | via resolver | n/a | fixture |
| **`preferred_windows_mode`** (hard/soft, default hard) | customer-availability enforcement (handover §8: HARD). Task windows `{from,to,days[]}` (days Sun=0..Sat=6, absent=all days): hard ⇒ disallowed days filtered from candidacy, non-matching slots disabled, batch narrows solver window, reason `no_preferred_window_day`; soft ⇒ legacy highlight-only | `resolvePrefWindowsMode` + `prefWindowAllowsDay/Range` (`buildCandidates` date filter + slot gating) | `resolve_pref_windows_mode` + `pref_allows_day/range` (`place_task` day gate + solver window narrowing) | ✅ window_start/end hard | prefwindow-cases.json fixture BOTH suites + e2e ✅ 2026-07-06 |
| `equal_city_distribution` | LEGACY tie-breaker — honored under consolidate only; spread has same-city built in | `_candidatesZone` | folded into spread scoring | n/a | — |
| `fill_first` | LEGACY — consolidate IS fill-first; flag now gates only the min-underfull skip | `_candidates*` | n/a | n/a | — |
| `slot_release {enabled,72/48/24}` | hold early slots for far cities | `_candidatesZone` (far_to_near only) | n/a by design (assigns whole days) | n/a | manual |
| `zone_drop_guard` | soft warn on manual cross-zone drop | `zoneDropDecision` | n/a (no manual path) | n/a | zones.test.js |
| `route_strict` (default false) | manual drop over-capacity OR no route-valid slot: false ⇒ soft warn (coordinator may override), true ⇒ hard block | `capacityDropDecision` (3 manual paths; route-fit via `calcOptimalTime`) | n/a by design — batch solver is capacity/route-hard (drops overflow) | n/a | zones.test.js |
| `gap_fill {enabled,auto}` | suggest fills on cancel | `rankGapFill` | n/a | n/a | sched.test.js |

## tenants.config.defaults
| Knob | Meaning | Live JS | Batch | Solver | Test |
|---|---|---|---|---|---|
| `work_days[]` | tenant operating weekdays | `isTenantWorkDay` | `tenant_works_day` | n/a | both suites (golden mirror) |
| `work_start`/`work_end` | fallback day hours | `getTechDaySchedule` | `tech_hours` | ✅ horizon | test_batch_correctness.py |
| `arrival_window_hours` | customer window length (fractional ok) | `settings.window` | `_arrival_window_hours` (defaults path — fixed 2026-07-05) | n/a | test_batch_correctness.py |
| `regular_job_minutes` (category time is the real driver) | tenant fallback duration | `effectiveDuration` (THE one resolver — all live spots route through it 2026-07-08) | `_effective_duration` | ✅ service times | duration-cases.json fixture BOTH suites (sched.test.js + test_duration_parity.py) |
| `max_daily_jobs` | fallback per-tech cap | `_candidates*` | `tech_max_daily` | n/a | test_batch_correctness.py |
| `break {enabled,start,end}` | tenant default break | `getTechPartialBlocks` | `tech_breaks` (+clamped to hours) | ✅ pinned pseudo-node | both |
| `lookahead_days` | candidate search horizon | `getNextDates` | n/a (explicit range) | n/a | — |

## tenants.config.audit (Route Intelligence P1 — 2026-07-09)
| Knob | Meaning | Live JS | Batch/Py | Solver | Test |
|---|---|---|---|---|---|
| `audit.enabled` (default false) | store route_audits rows: on `/optimize` (trigger=change, needs the JWT the app now sends), `/audit-day`, nightly 02:30-UTC sweep | display-only **by design** — JS renders stored rows (`healthChipHtml`, `openHealthPanel`), never computes | `main._resolve_audit_context` gate + `audit_sweep.run_audit_sweep` tenant filter | n/a | test_route_audit_flow.py |
| `audit.health_weights {…}` | per-component score weights (excess-drive/backtrack/lateness/idle/overtime/window + `reorder_min_saving` noise floor). Violation DEFINITIONS are system invariants — only weights are tunable | display-only by design | `route_health.DEFAULT_WEIGHTS` merge in `compute_health` (unknown keys ignored) | n/a | health-cases.json fixture (weights-override case) |

> **Health computation is Python-ONLY** (`backend/route_health.py`) — the deliberate exception
> to both-doors: one implementation means no parity to maintain; JS is a reader of
> `route_audits`. If a JS preview computation is ever added, `tests/fixtures/health-cases.json`
> becomes its parity contract. **Window semantics: ARRIVAL** — a stop violates only when its
> scheduled start falls outside [window_start, window_end]; service may end after the window
> (Israel replay 2026-07-09: finish-inside semantics falsely flagged 10/89 real stops). Note
> the solver is stricter when *placing* (finish-inside) — known asymmetry, deliberate.

> **Duration chain (unified 2026-07-08):** ONE resolver both doors — `effectiveDuration(catId,tech,categories,settings)` (JS) ⇄ `_effective_duration` (Py): per-tech override → **category time** → `regularTime` → 30. Every live spot (optimize payload, `calcOptimalTime`, candidate slot math, confirm-assign stacking, weekly/daily/monthly calendar block heights) routes through it — previously several ignored category time / tech override (live↔batch parity bug, fixed). **No per-call duration override by design** (Eran 2026-07-08 — durations are a per-tenant category-level setup decision; ad-hoc per-call values invite miscalculation). Parity locked by `tests/fixtures/duration-cases.json`.

## technicians.* (per-tech knobs)
> **Mandatory at creation (2026-07-07):** `name`, `phone`, `base_city`, `return_city`, `skills[]`,
> ≥1 working day, `max_daily≥1` (+`rotation` for zone tenants) are enforced by pure
> `techCompleteness(f,usesZones)` — `saveTech` blocks + flags any missing engine-critical field.
> Test: sched.test.js `techCompleteness`.

| Knob | Meaning | Live JS | Batch | Solver | Test |
|---|---|---|---|---|---|
| `rotation {dow: zone_id}` | weekday→zone | `getTechZoneId` | `tech_zone_for_day` | n/a | test_batch_correctness.py |
| `weekly_schedule {dow:{work,start,end}}` | per-day hours/off | `getTechDaySchedule` | `tech_is_working`/`tech_hours` | ✅ | both |
| `weekly_schedule._break` | per-tech break override | `getTechPartialBlocks` | `tech_breaks` | ✅ | both |
| `max_daily` / `min_daily` | daily caps | `_candidates*` | `tech_max_daily` (min: JS only ⚠) | n/a | test_batch_correctness.py |
| `skills[]` | allowed categories (empty = none, JS semantics) | `techHasSkill` | `tech_has_skill` | n/a | test_batch_correctness.py |
| `cat_limits {cat:n}` | per-category daily cap | `getCatLimitOk` | `cat_limit_ok` (existing+new) | n/a | test_batch_correctness.py |
| `blocked_cities[]` / `blocked_zones[]` | exclusions | `isCityBlocked` / `_candidatesZone` | `city_blocked`/`zone_blocked` | n/a | test_batch_correctness.py |
| `duration_overrides {cat:min}` | per-tech per-category duration (top of the chain) | `effectiveDuration` | `_effective_duration` | ✅ | duration-cases.json BOTH suites |
| `base_city` / `return_city` | depot / end depot | `_postOptimize` | day loop | ✅ two-depot | test_optimizer.py |

## tasks.* (per-call constraints)
| Knob | Meaning | Live JS | Batch | Solver | Test |
|---|---|---|---|---|---|
| `locked` + `scheduled_time` | coordinator pin | `splitLockedFlexible`/payload | existing-call policy | ✅ pinned, never dropped | test_sequencing.py |
| `scheduled_window_start/end` | customer promise | payload | existing-call policy (hard) | ✅ may wait | test_sequencing.py + test_batch_correctness.py |
| `lat`/`lon` | exact coords beat city centroid | `buildSequencePayload` | `_loc` | ✅ matrix | test_optimizer.py |
| `earliest_date`/`latest_date`/`fixed_date` | structured date constraints (Israel's cards) | `dateConstraintAllows` (buildCandidates gate) | `date_constraint_allows` (place_task gate) | ✅ removes disallowed dates | datecons-cases.json BOTH suites |
| `preferred_windows {from,to,days[]}` | customer availability (day-aware) | `prefWindowAllowsDay/Range` | `pref_allows_day/range` | ✅ hard window | prefwindow-cases.json BOTH suites |
| `manually_overridden` + `override_reason` | coordinator override of a soft placement guard (out-of-zone / over-capacity / no route-fit) — required reason, **audited via `_audit_tasks` trigger → audit_log** | `overrideStamp` + `guardManualPlacement` (3 manual paths) + `promptOverrideReason` | n/a (batch never overrides — solver-hard) | n/a | sched.test.js `overrideStamp` |

## Day-offs & shared geo
- `day_offs` (full/partial) — live `isTechAvailable`/`getTechPartialBlocks`; batch `tech_is_working`/`tech_breaks` (schema-tolerant: missing `type` ⇒ full). ✅ both since 2026-07-05.
- Place identity/coords — `geo_places`+`place_aliases` are the ONE source (JS `cityMatchKey` ↔ Py `_match_key`, golden fixture `tests/fixtures/geo-cases.json`); static lists = offline fallback only. See `context/zones-polygons.md`.

## Wizard coverage gap (C1 — drives the onboarding work)
Wizard configures today: name/plan/labels/mode/route/hours/one category/admin. **Everything else in this registry is SQL-set at onboarding** until the wizard catches up — which is exactly what `/onboard-client` exists to make safe.

---
> 🧠 [[maslul-brain.canvas|Brain map]] · Related: [[scheduling-rules]] · [[architecture]] · [[purewater]] · [[scheduling-scenarios]]
