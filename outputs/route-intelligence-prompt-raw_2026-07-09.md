# Route Intelligence — Eran's original brainstorming prompt (RAW, verbatim, 2026-07-09)

> Preserved before session compaction. This is the SOURCE for
> `outputs/route-intelligence-brief_2026-07-09.md` (the improved brief — to be written next).
> Claude's review verdict (same day): ~60% of this already exists in Maslul; the genuinely
> NEW product = Route Health score + Day Route Auditor + recommendation workflow +
> route-version/audit tables + (later) Weekly Rebalancer + dynamic slot release. Key edits
> agreed: gap-analysis-first (EXISTS/PARTIAL/MISSING per requirement), one shared
> constraint/scoring implementation across all doors (golden-fixture enforced), audit
> trigger = change-driven (markDayDirty hook) not day-full, stability threshold =
> minutes-saved-per-customer-disturbed (tenant knob), no new "micro-zone" entity (polygons
> + geo_addresses cover it), NOT an agent/n8n — deterministic engine extensions + background
> jobs on the existing FastAPI service; re-cut phases (P1 = read-only Route Health + Day
> Audit); simulation corpus = Israel's 20-month export.

---

Based on your existing understanding of Maslul's architecture, scheduling logic, tenant configuration, database, backend, and current product goals, help me develop the following idea.

Do not implement it yet.

First brainstorm the concept, challenge my assumptions, identify risks and missing considerations, and recommend the most effective way to integrate it into Maslul's existing logic.

The proposed solution should extend the current product naturally. Reuse existing scheduling, routing, tenant-rule, technician, appointment, zone, and availability functionality wherever appropriate.

I want an opinionated recommendation, not simply a restatement of my idea. If a different architecture, trigger mechanism, optimization method, or product workflow would work better, explain and recommend it.

## Core Product Goal

Maslul should not simply manage a calendar.

It should manage the most operationally efficient work route for each technician.

The primary goals are:

- Minimize total travel time.
- Minimize distance and fuel consumption.
- Reduce unnecessary driving and technician fatigue.
- Avoid far → near → far route patterns.
- Avoid returning to the same distant area later in the day.
- Group appointments geographically where appropriate.
- Prevent empty gaps during the workday.
- Prevent schedules that are already expected to be late.
- Respect customer arrival windows.
- Use the technician's available workday efficiently.
- Preserve suitable capacity for appointments that may be added later.
- Account for different rules for every tenant.
- Rebalance the schedule when a meaningfully better weekly allocation becomes available.

## Core Routing Principle

The default geographical principle is:

Farthest → nearest

Each technician may have:

- A starting location.
- An ending or return location.
- Working hours.
- Assigned or permitted zones.
- Permanent zones on particular days.
- Skills and installation capabilities.
- Maximum workload or appointment capacity.
- Break requirements.
- Tenant-specific restrictions.

The system should generally begin with the farthest appropriate appointment and gradually move the technician toward the configured return area.

However, treat this as an optimization preference rather than an unconditional rule.

Traffic, arrival windows, technician availability, service duration, road structure, and hard constraints may justify a different route.

Determine how this principle should fit into the existing Maslul scoring and constraint model.

## Customer Arrival Windows

Customers receive three-hour arrival windows instead of exact appointment times.

Examples:

- 07:00–10:00
- 08:00–11:00
- 09:00–12:00

Multiple appointments may belong to the same customer-facing window if the technician can realistically reach and complete all of them within that window.

The internal route should still calculate:

- Estimated arrival time.
- Estimated service start.
- Estimated completion.
- Travel duration.
- Service duration.
- Buffer time.
- Lateness risk.

The system should not assume that one displayed window can contain only one appointment.

## Protected Capacity

The system should preserve early capacity for potentially more distant appointments.

Example:

Possible appointments exist in:

- Dimona
- Be'er Sheva

Dimona is farther from the technician's return direction.

Therefore:

- Dimona may receive the earliest slot.
- Be'er Sheva should initially receive a later slot.
- Early capacity should remain available for a possible Dimona appointment.

Capacity should then be released dynamically as the service date approaches.

Possible behavior:

- 72 hours before: strongly protect early capacity for distant locations.
- 48 hours before: release some capacity if no distant demand exists.
- 24 hours before: prioritize filling remaining availability and eliminating gaps.

These thresholds and behaviors should be tenant-configurable.

Please consider whether fixed thresholds are the best approach or whether Maslul should eventually use historical demand, weekday patterns, seasonality, cancellation probability, and zone-specific booking behavior.

## Scenario 1: Multiple Appointments in One Window

Appointments:

- Dimona at the beginning of the day.
- Be'er Sheva after Dimona.
- An additional Be'er Sheva appointment.

Possible internal route:

- Dimona service: 07:00–07:30
- Travel to Be'er Sheva: approximately 60 minutes
- First Be'er Sheva arrival: 08:30
- Service: 08:30–09:00
- Travel to second address: 15 minutes
- Second service: 09:15–09:45

All three customers can still be served within a 07:00–10:00 customer-facing window.

The system should determine feasibility using actual internal timings rather than rejecting the additional appointment because the displayed window already appears occupied.

## Scenario 2: Address Order Within a City

A technician starts at location X and has four appointments in the same city.

Determine:

- Which address should be first.
- The best order between the four addresses.
- Which address should be last.
- Which final address provides the best exit toward the next city.
- Whether traffic or customer windows justify a different order.
- Whether the shortest route inside the city is still best when considering the following destination.

It is not enough to group appointments by city.

The internal address order should support the complete route and the transition to the next geographical cluster.

## Scenario 3: Geographical Backtracking

Potential route:

- Dimona
- Ashkelon
- Be'er Sheva

This may create far → near → far movement.

The system should detect the pattern and evaluate alternatives such as:

- Dimona → Be'er Sheva → Ashkelon.
- Reassigning one appointment to another technician.
- Moving an appointment to another permitted day or window.
- Retaining the existing schedule if hard constraints require it.

The recommendation should quantify the expected improvement.

## Scenario 4: A Day Reaches Capacity

A tenant may define a full day as:

- The maximum number of calls has been reached.
- No valid customer-facing windows remain.
- No realistic travel and service capacity remains.
- Adding another appointment would create lateness or overtime.

When a day becomes full, I want Maslul to run a Day Route Audit.

The audit should verify:

- Correct technician assignment.
- Correct appointment order.
- No unnecessary backtracking.
- No expected lateness.
- Realistic travel and service durations.
- Efficient city and micro-zone grouping.
- Reasonable buffers.
- Compliance with tenant and technician settings.
- Whether another technician could handle part of the route more efficiently.

Please evaluate whether "day becomes full" is the best trigger or whether auditing should occur incrementally after meaningful schedule changes.

## Scenario 5: Weekly Rebalancing

Approximately 100 weekly appointments may be distributed between three technicians.

Each technician may have:

- Different permanent daily zones.
- Different starting and return locations.
- Different skills.
- Different working hours.
- Different maximum workloads.
- Existing appointments that cannot be moved.
- Customer-confirmed appointments that should only be changed when the improvement is meaningful.

The system should evaluate whether:

- Calls should move between technicians.
- A city should be handled by another technician.
- Stops should be reordered.
- Calls should move between days when permitted.
- The efficiency improvement justifies disrupting a confirmed schedule.
- Workload should be redistributed.
- Two partially efficient routes could be consolidated into one stronger route.

Avoid constant schedule reshuffling for insignificant improvements.

Recommend a threshold or stability mechanism that balances optimization with operational predictability.

## Scenario 6: New Appointment During an Active Week

Appointments are continuously assigned while the business is operating.

When a new appointment is added, the system should not automatically recalculate the entire week.

It should:

1. Identify the affected technicians, days, zones, and routes.
2. Test valid insertion positions.
3. Compare the updated route with the current route.
4. Reject invalid assignments.
5. Recommend better technicians, dates, or windows where appropriate.
6. Recalculate only the affected scope.
7. Trigger wider rebalancing only when the change has meaningful impact.

Consider concurrency, including two coordinators booking appointments at the same time.

## Scenario 7: Different Tenant Logic

Maslul supports customers with significantly different:

- Service durations.
- Geographic areas.
- Technician structures.
- Maximum calls per day.
- Zone definitions.
- Appointment windows.
- Skills.
- Scheduling priorities.
- Rescheduling permissions.
- Capacity-release rules.
- Locked appointment behavior.

The optimization system should use structured tenant configuration.

Avoid scattered tenant-specific conditions and hardcoded customer logic.

Recommend how the existing tenant configuration should be extended while preserving one source of truth.

# Proposed Capabilities

These are initial ideas, not mandatory architectural boundaries. Recommend whether they should be separate services, background jobs, domain modules, or parts of the current scheduling engine.

## 1. Booking Guard

Run before confirming a new appointment.

Possible responsibilities:

- Validate technician eligibility.
- Validate arrival-window feasibility.
- Calculate travel and service feasibility.
- Detect likely lateness.
- Detect geographical backtracking.
- Score possible insertion positions.
- Recommend the best technician, date, and window.
- Explain why alternatives are unavailable.
- Preserve protected capacity where configured.
- Prevent race conditions and double booking.

## 2. Day Route Auditor

Possible triggers:

- A day reaches capacity.
- No valid slots remain.
- An important appointment is added, removed, or changed.
- A technician becomes unavailable.
- A dispatcher requests an audit.
- A scheduled audit runs.

Possible responsibilities:

- Review the complete technician route.
- Compare alternative stop orders.
- Detect inefficient assignments.
- Estimate the improvement from proposed changes.
- Avoid changes when the improvement is negligible.
- Store audit findings and route versions.

## 3. Weekly Rebalancer

Possible triggers:

- Before the operational week begins.
- Following major schedule changes.
- Following technician absence.
- When requested by a dispatcher.

Possible responsibilities:

- Compare assignments across eligible technicians.
- Respect permanent daily zones.
- Preserve locked or confirmed appointments.
- Reduce weekly travel time and distance.
- Improve workload distribution.
- Avoid unnecessary customer disruption.
- Recommend changes before applying them.

## 4. Slot Release Service

Possible responsibilities:

- Protect capacity for geographically distant demand.
- Release capacity as the appointment date approaches.
- Use tenant-specific release thresholds.
- Consider historical demand when sufficient data exists.
- Avoid leaving capacity unused when distant demand is unlikely.
- Explain why a window is protected or released.

## 5. Route Explanation Service

Convert structured optimization results into clear operational explanations.

Examples:

- "Moving appointment 184 to Technician 2 reduces estimated travel by 34 minutes."
- "This route returns to Be'er Sheva after reaching Ashkelon, adding approximately 41 km."
- "The 07:00 window is currently protected for appointments in the Dimona zone."
- "No change is recommended because the alternative saves only four minutes and requires changing a confirmed appointment."

Determine whether these explanations require an LLM or can mostly be produced from structured templates.

# Deterministic Optimization vs LLM

Do not use an LLM to calculate routes.

Deterministic code should handle:

- Route optimization.
- Time-window validation.
- Technician assignment.
- Capacity calculation.
- Travel-time calculation.
- Constraint validation.
- Route scoring.
- Schedule comparison.
- Feasible insertion testing.

Consider:

- Existing Maslul optimization functionality.
- Google OR-Tools or another proven routing solver.
- Google Routes API or another travel-time provider.
- Cached geocoding.
- Cached distance and duration matrices.
- Background optimization jobs.

An LLM should only be considered for:

- Human-readable explanations.
- Summarizing detected issues.
- Translating structured findings into dispatcher-friendly language.
- Answering questions about why a recommendation was made.

