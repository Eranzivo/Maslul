# Scheduling Engine Generalization — Plan A (Slices 1–2) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make every `route_strategy` real and honest, flip the unsafe `far_to_near` default to `flexible`, and add the `locked` task seam — all pure-JS, zero external quota, behind backward-compatible defaults.

**Architecture:** Extract the route-strategy decision into small pure helpers inside a new `// <sched-logic>` marker block (testable by a dependency-free Node harness), then refactor the existing `isRouteLogical` / `wouldBacktrack` / `_candidatesZone` to delegate to them. Add a `tasks.locked` boolean that round-trips DB↔JS plus a pure `splitLockedFlexible` helper, establishing the lock seam the Plan B auto-sequencer will consume.

**Tech Stack:** Single-file `index.html` (vanilla JS, no build step), Supabase (Eran runs migrations), dependency-free Node test harness in `tests/`.

**Source spec:** `outputs/scheduling-engine-design_2026-06-10.md` (§1, §2 guards, §4 locks, §10 testing, slices 1–2 of §11).

**Scope note:** This plan covers Slices 1–2 only. Slices 3–7 (drive-time cache, authoritative `sequenceDay`/`markDayDirty`, balance, gap-fill, rollout) require the backend `optimizer.py` + the post-quota-review Google budget number and get their own plan (Plan B) after this lands.

**Convention reminders for the implementer:**
- Never touch the production DB. Migrations are delivered as SQL code blocks for Eran to run in Supabase.
- Living-docs sync: the doc-sync task at the end is mandatory, in the same branch.
- Run tests with plain `node` — there is no npm/build.

---

## File Structure

| File | Responsibility | Change |
|---|---|---|
| `index.html` | The whole app. New `// <sched-logic>` block holds pure strategy helpers; engine functions delegate to them; task mappers carry `locked`. | Modify |
| `tests/sched.test.js` | New dependency-free harness extracting `// <sched-logic>` blocks and asserting the pure helpers. | Create |
| `outputs/migration-tasks-locked_2026-06-10.sql` | SQL for Eran to add `tasks.locked`. | Create |
| `context/scheduling-rules.md` | Living doc — strategy-as-bias, honest strategies, safe default, lock seam. | Modify |
| `context/clients/purewater.md` | Confirm `far_to_near` explicit, record default-flip safety. | Modify |

---

## Task 1: Pure strategy helpers + test harness

**Files:**
- Create: `tests/sched.test.js`
- Modify: `index.html` — insert a new `// <sched-logic>` block immediately before `function getCityIndexInZone(` (currently line 4680)

- [ ] **Step 1: Write the failing test**

Create `tests/sched.test.js`:

```js
'use strict';
const fs = require('fs');
const vm = require('vm');
const path = require('path');

// ── Extract all // <sched-logic> … // </sched-logic> blocks from index.html ──
const html = fs.readFileSync(path.join(__dirname, '..', 'index.html'), 'utf8');
const re = /\/\/ <sched-logic>([\s\S]*?)\/\/ <\/sched-logic>/g;
let code = '', m;
while ((m = re.exec(html)) !== null) code += m[1] + '\n';
if (!code.trim()) { console.error('FAIL: no <sched-logic> blocks found'); process.exit(1); }

const ctx = {};
vm.createContext(ctx);
vm.runInContext(code, ctx);

let passed = 0, failed = 0;
function check(name, cond) { if (cond) { passed++; } else { failed++; console.error('  ✗ ' + name); } }
function suite(name, fn){ console.log('• ' + name); fn(); }

suite('resolveRouteStrategy', () => {
  check('absent config → flexible (safe default)', ctx.resolveRouteStrategy(undefined) === 'flexible');
  check('empty scheduling → flexible', ctx.resolveRouteStrategy({}) === 'flexible');
  check('explicit far_to_near honored', ctx.resolveRouteStrategy({route_strategy:'far_to_near'}) === 'far_to_near');
  check('explicit nearest_first honored', ctx.resolveRouteStrategy({route_strategy:'nearest_first'}) === 'nearest_first');
  check('legacy route_logic:true → far_to_near', ctx.resolveRouteStrategy({route_logic:true}) === 'far_to_near');
  check('legacy route_logic:false → flexible', ctx.resolveRouteStrategy({route_logic:false}) === 'flexible');
});

suite('isPairOrdered', () => {
  // index 0 = farthest from depot, higher index = nearer
  check('far_to_near: far(0) before near(2) OK', ctx.isPairOrdered('far_to_near',0,2) === true);
  check('far_to_near: near(2) before far(0) violates', ctx.isPairOrdered('far_to_near',2,0) === false);
  check('far_to_near: equal index OK', ctx.isPairOrdered('far_to_near',1,1) === true);
  check('nearest_first: near(2) before far(0) OK', ctx.isPairOrdered('nearest_first',2,0) === true);
  check('nearest_first: far(0) before near(2) violates', ctx.isPairOrdered('nearest_first',0,2) === false);
  check('flexible: any order OK', ctx.isPairOrdered('flexible',2,0) === true && ctx.isPairOrdered('flexible',0,2) === true);
});

console.log(`\n${passed} passed, ${failed} failed`);
process.exit(failed ? 1 : 0);
```

