# Geo Foundation — Shared "Brain" + Per-Tenant Logic

**Eran's aim (2026-06-13):** every city any client enters should be saved — coordinates,
distances/times between cities, eventually traffic patterns — so the system *learns* an area's
movement and **reuses that knowledge across all clients**. The optimizer's *physics* is shared;
its *direction* (business rules) differs per client. Build this into the foundations = rock solid.

## The clean model: two layers

**Layer A — Geo/Physics brain (GLOBAL, tenant-independent, accumulating).**
True for everyone regardless of who asks:
- **Places:** city/address → canonical coordinates.
- **Travel:** coordinate-pair → drive minutes.
- **Patterns (future):** time-of-day / day-of-week travel, learned from real jobs.

**Layer B — Business logic (PER-TENANT, configured per client).**
- route_strategy, zones, windows, slot_release, balance, max_daily, breaks, durations, categories.

**The optimizer = A composed with B.** PureWater uses the shared travel brain but applies
far→near + zones + windows; client #2 uses the *same* brain with different rules (maybe
nearest-first + radius). That's what makes it "different per client" while the brain is shared.

## Where we already are (~70%)
- **`route_cache`** IS Layer-A travel — global, tenant-independent, deny-all RLS, service-key only,
  fail-open. Cache hits cost 0 Google quota. ✅
- **`tenants.config`** IS Layer B — per-tenant rules, absent = safe defaults. ✅
- So the architecture exists; the gap is **places** and **learning**.

## Gaps → the plan

**1. Promote places to a persistent shared table (`geo_places`).**
Today coordinates live in a static `backend/cities.py` dict — so a new settlement is missing until
we hardcode it (the 16 we just hit; חרב flagged). Instead:
- `geo_places(name_canonical, lat, lon, source, confidence, created_at)` — tenant-independent.
- Seed from the current `cities.py` (200+) + the 15 we added.
- **Geocode-on-entry:** when a coordinator adds a task with a new city/address, geocode it once
  (Google) → store lat/lon on the task AND in `geo_places` → available to every client forever.
- `resolve_coords` reads the table (memory-cached); `needs_location` fires only when geocoding
  genuinely fails (bad input / typo like חרב). Dedupe spellings via the existing alias/canonical
  layer so נהריה/נהרייה never splits.

**2. `route_cache` stays as Layer-A travel.** No change — already correct.

**3. Learn from actuals (Phase 2 — the real differentiator).**
We already capture tech GPS + job completion timestamps. Log the *actual* travel between
consecutive completed jobs into `route_observations`, then blend with Google estimates and bucket
by time-of-day/day-of-week. Over time the brain reflects *real* local conditions (a leg Google
calls 20 min that's always 35 in morning traffic). **Start by just logging now** (cheap); use later.

## Guardrails that keep it rock-solid
- **Strict layer separation:** onboarding a client = writing config (B), never touching geo (A).
  The brain only grows; it never forks per client.
- **Privacy boundary:** Layer A holds only *places and travel times* — never customer/client data.
  Physics is shareable; personal data is not. (Keep `route_cache`/`geo_places` PII-free.)
- **Provenance/confidence** on each place (geocoded vs manual vs approximate) so we know what to
  trust and what to refine.
- **Geocode at entry, not at optimize** — one-time cost, better UX, optimizer never guesses.

## Recommended first step
Promote `cities.py` → `geo_places` table + geocode-on-add. Highest-value foundation piece, and it
directly removes the coordinate friction we just hit. Worth doing **before client #2** so the brain
starts accumulating from a real schema. Then add `route_observations` logging (passive) to seed the
learning layer.
