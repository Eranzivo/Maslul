# Maslul — PureWater Pilot Handover (Israel's consolidated 2-month feedback)

> Delivered by Eran 2026-07-06, verbatim. THE requirements document for the PureWater pilot.
> Reality notes: team is 3 techs (doc says 4 — ignore, per Eran); much of this is already
> built — see `outputs/israel-handover-gapmap_2026-07-06.md` for built-vs-open, and
> `context/README.md` for where each durable rule was folded.

## 1. Product purpose

Maslul is a **Hebrew-first scheduling and routing decision engine for Israeli SMBs with field technicians**. It is not a generic calendar and it is not simply a task list.

The product's job is to help a dispatcher place each service call on the best technician's route while minimizing: driving time and fuel; backtracking; empty or poorly utilized time windows; technician overload; missed customer preferences; uneven distribution of work; manual dispatcher reasoning in WhatsApp, spreadsheets, and phone calls.

> A dispatcher enters a customer request, and Maslul returns the best feasible appointment recommendation based on technician skills, work hours, route direction, daily area, travel time, task duration, existing jobs, and business constraints.

## 2. PureWater pilot: confirmed context

Industry: installation and service work. Main categories: garbage disposals; hot/cold water taps and water systems; related installation/service visits. Existing system: Odoo v19 — Maslul should eventually coexist with Odoo rather than assume it is replaced. No confirmed Odoo API mapping, webhook contract, or field mapping has been defined yet.

> Do not hardcode business logic using `if tenant == "PureWater"`. PureWater behavior must be represented through tenant configuration, service-type configuration, technician profiles, skills, working hours, regional rules, and scheduling constraints.

## 3. Architecture principle: core engine vs. tenant configuration

**Maslul Core Engine** (generic, reusable): availability calculation, route sequencing, travel-time evaluation, skill matching, constraint validation, assignment scoring, recommendation generation, workload balancing, appointment windows, technician calendars, scheduling explanations.

**Tenant Configuration** (per-customer): technicians, skills, service types, durations, working hours, start/return city, daily regions, weekly region rotation, category limits, customer-facing windows, tenant business rules, integration mapping (future Odoo fields).

The backend owns business logic and routing decisions. The frontend displays decisions, explanations, options, and manual actions; it must not independently calculate the "best" technician or route.

## 4. Core operating model — route optimization, not calendar management

The engine must think in terms of a technician's whole workday:
1. Technician starts from a configured start location.
2. The day should generally begin with farther jobs.
3. Jobs progressively move closer to the technician's return city.
4. The technician finishes near or on the way back to the return city.
5. Avoid geographically irrational sequences and backtracking.

Correct: Yehud start → farther Rishon LeZion earlier → later jobs toward Tel Aviv / Ramat Gan / Yehud. Bad (must be actively penalized): Yehud → Tel Aviv → Rishon LeZion → Givatayim → Yehud.

## 5. Scheduling and appointment-window rules

**Customer-facing windows:** three-hour arrival windows (07:00–10:00, 10:00–13:00, 13:00–16:00, 16:00–19:00 where relevant). A window ≠ a single job — multiple jobs stack inside one window when travel + duration allow. The customer sees the window; Maslul manages the internal route and precise schedule.

**Default durations:** standard 30 min; package/extended 45 min — defaults only. Overrides supported by: service type, **specific job**, technician, tenant rule.

## 6. Technician model

A technician cannot be created without all critical operational fields: full name, active status, start city, return city, working days, working hours per day (incl. exceptions like a shortened Wednesday), skills, daily region assignment/eligibility, max workload/daily capacity.

Rules: never assign a job that ends after that day's end time (e.g., a Wednesday 14:00 finish); a technician may service a product but not install it — **skills are mandatory**; never assign without the required skill.

## 7. Regional planning model

Do not use permanent North/South boundaries. Use configurable **daily region assignment** (weekday → region). Rules: jobs only inside the day's assigned region unless explicitly approved; no tech locked to one area all week by default; **up to five weekly regional assignments per tech**; the rotation engine should spread regions and workload fairly; **the system should avoid splitting a partially loaded day across multiple technicians when one technician can absorb more nearby work efficiently.**

> **Fill the best nearby technician route first, then use the next-best route. Avoid creating multiple half-empty technician days.**

## 8. Assignment engine

**Hard constraints (never violate):** inactive tech; missing skill; not working that day; outside work hours; exceeds required early finish; overlaps confirmed booking; exceeds daily capacity; violates daily-region policy; violates customer availability; equipment/capability unavailable; route can't physically fit after travel + service time.

**Scoring factors (rank valid options):** added travel time; route direction quality (farther-to-nearer / return-home progression); distance from previous/to next job; distance from start/return city; utilization of empty capacity; fit within the customer window; workload balance; category/day quota; fairness; delay risk; **preference for grouping jobs in the same area**; merging two partial routes into one.