- [ ] **Step 2: Run test to verify it fails**

Run: `node tests/sched.test.js`
Expected: FAIL — `FAIL: no <sched-logic> blocks found` (exit 1), because the block doesn't exist yet.

- [ ] **Step 3: Add the pure helpers**

In `index.html`, immediately before `function getCityIndexInZone(city,zoneId,baseCity){` (line 4680), insert:

```js
// <sched-logic>
// Resolve the active route strategy with a SAFE default.
// far_to_near is PureWater/Israel-specific — it is NOT the global default.
// Absent config ⇒ 'flexible'. Legacy route_logic:true still opts into far_to_near.
function resolveRouteStrategy(sc){
  if(!sc) return 'flexible';
  if(sc.route_strategy) return sc.route_strategy;
  if(sc.route_logic === true) return 'far_to_near';
  return 'flexible';
}
// Is an (earlier-in-time, later-in-time) pair of zone indices ordered for this strategy?
// Zone index 0 = farthest from depot; higher index = nearer.
//   far_to_near  → index must not decrease over time (far first)  → earlier <= later
//   nearest_first→ index must not increase over time (near first) → earlier >= later
//   flexible     → no geographic constraint
function isPairOrdered(strategy, earlierIdx, laterIdx){
  if(strategy === 'far_to_near')  return earlierIdx <= laterIdx;
  if(strategy === 'nearest_first') return earlierIdx >= laterIdx;
  return true;
}
// </sched-logic>
```

- [ ] **Step 4: Run test to verify it passes**

Run: `node tests/sched.test.js`
Expected: PASS — `12 passed, 0 failed` (exit 0).

- [ ] **Step 5: Confirm the existing zone harness still passes**

Run: `node tests/zones.test.js`
Expected: PASS — unchanged (the new block does not touch `// <zone-logic>` blocks).

- [ ] **Step 6: Commit**

```bash
git add index.html tests/sched.test.js
git commit -m "feat(sched): pure route-strategy helpers + safe flexible default + test harness"
```

---

## Task 2: Make isRouteLogical, wouldBacktrack, and _candidatesZone strategy-aware

**Files:**
- Modify: `index.html` — `isRouteLogical` (line 4764), `wouldBacktrack` (line 4799), `_candidatesZone` (lines 4823–4849), `tests/sched.test.js`

This is a refactor of live engine code. Behavior for `far_to_near` must stay **byte-for-byte identical** (PureWater regression safety); `nearest_first` gains the mirror behavior; `flexible` disables geographic gating.

> **Line numbers below are pre-Task-1 approximations** — inserting the `// <sched-logic>` block in Task 1 shifts everything after it down by ~25 lines. The **quoted current-code strings are the authoritative anchors**; find by string, not by line number.

- [ ] **Step 1: Add regression + mirror assertions to the test**

Append to `tests/sched.test.js` before the final `console.log` line. These lock the truth table the refactor must satisfy:

```js
suite('strategy truth table (locks refactor intent)', () => {
  // far_to_near: a "before" task that is nearer (higher idx) than the new one is illegal
  check('FTN before-nearer illegal', ctx.isPairOrdered('far_to_near', /*earlier*/2, /*later=new*/1) === false);
  // far_to_near: an "after" task that is farther (lower idx) than the new one is illegal
  check('FTN after-farther illegal', ctx.isPairOrdered('far_to_near', /*earlier=new*/1, /*later*/0) === false);
  // nearest_first mirrors
  check('NF before-farther illegal', ctx.isPairOrdered('nearest_first', 0, 1) === false);
  check('NF after-nearer illegal', ctx.isPairOrdered('nearest_first', 1, 2) === false);
});
```

- [ ] **Step 2: Run test to verify the new assertions pass**