The optimization system should continue functioning without an LLM.

# N8N

Evaluate whether n8n adds meaningful value.

My current assumption is that n8n should not own:

- Core scheduling.
- Route calculations.
- Route scoring.
- Appointment assignment.
- Tenant rules.
- Optimization state.
- Any source-of-truth data.

It may be useful for peripheral workflows such as:

- Email.
- SMS or WhatsApp.
- Slack notifications.
- CRM updates.
- Daily reports.
- External system integrations.

Confirm or challenge this assumption based on Maslul's current architecture.

# Constraint Model

Separate hard and soft constraints.

Possible hard constraints:

- Technician working hours.
- Technician skills and eligibility.
- Customer arrival windows.
- Service duration.
- Travel time.
- Permitted and permanent zones.
- Maximum calls or workload.
- Mandatory breaks.
- Locked appointments.
- Customer restrictions.
- Tenant-specific prohibitions.
- Starting and return locations.
- Appointments that cannot be moved.
- Technician absence.

Possible soft constraints:

- Farthest-to-nearest direction.
- Minimize travel duration.
- Minimize distance and fuel-related cost.
- Avoid geographical backtracking.
- Group appointments by city and micro-zone.
- Finish each city near the best exit toward the next destination.
- Protect capacity for future distant calls.
- Balance workload.
- Minimize changes to confirmed appointments.
- Maintain technician/customer continuity.
- Minimize idle gaps.
- Prefer efficient progression along major roads.

Recommend which constraints should be configurable and which should remain system-level invariants.

# Route Scoring

Propose a configurable scoring model.

Possible components:

Route score =
- Travel-time penalty
- Distance penalty
- Lateness penalty
- Backtracking penalty
- Idle-time penalty
- Overtime penalty
- Workload-imbalance penalty
- Confirmed-appointment-change penalty
- Zone-violation penalty
- Unused-capacity penalty
+ City-grouping benefit
+ Route-direction benefit
+ Technician-continuity benefit

Hard-constraint violations should normally make a route invalid rather than simply reduce its score.

Explain:

- How route alternatives should be compared.
- How weights should be selected.
- Which weights should be tenant-configurable.
- How meaningful improvement should be defined.
- How to avoid constant minor schedule changes.
- How to record the reason behind every recommendation.
- Whether scores should be normalized so dispatchers can understand them.

The product should describe results as "the best route found under the configured constraints," not promise a mathematically perfect route.

# Data and Auditability

Assess whether the current data model supports:

- Geocoded appointment coordinates.
- Start and return locations.
- Technician capabilities.
- Tenant optimization settings.
- Zone and micro-zone membership.
- Appointment lock status.
- Customer confirmation status.
- Route versions.
- Optimization job status.
- Before-and-after route scores.
- Audit findings.
- Recommendation explanations.
- Accepted and rejected recommendations.
- Manual dispatcher overrides.
- Traffic-data timestamps.

Every recommendation should be auditable.

A dispatcher should understand:

- What changed.
- Why it changed.
- What improvement is expected.
- Which constraints influenced the result.
- Whether it was accepted, rejected, or manually overridden.

# Cost and Token Efficiency

Recommend an architecture that:

- Caches geocoded addresses.
- Caches distance and duration matrices.
- Uses suitable expiration rules for traffic-sensitive data.
- Recalculates only affected technicians, days, and route segments.
- Reuses unchanged calculations.
- Compares schedule deltas instead of reprocessing the entire week.
- Stores tenant rules as structured configuration.
- Runs deterministic validation before any LLM request.
- Skips the LLM when no natural-language explanation is needed.
- Sends only compact, structured findings to the LLM.
- Avoids sending raw customer data when anonymized data is sufficient.
- Uses smaller models for straightforward explanations.
- Tracks external API and LLM usage by tenant.

# Security and Multi-Tenancy

Preserve strict tenant isolation.

