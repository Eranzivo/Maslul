# Maslul — Impact Map ("the Neurons brain")

> **What this is:** the coupling map of a system that module-graph tools can't see (one inline-JS
> `index.html` + a Python backend). The real coupling is **shared config keys, shared DB columns, and
> the same rule implemented twice (JS live path ⇄ Python batch/optimize path)**. Read the relevant row
> **before changing** any of those — then verify the paired thing so the two engines never drift.
>
> **Golden rule:** if a rule runs in BOTH engines, its two implementations MUST agree, and a shared
> **golden fixture** (asserted by both test suites) is the contract. Change one side → change the other
> → update the fixture → same commit. See [[knob-registry-parity]] · `context/knobs.md` is the registry.

---

## 1. Dual-engine parity table (these MUST agree, or scheduling breaks)
Each rule below is implemented once in JS (live: dispatch/candidate/calendar) and once in Python
(batch `/batch-schedule` + `/optimize`). The fixture is the enforced contract.

| Rule | JS (`index.html`) | Python (`backend/`) | Golden fixture (both suites) |
|---|---|---|---|
| Route strategy (far→near / nearest / flexible) | `resolveRouteStrategy` + `isPairOrdered` | `resolve_route_strategy` | sched.test.js + backend resolver tests |
| Window semantics (finish/arrive) | `resolveWindowSemantics` | `resolve_window_semantics` → `solve_route_v2` | `test_window_semantics.py` (resolver + solver) |
| Placement policy (consolidate/spread) | `resolvePlacementPolicy` + `placementScore` | `resolve_placement_policy` + `_assignment_score` | **policy-cases.json** |
| Work days | `isTenantWorkDay` | `tenant_works_day` | both suites (resolver) |
| Service duration chain | `effectiveDuration` | `_effective_duration` | **duration-cases.json** |
| Overrun tolerance | `overrunDecision` + `resolveAutoOverrunMin` | `overrun_decision` + `resolve_auto_overrun_min` | **overrun-cases.json** |
| Traffic mode / time-bucket | `resolveTrafficMode` + `trafficBucket` | `resolve_traffic_mode` + `traffic_bucket` | **traffic-cases.json** |
| Tech skills filter | `techHasSkill` | `tech_has_skill` | test_batch_correctness.py |
| Per-category daily limits | `getCatLimitOk` | `cat_limit_ok` | test_batch_correctness.py |
| Preferred-windows mode | `resolvePrefWindowsMode` | `resolve_pref_windows_mode` | **prefwindow-cases.json** |
| Per-call date constraints | JS intake + candidate gates | batch date gates | **datecons-cases.json** |
| Polygon point-in-zone | `_pointInPolygon` | `point_in_polygon` | **geo-cases.json** (zones.test.js) |
| City → place resolution | `normalizeCity` / `canonicalCity` + `CITY_ALIASES` | `city_key` + `CITY_ALIASES` + `place_aliases` (`geo_resolver`) | **geo-cases.json** (zones.test.js + test_geo_fixture.py) |
| Observation leg key | `obsLocKey` | `route_cache.norm_key` | ⚠ mirror, NOT fixture-locked — keep in sync by hand (both: coords→4dp, else trim) |
| Route-health findings | `describeHealthFindingHe`/`healthBandHe` (render only) | `route_health.*` (computes) | **health-cases.json** — Py computes, JS only renders the finding `type` contract |

**When runtimes can't share code, the fixture IS the shared implementation.** Never "fix" one side
without re-asserting the fixture on both.

## 2. Intentionally single-engine (documented asymmetries — do NOT add a mirror)
| Function | Where | Why no pair |
|---|---|---|
| `resolveReportCards`, `resolveInsightsWindow`, `durationAccuracyInsights` | JS only | display-only (reports); influence no assignment |
| `resolve_learned_durations`, `get_learned_legs` | Py only | matrix building is backend-only; live JS builds no travel matrix |
| `resolve_effective_tenant` | Py only (`batch_auth`) | server-side authz (tenant forcing) |
| `deriveLegObservation`, `stampStatusTimestamps`, `logLegObservation` | JS only | execution events happen live (status flips); batch never executes |

