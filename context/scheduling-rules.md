# Scheduling Rules — Maslul

## Overarching Goal
The software does not manage a calendar. It manages an **optimal work route** for a technician.

### North Star — behave like an expert dispatcher (universal, every tenant)
The system should think and decide like a seasoned scheduling coordinator: understand geography and proximity, account for workload distribution and technician capacity, plan ahead (not just the current moment), know when to leave availability open for better future bookings, and eliminate the inefficiencies of manual scheduling — with greater consistency and scale. It balances operational efficiency, technician utilization, travel time, customer commitments, and future opportunities.

**Goal:** minimum driving, minimum fuel, minimum wasted time, no back-and-forth to the same area, no empty gaps, no late arrivals, full utilization of the workday.

### Scheduling priority order (the optimizer optimizes in THIS order)
1. **Correct route direction** — logical geographic flow, no backtracking. *Most important.*
2. **Full-day utilization** — maximize productive time, minimize idle gaps.
3. **Prevention of late arrivals** — never build a schedule that's predictably late.
4. **Reduce fuel & travel time** — continuous operational efficiency.
5. **Most appropriate technician** — chosen *only after* 1–4 are satisfied.

> ⚠️ **Tenant-specific vs universal:** the *dispatcher intelligence* above is universal. The *specific knobs* — **Far → Near** direction, **3-hour windows**, **zones-per-tech-per-day**, **72/48/24h release** — are **PureWater's** chosen instantiation (`route_strategy`, windows, `slot_release`), NOT global defaults. Another tenant pursues the same north star with different knobs. See [far-to-near-tenant-specific] and `context/clients/purewater.md`.

### What the system must never do
Go far→near→far, send a tech backwards geographically, leave dead time mid-day, schedule on clock-time alone (ignoring travel), allow unrestricted manual time selection that breaks routes, or build a schedule where lateness is predictable from the outset.

### Why 3-hour windows exist
A window (not an exact time) is **reserved capacity for insertion**: a job promised 07:00–10:00 lets the optimizer later slot 1–2 *more* nearby jobs into that same window (or visit someone before the original) without breaking the customer commitment. The window is the flexibility that makes live re-optimization possible.

## Technician Starting Point
Every technician has:
- `base_city` (departure) — where they start each morning
- `return_city` — where they end the day (may differ from departure)

The route MUST be calculated relative to the technician's own departure city.
The same schedule can be optimal for Ashkelon and completely wrong for Kiryat Gat.

## Time Window Reservation (72/48/24h) ✅ implemented 2026-06-08
Early slots are held for farther cities. Near cities are pushed later on the schedule as a "reservation" that relaxes as the day approaches:
- 72h+ before: 60-min buffer for near cities (strong reservation)
- 48-72h before: 30-min buffer
- 24-48h before: 15-min buffer
- <24h: no buffer — fill aggressively

**Why:** If Beer Sheva is scheduled at 08:00 and an order for Dimona (farther) comes in later, Dimona must be able to take 07:00. The system reserves this by not assigning 07:00 to Beer Sheva until it's too late for a Dimona order to realistically come in.

**Implementation:** `_candidatesZone()` in `index.html`. Guard: only active when `tenants.config.scheduling.slot_release.enabled = true`. PureWater has this enabled; new tenants default to off.
- "Near city" = `cityIndex / (zoneLength-1) >= 0.5` (in the closest half of the zone)
- Buffer rejects the candidate if `optTime < workStart + buffer_minutes`

## Core Rules (do not break)

1. A technician can only receive assignments in the zone assigned to them for that day of the week
2. Fill existing days before opening new days (`fillScore = existingInZone * 100 + currentLoad`)
3. Far-to-near routing — always schedule the farthest city first, work progressively closer toward the technician's base
4. Never create a route that sends a technician back from a nearby city to a far one — enforced by `wouldBacktrack()` ✅ 2026-06-08
5. The system must calculate the route based on each technician's starting point — the same schedule can be optimal for a technician in Ashkelon and completely wrong for one in Kiryat Gat
6. Category limits per technician per day must be strictly enforced (`tech.catLimits[catId]`)
7. Use arrival windows intelligently — if a job is at Dimona at 09:00 with a 3-hour window, schedule 2–3 additional nearby jobs within that same window as long as total travel + installation time is realistic
8. Never leave a time window empty if there are pending jobs in the same geographic cluster
9. It is better to start the day later than to create a far-near-far zigzag route
10. When inserting a new job, validate it does not create a geographic backtrack — if it does, reject the slot and find a better one

