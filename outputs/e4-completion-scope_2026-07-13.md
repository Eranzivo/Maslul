# E4-lite — Completion Timestamps → Reports Duration-Accuracy Insight (scope)

**Date:** 2026-07-13 · **Status:** ✅ PHASE A SHIPPED 2026-07-14 (Eran: "prioritize yourself, continue building").
Delivered: migration `en_route_at`/`arrived_at`/`completed_at` (nullable, applied via MCP, advisors clean);
`stampStatusTimestamps` on both write paths (first-write-wins); loader + `saveTaskToSupabase` mapping;
pure `durationAccuracyInsights` (min 3 jobs, ≥25% gap, median, outlier-clamped) surfaced in the reports
insights feed + the two stamps added to the CSV export. Tests: 9 golden cases in sched.test.js (253 green).
Q1 answered **yes** — `en_route_at` included (enables future travel-leg timing). **Phase B remains future.**

## 1. Why this exists — the learning loop
The engine's whole schedule quality rests on one number per category: **service duration**
(`effectiveDuration`, [index.html:5923](../index.html#L5923) — tech override → category `time` → default 30).
Today that number is a **human guess** entered at onboarding. If "טוחן אשפה" is configured at 30 min but
really takes 48, every day is over-packed, windows spill, and overrun logic fires more than it should.

We have no way to know, because **we never record how long a job actually took.** This slice closes the loop:
capture actual on-site time → surface, per category, "configured 30 min, actually ~48 (median of 12 jobs) —
consider raising." Suggestion only; the coordinator decides. It is the same doctrine as today's zone insights
(timeframe stamp · הצעה בלבד · never auto-change config).

## 2. Current state (evidence)
| Piece | State today | Evidence |
|---|---|---|
| Status lifecycle | pending → assigned → en_route → arrived → completed (+issue/cancelled) | `STATUS_MAP` [index.html:3484](../index.html#L3484) |
| Status write path (manager) | `setStatus(ns)` sets `t.status`, saves — **no timestamp** | [index.html:8157](../index.html#L8157) |
| Status write path (tech) | `techSetStatus(id,ns)` same — **no timestamp** | [index.html:8263](../index.html#L8263) |
| Persist mapping | `saveTaskToSupabase` maps `cancelled_at` (only transition stamp today) | [index.html:3342-3355](../index.html#L3342) |
| `tasks` columns | `created_at, updated_at, cancelled_at, geocoded_at` — **no `arrived_at`/`completed_at`** | [architecture.md:146](../context/architecture.md#L146) |
| Reports insights | zone coverage-gap + overload only; duration branch **absent** | `renderReports` insights block [index.html:4821](../index.html#L4821) |
| Interim shipped | דוחות footnote says accuracy needs completion events | [round2-port-map:98](round2-port-map_2026-07-12.md) |

**Precedent that de-risks this:** `cancelled_at` already proves the pattern — a nullable TIMESTAMPTZ column
stamped at a transition (`t.cancelledAt=new Date().toISOString()`), mapped in `saveTaskToSupabase`, read on load.
We copy that pattern exactly.

## 3. Scope boundary — E4-lite, not E4
Full E4 = live "departed/finished" events → **live ETA re-flow of downstream promises + proactive customer
alerts + WhatsApp** ([scheduling-scenarios.md:40](../context/scheduling-scenarios.md#L40)). That is post-pilot, big.

**This slice is a strict subset:** just *record and read back* two timestamps. No re-flow, no alerts, no WhatsApp,
no live recompute. It is safe, additive, and independently valuable.

| In scope (E4-lite) | Out of scope (full E4 / later) |
|---|---|
| `arrived_at`, `completed_at` columns (nullable) | live ETA re-flow of later jobs |
| stamp them on status flip (both write paths) | proactive customer "running late" alerts |
| median actual-vs-configured insight per category | WhatsApp event channel (יצאתי/סיימתי) |
| CSV/export carries the two stamps | **engine auto-consuming** learned durations (Phase B) |

## 4. What "actual duration" means (and why)
The configured number represents **service time**, so the honest comparison is **`completed_at − arrived_at`**
(time on site). NOT `en_route → completed` (that folds in travel) and NOT `assigned → completed` (includes wait).

- Stamp `arrived_at` on first entry to `arrived`; `completed_at` on entry to `completed`. First-write-wins
  (never overwrite if a status is re-flipped — the first arrival is the truth).
- A job that jumps straight assigned→completed (tech skipped "arrived") has **no** `arrived_at` ⇒ **excluded**
  from the insight (can't measure it). Acceptable; note it so techs are nudged to use the arrived step.

## 5. Design — four small parts
**A. DB (migration, follows new-entity/knob rules)**
- `ALTER TABLE tasks ADD COLUMN arrived_at TIMESTAMPTZ, ADD COLUMN completed_at TIMESTAMPTZ;` (both nullable).
- No backfill — historical rows stay null and are simply excluded (median over what we have).
- RLS unchanged (same table, same policies). Run Supabase security advisors after (standing rule).
- File: `outputs/migrations/migration-completion-timestamps_YYYY-MM-DD.sql`; mirror columns into
  `context/architecture.md` schema row **same commit**.

**B. Capture (both write paths, tiny)**
- `setStatus` + `techSetStatus`: before save, `if(ns==='arrived' && !t.arrivedAt) t.arrivedAt=nowIso();`
  `if(ns==='completed' && !t.completedAt) t.completedAt=nowIso();`
- Map in `saveTaskToSupabase`: `arrived_at: task.arrivedAt||null, completed_at: task.completedAt||null`.
- Read back in the task loader (where `createdAt`/`cancelledAt` are hydrated, ~[index.html:2933](../index.html#L2933)).
- One helper `nowIso()` used by both paths — one implementation, no drift.

**C. Compute (pure, testable — put in `<sched-logic>`)**
```
durationAccuracyInsights(tasks, categories, opts) -> [{catId, catName, configured, actualMedian, deltaPct, n}]
```
- Per category: collect `completed_at − arrived_at` for rows in the reporting period where BOTH stamps exist
  AND delta is sane (≥ 3 min, ≤ 8 h — drops clock glitches / overnight).
- `actualMedian` = **median** (robust to the one 3-hour outlier), rounded to 5 min.
- Emit only when `n ≥ minSample` (default **5**) AND `|deltaPct| ≥ deltaThreshold` (default **25%**).
- Pure `var function` (test VM only sees `var`/function top-level — same rule as `REPORT_CARDS`).

**D. Surface (reports)**
- In `renderReports` insights array, add a branch that calls `durationAccuracyInsights(filtered, categories, …)`
  and pushes rows like: `קטגוריה "${name}" מוגדרת ל-${configured} דק׳ אך נמשכת בפועל ~${actualMedian} דק׳
  (חציון על ${n} קריאות ${rng.label}) — שקול לעדכן`. Suggestion only, obeys the 2-visible + עוד toggle doctrine.
- Also exposed in the categories card as a subtle "בפועל ~X" chip next to "מוגדר: Y דק׳" (optional polish).
- CSV export gains the two stamps (extend the export row builder ~[index.html:4694](../index.html#L4694)).

## 6. Edge cases (all handled in §5C filter)
- Missing either stamp → excluded. · Negative/zero delta (completed before arrived, clock skew) → excluded.
- Absurd delta (> 8 h, overnight) → excluded. · Small sample (n < 5) → suppressed (no "1 job says X").
- Cancelled/issue rows → never have `completed_at`, naturally excluded.
- Tenant with no arrived-step discipline → few qualifying rows → insight simply doesn't appear (fail-quiet).

## 7. Testing
- `tests/sched.test.js`: golden cases for `durationAccuracyInsights` — (a) exact match → no insight,
  (b) 60% over on 12 jobs → insight w/ correct median, (c) n=4 → suppressed, (d) one 5-hour outlier → clamped
  out, median unchanged, (e) missing `arrived_at` rows ignored.
- **Not a cross-runtime parity case.** This is display-only and does **not** influence any assignment/sequence
  decision, so there is no Python/batch counterpart and no golden fixture needed — unlike a real knob.
  (If Phase B ever feeds durations back into the solver, THAT becomes a knob with both readers + fixture.)
- jsdom smoke: flip a task arrived→completed, assert `arrived_at`/`completed_at` land in the upsert payload.

## 8. Knob decision
For v1, `minSample` (5) and `deltaThreshold` (25%) are **named constants**, not knobs — the insight is a display
heuristic, identical for every tenant, and changes no engine behavior. Promote to `insights.duration_*` knobs
(with the registry row + reader) only when a second tenant needs different sensitivity. Documented here so the
decision is explicit rather than silent. (The existing `insights.window_days` / `reports.cards` knobs already
gate visibility and period — this rides on those, adds no new tenant surface for v1.)

## 9. Effort, phasing, cost
- **Phase A (this scope) — capture + surface.** ~½ day. One migration, ~8 lines across two write paths + mapping
  + loader, one pure function + tests, one insights branch + export column. Low risk (additive, nullable, no RLS
  change, no engine path touched). **$0 infra** (columns are free; no new API calls).
- **Phase B (future, separate approval) — close the loop into the engine.** Actual medians *suggest* (or, opt-in,
  auto-apply) category `time` / per-tech overrides, or the solver reads a learned duration. This one **is** a knob,
  **is** cross-runtime (JS live + Python batch both must read the learned value), needs the golden fixture, and
  wants a human-approval gate (never silently re-time a client's history). Bigger; do after Phase A has ~weeks of data.

## 10. Bonus — one capture unblocks two loops
The same `arrived_at`/`completed_at` (plus GPS we already store) also unblocks the **travel-time learning loop**
that [geo-corrections-loop-design](geo-corrections-loop-design_2026-06-13.md) and the geo-foundation design
*assumed we already had* ("we already capture job-completion timestamps" — we don't yet). Actual on-site + actual
inter-stop travel is exactly what `route_cache` / the geo brain want to learn real durations instead of haversine
estimates. So Phase A is a foundation stone for [[geo-foundation-vision]], not a one-off report tweak.

## Open questions for Eran
1. Also stamp `en_route_at` now (free, enables future travel-leg timing) or keep to the two we need? (Rec: add it too — one migration, same cost.)
2. Insight sensitivity — 25% / min-5 feel right, or louder/quieter for the pilot?
3. Build Phase A now, or hold until after your QA pass? (Rec: after QA — it's additive and can slot in cleanly.)
