# The Major Brain — cross-tenant learning supervisor (design)

**Date:** 2026-07-14 · **Origin:** Eran's vision — "save data at tenant level, and hold a major brain
(supervisor) that says tenants 1,2,3,4 with the same conclusion ⇒ it's a general rule for all clients."
Extends [[geo-foundation-vision]]. **Status:** vision + phased plan; Phase 0 (infra seam) building now.

## The idea in one line
Every tenant learns from its own real operations (Tier 1); a supervisor promotes findings that
**several tenants independently confirm** into a global brain every new client inherits (Tier 2).

## Why it's legitimate (the privacy line)
Only **physical / geographic facts** globalize — a road leg A→B takes X minutes at time T; a zone is
chronically over-subscribed at 09:00. These are physics, non-competitive, identical for everyone.
**Never** globalize tenant business data (clients, categories, prices, volumes). Tier-1 observations
are tenant-scoped; only anonymized physical aggregates graduate to Tier 2.

## Two tiers + the supervisor
**Tier 1 — tenant observations (`route_observations`, future).** Append-only log of real learned legs:
`tenant_id, from_key, to_key, time_bucket, observed_min, source (timestamps|gps), observed_at`.
Fed by the E4-lite status timestamps (`en_route_at`/`arrived_at`/`completed_at`, shipped 2026-07-14)
+ tech GPS. Zero API cost; accuracy compounds per client.

**Tier 2 — the global brain (`route_cache`, exists today).** Promoted, trusted travel durations per
`(from_key, to_key, time_bucket)` with `source` + (future) `confidence` + `sample_count`. The optimizer
reads this. Deny-all RLS, tenant-independent — already the right shape.

**The supervisor (promotion job, future).** Periodic aggregation with a **two-store confidence model**
(same doctrine as the geo-corrections loop):
1. Within a tenant: enough consistent samples for a `(leg, bucket)` ⇒ tenant-trusted.
2. Across tenants: **N independent tenants agree** (quorum) within tolerance ⇒ promote to `route_cache`
   as `source='learned-global'` with confidence. Disagreement ⇒ stays tenant-local (real local variance,
   e.g. a depot-specific shortcut) — surfaced, not forced.
Reversible, fail-open, never blocks scheduling. A conflict between global and a tenant's own strong
signal ⇒ tenant signal wins locally (local truth beats the average).

## What this unlocks (Eran's examples)
- **Rush-hour logic** — `time_bucket` per leg: "North TLV → South TLV = 35 min @09:00 vs 18 min @11:00"
  (intra-metro legs behaving like intercity). Learned, then globalized for Gush-Dan clients.
- **Dead spots** — times/zones that consistently fail to place or run long; cross-tenant corroboration
  turns "my bad Tuesday" into "central-region 08:00 is structurally tight."
- **Seasonal / density trends** — buckets can extend to day-type/season later.

## Phasing (each phase safe + revertible)
- **Phase 0 — infra seam (BUILDING NOW).** `time_bucket` on `route_cache` (default `'static'`, PK now
  `(from_key,to_key,time_bucket)`, existing rows unchanged); `routing.traffic_mode` knob (`off`|`rush_hour`|
  `live`, **PureWater = off**) + both-engine readers + a pure `trafficBucket(mode,hhmm)` helper + golden
  fixture. Default `off` ⇒ always `'static'` ⇒ **zero behavior change**. Lays the bucket seam.
- **Phase 1 — log observations.** `route_observations` table + write from the E4-lite timestamps/GPS on
  job completion (tenant-scoped, fail-open). No consumption yet.
- **Phase 2 — tenant aggregation.** Roll observations into tenant-trusted `(leg,bucket)` durations; optimizer
  reads tenant-trusted first, then global `route_cache`, then Google/haversine. `rush_hour` mode = static ×
  per-tenant multiplier windows (zero API). `live` mode = evening re-solve of tomorrow's legs only.
- **Phase 3 — the supervisor / promotion.** Cross-tenant quorum → promote to global with confidence;
  super-admin "brain health" view (see→confirm→promote/rollback). This is the "major brain."

## Guardrails (carry from the geo/route doctrine)
Fail-open (cache/brain errors never break scheduling) · physics trust-bounds on every learned leg
(`is_trustworthy`) · high bar to enter the global brain, below-bar surfaces as work · reversible ·
knob-gated per tenant (a client can stay fully static). Cross-runtime parity: any bucket/mode logic the
optimizer uses ships in BOTH the JS live path and the Python batch path with a golden fixture.

## Open questions for later
- Quorum N and agreement tolerance (start conservative — 3 tenants, ±20%).
- Confidence decay (roads change; old samples age out).
- Whether `dead-spot` detection lives here or in the reports/insights layer (leaning: detect in reports
  per tenant, promote the *pattern* here).