## Example — Zone South

Cities ordered by distance from base (Ashkelon):
```
Dimona (farthest) → Yeruham → Arad → Ofakim → Ashdod → Ashkelon (base)
```

**Correct daily plan:**
- 07:00 → Dimona
- 08:30 → Yeruham or Arad
- 10:00 → Ofakim
- 11:30 → Ashdod
- 13:00 → Ashkelon

**What must NEVER happen:**
Ashkelon → Ashdod → Dimona → Ofakim → Yeruham → then new job added to Dimona at 11:40.
This forces the technician to backtrack from Yeruham back to Dimona. Must be detected and rejected.

## Zone System
- Each zone = a name + ordered list of cities (ordered far-to-near from tech's base)
- Technician rotation maps each weekday (0=Sun–5=Fri) to one zone
- A call in city X only goes to the tech whose zone includes X on that day — no exceptions
- City dropdown in Dispatch only shows cities that exist in zones — if not found, user must add the city with mandatory zone selection

## Scheduling Engine (JS)
Core functions: `findBestSlot()` / `buildCandidates()`

**Candidate scoring:**
- `fillScore = existingInZone * 100 + currentLoad` — always prefer days already active in a zone
- `getCityIndexInZone()` — returns position of city within zone (used for far-to-near ordering)
- `isTechAvailable(tech, dateStr)` — checks `dayoffs` array AND `weekly_schedule`
- `getTechDaySchedule(tech, dateStr)` — returns day-specific hours, falls back to global `tech.start`/`tech.end`

## Weekly Schedule Per Technician
- `weekly_schedule` JSONB in technicians table: `{"0": {"work": true, "start": "07:00", "end": "17:00"}, ...}`
- Keys 0–5 = Sunday–Friday. Saturday always skipped.
- Dispatch and optimizer both use day-specific hours

## Category Limits
- `tech.catLimits[catId]` = max jobs of that category per day per tech
- Enforced before adding any candidate slot
- Example: max 3 water system installs per tech per day

## Defaults (from tenants.config)
```json
{
  "regular_job_minutes": 30,
  "package_job_minutes": 45,
  "arrival_window_hours": 3,
  "max_daily_jobs": 9,
  "lookahead_days": 30,
  "work_start": "07:00",
  "work_end": "18:00"
}
```

## Route Optimization Backend
- OR-Tools TSP solver on Railway (FastAPI)
- Builds distance matrix via Google Maps Distance Matrix API (real drive times) or haversine fallback
- **Drive-time cache (`route_cache`, June 2026):** cached legs are reused across calls — only new city/coord pairs hit Google (bounded by `GMAPS_DAILY_ELEMENT_LIMIT`). Makes always-on real-drive-time sequencing (Plan B2) affordable. See `context/architecture.md` → Drive-Time Cache
- Returns ordered task list with estimated arrival times
- Triggered by "🔀 מסלול מיטבי" button when tech has 2+ tasks today

---

## Configurable Scheduling Engine (June 2026)

New tenants configure the engine via the onboarding wizard. Settings stored in `tenants.config.scheduling`.

### Two-axis zone model (`scheduling.mode` × `scheduling.zone_match`)
Zone behavior is two **independent** settings:

**`scheduling.mode`** — assignment strategy:
| Mode | Behavior |
|---|---|
| `zone` | Default. Zone-strict — tech only works in their rotation zone. Route ordered by `route_strategy`. |
| `open` | No zone enforcement. Assigns by workload balance across all techs. |
| `radius` | Proximity-based. Assigns nearest available tech to each city. |

**`scheduling.zone_match`** (only relevant when `mode = zone`) — how a zone boundary is matched, via the `resolveZone()` seam:
| zone_match | Behavior |
|---|---|
| `city_list` (default) | Match by canonical city in the zone's `cities[]` (PureWater). |
| `polygon` | Match by point-in-polygon on the geocoded address against the zone's `polygons[]`. |

Absent settings = `zone` + `city_list` = today's behavior. See `context/zones-polygons.md` for `resolveZone`.

**Mode-aware UI:** zone UI (settings tab, rotation grid, city-in-zone gate, zone error copy, batch CTA) renders only when `appUsesZones()` (mode `zone`/absent). `open`/`radius` tenants get address→auto-assign with no zone concepts. The onboarding wizard's "מודל שיבוץ" picker chooses `mode`. See `context/architecture.md` → Mode-Aware UI.

### Route Strategies (`scheduling.route_strategy`)
Resolved via `resolveRouteStrategy(sc)` — **absent config ⇒ `flexible`** (the safe global default). `far_to_near` is PureWater/Israel-specific and is NEVER the fallback. Legacy `route_logic:true` still opts into far_to_near for back-compat.

| Strategy | Behavior |
|---|---|
| `flexible` (default) | No geographic ordering constraint — fill by load score. Sanity guards (`isRouteLogical`/`wouldBacktrack`) are no-ops. |
| `far_to_near` | Farthest cities first within the zone. `getCityIndexInZone()` (idx 0 = farthest) orders candidates; **slot-release reservation runs only under this strategy.** |
| `nearest_first` | Closest cities first — **now fully implemented** (mirror of far_to_near via `isPairOrdered`), not a silent flexible. Useful for dense urban zones / delivery. |

`isRouteLogical` / `wouldBacktrack` are **strategy-aware sanity guards** (via `isPairOrdered(strategy, earlierIdx, laterIdx)`); for `far_to_near` they behave exactly as before. `_candidatesZone` enables geographic gating for any non-`flexible` strategy.

### Manual override (`tasks.locked`)
A `locked` task is pinned by the coordinator and is a **fixed constraint** — the (Plan B) auto-sequencer must never move, reorder, or gap-fill it. `splitLockedFlexible(dayTasks)` separates locked (immovable) from flexible (sequenceable). The flag round-trips DB↔JS today; the draw-to-create UI and sequencer integration land in Plan B (Slices 3–7). See `outputs/scheduling-engine-design_2026-06-10.md`.

_2026-06-10 — Slices 1–2: honest strategies + safe `flexible` default + `locked` seam._

### Per-Tech Job Duration Overrides
- Stored in `technicians.duration_overrides` JSONB: `{ "category_uuid": minutes }`
- Engine priority: **tech override → category default → `settings.regularTime`**
- Enabled per-tenant via `features.tech_duration_overrides: true`
- Set in tech edit drawer under "משך לפי קטגוריה"
- Migration: `outputs/migration-duration-overrides_2026-06-01.sql`

---

## Break Time System (June 2026)

Break is stored in config only — NOT in `day_offs`. No new DB column.

### Storage
- **Tenant default**: `tenantConfig.defaults.break = { enabled, start, end }` — set in Settings page
- **Per-tech override**: `tech.weekly_schedule._break = { mode, start?, end? }` — set in tech drawer
  - `mode: 'default'` — uses tenant default
  - `mode: 'custom'` — uses tech-specific `start`/`end`
  - `mode: 'none'` — this tech has no break (overrides tenant setting)

### Engine Integration
- `getTechPartialBlocks(tech, dateStr)` — returns all blocked intervals `[{from, to}]` in minutes
  - Includes manual `day_offs` partials AND resolved break block
  - Used by `calcOptimalTime()` and all three candidate strategies (`_candidatesZone`, `_candidatesOpen`, `_candidatesRadius`)
- **Convergent nudge**: `while(changed)` loop ensures a candidate slot clears ALL adjacent partial blocks
  - A single-pass `for` loop fails when nudging past block 1 creates overlap with block 2
  - The `while` loop re-checks until no block overlaps remain

---

## Service Windows (June 2026) ✅ implemented 2026-06-08

Customers receive a **3-hour arrival window** (e.g., 07:00–10:00), not an exact time.

### DB Columns (tasks table)
- `scheduled_window_start` TEXT — e.g., "07:00"
- `scheduled_window_end` TEXT — e.g., "10:00"
- `scheduled_time` TEXT — estimated tech arrival within the window (internal, not shown to customer)

### Flow
1. Coordinator dispatches → selects a 3-hour slot from `showCandidate()` UI
2. `confirmAssign()` writes `windowStart`/`windowEnd` from the selected slot + `time` (estimated arrival)
3. `saveTaskToSupabase()` persists all three to DB
4. Multiple tasks can share the same window — the engine packs them using `slotCapacity` math

### Calendar Display
- Daily view rebuilt (June 2026) as absolute-positioned div grid (1px/min, 60px/hour)
- Each window = one block spanning the full 3h (180px); tasks listed inside
- Tasks without windows: shown at their exact time with duration height
- Unscheduled tasks (no time, no window): listed below the grid in "ממתין לשיבוץ" section
- One tech at a time — tech tabs at top of daily view

## Authoritative Auto-Sequencing (`features.auto_sequence`) ✅ implemented 2026-06-12

The OR-Tools optimizer is the **single source of truth** for a tech-day's order and times when the flag is on (default OFF — absent flag = zero behavior change).

**The seam:** every task mutation (dispatch confirm, cancel, cancel+replace, edit/move) calls `markDayDirty(techId, date)` — the ONLY integration point. It debounces ~1s per tech-day, bumps an **epoch counter**, and calls `sequenceDay`:
1. Gather the day's non-cancelled tasks (needs ≥2); build payload via `buildSequencePayload` (pure, tested)
2. POST `/optimize` with breaks (`getTechPartialBlocks`), per-task hard windows, and `locked` pins
3. Apply via `applySequenceResult` (pure) **only if the epoch still matches** — stale replies discarded
4. Persist each task awaited (`saveTaskToSupabase`); partial failure leaves the day dirty for retry
5. Render trace + clear badge. On optimizer failure: amber **"טעון אופטימיזציה"** badge, day keeps heuristic order, never blocks

**Constraint semantics (backend `solve_route_v2`):**
- `locked` + time ⇒ pinned exactly, **never moved, never dropped**; two conflicting locked tasks ⇒ `conflict:true` → coordinator toast "שתי קריאות נעולות מתנגשות"
- `window_start/window_end` ⇒ hard customer window; the solver may insert **waiting** (arrivals come from the Time dimension, not accumulation)
- Tech breaks ⇒ zero-travel pinned pseudo-nodes — no task overlaps a break
- Over-full day ⇒ flexible tasks are **dropped to the pending tray** (Hebrew toast "היום מלא — N קריאות הוחזרו"), never silently lost; no return-city ⇒ the day ends at the last client (return leg costs no work time)
- Response includes a per-stop **decision trace** (`prev` city + `drive_minutes`) shown in the daily view (🚗 X דק׳ מ-Y); 🔒 marks locked tasks

**Quota honesty:** with the cache active, the daily Google counter charges only **actual** fetches (cache hits are free); legacy path unchanged.

Rollout: enable per tenant via `config.features.auto_sequence`. PureWater stays OFF until the B3 shadow-compare. Deferred to B3: weekly cross-tech balance, gap-fill suggestions, `updated_at` optimistic versioning, lock/unlock UI.

## Batch Scheduler (June 2026) ✅ implemented 2026-06-08

POST `/batch-schedule` on the Railway backend auto-assigns all pending tasks for a tenant across a date range.

### Algorithm
1. **Greedy assignment**: for each pending task, find the best `(tech, date)` pair:
   - Tech's rotation zone for that day must contain the task's city
   - Score: `count * 100 - city_load * 50` — fill active days first, penalise over-concentration of one city
   - Saturday always skipped; empty rotation string = tech off that day
2. **Per-day optimization**: for each `(tech, date)` group, run OR-Tools to order tasks by travel time (haversine), assign `scheduled_time` + `scheduled_window_start/end`
3. **Window formula**: `slot_num = (arr_min - start_min) // 180; window_start = start_min + slot_num * 180`

### Key invariants
- Zone rotation enforced hard — a task in zone A can only go to the tech assigned zone A that day
- `arrival_window_hours` read from `tenants.config` (PureWater = 3)
- `max_daily` read from technician row; falls back to `config.defaults.max_daily_jobs`
- `dry_run=true` previews without writing to DB
- Protected endpoint: requires `Authorization: Bearer <SUPABASE_SERVICE_KEY>`

### City normalization
`_CITY_ALIASES` in `batch_schedule.py` mirrors `normalizeCity()` in JS. Both must stay in sync when adding city variants.

---

## Return City in Optimizer (June 2026) ✅ implemented 2026-06-08

When `tech.return_city != tech.base_city`, the OR-Tools model uses a two-depot setup:
- Node 0 = start depot (base_city)
- Nodes 1..n = tasks
- Node n+1 = end depot (return_city)

`RoutingIndexManager(n_nodes, 1, start=0, end=n_nodes-1)`
The matrix includes the return city as the last row/col.
`total_drive_minutes` includes the final leg back to return_city.