## 3. Config keys → consumers (`tenants.config`)
The registry with both readers + tests is **`context/knobs.md`** (source of truth). Sections:
`scheduling.*` (route_strategy, window_semantics, placement_policy, balance, equal_city_distribution,
zone_strict, zone_drop_guard, preferred_windows_mode, auto_overrun_min, work_days, max_daily_jobs,
break, lookahead_days) · `routing.*` (traffic_mode, learned_durations — **cross-tenant brain**) ·
`reports.cards` · `insights.window_days` · `audit.*` · `defaults.*` (regular_job_minutes, work_days).
**Every new knob = a knobs.md row + BOTH readers (or documented n/a) + test, same commit.**

## 4. DB table / column → readers & writers
| Table / column | Written by | Read by | Notes |
|---|---|---|---|
| `tasks.status` + `en_route_at`/`arrived_at`/`completed_at` | `stampStatusTimestamps` → `setStatus`/`techSetStatus` (JS) | `logLegObservation`, `durationAccuracyInsights`, reports | first-write-wins; E4-lite |
| `tenants.config` (JSONB) | admin/wizard (JS) + SQL onboarding | every resolver in §1/§3, both engines | THE per-tenant brain |
| `route_cache` (+`time_bucket`) | `route_cache.put_cached` (backend) | `build_matrix_cached` | global, deny-all, backend-only |
| `route_observations` | `logLegObservation` (JS, fire-and-forget) | 🧠 brain view (proposals); future supervisor | tenant-scoped, append-only |
| `route_learned_approved` | 🧠 brain view approve/revoke (JS) | `get_learned_legs` → `/optimize` | **the approval gate** — only source routing reads |
| `zones.polygons` / `cities` | zone authoring (JS) | `resolveZone`/`_pointInPolygon` (JS) + `point_in_polygon` (Py) | polygon vs city-list axis |
| `technicians` (skills, cat_limits, rotation, color, weekly_schedule) | tech edit (JS) | candidate engine (JS) + batch (Py) | color also = calendar/map/chips |
| `geo_places` / `place_aliases` / `geo_addresses` | curation + geocode | `geo_resolver` (Py) + JS resolution | global geo brain (Layer A) |

## 5. "If you change X → verify Y" quick checklist
- **A knob's meaning/default** → both readers (§1) + its fixture + knobs.md row + test. Same commit.
- **A scheduling rule** → is it in BOTH engines? Add/adjust both + the golden fixture. Run `node tests/sched.test.js`, `node tests/zones.test.js`, `cd backend && pytest`.
- **City normalization / aliases** → `normalizeCity`/`canonicalCity`/`CITY_ALIASES` (JS) AND `city_key`/`CITY_ALIASES`/`place_aliases` (Py) must agree → run **geo-cases.json** on both.
- **`route_cache` / observations / approved schema** → `route_cache.py` / `route_observations.py` + loader mapping (`loadFromSupabase`) + `context/architecture.md` + advisors after DDL.
- **Task status flow** → `STATUS_MAP` + `stampStatusTimestamps` + `logLegObservation` (dup-guard on first arrival).
- **Any new Supabase table** → `context/new-entity-checklist.md` (RLS, tenant_id, architecture.md) + advisors.
- **Tech `color`** → remember it's shared across calendar + map pins + chips (one source of truth).

## 6. Keeping this current
This map is derived from code, not memory — re-derive when in doubt (grep the resolver names in §1).
Pairs it with `context/knobs.md` (the knob registry) and the `tests/fixtures/*.json` golden files.
The motivating bug (Sec. 5B placement divergence, June) was a parity failure this table would have
flagged. Update this file in the same commit as any change to a §1 pair, a §3 knob, or a §4 table.

> 🔗 Related: [[knob-registry-parity]] · `context/knobs.md` · `context/architecture.md` · [[cross-tenant-brain]] · [[scheduling-engine-plan]]
