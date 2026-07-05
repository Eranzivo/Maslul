# Batch Correctness Pack — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `/batch-schedule` read the live calendar and enforce every tenant rule the live JS path enforces (spec: `outputs/batch-correctness-design_2026-07-05.md`).

**Architecture:** All changes in `backend/batch_schedule.py` as small pure helpers + a restructured `run_batch_schedule` (fetch live state → seeded greedy → per-day solve including existing calls → bounded retry of dropped). End-to-end tests run `run_batch_schedule` against a fake in-memory Supabase (monkeypatched `_sb_get`/`_sb_patch`) with PureWater-shaped fixtures.

**Tech Stack:** Python 3.12, pytest, OR-Tools via existing `solve_route_v2` (solver itself untouched).

## Global Constraints
- Absent config ⇒ behavior unchanged (every new enforcement no-ops when the field is absent/empty), EXCEPT the two outright bugs: existing-task blindness and the `arrival_window_hours` path.
- Mirror JS semantics exactly (`techHasSkill`, `getCatLimitOk`, `getTechPartialBlocks`, `isCityBlocked`, `blockedZones`).
- Existing calls: window/date/tech/status never modified; `scheduled_time` may change within window; locked pinned; existing never dropped in favor of new.
- Branch `batch-correctness`; commit per task; no push, no live write (dry-run only) without Eran's approval.

---

### Task 1: Config + eligibility pure helpers
**Files:** Modify `backend/batch_schedule.py`; Test `backend/tests/test_batch_correctness.py` (new)
**Produces:** `_arrival_window_hours(config)->int` · `_effective_duration(cat_id, tech, cat_duration, config)->int` · `tech_has_skill(tech, cat_id)->bool` · `cat_limit_ok(tech, cat_id, current_count)->bool` · `city_blocked(tech, city_norm)->bool` · `zone_blocked(tech, zone_id)->bool`

- [ ] Write failing tests: window-hours read from `defaults` (2 ⇒ 2; absent ⇒ 3; legacy top-level still honored as fallback); duration chain override→category→`regular_job_minutes`→30; skill semantics mirroring JS (`no cat_id ⇒ True`, configured skills without the cat ⇒ False, empty/absent skills with cat_id ⇒ False — same as JS `(tech.skills||[]).includes`); cat-limit counting; blocked city/zone.
- [ ] Run to fail → implement helpers → run to pass → commit.

### Task 2: Breaks + partial day-offs helper
**Files:** Modify `backend/batch_schedule.py`; Test `backend/tests/test_batch_correctness.py`
**Produces:** `tech_breaks(tech, config, partial_dayoffs)->list[{"from","to"}]` — mirror of JS `getTechPartialBlocks`: partial day_offs + break resolved tech `weekly_schedule._break` (`none`⇒no break, `custom`⇒its hours, else tenant `defaults.break` when `enabled`).

- [ ] Failing tests (none-mode, custom-mode, tenant default, disabled, partial day_off merge) → implement → pass → commit.

### Task 3: Live-state fetch + seeded greedy enforcement (the core)
**Files:** Modify `backend/batch_schedule.py` (`run_batch_schedule`, technicians select += `skills,cat_limits,blocked_zones,blocked_cities,duration_overrides`; new fetches: existing tasks in range `status=in.(assigned,en_route,arrived)` + `day_offs` in range); Test `backend/tests/test_batch_correctness.py`
**Produces:** fake-Supabase harness `FakeSB(tables)->monkeypatched _sb_get/_sb_patch` capturing patches; PureWater-shaped fixture builder `pw_fixture(...)`.

- [ ] Build the harness + fixtures (3 techs, real zone names, rotation, config shape from live).
- [ ] Failing tests: (a) 5 existing on a tech-day + max_daily 9 ⇒ ≤4 new placed there, overflow to other covering days; (b) full day_off ⇒ day skipped; (c) cat_limits count existing+new; (d) skills/blocked_zones/blocked_cities filter; (e) same-city counts seeded from existing.
- [ ] Implement: fetch both new sources up front (fail-closed by existing `raise_for_status`); seed `existing_slots[(tech,date)]`, `city_counts`, `cat_counts`; greedy candidate filter gains day_off/skill/cat-limit/blocked checks and counts existing occupancy; durations via `_effective_duration`; windows via `_arrival_window_hours`.
- [ ] Pass → commit.

### Task 4: Existing calls inside the day solve
**Files:** Modify `backend/batch_schedule.py` (`optimize_day` signature → `optimize_day(matrix, v2_tasks, start_t, end_t, breaks, return_node, route_strategy)`; day loop builds v2 tasks = existing (window hard from `scheduled_window_start/end`; locked ⇒ `locked+scheduled_time`) + new (flexible)); Test `backend/tests/test_batch_correctness.py`

- [ ] Failing tests: existing window preserved, time re-flows within window only; locked pinned exactly; if attempt 1 drops an existing ⇒ attempt 2 re-solves with ALL existing pinned at current times and only new calls drop; `_sb_patch` for existing carries `{"scheduled_time"}` only and only when changed.
- [ ] Implement (two-attempt policy, selective persist, breaks passed from Task 2 helper) → pass → commit.

### Task 5: Bounded retry of dropped new tasks
**Files:** Modify `backend/batch_schedule.py` (assignment+optimize wrapped in rounds; per-task exclusion set of tried (tech,date); max 6 rounds); Test `backend/tests/test_batch_correctness.py`

- [ ] Failing test: day A time-full ⇒ dropped task lands on covering day B same run; genuinely nowhere ⇒ `day_over_capacity`.
- [ ] Implement → pass → commit.

### Task 6: Regression + full verification
- [ ] All-pending regression test (no existing tasks ⇒ counts/behavior match today's semantics; absent-config tenant unchanged).
- [ ] `python -m pytest tests/ -q` all green; `node tests/zones.test.js && node tests/sched.test.js` untouched-green.
- [ ] Commit.

### Task 7: Live dry-run diff + docs + review
- [ ] Local read-only script (scratchpad) calling `run_batch_schedule(dry_run=True)` for PureWater over the current live week using `.env` service key; produce `outputs/batch-dryrun-diff_2026-07-05.md` (proposed vs current calendar; assignment counts; flags). NO writes.
- [ ] Living docs same branch: `context/scheduling-rules.md` batch section (live-state read, enforcement parity, retry, existing-call policy).
- [ ] `/code-review` on the branch diff; log methodology + findings in `outputs/ways-of-working_2026-07-02.md`.
