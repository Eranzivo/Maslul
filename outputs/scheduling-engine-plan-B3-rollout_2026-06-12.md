# Plan B3 — Strategy Bias, Balance, Gap-Fill & PureWater Rollout Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans. Steps use checkbox (`- [ ]`) syntax.

**Goal:** Close the expert-dispatcher loop: honor each tenant's route philosophy inside the optimal solver, balance work across technicians, suggest gap-fills when a slot frees up, and gate PureWater's enablement behind a side-by-side shadow comparison.

**Architecture:** Four independent, individually-shippable pieces: (1) `route_strategy` as a *soft bias* inside `solve_route_v2` (depot-arc cost shaping — far-first preferred when costs are close, min-drive still dominates); (2) a weekly cross-tech balance term in assignment scoring (config-gated); (3) cheapest-insertion gap-fill suggestions after a cancel; (4) a super-admin shadow-compare modal that calls `/optimize` read-only and shows current vs proposed order with total drive minutes — the PureWater go/no-go artifact.

**Tech Stack:** as B2 (vanilla JS + `<sched-logic>` tests; FastAPI/OR-Tools + pytest at `%LOCALAPPDATA%\Programs\Python\Python312\python.exe`).

**Source:** design spec §2 (balance), §3 (gap-fill), §8 (rollout/shadow); B2 live observation (recorded in `context/scheduling-rules.md`): v2 ordered באר שבע→דימונה (95 min) vs the far→near heuristic's דימונה→באר שבע (118 min) — the bias must make far-first win ties without sacrificing real savings.

---

## Task 1: `route_strategy` bias in `solve_route_v2` (backend, TDD)

**Approach:** keep the min-drive objective; add a **depot-departure shaping cost**: for `far_to_near`, the arc depot→task `j` gets `+ bias × closeness(j)` where `closeness(j) = (max_depot_dist − depot_dist(j))` scaled so the bias is ~15% of the matrix mean — enough to win ties and near-ties, never enough to force a 20%-worse route. `nearest_first` mirrors (penalize far starts). `flexible` = no shaping.