**Output must include a human-readable reason**, e.g.: "Recommended: Daniel, Tuesday 10:00–13:00 — qualified for water-system installation; already in Holon in this window; adds only 12 minutes of travel; keeps the route progressing toward his return city; fits before his 16:00 end time."

## 9. Recommendation behavior

Show **one primary best recommendation** with its reason; alternatives only when the dispatcher asks (`Find Another Date`, `Check Specific Dates`, `Override / Assign Manually`). Resolves the earlier 3-cards-vs-1 tension: one best first; three option cards only on explicit request; never dump three equally weighted choices without identifying the best.

## 10. Dispatcher workflow

1. **Search** (not a calendar): city, address, category, service type, required skill/product, customer availability/requested window, preferred date, priority, notes.
2. **Recommendation:** day+date, customer window, technician, high-level route reason, service type, duration, constraints considered.
3. **Confirm / find another date / check specific dates / manual override.**
4. **Confirm:** create assignment, update route + capacity, keep chronological order, preserve route logic for later recommendations.

## 11. Calendar and schedule behavior

Home: simple — tech names, high-level workload/status, search entry. Weekly schedule: days × technician × window/time, city, address, type, status, route order; chronological top-to-bottom. Status model: pending recommendation → assigned/confirmed → in progress → completed → cancelled. **Pending recommendations look like drafts; the operational calendar shows confirmed/completed only.**

## 12. UI / UX direction

Calm, clear operations cockpit. Hebrew-first, RTL, very low cognitive load, minimal dispatcher decisions, strong explanation of recommendations, no dense enterprise UI, no routing math needed to use it. Pattern: search → best recommendation → concise reason → confirm → route updates automatically. Colors: amber pending · indigo assigned · green completed; never same color for unrelated meanings.

## 13. Core data model (suggested)

Entities: Tenant, User, Technician, Skill, TechnicianSkill, ServiceType, Job, JobRequirement, Customer, Address, Region, TechnicianRegionAssignment, TechnicianAvailability, TenantRule, TenantSetting, AppointmentWindow, Assignment, RoutePlan, RouteStop, TravelEstimate, ExternalIntegrationMapping, AuditLog.

Key Job fields: customer, address, service type, required skills, duration, requested date/window, customer preferences, priority, status, external_reference_id, notes. Key Assignment fields: scheduled start/end, customer window, route_sequence, travel minutes from-prev/to-next, recommendation_score, recommendation_reason, status, **manually_overridden + override_reason**.

## 14. Tenant configuration example (shape only — do not invent real values)

```json
{
  "tenant": "purewater",
  "timezone": "Asia/Jerusalem",
  "workweek": ["Sunday","Monday","Tuesday","Wednesday","Thursday"],
  "appointment_windows": [{"start":"07:00","end":"10:00"},{"start":"10:00","end":"13:00"},{"start":"13:00","end":"16:00"}],
  "service_types": [{"name":"Standard Service","default_duration_minutes":30},{"name":"Extended Installation","default_duration_minutes":45}],
  "routing_rules": {"prefer_farthest_jobs_earlier":true,"prefer_return_toward_home":true,"avoid_backtracking":true,"daily_region_required":true,"fair_distribution_enabled":true,"max_weekly_regions_per_technician":5}
}
```

## 15. Example test scenarios

- **A — Skill matching:** installation job → only installation-qualified & available techs eligible.
- **B — Wednesday early finish:** route ends 12:45, job = 45 min + 20 travel, end time 14:00 → reject.
- **C — Route direction:** Yehud base, morning Rishon job → Holon ranks above Petah Tikva if it supports the route back toward Yehud; never chosen merely for free time.
- **D — Capacity consolidation:** Tech A has two nearby jobs + room; Tech B one distant job + big empty capacity; new nearby job → **assign to A rather than spreading unnecessarily.**
- **E — 3h window stacking:** 10:00–13:00 accepted, 30-min job, tech nearby at 10:15–10:45 → schedule ~11:00; the window is not blocked by one appointment.
- **F — Manual override:** dispatcher overrides recommendation → allowed, recorded, **reason required**, downstream route implications recalculated.

## 16. Implementation rules

1. Inspect the repo before changing architecture. 2. Preserve useful work. 3. Business logic in backend/domain services. 4. PureWater logic configurable, never in conditionals. 5. Build incrementally (data model → config → intake → feasibility → scoring → confirm → weekly schedule). 6. Deterministic test scenarios. 7. Explainable routing. 8. Log why candidates were rejected/selected. 9. Appointments are windows, not fixed clock times, customer-side. 10. Don't build a drag-and-drop calendar first and call it route optimization. 11. Manual override with auditability. 12. Hebrew-first + RTL from the beginning.

## 17. Non-goals for the first build

Not prerequisites: live Odoo sync, real-time traffic prediction, multi-tenant billing, customer portal, mobile tech app, AI chat, fully automatic scheduling without dispatcher confirmation, national-scale optimization.

> The first usable version proves one thing well: given a new PureWater service request, Maslul recommends a sensible technician, date, and three-hour arrival window while respecting skills, hours, travel, route direction, daily region, and existing work.
