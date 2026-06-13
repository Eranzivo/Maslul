# Geo Corrections Loop — Self-Healing Place Brain (Design)

> **Status (2026-06-13):** Design / spec. Builds on the live geo foundation
> (`geo_places`, `place_aliases`, `place_resolution_log`, [geo_resolver.py](../backend/geo_resolver.py),
> [canonicalize.py](../backend/canonicalize.py)). See [geo-foundation-design_2026-06-13.md](geo-foundation-design_2026-06-13.md)
> for the two-layer architecture this sits inside.

**Goal:** Turn the geo brain from *safe-but-dumb* into *safe-and-self-improving* — log what it
can't resolve, let a non-technical owner fix it in one place, learn the fix forever, and heal
from technician GPS over time. **Without changing the routing engine.**

---

## Scope & non-goals

**In scope (additive only):**
- Writing to `place_resolution_log` (failures + low-confidence + applied fixes).
- A `confidence` model that gates what becomes a trusted shared fact.
- A super_admin **Geo Health** page: see → fix → save → re-assign → log.
- Passive **technician-GPS** healing of stored coordinates.
- Observability: `/health` geo counters + on-demand digest outputs.

**Explicit non-goals (guardrails):**
- **Does NOT change `solve_route` / the optimizer hot path.** Resolution stays fail-open and
  behaviourally identical; logging is a best-effort side-effect that must never raise into routing.
- **Does NOT block data entry.** A missing/approximate pin is a soft flag — the technician has the
  client's phone in the call details and can verify and drive. Geography never stops a call.
- **Does NOT auto-merge on weak signals.** Below the confidence bar, nothing enters the brain;
  it surfaces as work instead.
- Streets are not canonicalized as strings — full address → coordinates; the string is display only.

---

## The two-store confidence model (the core idea)

One confidence threshold, applied to **opposite sides** for two different stores:

- **The brain (`geo_places` — trusted facts every tenant inherits).**
  A place/coordinate enters here **only above a high confidence bar**. A shaky guess must never
  become a "fact" that poisons every client. High bar to *enter.*
- **The corrections queue (the diagnostics — the to-do list).**
  The **failed and low-confidence** resolutions are exactly what we log here, because that's the
  list a human fixes. High-confidence resolutions are correct and silent — not logged.

> Gate what becomes a *fact* by confidence; surface what's *below* it as work. Same threshold,
> two sides of it.

### Confidence bands

| Band | Source / method | Goes to brain? | Logged? | UI flag |
|---|---|---|---|---|
| **Verified** | technician GPS confirmed, or human pin | yes | on change only | ✓ |
| **High** | exact key / curated alias / coord-proximity ≤150m | yes | no | ✓ |
| **Approximate** | city-centroid fallback for an un-geocodable address | used for routing, marked | yes | ⚠ approximate |
| **Suggested** | fuzzy near-miss ("did you mean X?") | **no** (never auto) | yes | ⚠ needs confirm |
| **Failed** | resolves to nothing | no | yes | ⚠ needs location |

Thresholds live in **one named place** (a `geo` block in config / a constants module), never as
scattered magic numbers, so they're auditable and tunable.

---

## Resolution + logging flow

Resolution itself is unchanged (normalize → alias → exact → `cities.py` → None, fail-open). We add
a **non-blocking** log write *after* the decision:

```
resolve(name) -> (coords, method, confidence)
   if confidence >= HIGH:  use silently            # correct + quiet
   elif Approximate:       use city centroid, log "approximate"
   elif Suggested/Failed:  flag needs_location, log it    # -> corrections queue
```

The log row records: `tenant_id, input_raw, normalized_key, matched_key, method, confidence,
coords_used, call_id, created_at`. Logging is best-effort and wrapped — a logging failure can never
affect scheduling.

**When a fix is applied** (below), we log a second kind of row: `action=fix, input_raw,
chosen_key, coords, by_user, before→after`. So the log holds both **what broke** and **what fixed
it** — the raw material for learning.

---

## The corrections loop — "saved, fired, logged"

A single **Geo Health** page, super_admin (Eran sees every tenant in one place; reads DB only):

1. **See** — every `failed` / `approximate` / `suggested` place, with the affected call(s), the raw
   string typed, what we guessed (if anything), and why it's flagged. A "needs attention: N" badge.
2. **Fix** — pick the canonical city from the typeahead, **or** drop a pin on the map (one-time
   geocode allowed here). Homonyms surface as 2 options disambiguated by region.
3. **Save** — writes the place to `geo_places` at **Verified** confidence **and** the raw string →
   canonical as an alias. Future occurrences resolve automatically, across tenants.
4. **Fire** — every current call matching that string re-resolves and re-sequences.
5. **Log** — who / when / before→after. **Auditable and reversible — never a destructive merge.**