**Files:** `backend/optimizer.py` (`solve_route_v2` signature + shaping), `backend/main.py` (pass `scheduling.route_strategy` from the request's `SchedulingConfig`), `backend/tests/test_sequencing.py`

- [ ] **Step 1 — failing tests:**

```python
def test_far_to_near_bias_wins_ties():
    # symmetric matrix: both orders cost the same → far task (idx 1, 30 from depot) must go FIRST
    m = [[0, 10, 30], [10, 0, 20], [30, 20, 0]]
    tasks = base_tasks()
    r = solve_route_v2(m, tasks, "07:00", "18:00", breaks=[], route_strategy="far_to_near")
    assert r["ordered"][0] == 1  # farther-from-depot first

def test_bias_never_overrides_big_savings():
    # far-first costs much more (40+35=75 vs near-first 10+35=45) → min-drive must still win
    m = [[0, 10, 40], [10, 0, 35], [40, 35, 0]]
    tasks = base_tasks()
    r = solve_route_v2(m, tasks, "07:00", "18:00", breaks=[], route_strategy="far_to_near")
    assert r["ordered"][0] == 0  # cheaper route preserved despite bias
```

- [ ] **Step 2 — run, verify FAIL** (unexpected keyword `route_strategy`).
- [ ] **Step 3 — implement:** add `route_strategy: str = "flexible"` param; after building `full`, when strategy is `far_to_near`/`nearest_first`:

```python
    if route_strategy in ("far_to_near", "nearest_first") and n_tasks >= 2:
        depot_d = [full[0][j] for j in range(1, n_tasks + 1)]
        max_d = max(depot_d) or 1
        mean_cost = sum(sum(row) for row in full) / max(1, (n_nodes * n_nodes - n_nodes))
        bias = max(1, int(mean_cost * 0.15))
        for j in range(1, n_tasks + 1):
            closeness = (max_d - full[0][j]) / max_d          # 1 = nearest, 0 = farthest
            shape = closeness if route_strategy == "far_to_near" else (1 - closeness)
            full[0][j] += int(bias * 3 * shape)               # only the depot-departure arc
```
(Shaping only the first leg keeps the rest of the tour purely min-drive.)
- [ ] **Step 4 —** `optimize_routes`: read strategy from a new param `route_strategy` (default "flexible"); `main.py` `/optimize` passes `req.scheduling.route_strategy if req.scheduling else "flexible"` — extend `SchedulingConfig` with `route_strategy: str = "flexible"`. **Frontend `sequenceDay`** already sends no `scheduling` → add `scheduling:{route_strategy:resolveRouteStrategy(tenantConfig.scheduling)}` to its POST body (pure helper exists).
- [ ] **Step 5 — run all backend tests** (expect 44) + frontend suites; commit:

```bash
git commit -m "feat(seq): route_strategy as depot-arc bias in solve_route_v2 — far-first wins ties, min-drive wins real savings"
```

---

## Task 2: Weekly cross-tech balance term (frontend pure, TDD)

**The Michael-Sunday rule:** adding a Netanya job should prefer Michael's *partial* Sunday over opening Eliran's *empty* Thursday — across techs, across the lookahead window.

**Files:** `index.html` (`<sched-logic>` + `_candidatesZone`/`_candidatesOpen`), `tests/sched.test.js`

- [ ] **Step 1 — failing tests** for a pure helper:

```js
suite('balanceAdjust', () => {
  // candidate A: day already has 3 tasks (partial) → bonus; candidate B: empty day later → none
  check('partial day beats empty later day',
    ctx.balanceAdjust({enabled:true,weight:50}, {dayLoad:3, dateOffset:0}) >
    ctx.balanceAdjust({enabled:true,weight:50}, {dayLoad:0, dateOffset:4}));
  check('disabled → 0', ctx.balanceAdjust({enabled:false,weight:50}, {dayLoad:3, dateOffset:0}) === 0);
  check('absent config → 0', ctx.balanceAdjust(undefined, {dayLoad:3, dateOffset:0}) === 0);
});
```

- [ ] **Step 2 — implement** in `<sched-logic>`:

```js
// Cross-tech fill-before-open: reward candidates landing on already-active days,
// penalize opening empty days that are further in the future. Config: scheduling.balance.
function balanceAdjust(balanceConf, c){
  if(!balanceConf || !balanceConf.enabled) return 0;
  const w = balanceConf.weight || 50;
  const fillBonus = c.dayLoad > 0 ? w : 0;
  const emptyLatePenalty = c.dayLoad === 0 ? Math.min(c.dateOffset, 6) * (w / 10) : 0;
  return fillBonus - emptyLatePenalty;
}
```

- [ ] **Step 3 — wire:** in `_candidatesZone` and `_candidatesOpen`, after `fillScore` is computed: `fillScore += balanceAdjust(sc.balance, {dayLoad:load, dateOffset:dates.indexOf(date)});` (absent config ⇒ +0 ⇒ today's behavior).
- [ ] **Step 4 — tests green (36 sched expected), commit.**

---

## Task 3: Gap-fill suggestions after cancel (frontend)

**Files:** `index.html`, `tests/sched.test.js`

- [ ] **Step 1 — pure ranking helper + tests:**

```js
suite('rankGapFill', () => {
  const freed={techId:'T',date:'2026-06-15',time:'09:00',city:'באר שבע'};
  const pending=[
    {id:'a',status:'pending',city:'באר שבע'},
    {id:'b',status:'pending',city:'קריית שמונה'},
    {id:'c',status:'assigned',city:'באר שבע'},
  ];
  const ranked=ctx.rankGapFill(freed,pending,(c1,c2)=>c1===c2?0:300);
  check('same-city pending ranks first', ranked[0]&&ranked[0].id==='a');
  check('non-pending excluded', !ranked.some(t=>t.id==='c'));
});
```

Implementation (in `<sched-logic>`): filter `status==='pending'`, sort by `distanceOf(freed.city, t.city)` ascending (caller passes a distance function — city-coords haversine), return top 5.
- [ ] **Step 2 — UI:** in `cancelOnly`, when `_autoSeqOn()`, after `markDayDirty`: compute `rankGapFill` against pending tasks; if any, toast with action: `showToast('התפנה חריץ — יש קריאות ממתינות מתאימות. פתח שיבוץ?')` and render the top suggestions into the existing pending-queue panel order (set a `_gapFillHint` that `renderPendingQueue` sorts by). Non-blocking, no auto-assign (B-future: `gap_fill.auto`).
- [ ] **Step 3 — tests + commit.**

---

## Task 4: Shadow-compare modal (the PureWater gate)

**Files:** `index.html`

- [ ] **Step 1 — UI entry:** in the daily planner header (next to `optBtn`), super_admin only: `🔍 השוואת מסלול` → `shadowCompare(techId, ds)`.
- [ ] **Step 2 — implement** `shadowCompare`: builds the same payload as `sequenceDay` (reuse `buildSequencePayload`), POSTs `/optimize`, **persists nothing**; renders a modal with two columns:
  - **נוכחי:** tasks in current `time` order + current total drive (sum of legs is unknown client-side → show backend `total_drive_minutes` from a second call with `locked:true` on every task at its current time — pinning all tasks reproduces the current order's cost)
  - **מוצע:** proposed order with arrival times, per-leg 🚗 trace, `total_drive_minutes`, and a delta line: `חיסכון: X דק׳ נסיעה`
  - Buttons: `סגור` / `החל סדר מוצע` (the apply button calls `applySequenceResult` + persists — same code path as `sequenceDay`).
- [ ] **Step 3 — manual QA** on the test tenant; commit.

---

## Task 5: Optimistic versioning (two-coordinator guard)

**Files:** `index.html`

- [ ] In `sequenceDay`, before persisting: re-fetch the day's tasks' `updated_at` *(already returned by `select('*')` loads — map `updatedAt: t.updated_at` in the task loader if absent)* and compare to the values held when the payload was built; on any mismatch → abort persist, `markDayDirty` again (re-sequence from fresh state). Add `updatedAt` to the load mapper + keep it refreshed in `saveTaskToSupabase` responses. Commit.

---

## Task 6: Living-docs + PureWater rollout checklist

- [ ] Docs: scheduling-rules (bias semantics, balance config, gap-fill, shadow-compare), architecture (API param), purewater.md (rollout state).
- [ ] **Rollout sequence (Eran-driven, in order):**
  1. Enable `auto_sequence` on **Maslul Admin** tenant → live QA (assign 3 → self-sequence; cancel → tighten; lock → pinned; overfill → tray).
  2. Run **shadow-compare** on 2–3 real PureWater days (impersonated, read-only) → show Israel current vs proposed + fuel delta.
  3. Israel approves → set `route_strategy` bias expectation (far-first tie-break) → enable `auto_sequence` for PureWater.
  4. Watch the first live week; `route_cache` warms; `/health` Google usage should trend toward zero.

---

## Verification (whole plan)
1. Backend 44/44; frontend sched ≥36 + zones 18.
2. Bias: far-first on ties, min-drive on real savings (Tasks 1 tests) — and live: the באר שבע/דימונה pair re-run returns דימונה first when strategy=far_to_near with near-equal costs, באר שבע first when savings are big.
3. Balance/gap-fill/shadow all no-ops when configs absent.
4. PureWater unchanged until step 3 of the rollout checklist.
