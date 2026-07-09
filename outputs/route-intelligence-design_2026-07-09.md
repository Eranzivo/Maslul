# Route Intelligence — Design (answers to the brief's open questions + P1 spec)

> Runs against `outputs/route-intelligence-brief_2026-07-09.md` (requirement source-of-truth).
> Status: **P1 BUILT same day (Eran approved "go ahead and start")** — all 7 slices shipped;
> replay validated (`outputs/route-health-replay_2026-07-09.md`). Two calibrations the replay
> forced, now canon: **window semantics = ARRIVAL** (start-inside; solver stays stricter when
> placing) and **solver-endorsed zigzags are not flagged**. Live behind `config.audit.enabled`
> (default false — enable per tenant after smoke test). P2 (recommendation workflow) awaits
> Eran's go.
> Method: fable-mode — every claim below is anchored to code read 2026-07-09.

---

## The one architectural insight everything else follows from

`solve_route_v2` (backend/optimizer.py:263) already returns, for every solve:
`ordered` (best stop order), `arrivals` (absolute minutes, waiting included),
`legs` (drive minutes per leg), `dropped`, `conflict`. And the live auto-sequencer
already calls it on **every schedule change** (`markDayDirty` index.html:5497 →
debounced `sequenceDay` → `_postOptimize` index.html:5508).

So the Day Route Audit is not a new engine — it is a **diff between the actual day
and the solver's answer for the same day**, computed from a solve that is already
being paid for. Route Health falls out of the same numbers.

Consequences:
- **No third door.** The auditor never re-implements a constraint. It feeds the day
  through the SAME `/optimize` payload builder and compares.
- **Near-zero marginal cost.** The change-driven trigger is the existing debounced
  hook; the matrix comes from `route_cache`; the only new compute is arithmetic.
- **One implementation, one language.** Health/findings are computed **in Python
  only** (where the solve result lives). The JS side *displays stored results* — it
  never recomputes. This answers brief open-question #2 more cleanly than fixture
  parity: there is nothing to keep in parity because there is only one implementation.
  (Golden fixtures still pin the Python computation itself.)

---

## Q1 — Route Health formula

Per tech-day, 0–100, computed from the solve result + actual schedule. Start = 100,
subtract weighted penalties; floor 0. Every component is separately stored and
explainable (template per component, same style as `explainCandidate`).

| Component | Signal (source) | Default penalty |
|---|---|---|
| **Excess drive** | `actual_drive − solver_best_drive` (Σ legs, both from solve_route_v2) | 1.5 pts / excess minute |
| **Backtracking** | count + magnitude of direction violations in the ACTUAL order (same monotone test as optimizer.py:331–341, run as arithmetic on `d_base`) | 8 pts / violation, cap 24 |
| **Lateness risk** | stops whose computed arrival > window_end − duration (windows from tasks) | 15 pts / at-risk stop |
| **Idle gaps** | Σ non-break slack > 15 min between consecutive stops | 1 pt / 5 idle min, cap 20 |
| **Overtime risk** | computed day end > work end (getTechDaySchedule / batch equivalent) | 10 pts + 1/min |
| **Window compliance** | stop scheduled outside its promised customer window | 20 pts / stop (data bug — should be rare) |

- **Tenant knobs:** the six weights, as `config.audit.health_weights` (one knob row,
  object-valued, like `slot_release`). Defaults above are system values.
- **System invariants (not knobs):** what counts as a violation (window math,
  direction test) — these mirror engine hard/soft semantics and must not fork per
  tenant.
- **Normalization:** absolute 0–100 with fixed bands — 90+ healthy / 70–89 review /
  <70 issues. Absolute (not percentile) so the score means the same thing on a
  2-call day and a 9-call day; the cap values keep any single component from
  drowning the rest.

## Q2 — Shared-implementation mechanics

Answered above: **Python-only computation, JS displays stored results.**
- New pure module `backend/route_health.py`: `compute_health(day) -> {score,
  components, findings[]}` where `day` = the same structured inputs
  `solve_day_with_existing` consumes + the actual current order.
- It reuses existing primitives (`time_to_min`, matrix rows, `_effective_duration`)
  — imports, never copies.
- Golden fixture `tests/fixtures/health-cases.json` pins score + findings for ~10
  canonical days (perfect day, one backtrack, gap day, lateness day, overfull day…).
  If the JS ever needs a preview computation later, this fixture becomes the parity
  contract — same mechanism as duration-cases.json.

## Q3 — Schema (minimal; new-entity-checklist applies to each)

Two tables, not four. YAGNI applied:

**`route_audits`** (P1) — one row per audited tech-day (latest wins; history kept):
`id, tenant_id (RLS), technician_id, date, score int, components jsonb,
findings jsonb, route_snapshot jsonb (ordered stops + times — this IS the route
version), solver_best jsonb (best order + drive total), trigger text
('change'|'nightly'|'manual'), created_at`.
Written by backend (service key), read by frontend under tenant RLS. Retention:
keep all for the pilot; revisit at client #2.

**`recommendations`** (P2) — one row per proposed change:
`id, tenant_id (RLS), audit_id fk, kind ('reorder'|'reassign'|'move_day'),
proposal jsonb (before/after), expected_saving_min int, disturbed_customers int,
status ('open'|'accepted'|'rejected'|'expired'), acted_by, acted_at, created_at`.
Accept/reject writes flow through the normal task-update path → `_audit_tasks`
trigger gives the change trail for free.