Run: `node tests/sched.test.js`
Expected: PASS — `16 passed, 0 failed`. (The helpers from Task 1 already satisfy these; this step pins the contract before refactoring callers.)

- [ ] **Step 3: Refactor `isRouteLogical` to delegate to `isPairOrdered`**

Replace the body of `isRouteLogical` (lines 4764–4781). Current:

```js
function isRouteLogical(tech,dateStr,newCity,catId){
  const optTime=calcOptimalTime(tech,dateStr,newCity,catId);
  if(!optTime)return false;
  const zid=getTechZoneId(tech,dateStr);
  const newIdx=getCityIndexInZone(newCity,zid,tech.base);
  if(newIdx===999)return true; // city not in zone index — can't validate, allow
  const newTimeMins=timeToMins(optTime);
  return getTechDayTasks(tech,dateStr).every(t=>{
    const tIdx=getCityIndexInZone(t.city,zid,tech.base);
    if(tIdx===999)return true;
    const tTime=timeToMins(t.time);
    // A task scheduled BEFORE us must not be closer (higher idx) — that would be near-then-far
    if(tTime<newTimeMins&&tIdx>newIdx)return false;
    // A task scheduled AFTER us must not be farther (lower idx) — that would be far-near-far zigzag
    if(tTime>newTimeMins&&tIdx<newIdx)return false;
    return true;
  });
}
```

New (strategy-aware, identical for far_to_near):

```js
function isRouteLogical(tech,dateStr,newCity,catId){
  const optTime=calcOptimalTime(tech,dateStr,newCity,catId);
  if(!optTime)return false;
  const strategy=resolveRouteStrategy(tenantConfig.scheduling);
  if(strategy==='flexible')return true; // no geographic constraint
  const zid=getTechZoneId(tech,dateStr);
  const newIdx=getCityIndexInZone(newCity,zid,tech.base);
  if(newIdx===999)return true; // city not in zone index — can't validate, allow
  const newTimeMins=timeToMins(optTime);
  return getTechDayTasks(tech,dateStr).every(t=>{
    const tIdx=getCityIndexInZone(t.city,zid,tech.base);
    if(tIdx===999)return true;
    const tTime=timeToMins(t.time);
    // task BEFORE new: pair (tIdx → newIdx) must be ordered for this strategy
    if(tTime<newTimeMins && !isPairOrdered(strategy,tIdx,newIdx))return false;
    // task AFTER new: pair (newIdx → tIdx) must be ordered for this strategy
    if(tTime>newTimeMins && !isPairOrdered(strategy,newIdx,tIdx))return false;
    return true;
  });
}
```

- [ ] **Step 4: Refactor `wouldBacktrack` to be strategy-aware**

Replace `wouldBacktrack` (lines 4799–4812). New version preserves the exact far_to_near predicate (`i < newIdx`) and mirrors it for nearest_first:

```js
function wouldBacktrack(tech,dateStr,newCity){
  const strategy=resolveRouteStrategy(tenantConfig.scheduling);
  if(strategy==='flexible')return false;
  const zid=getTechZoneId(tech,dateStr);if(!zid)return false;
  const dayTasks=getTechDayTasks(tech,dateStr).filter(t=>t.status!=='cancelled'&&t.time);
  if(dayTasks.length===0)return false;
  const newIdx=getCityIndexInZone(newCity,zid,tech.base);if(newIdx===999)return false;
  // far_to_near: an existing FARTHER task (lower idx) conflicts with inserting a nearer one.
  // nearest_first: an existing NEARER task (higher idx) conflicts.
  const conflicting=dayTasks.filter(t=>{
    const i=getCityIndexInZone(t.city,zid,tech.base);
    if(i===999)return false;
    return strategy==='far_to_near' ? i<newIdx : i>newIdx;
  });
  return conflicting.length>0;
}
```

- [ ] **Step 5: Update `_candidatesZone` — use resolver, enable nearest_first, gate slot-release**

In `_candidatesZone`, replace line 4823:

```js
  const routeStrategy=sc.route_strategy||(sc.route_logic!==false?'far_to_near':'flexible');
```
with:
```js
  const routeStrategy=resolveRouteStrategy(sc);
```

Replace line 4824:
```js
  const routeLogic=routeStrategy==='far_to_near';
```
with (now nearest_first also enforces ordering):
```js
  const routeLogic=routeStrategy!=='flexible';
```

Change the slot-release guard (line 4849) so the reservation logic — which is defined in far→near terms — only runs under far_to_near:
```js
      if(slRel?.enabled){
```
becomes:
```js
      if(slRel?.enabled && routeStrategy==='far_to_near'){
```