Consider:

- Supabase Row Level Security.
- Backend authorization.
- Service-role usage.
- Optimization jobs and queues.
- Route-result access.
- Logging and error reporting.
- Cross-tenant caching risks.
- LLM data exposure.
- Traffic API requests.

No job, cache entry, log, recommendation, or LLM request should expose one tenant's data to another tenant.

# Failure Handling

The design should handle:

- Missing or invalid coordinates.
- Traffic API failure.
- Rate limits.
- Solver timeout.
- No feasible route.
- Technician absence.
- Appointment cancellation.
- Manual changes during optimization.
- Stale route versions.
- Conflicting tenant rules.
- Concurrent bookings.
- A route that is technically feasible but operationally unreasonable.

The current confirmed schedule must remain usable if optimization fails.

# Product Experience

Consider how dispatchers should interact with this functionality.

Possible UI states:

- Route is healthy.
- Optimization is running.
- Issues detected.
- Recommendations available.
- No feasible route.
- Recommendation accepted.
- Recommendation rejected.
- Manually overridden.

The dispatcher should be able to see:

- Current route.
- Proposed route.
- Before-and-after comparison.
- Estimated time and distance savings.
- Lateness risk.
- Affected customers.
- Confidence or quality indicator.
- Reasons for the recommendation.
- Whether customer communication may be required.

Initially, prefer recommendations and human approval over automatic schedule changes.

# Suggested Delivery Phases

Evaluate and improve this phased approach:

Phase 1:
- Route observability.
- Route scoring.
- Violation detection.
- No automatic schedule changes.

Phase 2:
- Day Route Auditor.
- Before-and-after recommendations.
- Dispatcher approval workflow.

Phase 3:
- Booking Guard.
- Feasible insertion scoring.
- Better technician/date/window recommendations.

Phase 4:
- Weekly Rebalancer.
- Cross-technician and cross-day recommendations.

Phase 5:
- Protected-capacity and Slot Release Service.

Phase 6:
- Optional natural-language explanations.
- Notifications and external integrations.
- n8n only where it provides clear value.

# Testing Scenarios

Include a testing strategy for:

- One technician and one appointment.
- Several appointments in one city.
- Four addresses in one city followed by another city.
- Ten appointments across ten cities.
- Multiple appointments sharing one arrival window.
- Far → near → far backtracking.
- Heavy traffic.
- Technician absence.
- Locked appointments.
- Confirmed appointments.
- Cross-zone appointments.
- Conflicting rules.
- No feasible schedule.
- Concurrent bookings.
- Manual overrides.
- Optimization timeout.
- Traffic API failure.
- Different tenant configurations.
- Tenant-isolation attempts.
- Weekly redistribution of approximately 100 calls across three technicians.

# Required Response

Do not implement anything yet.

Return a structured brainstorming and recommendation document containing:

1. Your understanding of the idea.
2. How it fits Maslul's current product logic.
3. Existing capabilities that can support it.
4. Assumptions that should be challenged.
5. Missing business or technical considerations.
6. Recommended architecture.
7. Whether these should be separate agents, services, jobs, or existing engine extensions.
8. Recommended deterministic optimization method.
9. Hard and soft constraint model.
10. Route-scoring model.
11. Trigger strategy.
12. Data-model changes.
13. API and background-job design.
14. Dispatcher experience.
15. Auditability and override behavior.
16. Failure and fallback strategy.
17. Security and tenant-isolation considerations.
18. Token, infrastructure, and external API cost strategy.
19. Recommended implementation phases.
20. Testing and simulation plan.
21. Risks and tradeoffs.
22. Alternative approaches you considered.
23. Your final recommended MVP.
24. Open questions that cannot be answered from the current product context.

Reference relevant existing files, services, tables, and functions when explaining how the recommendation would integrate with Maslul.

Be critical and practical. The goal is to improve the idea and find the best implementation for Maslul, not merely confirm my proposed solution.
