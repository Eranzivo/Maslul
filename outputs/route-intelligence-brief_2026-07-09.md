# Route Intelligence — Improved Brief (requirement source-of-truth)

> **Status:** approved direction, 2026-07-09. Source: `outputs/route-intelligence-prompt-raw_2026-07-09.md`
> (Eran's verbatim brainstorming prompt) + the same-day review Eran accepted.
> **How to use:** this file is the requirement source-of-truth for the Route Intelligence
> workstream. The design/brainstorm session runs against THIS brief, not the raw prompt.
> Anything marked **SETTLED** is decided — do not re-litigate. Anything in **Open questions**
> is what the design session must answer.

---

## 0. One-paragraph summary

Maslul already IS most of the "route intelligence agent" the raw prompt describes — the
review found ~60% built and shipped — and the code-verified gap map below raised that
further (slot release with 72/48/24h thresholds and insert-time backtrack rejection are
ALSO already live). The genuinely new product is **observability and hindsight**: a Route
Health score, a Day Route Auditor that re-examines schedules already built, a
recommendation approve/reject workflow with route versioning, and later a Weekly
Rebalancer. It is built as **deterministic engine extensions + background jobs
on the existing FastAPI service** — not an agent, not n8n, no LLM in the calculation path.

---

## 1. Gap map — SETTLED (verified against code 2026-07-09)

Every requirement from the raw prompt, mapped to what exists. File anchors verified.

### EXISTS — do not rebuild; extend or reuse

| Raw-prompt requirement | Where it lives today |
|---|---|
| Far→near as a soft optimization preference, per tenant | `resolveRouteStrategy` index.html:5191 → `route_strategy` in every optimize payload; `route_strict` knob (index.html:5076–5081) picks hard-block vs soft-warn |
| Deterministic solver (no LLM routing) | OR-Tools: `solve_route_v2` backend/optimizer.py:263, `solve_day_with_existing` backend/batch_schedule.py:349 |
| Cached distance/duration matrices | `backend/route_cache.py` (deny-all RLS, service-key only); trust-check + write-back in optimizer.py:109–137 |
| Cached geocoding | `backend/geo_addresses.py` — global Layer-A table, same RLS model |
| 3-hour customer windows with real internal timings; multiple appointments per displayed window | `calcOptimalTime` index.html:5661 stacks by actual travel+service times, never "window looks occupied" |
| Booking-Guard core (eligibility, feasibility, best tech/date/window, why-not explanations) | `buildCandidates` index.html:5743 + `findBestSlot` index.html:6184 + `guardManualPlacement` index.html:5137 + `explainCandidate` index.html:5383 |
| Change-driven localized recalc (not whole-week) | `markDayDirty` index.html:5497 → debounced `sequenceDay`; single shared payload builder `_postOptimize` index.html:5508 (auto + manual button can't drift) |
| One tenant-config source of truth | `tenants.config` + the knob contract in `context/knobs.md` (key → JS reader → batch reader → test); `placement_policy` consolidate/spread batch_schedule.py:310–343 |
| Duration chain, one resolver both doors | `effectiveDuration` index.html:5481 ⇄ `_effective_duration` batch_schedule.py:242, golden fixture `tests/fixtures/duration-cases.json` |
| Manual-override audit trail | `tasks.manually_overridden` + `override_reason` → `_audit_tasks` trigger → `audit_log` (free — no new infra) |
| Structured explanations without an LLM | `explainCandidate` + `describeConstraintsHe` prove the template approach; Hebrew, dispatcher-readable |
| Fill-first within full optimization (priority semantics) | Shipped engine default — Eran's E15 definition in `context/scheduling-scenarios.md` |
| **Dynamic slot release with 72/48/24h tenant thresholds** (raw prompt capability #4) | `slot_release {enabled, conservative/moderate/aggressive_hours}` knob (knobs.md:24) enforced in `_candidatesZone` index.html:5813–5830 + `getSlotReservationOffset` late-start reservation in `calcOptimalTime` index.html:5675–5681; batch n/a **by design** (assigns whole days). Missing only: dispatcher-facing "why is this slot protected" explanation + demand-history smartness (deferred) |
| Insert-time backtrack rejection | `wouldBacktrack` index.html:5763 + `isRouteLogical` index.html:5719 reject far→near→far placements; OR-Tools `DIRECTION_PENALTY` (optimizer.py:331–341) enforces monotone direction in sequencing |
| Tenant isolation for jobs/caches | RLS everywhere; global tables deny-all + service key; per-tenant config never in shared code |

### PARTIAL — exists at insert-time, missing as hindsight

| Requirement | What exists | What's missing |
|---|---|---|
| Backtracking (far→near→far) | Rejected at insert-time (`wouldBacktrack`) and penalized in sequencing (OR-Tools direction penalty) | No detector/quantifier that flags it on an **existing** schedule (hindsight) |
| Within-city address order + best exit toward next city | Solver handles it at coordinate level when addresses are geocoded | Not audited, not explained to the dispatcher |
| Protected capacity visibility | Fully enforced (see slot_release row above) | Dispatcher can't see WHY a slot is held; no release observability |
| Lateness / idle-gap awareness | Computed when placing a call | Not continuously scored on the standing schedule |
| Concurrency (two coordinators booking at once) | Nothing — **named real gap** | Booking-time version check / optimistic lock |

### MISSING — the genuinely new product

1. **Route Health score** — normalized per tech-day (dispatcher-readable), computed from the existing scoring signals.
2. **Day Route Auditor** — re-evaluates a built day: order, assignment, backtracking, lateness risk, buffers; quantifies each finding.
3. **Recommendation workflow** — propose → show before/after + expected saving → dispatcher approves/rejects; nothing auto-applies.
4. **Persistence for the above** — `route_versions`, `audit_findings`, recommendations + accept/reject status, optimization-job status.
5. **Weekly Rebalancer** — cross-tech / cross-day proposals, stability-thresholded, dry-run first.

~~6. Dynamic slot release~~ — **already shipped** (see EXISTS table); only its dispatcher-facing explanation remains, which folds into the auditor's finding/explanation templates.

---

## 2. Non-negotiable invariants — SETTLED

1. **One shared constraint/scoring implementation.** The auditor/health-score MUST read the
   same constraint and scoring logic as live JS and batch Python — golden-fixture enforced,
   exactly like the duration chain. **No third door.** If the auditor needs a rule the
   engine has, it calls the engine's implementation.
2. **Deterministic engine extensions + FastAPI background jobs.** Not a separate agent
   service, not n8n (n8n stays peripheral-only — notifications/CRM — and is unneeded at
   pilot scale). No LLM anywhere in calculation, validation, or scoring; templates first
   for explanations (existing pattern proves sufficiency), LLM optional later for prose only.
3. **Change-driven triggers, not day-full.** Audits hook the existing `markDayDirty`
   seam (plus dispatcher-requested and scheduled runs). "Day becomes full" is one signal
   among several, not the trigger.
4. **Recommendations, never auto-apply.** Phase 1–3 are read-only or approve-gated. The
   confirmed schedule must remain usable if optimization fails (fail-open, existing habit).
5. **Stability metric = minutes-saved-per-customer-disturbed**, a tenant knob. A change
   that saves 4 minutes but touches a confirmed appointment is rejected by default.
6. **No new "micro-zone" entity.** Polygons + `geo_addresses` coordinates already cover
   sub-city grouping; grouping is a scoring concern, not a schema concern.
7. **Every new tenant rule follows the knob contract** (`context/knobs.md`): key → both
   readers → test, same commit. Nothing PureWater-specific hardcoded.
8. **Tenant isolation extends to everything new**: route versions, findings, jobs, logs.
   Global caches stay tenant-independent by construction (coordinates only, no customer data).

---

## 3. Decisions already made — SETTLED (with rationale)

- **Reframe: this is an audit/observability layer over an engine that already optimizes,**
  not a new optimization system. The raw prompt's Booking Guard is mostly shipped; its
  remaining delta (concurrency protection, protected-capacity awareness) folds into
  existing booking paths rather than a standalone phase.
- **Route Health is computed from existing signals** (travel share, backtrack count,
  idle gaps, lateness risk, window compliance) and normalized so a dispatcher can read it.
  It's the Phase-1 deliverable because it creates the shared scoring vocabulary every
  later phase consumes.
- **Simulation corpus = Israel's 20-month export** (already imported). Every auditor/
  rebalancer claim is validated by replaying real PureWater history: "on week X the
  rebalancer would have proposed Y, saving Z minutes."
- **Concurrency is a real gap and is in scope** (optimistic version check on booking
  write), sized during design — it protects the existing product, not just the new layer.
- **Fixed release thresholds stand** — they're already shipped as the `slot_release` knob;
  demand-history-driven release is explicitly deferred — there is not yet enough
  multi-tenant history to learn from.

---

## 4. Delivery phases — SETTLED (re-cut from the raw prompt's six)

- **P1 — Read-only Route Health + Day Audit.** Score every tech-day; list findings
  (backtracking, gaps, lateness risk, better-order-exists) with quantified impact. No
  schedule writes at all. Golden fixtures pin the score to engine scoring.
- **P2 — Recommendation workflow.** `route_versions` + `audit_findings` +
  recommendations tables; before/after comparison UI; approve/reject; audit trail via the
  existing `_audit_tasks` pattern. Booking-concurrency guard lands here.
- **P3 — Weekly Rebalancer, dry-run behind a flag.** Cross-tech/cross-day proposals
  validated against the 20-month replay before any live tenant sees them; stability knob
  enforced.
- **P4 (optional) — LLM prose + notifications/n8n peripherals.** Only if templates prove
  insufficient; engine must keep working without it.

Dropped: the raw prompt's standalone "Booking Guard" phase (built), its "Slot Release
Service" phase (built — `slot_release` knob live since before this brief; its
"why protected" explanation lands as a P1 audit finding type), and its "Phase 1 route
observability with scoring but no detection" split (health score and violation detection
are the same computation — shipping them together is cheaper).

---

## 5. What the design session must still produce (Open questions)

1. **Route Health formula** — which signals, weights, normalization (0–100?), and which
   weights are tenant knobs vs system invariants. Must be explainable per component.
2. **Shared-implementation mechanics** — concretely how the auditor (Python, background)
   reuses live-JS scoring rules without a third door: shared fixtures only, or promote
   scoring to the batch reader + fixture-pin the JS side? Decide per rule.
3. **Schema design** for `route_versions`, `audit_findings`, recommendations, job status —
   run `context/new-entity-checklist.md` for each; define retention (versions per day?).
4. **Trigger tuning** — debounce/coalescing for audit jobs off `markDayDirty` at batch
   scale; scheduled nightly audit scope; who pays (job budget per tenant).
5. **Concurrency mechanism** — optimistic version column vs advisory lock vs
   check-and-insert; where it sits in `findBestSlot`→save and the batch commit path.
6. **Stability-knob default** — a concrete starting value for minutes-per-disturbed-customer
   (propose from the 20-month replay, confirm with Eran/Israel).
7. **Dispatcher UX states** — where Health + findings surface (home cockpit? day view?),
   consistent with the AI-dispatch-cockpit north star and the pending Home redesign.
8. **Traffic-time freshness** — whether/when cached durations need time-of-day awareness,
   and what that does to route_cache keys and Google quota (hard caps: DM 700/day).

---

## 6. Requirement detail retained from the raw prompt

The raw prompt's scenario sections remain the acceptance catalog — read them verbatim in
`outputs/route-intelligence-prompt-raw_2026-07-09.md`:

- **Scenarios 1–3** (multi-appointment windows, within-city order, backtracking) → P1
  auditor test cases. Scenario 1 is already engine behavior; the auditor must *confirm*
  it, not re-implement it.
- **Scenario 4** (day full) → one audit trigger among several (see invariant #3).
- **Scenario 5** (weekly rebalance, ~100 calls / 3 techs) → P3 acceptance test, run as
  replay on real history.
- **Scenario 6** (new appointment mid-week) → mostly shipped; its concurrency clause is
  the P2 guard.
- **Scenario 7** (different tenant logic) → the knob contract, already the house rule.
- **Constraint model / scoring sections** → input to Open questions 1–2; hard constraints
  invalidate, soft constraints score — matches the engine's current split.
- **Failure handling, security, cost sections** → checklists for each phase's design
  review; nothing there contradicts current architecture.
- **Testing scenarios list** → the auditor/rebalancer test matrix, executed primarily as
  golden fixtures + 20-month replay.

---

## 7. Process requirements for the design session

- Run under **fable-mode** discipline: gap-map first (done — §1), evidence over memory
  (open the real files before specifying), adversarial pass on the Health formula and
  stability threshold, verify by replay, report calibrated.
- Read before designing: `context/scheduling-rules.md`, `context/scheduling-scenarios.md`,
  `context/knobs.md`, `backend/batch_schedule.py`, `backend/optimizer.py`,
  the `<sched-logic>` block in `index.html`, `context/new-entity-checklist.md`.
- Output: a design doc (`outputs/route-intelligence-design_2026-07-09.md`) answering §5's
  open questions + a concrete P1 spec (files, functions, fixtures, tests, migration list),
  sized so P1 is shippable in one focused slice sequence.
- Living docs: new scenarios → `context/scheduling-scenarios.md`; new knobs →
  `context/knobs.md`; new tables → checklist + advisors. Same-commit rule applies.
