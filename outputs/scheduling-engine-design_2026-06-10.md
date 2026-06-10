# Scheduling Engine Generalization — Design Spec

> Date: 2026-06-10 · Workstream 2 of the Maslul foundation (after Zones & Polygons).
> Status: design approved, pending spec review → implementation plan.

## Goal

Make the Maslul scheduling engine produce **real, drive-time-optimal routes** for every tenant, with every route strategy **real and honest**, while staying **per-tenant configurable, incremental, reactive, manually overridable, and safe** — no change here may alter another tenant's behavior or leak into other sections.

This builds on the existing two-axis zone model (`scheduling.mode` × `scheduling.zone_match`) and the `resolveZone()` seam from the Zones & Polygons workstream.

---

## 0. Dispatcher requirements (PureWater spec) → coverage

North star (universal): **behave like an expert dispatcher.** The optimizer's priority order — **(1) correct route direction → (2) full-day utilization → (3) prevent lateness → (4) cut fuel/travel → (5) pick the tech** — is the objective ranking Plan B's sequencer must encode. PureWater's far→near, 3-hour windows, zones-per-day, and 72/48/24h release are tenant *knobs* toward it (already config-gated). Full rules: `context/scheduling-rules.md`.

| Requirement | Where addressed |
|---|---|
| Correct route direction, no far→near→far | §1 sequencing (TSP) + Plan A strategy guards (shipped) |
| 3-hour window = reserved capacity for **insertion** of more nearby jobs | §3 gap-fill (cheapest-insertion) + §6 windows as hard constraints |
| Reserved capacity / progressive 72-48-24h release | `slot_release` (PureWater config, shipped Plan A) |
| Fill partial/active days before opening a new tech-day (Michael-Sun vs Eliran-Thu) | §2 assignment scoring `fillScore` + weekly balance; **strengthen so cross-tech fill beats opening a far empty day** |
| Dynamic route calc on new job (travel, duration, window, direction, load, traffic) | §1 + §5 cache (real drive times) + §6 `sequenceDay` |
| Per-tech base/return depot drives routing | shipped (return_city end-depot) |
| No unrestricted manual time selection that breaks routes | §4 locks are **per-tenant-gated** (`features.manual_override`); PureWater may keep it off/constrained; conflicts always surfaced |
| **Changes from UI OR backend are stored & stay consistent** | §6 epoch + optimistic-version guards; all writes awaited (data-persistence rule); batch/optimizer write-back to same rows |

This section is the acceptance checklist for Plan B.

---

## 1. Core architecture: assignment vs. sequencing

The root cause of the observed zigzag (Kiryat Gat mid-day, Tel Aviv in-and-out) is that the JS engine both *assigns* and *orders* tasks, using a far-to-near heuristic that linearizes 2-D geography onto a 1-D "index in zone" from haversine distance. The OR-Tools optimizer (real drive times) only runs on a manual button press.

**Fix: split the two responsibilities.**

- **Assignment (JS, config-driven)** — decides *which tech + which day*. `buildCandidates` / `_candidatesZone|Open|Radius`: zone matching, fill-first, category limits, blocked zones, availability, **workload balance**. Unchanged in spirit.
- **Sequencing (authoritative, OR-Tools)** — decides *order + arrival times within a tech-day*. Always a real min-drive-time TSP. **Single source of truth** for the calendar. The JS heuristic no longer sets final order.

### `route_strategy` redefined

It stops being a hard JS ordering gate (and stops lying — `nearest_first` currently does nothing). It becomes a **secondary objective/bias** on top of an always-optimal min-drive route:

| Strategy | Sequencing | Secondary behavior |
|---|---|---|
| `flexible` (**new safe default**) | Pure min-drive TSP | None |
| `far_to_near` (PureWater) | Min-drive TSP | Enables slot-release reservation + far-first tie-break |
| `nearest_first` | Min-drive TSP | Near-first tie-break / bias |

The JS `isRouteLogical` / `wouldBacktrack` checks downgrade to **cheap, strategy-aware assignment-time sanity guards** (reject an obviously-bad day before calling the optimizer), not the final word.

**Two safety fixes fall out:**
1. `nearest_first` becomes real (actual near-first bias, not silent flexible).
2. Unsafe default flips: absent `route_strategy` ⇒ `flexible`, never `far_to_near`. A config audit confirms PureWater has `far_to_near` set explicitly **before** the flip.

---

## 2. Online, state-aware, balanced assignment

Clients add calls **one at a time across a week** — this is the normal path, not bulk. Every single dispatch re-runs `buildCandidates` against live state. Added: a **workload-balance term** in the candidate score, mode-aware:

- **zone mode (PureWater):** day-of-week rotation distributes techs structurally; balance is a **tie-breaker** among eligible days so one tech's day doesn't overfill while another's idles.
- **open / radius modes:** explicit per-tech load balancing is the primary signal — next call goes to the tech genuinely freest *now* (current load, blockers, category limits, availability).

**Balance is weekly, not daily** — the term looks across the lookahead window so a tech isn't loaded every day while another idles.

Config: `scheduling.balance = { enabled, weight }` (default off → today's fill-first behavior preserved).

---

## 3. Reactive re-sequencing + gap-fill

Driven off one signal: **"this tech-day changed."**

- **Cancel / delay-within-day** → day marked dirty → auto-sequencer re-runs the TSP on remaining jobs → route **tightens** (hole closes).
- **Gap-fill suggestions:** freed capacity is matched against eligible **pending** jobs, ranked by **cheapest-insertion cost** (least detour *between the neighbors before & after the open slot*). Surfaced as non-blocking suggestions ("slot opened on Eliran's Tuesday — these 3 fit best"); one-click assign, or auto-fill if the tenant opts in. Gap-fill only suggests jobs whose **customer window covers the freed slot**.
- **Delay/move to another day** → re-runs *assignment* (may belong to a different tech), not just sequencing.

Config: `scheduling.gap_fill = { enabled, auto }` (default: suggestions off).

---

## 4. Manual overrides — human wins, always

A task can be **`locked`** (manually placed: drew a block on an empty slot, or dragged a job to a time). A locked task is a **fixed constraint**: the auto-sequencer never moves, reorders, or gap-fills it. The optimizer routes all **flexible** jobs **around** locked ones (pinned node with a fixed time window).

- **Drag = intent to pin** → dragged task becomes `locked`; an explicit "שחרר" returns it to flexible. No ambiguity about what the optimizer may touch.
- **Draw-to-create** (empty-block UI) creates a task born `locked` at that time/tech. *UI deferred*; the `locked` flag + "sequencer respects locks" seam is built now so nothing is re-architected later.
- Conflicts (locked-vs-locked overlap, manual block on a non-working day, locked job out of zone, impossible window) → **surfaced to the coordinator with an actionable Hebrew message**, intent left intact. Engine never silently resolves.

Schema: `tasks.locked BOOLEAN NOT NULL DEFAULT false`.

---

## 5. Drive-time cache (makes auto-sequencing quota-affordable)

New per-tenant table `route_cache` (runs through `context/new-entity-checklist.md` — RLS, etc.):

| column | purpose |
|---|---|
| `tenant_id UUID` | tenant isolation (RLS) |
| `from_key TEXT`, `to_key TEXT` | normalized `"lat,lon"` (~4 decimals) or city name when no coords |
| `drive_minutes INT`, `drive_meters INT` | the cached directional leg |
| `source TEXT` | `google` \| `haversine` |
| `updated_at TIMESTAMPTZ` | freshness (no expiry v1; reserved for refresh) |
| PK | `(tenant_id, from_key, to_key)` |

**Backend owns the cache** (it holds the service key). On each `/optimize`: build needed pairs → read `route_cache` → for misses, if under a **daily Google budget cap**, batch-call Distance Matrix and write back; else haversine fallback marked `source='haversine'`. Cities repeat constantly → after warm-up nearly every leg is a hit → near-zero ongoing quota (directly answers the standing Google-quota concern).

**Cache trust:** a Google leg wildly off its haversine floor (< straight-line time, or > 10×) is **distrusted, not cached** — guards against a bad API row poisoning a route forever. `source` + `updated_at` enable a later "refresh stale legs" admin action; a depot move invalidates that tenant's legs.

---

## 6. Data flow — one integration seam

`markDayDirty(techId, date)` is the **only** function other code calls. Invoked from every mutation: dispatch-confirm, cancel, delay/reschedule, drag-move, lock/unlock. It **debounces (~1s)** per tech-day, then calls `sequenceDay(techId, date)`:

1. Gather day's tasks → split **locked** (fixed time/tech) vs. **flexible**.
2. POST `/optimize` with `route_strategy` (bias) + locked nodes pinned + **hard constraints**: customer arrival windows, tech breaks/partial day-offs (`getTechPartialBlocks`), work-hours, category limits.
3. Persist returned order + `scheduled_time` + window for flexible tasks (**await** every write; partial failure → day stays dirty & retries — no half-sequenced days). Locked tasks untouched. Unknown/deleted IDs ignored.
4. Re-render that tech-day.

### Concurrency guards
- **Sequence epoch per tech-day:** each `markDayDirty` bumps a counter; an `/optimize` reply is applied **only if its epoch still matches**, else discarded. Stops a slow reply clobbering a newer edit.
- **Two coordinators, same day:** optimistic version check (`updated_at` guard) on persist; on conflict, re-read + re-sequence instead of overwrite.

### Feasibility — never silently drop a job
If a day can't fit everything, overflow tasks move to the visible **"ממתין לשיבוץ"** tray with a plain reason ("היום מלא — נותרו 2 קריאות לשבץ"). Never dropped, never fudged.

---

## 7. Error handling (principal rule)

No internal/backend/code errors anywhere in the UI. Every failure path is generic + actionable Hebrew; real error → `console.error` + `Sentry?.captureException` for Eran.

- **Optimizer down / offline** → graceful fallback to the current JS heuristic order; day gets a quiet **"טעון אופטימיזציה"** badge; coordinator never blocked; day re-optimizes automatically when reachable.
- **Geocode missing** (no lat/lon) → fall back to city-centroid/haversine; if city unknown → flag the task, don't sequence blindly.

---

## 8. Rollout safety

- Whole feature behind **`features.auto_sequence`** (off by default) + per-task `locked`. **Absent config / absent flag = today's exact behavior.**
- **Config audit** confirms PureWater has `route_strategy: far_to_near` explicit before the default flips.
- **Dry-run shadow compare** before enabling auto-sequence for PureWater: run new sequencing read-only, show Eran old-vs-new routes for a few real days. Eyes-on switch, not a surprise reorder of a live schedule.

---

## 9. Config & schema summary

**`tenants.config.scheduling`** (all default to current behavior when absent):
```jsonc
{
  "mode": "zone|open|radius",
  "zone_match": "city_list|polygon",
  "route_strategy": "flexible|far_to_near|nearest_first",   // absent ⇒ flexible
  "balance": { "enabled": false, "weight": 50 },
  "gap_fill": { "enabled": false, "auto": false },
  "slot_release": { "enabled": false, "conservative_hours": 72, "moderate_hours": 48, "aggressive_hours": 24 }
}
```
**`tenants.config.features`**: `auto_sequence` (bool, default false).

**Schema:**
- `tasks.locked BOOLEAN NOT NULL DEFAULT false`
- new table `route_cache` (§5) — via new-entity-checklist.

**Backend (`backend/`):** `optimizer.py` reads/writes `route_cache`, honors `route_strategy` bias + locked/fixed nodes + window/break constraints; `main.py` passes strategy, locked flags, constraints through.

---

## 10. Testing

Extend the dependency-free Node harness (`tests/`, `// <zone-logic>` style markers) with a `// <sched-logic>` block covering pure functions:
- `route_strategy` resolution + safe default (absent ⇒ flexible).
- Strategy-aware `isRouteLogical` / `wouldBacktrack` (far→near monotonic, near→far monotonic, flexible = no-op).
- Cheapest-insertion ranking for gap-fill.
- Weekly balance term.
- Cache key normalization + trust sanity-bound.
- Epoch guard (stale-result discard) logic.

Backend: unit tests for cache read/write, budget cap, haversine fallback, locked-node pinning, window/break constraints, infeasible→overflow.

---

## 11. Decomposition / build order (slices)

Built so the **low-risk safety foundation lands first**, each slice independently shippable behind flags:

1. **Honest strategies + safe default + guards** (JS only, no quota): implement real `nearest_first`, strategy-aware `isRouteLogical`/`wouldBacktrack`, flip default to `flexible`, PureWater config audit. + tests.
2. **`locked` flag + sequencer respects locks** (schema + seam; no UI yet).
3. **Drive-time cache** (`route_cache` table + backend read/write/budget/fallback/trust). + backend tests.
4. **Authoritative `sequenceDay` + `markDayDirty` + epoch/version guards + window/break constraints + overflow tray.**
5. **Balance term** (weekly, mode-aware).
6. **Reactive gap-fill** (suggestions; auto opt-in).
7. **Rollout:** `features.auto_sequence`, dry-run shadow compare, enable for PureWater.

---

## 12. Documentation sync map (living docs)

Every code change updates its one doc in the same commit:
- `context/scheduling-rules.md` — assignment/sequencing split, strategy-as-bias, balance, gap-fill, locks, cache, auto_sequence.
- `context/architecture.md` — `route_cache` table, `tasks.locked`, the `markDayDirty`/`sequenceDay` seam.
- `context/clients/purewater.md` — confirm `far_to_near` explicit; record auto_sequence rollout state.
- `DEVELOPER.md` — engine seams, epoch guard, cache budget.
- `context/new-entity-checklist.md` — followed for `route_cache`.
- `CLAUDE.md` — done-list line.
- Memory: link to [[far-to-near-tenant-specific]], [[living-docs-sync]], [[error-messages-rule]], [[google-maps-quota-review]], [[data-persistence-rules]].
