# Geo Foundation — Shared "Brain" + Per-Tenant Logic

> **Status (2026-06-13):** Layer-A schema **applied + seeded + verified** — `geo_places` (157
> from `cities.py`), `place_aliases` (14, incl. corrective `seed-fix` for נהריה/קרית שמונה/זיכרון
> יעקב divergences), `place_resolution_log`. Every PureWater city (tasks + zones) resolves except
> חרב. Canonicalizer (`canonicalize.py`) built + tested. **Wired (fail-safe):** `geo_resolver.py`
> loads the brain into memory (TTL-cached); `resolve()` backs the optimizer's `_parse_loc` and the
> batch `needs_location` check — brain → `cities.py` → TLV last-resort, so a brain outage degrades
> to exactly today's behavior. Backend 64/64. **Pending:** geocode-on-entry (new city → geocode
> once → store) + resolution logging. Migration: `outputs/migration-geo-foundation_2026-06-13.sql`.

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

## Canonicalization — merging spellings safely (the load-bearing part)

The same real place arrives spelled many ways: `ת"א` / `תל אביב` / `תל אביב-יפו` / `יפו`;
`נהריה` / `נהרייה`; `ב"ש` / `באר שבע`; `קרית` / `קריית`; quote vs gershayim (`"`/`״`), geresh,
hyphen/maqaf, trailing spaces; plus genuine typos (`חרב`). If these don't collapse to ONE place,
the engine gets wrong/missing distances — and because Layer A is shared, a wrong merge poisons
**every** client. So the rule is: **be eager to normalize noise, but conservative about merging.**

**Four resolution tiers, safest first — only the first three may auto-merge:**
1. **Deterministic normalization** (`normalize_place_key`): NFKC, strip gershayim/geresh/quotes
   (`ת"א`→`תא`), collapse whitespace + hyphen/maqaf (`קרית-גת`→`קרית גת`). Pure, tested, zero risk —
   it only removes punctuation noise, it does NOT decide two *different* spellings are the same.
2. **Curated aliases** (`place_aliases` table): human-blessed maps (`תא`→`תל אביב`, `בש`→`באר שבע`,
   `נהרייה`→`נהריה`, `יפו`→`תל אביב` per Eran). Authoritative, auditable, grows deliberately.
3. **Coordinate identity (the real key):** geocode → if two labels land within ~150 m they ARE the
   same place → merge. Language-agnostic, the strongest signal (`נהריה` and `נהרייה` both geocode to
   ~33.00,35.10). **Coordinates are the identity; the spelling is just a label.**
4. **Fuzzy similarity (SUGGEST ONLY, never auto-merge):** edit-distance near-misses surface as
   "did you mean X?" for a human to confirm. This is where `בלפוריה`≈`פוריה`-type traps live, so it
   must never auto-apply.

**Streets:** don't try to canonicalize free-text street strings — **geocode the full address to
coordinates** and let the coords be the identity. The string is only for display.

**Guardrails (think-double):**
- Auto-merge ONLY on exact-normalized, curated-alias, or coordinate-proximity. Fuzzy = suggest.
- **Provenance on every place** (source: geocoded/manual/alias; who/what confirmed) → merges are
  auditable and **reversible**. Never a destructive merge.
- **Single authority:** resolution lives in ONE backend module (`canonicalize.py`), not duplicated
  in JS — the JS/backend split is exactly what caused the `נהריה`/`נהרייה` false-flag. Frontend defers.

**Monitoring (so we catch problems before they corrupt routes):**
- Log every resolution: `input → key → canonical, method (exact|alias|geocode|fuzzy-suggested|failed),
  confidence`. Surface a small report: unresolved inputs, low-confidence matches, pending fuzzy
  suggestions, and any place whose coords moved. Review before anything auto-merges at scale.

## Recommended first step
Promote `cities.py` → `geo_places` table + geocode-on-add. Highest-value foundation piece, and it
directly removes the coordinate friction we just hit. Worth doing **before client #2** so the brain
starts accumulating from a real schema. Then add `route_observations` logging (passive) to seed the
learning layer.
