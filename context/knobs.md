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
| `fill_first` | pack active days before opening new | ⚠ partial — scoring unconditional, flag gates only min-underfull skip | ⚠ not read | n/a | — (Slice 3: fold into placement_policy) |
| `balance {enabled,weight}` | workload spread | ⚠ `balanceAdjust` consolidates | ⚠ `_assignment_score` spreads — OPPOSITE semantics | n/a | test_batch_schedule.py (Slice 3 unifies) |
| `equal_city_distribution` | split same-city across techs | ⚠ tie-breaker only | ⚠ flag ignored (penalty always on) | n/a | — (Slice 3) |
| `slot_release {enabled,72/48/24}` | hold early slots for far cities | `_candidatesZone` (far_to_near only) | n/a by design (assigns whole days) | n/a | manual |
| `zone_drop_guard` | soft warn on manual cross-zone drop | `zoneDropDecision` | n/a (no manual path) | n/a | zones.test.js |
| `gap_fill {enabled,auto}` | suggest fills on cancel | `rankGapFill` | n/a | n/a | sched.test.js |

## tenants.config.defaults
| Knob | Meaning | Live JS | Batch | Solver | Test |
|---|---|---|---|---|---|
| `work_days[]` | tenant operating weekdays | `isTenantWorkDay` | `tenant_works_day` | n/a | both suites (golden mirror) |
| `work_start`/`work_end` | fallback day hours | `getTechDaySchedule` | `tech_hours` | ✅ horizon | test_batch_correctness.py |
| `arrival_window_hours` | customer window length (fractional ok) | `settings.window` | `_arrival_window_hours` (defaults path — fixed 2026-07-05) | n/a | test_batch_correctness.py |
| `regular_job_minutes` / `package_job_minutes` | default durations | duration chain | `_effective_duration` | ✅ service times | test_batch_correctness.py |
| `max_daily_jobs` | fallback per-tech cap | `_candidates*` | `tech_max_daily` | n/a | test_batch_correctness.py |
| `break {enabled,start,end}` | tenant default break | `getTechPartialBlocks` | `tech_breaks` (+clamped to hours) | ✅ pinned pseudo-node | both |
| `lookahead_days` | candidate search horizon | `getNextDates` | n/a (explicit range) | n/a | — |

## technicians.* (per-tech knobs)
| Knob | Meaning | Live JS | Batch | Solver | Test |
|---|---|---|---|---|---|
| `rotation {dow: zone_id}` | weekday→zone | `getTechZoneId` | `tech_zone_for_day` | n/a | test_batch_correctness.py |
| `weekly_schedule {dow:{work,start,end}}` | per-day hours/off | `getTechDaySchedule` | `tech_is_working`/`tech_hours` | ✅ | both |
| `weekly_schedule._break` | per-tech break override | `getTechPartialBlocks` | `tech_breaks` | ✅ | both |
| `max_daily` / `min_daily` | daily caps | `_candidates*` | `tech_max_daily` (min: JS only ⚠) | n/a | test_batch_correctness.py |
| `skills[]` | allowed categories (empty = none, JS semantics) | `techHasSkill` | `tech_has_skill` | n/a | test_batch_correctness.py |
| `cat_limits {cat:n}` | per-category daily cap | `getCatLimitOk` | `cat_limit_ok` (existing+new) | n/a | test_batch_correctness.py |
| `blocked_cities[]` / `blocked_zones[]` | exclusions | `isCityBlocked` / `_candidatesZone` | `city_blocked`/`zone_blocked` | n/a | test_batch_correctness.py |
| `duration_overrides {cat:min}` | per-tech durations | duration chain (all 3 modes) | `_effective_duration` | ✅ | test_batch_correctness.py |
| `base_city` / `return_city` | depot / end depot | `_postOptimize` | day loop | ✅ two-depot | test_optimizer.py |

## tasks.* (per-call constraints)
| Knob | Meaning | Live JS | Batch | Solver | Test |
|---|---|---|---|---|---|
| `locked` + `scheduled_time` | coordinator pin | `splitLockedFlexible`/payload | existing-call policy | ✅ pinned, never dropped | test_sequencing.py |
| `scheduled_window_start/end` | customer promise | payload | existing-call policy (hard) | ✅ may wait | test_sequencing.py + test_batch_correctness.py |
| `lat`/`lon` | exact coords beat city centroid | `buildSequencePayload` | `_loc` | ✅ matrix | test_optimizer.py |
| structured constraints (earliest/latest/fixed_date/approval/contact) | Israel's real cards | ❌ future — free-text notes today | ❌ | ❌ | backlog |

## Day-offs & shared geo
- `day_offs` (full/partial) — live `isTechAvailable`/`getTechPartialBlocks`; batch `tech_is_working`/`tech_breaks` (schema-tolerant: missing `type` ⇒ full). ✅ both since 2026-07-05.
- Place identity/coords — `geo_places`+`place_aliases` are the ONE source (JS `cityMatchKey` ↔ Py `_match_key`, golden fixture `tests/fixtures/geo-cases.json`); static lists = offline fallback only. See `context/zones-polygons.md`.

## Wizard coverage gap (C1 — drives the onboarding work)
Wizard configures today: name/plan/labels/mode/route/hours/one category/admin. **Everything else in this registry is SQL-set at onboarding** until the wizard catches up — which is exactly what `/onboard-client` exists to make safe.
