# Batch Correctness Pack — Design Spec (Slice 1)

> Approved by Eran 2026-07-05 (brainstorm in-session). Source findings: `outputs/product-review-fable_2026-07-05.md` §A1–A4, A6.
> Principle (Eran's words): whatever the door — one call, a list of 5/10/15, or a whole-week batch — the scheduler must **read the entire current situation and every influencer** (zone/rotation days, tech settings, workload, existing calls) and pick the genuinely best assignment. Fill-first or spread must never override zone correctness. Spreading (e.g. 15 same-city calls → 5/5/5 across three covering techs) is situational, never rigid.

## Goal

Make `/batch-schedule` enforce exactly the same tenant rules as the live JS dispatch path, against the **live** calendar state — so any batch run over a partially-filled week is safe and optimal.

## Changes (all in `backend/batch_schedule.py` + tests; solver untouched except consuming existing inputs)

### 1. Read live state
- Fetch, in addition to pending tasks: tasks with `status in (assigned, en_route, arrived)` and `scheduled_date` in `[date_from, date_to]` (select incl. `scheduled_time`, `scheduled_window_start/end`, `locked`, `category_id`, coords).
- Fetch `day_offs` for the tenant in range.
- Seed per-(tech,day) occupancy, per-tech same-city counts, and per-(tech,day,category) counts from existing calls before the greedy loop.

### 2. Config path fixes
- `arrival_window_hours` ← `config.defaults.arrival_window_hours` (fallback 3). (Bug A3: today read from top-level, NULL live.)
- Task duration ← tech `duration_overrides[cat]` → category `duration_minutes` → `config.defaults.regular_job_minutes` → 30 (mirrors live chain).

### 3. Rule enforcement in candidate filtering (greedy loop)
Add, with the same AND-semantics as `_candidatesZone`:
- **day_offs**: full-day off ⇒ tech-day skipped; partial ⇒ becomes a break-block (see 4).
- **cat_limits** (`technicians.cat_limits`): per (tech, day, category), counting existing + newly placed.
- **skills** (`technicians.skills`): task category must be in the tech's skills when the list is non-empty/defined — mirror JS `techHasSkill` exactly (no catId or no skills configured ⇒ allowed).
- **blocked_zones** / **blocked_cities**: skip tech-days whose rotation zone is blocked; skip blocked cities.
- Zone match remains first and hard (unchanged).

### 4. Breaks + partial day-offs → solver
- Resolve break per tech (tenant `defaults.break` / `weekly_schedule._break` override — mirror of JS `getTechPartialBlocks`) + partial day_offs ⇒ pass as `breaks=[{from,to}]` to `solve_route_v2` per tech-day.
- PureWater today: break disabled, no day-offs ⇒ zero behavior change (architecture-ready for future tenants).

### 5. Existing calls inside the day solve (approved policy: "windows fixed, times may re-flow")
- Existing calls join the tech-day's solver input with `window_start/window_end` as **hard constraints**; `locked=true` calls pinned at their exact `scheduled_time`.
- Persisted for existing calls: `scheduled_time` ONLY, and only when it changed — never window/date/tech/status.
- New calls: full payload as today.
- If the solver drops an EXISTING call (day genuinely infeasible), the existing call is **never** unassigned by batch — it keeps its current values and the day is reported `day_over_capacity` with the new calls dropped instead. (Existing commitments outrank new placements.)

### 6. Retry dropped tasks
- A NEW task dropped by `optimize_day` returns to the assignment pool with that (tech,day) excluded, and the greedy re-runs for it (next-best covering day). Bounded (each task tries each covering day at most once). Only when no covering day fits ⇒ `day_over_capacity`.

### 7. Error handling
- Supabase fetch failures ⇒ fail-closed: abort the batch with a clear error before any write (no partial state).
- Everything else keeps current fail-open semantics (`needs_location` flags, etc.).

## Testing (TDD, real-data-shaped)
Fixtures modeled on PureWater (real zone names/rotation shape/config shape, anonymized clients). New pytest cases:
1. Existing 5 calls on a tech-day + max_daily 9 ⇒ at most 4 new placed there.
2. `arrival_window_hours: 2` under `defaults` ⇒ 2h windows in output (kills A3).
3. Full day_off ⇒ no assignment that day; partial day_off ⇒ no time overlap.
4. cat_limits counting existing + new; skills filter; blocked_zones/cities.
5. duration_overrides + `regular_job_minutes` respected in day packing.
6. Existing call windows preserved; internal time may shift within window; locked pinned exactly; existing never dropped/unassigned.
7. Dropped new task retries and lands on the next covering day when it fits.
8. Regression: all-pending run (the 108-task scenario) produces same-or-better results; absent config unchanged.

## Verification before merge
`python -m pytest` green + `node tests/*.test.js` green + **dry-run against live PureWater** (read-only) with a before/after diff of the proposed assignment vs current calendar; reviewed by Eran before any live write.

## Out of scope (later slices)
- Placement-policy unification (consolidate vs spread semantics across doors) — Slice 3, pending Israel's decision; Eran's guidance recorded: fluid situational best-fit, not rigid.
- `nearest_first` in the solver — Slice 4.
- Window-less tenants (`arrival_window_hours: none` — call-by-call schedule per tech): future knob, recorded in the knob registry; batch window math must tolerate it then.
- timing.tech reference (checked live 2026-07-05): their "smart automatic time-windows" (slot computed from travel+duration) and "call balance" are the mature versions of exactly these knobs — direction confirmed.