- [ ] **Step 6: Run both test suites**

Run: `node tests/sched.test.js && node tests/zones.test.js`
Expected: PASS — `16 passed, 0 failed` then the zones suite passing. (Engine functions that touch globals aren't unit-run here; the pure helpers they delegate to are fully covered.)

- [ ] **Step 7: Manual smoke in a browser (no automated DOM here)**

Open `index.html` locally (or the deployed copy after push). As PureWater (far_to_near), dispatch a task and confirm the route preview still orders far→near exactly as before. This confirms the refactor is behavior-preserving for the live tenant.

- [ ] **Step 8: Commit**

```bash
git add index.html tests/sched.test.js
git commit -m "refactor(sched): strategy-aware isRouteLogical/wouldBacktrack + real nearest_first + flexible default in _candidatesZone"
```

---

## Task 3: PureWater config audit + safe-default documentation

**Files:**
- Create: `outputs/` has none here — this task delivers SQL as a chat code block (no file) per the SQL-delivery rule, plus doc updates.
- Modify: `context/clients/purewater.md`

The engine default is now `flexible`. PureWater must keep `far_to_near` — verify it is set **explicitly** in `tenants.config` (not relying on the old fallback).

- [ ] **Step 1: Deliver the audit SQL to Eran (chat code block, do not run)**

Provide this read-only check for Eran to run in Supabase:

```sql
-- Confirm PureWater has route_strategy set EXPLICITLY (must return 'far_to_near')
SELECT id,
       config->'scheduling'->>'route_strategy' AS route_strategy,
       config->'scheduling'->>'route_logic'    AS route_logic
FROM tenants
WHERE id = '00000000-0000-0000-0000-000000000001';
```

If `route_strategy` is NULL, deliver this fix SQL (chat code block, Eran runs it):

```sql
UPDATE tenants
SET config = jsonb_set(config, '{scheduling,route_strategy}', '"far_to_near"')
WHERE id = '00000000-0000-0000-0000-000000000001'
  AND config->'scheduling'->>'route_strategy' IS NULL;
```

- [ ] **Step 2: Update `context/clients/purewater.md`**

In the "Runtime config" table, confirm the `scheduling.route_strategy = far_to_near` row notes "**set explicitly** — engine default is now `flexible`". Add a Change-log line dated 2026-06-10: "Engine default route_strategy flipped to flexible (far_to_near is PureWater-specific); confirmed PureWater sets far_to_near explicitly."

- [ ] **Step 3: Commit**

```bash
git add context/clients/purewater.md
git commit -m "docs(purewater): record explicit far_to_near + engine flexible default flip"
```

---

## Task 4: `tasks.locked` column + DB↔JS round-trip

**Files:**
- Create: `outputs/migration-tasks-locked_2026-06-10.sql`
- Modify: `index.html` — task load mapper (line 2469), `saveTaskToSupabase` (line 2873)

- [ ] **Step 1: Write the migration file**

Create `outputs/migration-tasks-locked_2026-06-10.sql`:

```sql
-- Manual override flag: a locked task is pinned by the coordinator and the
-- auto-sequencer (Plan B) must never move, reorder, or gap-fill it.
ALTER TABLE public.tasks
  ADD COLUMN IF NOT EXISTS locked BOOLEAN NOT NULL DEFAULT false;
```

- [ ] **Step 2: Deliver the migration SQL to Eran (chat code block)**

Paste the same SQL above as a chat code block for Eran to run in Supabase. Do not run it yourself.

- [ ] **Step 3: Read `locked` back when loading tasks**

In `index.html`, the task-load mapper currently has (line 2469):

```js
      windowStart: t.scheduled_window_start || '', windowEnd: t.scheduled_window_end || '',
```

Add `locked` to the mapped object on the same area — change that line to:

```js
      windowStart: t.scheduled_window_start || '', windowEnd: t.scheduled_window_end || '', locked: !!t.locked,
```

- [ ] **Step 4: Persist `locked` when saving a task**

In `saveTaskToSupabase` (line 2873), current:

```js
    scheduled_window_start: task.windowStart || null, scheduled_window_end: task.windowEnd || null,
```

Change to:

```js
    scheduled_window_start: task.windowStart || null, scheduled_window_end: task.windowEnd || null, locked: !!task.locked,
```

- [ ] **Step 5: Verify the round-trip manually**

After Eran runs the migration and you deploy: in the browser console, set `tasks[0].locked = true; saveTaskToSupabase(tasks[0])`, reload, confirm `tasks[0].locked === true`. (No automated DB test — the harness is pure-logic only.)

- [ ] **Step 6: Commit**

```bash
git add index.html outputs/migration-tasks-locked_2026-06-10.sql
git commit -m "feat(tasks): add locked flag with DB round-trip (manual-override seam)"
```

---

## Task 5: `splitLockedFlexible` pure helper (lock seam for Plan B)

**Files:**
- Modify: `index.html` — extend the `// <sched-logic>` block; `tests/sched.test.js`

- [ ] **Step 1: Write the failing test**

Append to `tests/sched.test.js` before the final `console.log`:

```js
suite('splitLockedFlexible', () => {
  const day = [
    {id:1, city:'a', locked:true},
    {id:2, city:'b'},
    {id:3, city:'c', locked:false},
    {id:4, city:'d', locked:true},
  ];
  const r = ctx.splitLockedFlexible(day);
  check('locked picks only truthy locked', r.locked.map(t=>t.id).join(',') === '1,4');
  check('flexible is the rest', r.flexible.map(t=>t.id).join(',') === '2,3');
  check('empty input → empty arrays', JSON.stringify(ctx.splitLockedFlexible([])) === '{"locked":[],"flexible":[]}');
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `node tests/sched.test.js`
Expected: FAIL — assertions in `splitLockedFlexible` fail (`ctx.splitLockedFlexible is not a function`).

- [ ] **Step 3: Add the helper to the `// <sched-logic>` block**

Inside the existing `// <sched-logic>` … `// </sched-logic>` block (before the closing marker), add:

```js
// Split a tech-day's tasks into locked (pinned, immovable) vs flexible (optimizer may sequence).
// The Plan B auto-sequencer passes `locked` as fixed constraints and only reorders `flexible`.
function splitLockedFlexible(dayTasks){
  const locked=[], flexible=[];
  for(const t of (dayTasks||[])){ (t && t.locked ? locked : flexible).push(t); }
  return {locked, flexible};
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `node tests/sched.test.js`
Expected: PASS — `19 passed, 0 failed`.

- [ ] **Step 5: Commit**

```bash
git add index.html tests/sched.test.js
git commit -m "feat(sched): splitLockedFlexible helper + tests (lock seam for auto-sequencer)"
```

---

## Task 6: Living-docs sync

**Files:**
- Modify: `context/scheduling-rules.md`

- [ ] **Step 1: Update `context/scheduling-rules.md`**

In the "Configurable Scheduling Engine" → "Route Strategies" subsection, update the table/notes to state:
- The engine default (absent config) is now **`flexible`**, resolved via `resolveRouteStrategy(sc)` — `far_to_near` is PureWater-specific, never the global fallback.
- `nearest_first` is now **fully implemented** (mirror of far_to_near via `isPairOrdered`), not a silent flexible.
- `isRouteLogical` / `wouldBacktrack` are **strategy-aware sanity guards**; `slot_release` reservation runs **only under `far_to_near`**.
- New `tasks.locked` flag: locked tasks are fixed constraints; `splitLockedFlexible(dayTasks)` separates them for the (forthcoming) auto-sequencer.

Add a dated line under the relevant changelog/section: "2026-06-10 — Slices 1–2: honest strategies + safe flexible default + locked seam."

- [ ] **Step 2: Commit**

```bash
git add context/scheduling-rules.md
git commit -m "docs(scheduling): honest strategies, flexible default, locked seam (Slices 1-2)"
```

---

## Verification (whole plan)

1. `node tests/sched.test.js` → `19 passed, 0 failed`.
2. `node tests/zones.test.js` → still passing (no regression).
3. Eran runs the audit SQL → returns `far_to_near`; runs `tasks.locked` migration → column exists.
4. Browser smoke as PureWater: far→near route preview unchanged (refactor is behavior-preserving).
5. Browser smoke as a `flexible`-or-unset tenant: dispatch no longer rejects slots on geographic grounds (no false "no result").
6. `locked` round-trips: set true, reload, still true.

---

## What Plan B will cover (not in this plan)

Slices 3–7: `route_cache` table + backend cache read/write/budget/fallback/trust, authoritative `sequenceDay` + `markDayDirty` + epoch/version guards + window/break constraints + overflow tray, weekly balance term, reactive gap-fill, and rollout behind `features.auto_sequence` with the dry-run shadow compare. Requires `backend/optimizer.py` + the post-quota-review Google budget number.
