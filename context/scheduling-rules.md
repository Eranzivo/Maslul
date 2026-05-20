# Scheduling Rules — Maslul

## Overarching Goal
The software does not manage a calendar. It manages an optimal work route for a technician.
**Goal:** minimum driving, minimum fuel, minimum wasted time, no back-and-forth to the same area, no empty time windows, no delays, full utilization of the working day, route always planned Far → Near.

## Technician Starting Point
Every technician has:
- `base_city` (departure) — where they start each morning
- `return_city` — where they end the day (may differ from departure)

The route MUST be calculated relative to the technician's own departure city.
The same schedule can be optimal for Ashkelon and completely wrong for Kiryat Gat.

## Time Window Reservation (72/48/24h)
Early slots are held for farther cities. Near cities are pushed later on the schedule as a "reservation" that relaxes as the day approaches:
- 72h+ before: 60-min buffer for near cities (strong reservation)
- 48-72h before: 30-min buffer
- 24-48h before: 15-min buffer
- <24h: no buffer — fill aggressively

**Why:** If Beer Sheva is scheduled at 08:00 and an order for Dimona (farther) comes in later, Dimona must be able to take 07:00. The system reserves this by not assigning 07:00 to Beer Sheva until it's too late for a Dimona order to realistically come in.

## Core Rules (do not break)

1. A technician can only receive assignments in the zone assigned to them for that day of the week
2. Fill existing days before opening new days (`fillScore = existingInZone * 100 + currentLoad`)
3. Far-to-near routing — always schedule the farthest city first, work progressively closer toward the technician's base
4. Never create a route that sends a technician back from a nearby city to a far one
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
- Returns ordered task list with estimated arrival times
- Triggered by "🔀 מסלול מיטבי" button when tech has 2+ tasks today