Fix `קרת גת` once → it's an alias forever, for everyone. The brain learns from the correction
instead of asking again. **Fix propagation:** one correction silently cleans every matching call,
current and future, every tenant.

### Global vs per-tenant
`geo_places` (objective geography) stays **global, PII-free, shared** — `באר שבע` is `באר שבע` for
everyone, so client #2 inherits it free. Private shorthand ("the north depot", a customer nickname)
is **tenant-scoped** via an optional `tenant_id` on aliases (NULL = global, set = private) so one
tenant's slang never pollutes the shared brain.

---

## Technician GPS as ground truth (self-healing)

We already capture tech GPS + job-completion timestamps. When a job is marked done, the tech's pin
**is** the real coordinate:
- If it's close to our stored guess → quietly **upgrade** that place toward Verified.
- If it's far → surface it in the queue as "stored location looks wrong" (or, for a genuinely
  un-geocoded address, adopt the GPS pin at Verified).

This closes the loop: **the field work itself verifies and heals the brain**, with zero extra effort
from anyone. Implemented as a passive/async check off completion events — **not** in the routing path.

---

## Observability — three lenses on one log

All driven by `place_resolution_log` + `geo_places` + `place_aliases`. No external calls.

1. **Operational (technician / coordinator)** — in-app call details always show client + phone; soft
   flags only. Never blocked.
2. **Owner, non-technical (Israel / you)** — the **Geo Health** page (fix things) + a "needs
   attention" badge. Plus `/health` geo counters for an at-a-glance number:
   `geo_places_count, aliases_count, unresolved_today, approximate_today, fixes_today`.
3. **Builder + AI (you in VSCode, me via Supabase MCP)** — I query the log and return an on-demand
   **digest** to `outputs/geo-digest_[date].md`: top unresolved strings, low-confidence places,
   coords that moved, pending fuzzy suggestions, fix-rate over time, and concrete recommendations
   ("12 calls used 3 spellings of `באר שבע` — alias them?") that you approve in the queue with one
   click. This is the *monitor → learn → suggest → output* loop.

### How the human stays in control (no code needed)
- **Visually:** the Geo Health page — fix, save, re-assign.
- **One URL:** `/health` shows the geo counters next to the existing call counters.
- **Through me:** "how's the geo brain doing?" → I run the log and hand back a plain-language digest
  with suggestions. Nothing auto-applies; you decide.

---

## Data model touches (small, additive)

- `geo_places`: add `confidence` (text/enum) + `provenance` (geocoded | manual | gps | alias) +
  `verified_at`. (`source` already exists.)
- `place_aliases`: add optional `tenant_id` (NULL = global).
- `place_resolution_log`: start writing to it (table already exists); columns above.
- `tasks`: no new columns required — `needs_location` flag already exists; approximate calls reuse it
  plus the stored centroid coords.

No RLS model change: `geo_places` / `place_aliases` / log stay service-key / super_admin only,
PII-free; the corrections page is super_admin (already bypasses RLS).

---

## Guardrails (think-double)

- **Hot path untouched** — logging is best-effort, wrapped, async-safe; a log error never reaches
  routing. Resolution behaviour is byte-identical to today for known cities.
- **High bar to enter the brain** — only Verified/High/coord-proximity become facts; Suggested never
  auto-applies.
- **Reversible** — every merge has provenance + who/when; undo is always possible. No destructive merge.
- **PII-free Layer A** — places & travel only; customer data never enters the shared brain.
- **Single authority** — resolution stays in the backend ([canonicalize.py](../backend/canonicalize.py)
  / [geo_resolver.py](../backend/geo_resolver.py)); the frontend defers (this split is what caused the
  original `נהריה`/`נהרייה` false-flag).

---

## Phasing (safest-first)

1. **Logging on** — write `place_resolution_log` for approximate/suggested/failed + the `confidence`
   column on `geo_places`. Pure observation, zero risk. Gives us eyes immediately.
2. **Geo Health page** — the see → fix → save → fire → log loop (super_admin). The visible win for
   Israel; kills typos where data enters.
3. **Digest output** — I generate `outputs/geo-digest_[date].md` on demand from the log.
4. **Typeahead-constrained city input** at the human doors (zone editor, polygon, assign, calls) —
   prevent the mess at the source.
5. **Bulk-door fuzzy + centroid ladder** — once we've watched the logs.
6. **GPS ground-truth healing** — passive, off completion events.

Steps 1–3 are observation/UI and touch nothing in routing. 4–6 layer in after we trust the data.

---

## Open decisions

- Confidence threshold value(s) — start conservative (proximity ≤150m = High) and tune from the log.
- Where the threshold constant lives — `tenants.config.geo` vs a backend constants module (lean: a
  global default in code, per-tenant override in config only if a client ever needs it).
- Digest cadence — on-demand only to start; consider a weekly auto-output once the log has volume.