No separate `route_versions` table: `route_snapshot` on the audit row covers P1–P3;
a dedicated table only if the Weekly Rebalancer needs cross-day version graphs.
No `audit_findings` table: findings are jsonb on the audit row — they're read
together, always.

## Q4 — Trigger strategy

- **Change-driven (primary):** after `sequenceDay`'s solve returns, the backend
  computes health in the same request — `/optimize` response gains a `health`
  block and (server-side) upserts `route_audits`. The existing 1s debounce in
  `markDayDirty` already coalesces bursts. Frontend changes when auto-sequence is
  OFF: `markDayDirty` still fires; add an audit-only call (`/audit-day`) that runs
  the same payload with `dry_run` semantics — solver output is compared, nothing
  written to tasks.
- **Nightly (safety net):** FastAPI background job (same service, `asyncio` task or
  Railway cron hitting an endpoint) audits the next 7 days per tenant — catches
  days changed by paths that don't hit the optimizer. Budget: ≤ techs × 7 solves
  per tenant per night, matrix from route_cache ⇒ no Google cost on cached pairs;
  respects the DM 700/day hard cap by running cache-only (skip-and-flag on miss).
- **Manual:** dispatcher button per day (P2, with the UI).
- "Day becomes full" is just a state the score reflects — not a trigger (SETTLED).

## Q5 — Concurrency (booking guard delta)

Pilot-right-sized, two layers:
1. **DB uniqueness backstop:** partial unique index on
   `(tenant_id, technician_id, scheduled_date, scheduled_time) WHERE status IN
   ('assigned','en_route','arrived')` — two coordinators can no longer double-book
   the exact same slot; the second save surfaces as a friendly conflict toast
   (generic-Hebrew error rule applies).
2. **Stale-read guard:** before the save in the assign path, re-fetch the tech-day's
   task count + times and re-run the (existing) `guardManualPlacement` /
   `calcOptimalTime` check against fresh rows; abort with "הלוח התעדכן — רענן ונסה
   שוב" if the slot moved.
Full optimistic `version` columns are deferred — at 2 coordinators the index +
recheck close the realistic race; revisit at client #2 scale.

## Q6 — Stability knob default

`config.audit.min_saving_per_disturbed_min`, default **15** (a recommendation must
save ≥15 drive-minutes per confirmed customer it moves; 0-customer reorders need
≥10 total). Provisional — P3's replay of Israel's 20-month export calibrates it:
we compute the histogram of would-have-been savings and set the default where
recommendations become "obviously worth a phone call". Confirm with Eran/Israel.

## Q7 — Dispatcher UX (P1 minimal, redesign-compatible)

P1 ships **read-only**: a health chip (🟢 92 / 🟡 78 / 🔴 55) on each tech-day header
in the daily/weekly views, click → side panel listing findings in Hebrew (template
strings, `describeConstraintsHe` style). No layout rework — the chip slots into the
existing day header; the Home-redesign direction Eran picks decides its final home
(cockpit KPI row is the natural landing spot). P2 adds the recommendation
before/after panel with accept/reject.

## Q8 — Traffic freshness

Deferred, deliberately: route_cache stores time-of-day-independent durations; the
health math inherits whatever the matrix says, so freshness upgrades later improve
audits with zero auditor changes. Revisit when address-level geocoding goes live
(same trigger as the geo meter — client #2). Quota note stands: cache-only nightly
audits, DM 700/day hard cap.

---

## P1 spec (shippable slice sequence)

1. **`backend/route_health.py`** — pure `compute_health(...)`; TDD with
   `tests/fixtures/health-cases.json` (10 canonical days) + pytest suite.
2. **`route_audits` table** — full new-entity-checklist (RLS, load mapping n/a —
   frontend read-only via select, advisors run).
3. **`/optimize` response + upsert** — health block computed from the solve already
   performed; upsert audit row (service key). Flag-gated: `config.audit.enabled`
   (default false; on for PureWater after Eran's smoke test).
4. **`/audit-day` endpoint** — same payload builder, no task writes; used by
   nightly job + manual trigger later.
5. **Nightly job** — 7-day cache-only sweep per tenant with `audit.enabled`.
6. **Health chip + findings panel** — read `route_audits`, display; UI-testing rule.
7. **Replay validation** — run the auditor across Israel's 20-month export; report
   score distribution + top finding types (this doubles as the Q6 calibration data
   and the "does this thing say true things" acceptance test).

Living docs, same commits: knob rows (`audit.enabled`, `audit.health_weights`,
`audit.min_saving_per_disturbed_min` — reader is Python-only; knobs.md marks the JS
column "display-only by design", like slot_release's batch column), scenario rows in
`context/scheduling-scenarios.md`, architecture.md table entry.

## Risks / honest unknowns

- **Solver-diff noise:** the solver may find a 2-minute-better order on a healthy
  day; the findings threshold (don't report reorders < 10 min) is what keeps trust.
  Set it before the chip ships, not after dispatchers learn to ignore yellow.
- **Matrix gaps:** days with uncached city pairs get partial audits — the audit row
  must say `partial: true` rather than emit a fake score (fail-open, visibly).
- **`sequenceDay` path coverage:** manual placements with auto-sequence disabled
  bypass the optimizer today; step 4's `/audit-day` covers them, but until the
  nightly job ships those days audit only on demand.
