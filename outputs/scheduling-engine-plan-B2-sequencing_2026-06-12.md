# Plan B2 — Authoritative Auto-Sequencing Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans. Steps use checkbox (`- [ ]`) syntax.

**Goal:** Make the OR-Tools optimizer the single source of truth for each tech-day's task order and times — re-sequencing automatically on every change, honoring locked tasks / customer windows / breaks as hard constraints, never silently dropping a job, and explaining each decision in Hebrew.

**Architecture:** One frontend seam (`markDayDirty` → debounced `sequenceDay`) called from every task mutation, gated by `features.auto_sequence` (default off — zero behavior change until enabled). The backend `/optimize` gains hard constraints (pinned/locked nodes, time windows, break blocks) and droppable-task disjunctions so an over-full day returns `dropped_tasks` instead of failing. Epoch + awaited persistence guards prevent stale/partial writes.

**Tech Stack:** vanilla JS (`index.html`, `// <sched-logic>` markers + `tests/sched.test.js`), FastAPI + OR-Tools (`backend/`, pytest — local Python 3.12 at `%LOCALAPPDATA%\Programs\Python\Python312\python.exe`).

**Source spec:** `outputs/scheduling-engine-design_2026-06-10.md` §0 (priority order), §4 (locks), §6 (data flow, epochs, feasibility), §7 (errors), + decision-trace recommendation from `outputs/product-review-fable_2026-06-12.md`.

**Verified anchors (2026-06-12):** `confirmAssign` (index.html:5403), cancel paths (index.html:5691, 5714), `editTaskFromDetail` (index.html:7009), `splitLockedFlexible` (in `<sched-logic>` block), `solve_route` (backend/optimizer.py:107+), `Task`/`Technician` models (backend/main.py:57–74), `getTechPartialBlocks` exists for breaks. Line numbers are pre-edit approximations — **match by quoted strings**.

---

## Critical correctness note for the implementer (read first)

`solve_route` currently computes arrival times by **manually accumulating** travel+service while walking the route. Once time windows exist, the solver may insert **waiting time** before a windowed/pinned stop — manual accumulation ignores waits and reports wrong times. Step one of the backend task is therefore: **read arrivals from the solver's Time dimension** (`solution.Value(time_dim.CumulVar(index))`), not by accumulation.

---

## File Structure

| File | Responsibility | Change |
|---|---|---|
| `backend/optimizer.py` | `solve_route`: window/pinned constraints, break pseudo-node, disjunctions (droppable), Time-dimension arrivals, per-stop trace data | Modify |
| `backend/main.py` | `Task` model: `window_start`, `window_end`, `locked`; `Technician`: `breaks`; quota accounting moved to actual Google fetches | Modify |
| `backend/tests/test_sequencing.py` | Constraint tests: pinned stays pinned, window honored, waiting handled, overflow dropped not failed | Create |
| `index.html` | `<sched-logic>`: `buildSequencePayload`, `applySequenceResult` (pure); app: `markDayDirty`/`sequenceDay` seam + epoch + call-site hooks + tray/badge/trace UI | Modify |
| `tests/sched.test.js` | Pure-helper tests: payload builder, epoch guard, result application | Modify |
| `context/scheduling-rules.md`, `context/architecture.md`, `context/clients/purewater.md` | living-docs | Modify |

---

## Task 1: Backend — constraint-aware `solve_route` (TDD)

**Files:** `backend/tests/test_sequencing.py` (create), `backend/optimizer.py` (modify)

- [ ] **Step 1: Write the failing tests**

```python
# backend/tests/test_sequencing.py
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from optimizer import solve_route_v2, time_to_min

# 3-node toy matrix: 0=depot, 1=A, 2=B (minutes)
M = [
    [0, 10, 20],
    [10, 0, 15],
    [20, 15, 0],
]

def base_tasks():
    return [
        {"duration": 30, "window_start": None, "window_end": None, "locked": False, "scheduled_time": None},
        {"duration": 30, "window_start": None, "window_end": None, "locked": False, "scheduled_time": None},
    ]

def test_unconstrained_orders_all_tasks():
    r = solve_route_v2(M, base_tasks(), "07:00", "18:00", breaks=[])
    assert sorted(r["ordered"]) == [0, 1]
    assert r["dropped"] == []
    assert len(r["arrivals"]) == 2

def test_locked_task_is_pinned_to_its_time():
    tasks = base_tasks()
    tasks[1]["locked"] = True
    tasks[1]["scheduled_time"] = "09:00"
    r = solve_route_v2(M, tasks, "07:00", "18:00", breaks=[])
    i = r["ordered"].index(1)
    assert r["arrivals"][i] == time_to_min("09:00")  # exactly pinned

def test_window_is_honored_with_waiting():
    tasks = base_tasks()
    tasks[0]["window_start"] = "10:00"   # can't start before 10 even though day starts 07:00
    tasks[0]["window_end"] = "13:00"
    r = solve_route_v2(M, tasks, "07:00", "18:00", breaks=[])
    i = r["ordered"].index(0)
    assert r["arrivals"][i] >= time_to_min("10:00")  # solver waited — Time dimension, not accumulation

def test_overfull_day_drops_flexible_not_fail():
    # 60-minute day, two 45-min jobs → only one fits; must drop, not return no-solution
    tasks = base_tasks()
    tasks[0]["duration"] = 45
    tasks[1]["duration"] = 45
    r = solve_route_v2(M, tasks, "07:00", "08:00", breaks=[])
    assert len(r["ordered"]) == 1
    assert len(r["dropped"]) == 1

def test_locked_is_never_dropped():
    tasks = base_tasks()
    tasks[0]["duration"] = 45
    tasks[1]["duration"] = 45
    tasks[1]["locked"] = True
    tasks[1]["scheduled_time"] = "07:10"
    r = solve_route_v2(M, tasks, "07:00", "08:00", breaks=[])
    assert 1 in r["ordered"]          # locked survived
    assert r["dropped"] == [0]        # flexible was dropped

def test_break_blocks_time():
    # 12:00-13:00 break: a task pinned at 11:50 with 30min duration is infeasible →
    # flexible task must be scheduled outside the break instead
    tasks = base_tasks()
    r = solve_route_v2(M, tasks, "07:00", "18:00", breaks=[{"from": "12:00", "to": "13:00"}])
    for i, arr in zip(r["ordered"], r["arrivals"]):
        dur = tasks[i]["duration"]
        assert not (arr < time_to_min("13:00") and arr + dur > time_to_min("12:00"))
```

- [ ] **Step 2: Run to verify failure**

Run (in `backend/`): `& "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe" -m pytest tests/test_sequencing.py -q`
Expected: FAIL — `ImportError: cannot import name 'solve_route_v2'`.

- [ ] **Step 3: Implement `solve_route_v2`** in `backend/optimizer.py` (new function after `solve_route`; the legacy function stays untouched for the old path):

```python
def solve_route_v2(matrix, tasks, start_time_str, end_time_str, breaks,
                   return_node: bool = False):
    """Constraint-aware single-vehicle solver.

    matrix: (n_tasks+1[+1]) square travel-minutes matrix, node 0 = start depot,
            nodes 1..n = tasks (same order as `tasks`), optional last node = end depot.
    tasks:  [{duration, window_start, window_end, locked, scheduled_time}]
    breaks: [{"from": "12:00", "to": "13:00"}] — modeled as zero-travel pinned pseudo-tasks.
    Returns {"ordered": [task_idx...], "arrivals": [abs-minute...], "dropped": [task_idx...],
             "legs": [drive-minutes-from-previous-stop ...]}.
    """
    n_tasks = len(tasks)
    start_min = time_to_min(start_time_str)
    end_min = time_to_min(end_time_str)
    if n_tasks == 0:
        return {"ordered": [], "arrivals": [], "dropped": [], "legs": []}

    # ── Append break pseudo-nodes: zero travel to/from everywhere, pinned window ──
    brk_specs = [{"from_min": time_to_min(b["from"]), "to_min": time_to_min(b["to"])} for b in (breaks or [])]
    base_n = len(matrix)
    n_nodes = base_n + len(brk_specs)
    full = [row[:] + [0] * len(brk_specs) for row in matrix]
    for _ in brk_specs:
        full.append([0] * n_nodes)

    end_depot = base_n - 1 if return_node else 0
    manager = pywrapcp.RoutingIndexManager(n_nodes, 1, [0], [end_depot]) if return_node \
        else pywrapcp.RoutingIndexManager(n_nodes, 1, 0)
    routing = pywrapcp.RoutingModel(manager)

    def node_duration(node):
        if 1 <= node <= n_tasks:
            return tasks[node - 1]["duration"]
        if node >= base_n:  # break pseudo-node
            spec = brk_specs[node - base_n]
            return spec["to_min"] - spec["from_min"]
        return 0

    def transit_cb(fi, ti):
        f, t = manager.IndexToNode(fi), manager.IndexToNode(ti)
        return node_duration(f) + full[f][t]

    cb = routing.RegisterTransitCallback(transit_cb)
    routing.SetArcCostEvaluatorOfAllVehicles(cb)
    horizon = end_min - start_min
    routing.AddDimension(cb, horizon, horizon, False, 'Time')  # slack = waiting allowed
    time_dim = routing.GetDimensionOrDie('Time')

    # Day bounds on start/end
    time_dim.CumulVar(routing.Start(0)).SetRange(0, horizon)
    time_dim.CumulVar(routing.End(0)).SetRange(0, horizon)

    # ── Per-task constraints (Time cumul is minutes-from-day-start) ──
    for i, t in enumerate(tasks):
        idx = manager.NodeToIndex(i + 1)
        lo, hi = 0, horizon
        if t.get("window_start"):
            lo = max(lo, time_to_min(t["window_start"]) - start_min)
        if t.get("window_end"):
            # must START early enough to finish inside the window
            hi = min(hi, time_to_min(t["window_end"]) - start_min - t["duration"])
        if t.get("locked") and t.get("scheduled_time"):
            pin = time_to_min(t["scheduled_time"]) - start_min
            lo = hi = pin
        if hi < lo:
            hi = lo  # impossible window → keep solvable; task will be dropped by disjunction
        time_dim.CumulVar(idx).SetRange(lo, hi)
        if not t.get("locked"):
            # Droppable: large penalty so dropping is the last resort, never an unsolvable model
            routing.AddDisjunction([idx], 100000)

    # Break pseudo-nodes: mandatory + pinned to their window
    for b_i, spec in enumerate(brk_specs):
        idx = manager.NodeToIndex(base_n + b_i)
        time_dim.CumulVar(idx).SetRange(spec["from_min"] - start_min, spec["from_min"] - start_min)

    params = pywrapcp.DefaultRoutingSearchParameters()
    params.first_solution_strategy = routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
    params.local_search_metaheuristic = routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
    params.time_limit.seconds = 5
    solution = routing.SolveWithParameters(params)
    if not solution:
        # With disjunctions this is rare (e.g. conflicting locked tasks) — surface as all-flexible-dropped
        locked_idx = [i for i, t in enumerate(tasks) if t.get("locked")]
        flex_idx = [i for i, t in enumerate(tasks) if not t.get("locked")]
        return {"ordered": locked_idx,
                "arrivals": [time_to_min(tasks[i]["scheduled_time"]) for i in locked_idx],
                "dropped": flex_idx, "legs": [0] * len(locked_idx), "conflict": True}

    ordered, arrivals, legs = [], [], []
    index = routing.Start(0)
    prev_node = manager.IndexToNode(index)
    while not routing.IsEnd(index):
        node = manager.IndexToNode(index)
        if 1 <= node <= n_tasks:
            ordered.append(node - 1)
            # Arrival from the Time dimension — includes solver-inserted waiting
            arrivals.append(start_min + solution.Value(time_dim.CumulVar(index)))
            legs.append(full[prev_node][node])
            prev_node = node
        index = solution.Value(routing.NextVar(index))

    visited = set(ordered)
    dropped = [i for i in range(n_tasks) if i not in visited]
    return {"ordered": ordered, "arrivals": arrivals, "dropped": dropped, "legs": legs}
```

- [ ] **Step 4: Run tests until green**

Run: same pytest command. Expected: 6 passed. Iterate on constraint details if OR-Tools semantics bite (the structure above is correct; off-by-one on service-time-vs-arrival is the usual suspect — arrival = cumul at node, service happens after).

- [ ] **Step 5: Commit**

```bash
git add backend/optimizer.py backend/tests/test_sequencing.py
git commit -m "feat(seq): constraint-aware solve_route_v2 — pinned/window/breaks/droppable (TDD 6/6)"
```

---

## Task 2: Backend — wire `/optimize` to v2 + trace + honest quota accounting

**Files:** `backend/main.py`, `backend/optimizer.py`

- [ ] **Step 1: Extend the models** in `main.py` (match by string):

```python
class Task(BaseModel):
    id: str
    city: str
    address: Optional[str] = None
    lat: Optional[float] = None
    lon: Optional[float] = None
    duration_minutes: int = 30
    scheduled_time: Optional[str] = None
    window_start: Optional[str] = None
    window_end: Optional[str] = None
    locked: bool = False

class Technician(BaseModel):
    id: str
    name: str
    base_city: str
    return_city: Optional[str] = None
    start_time: str = "07:00"
    end_time: str = "18:00"
    breaks: list = []          # [{"from":"12:00","to":"13:00"}]
    tasks: list[Task] = []
```

- [ ] **Step 2: Use v2 in `optimize_routes`** (`optimizer.py`): replace the `solve_route(...)` call block with:

```python
        v2_tasks = [{
            "duration": t.duration_minutes,
            "window_start": getattr(t, "window_start", None),
            "window_end": getattr(t, "window_end", None),
            "locked": getattr(t, "locked", False),
            "scheduled_time": t.scheduled_time,
        } for t in tech.tasks]
        r = solve_route_v2(matrix, v2_tasks, tech.start_time, tech.end_time,
                           breaks=getattr(tech, "breaks", []) or [],
                           return_node=bool(return_loc))
        ordered_idx, arrivals = r["ordered"], r["arrivals"]
```

and extend the result dict:

```python
        results.append({
            'technician_id': tech.id,
            'ordered_tasks': ordered_task_ids,
            'estimated_times': time_map,
            'dropped_tasks': [tech.tasks[i].id for i in r["dropped"]],
            'conflict': r.get("conflict", False),
            'trace': {tech.tasks[i].id: {
                          'prev': (tech.tasks[r["ordered"][k-1]].city if k > 0 else tech.base_city),
                          'drive_minutes': r["legs"][k]}
                      for k, i in enumerate(r["ordered"])},
            'total_drive_minutes': sum(r["legs"]),
            'mode': mode,
        })
```

- [ ] **Step 3: Honest quota accounting.** In `main.py` `/optimize`: stop pre-charging `_total_elements` when the cache path is active. Move the charge into `optimizer.build_matrix_cached` via a callback: simplest mechanical version — `main.py` keeps the pre-check ONLY as a hard ceiling (`use_gmaps`), and `build_matrix_cached` is changed to call Google only when `misses` is non-empty (already true), so warm days cost 0 real elements. Then change `/optimize` to charge `_gmaps_quota_ok(needed)` **only when** `os.getenv("SUPABASE_SERVICE_KEY")` is absent (legacy path); when the cache is active, charge after the fact is impossible cross-module without import cycles — so add `optimizer.LAST_GOOGLE_ELEMENTS` (module global set by `build_matrix_cached` to `len(locations)**2` when it fetched, else 0) and have `/optimize` add it to the counter after the call. Keep it simple; exactness not required — direction of error must be "counts only real fetches".

- [ ] **Step 4: Run ALL backend tests** — `pytest tests/ -q` → expected 42 passed (36 existing + 6 new).

- [ ] **Step 5: Commit**

```bash
git add backend/main.py backend/optimizer.py
git commit -m "feat(seq): /optimize v2 — windows/locks/breaks/dropped/trace + count only real Google fetches"
```

---

## Task 3: Frontend pure helpers — payload builder + result applier (TDD)

**Files:** `index.html` (`<sched-logic>` block), `tests/sched.test.js`

- [ ] **Step 1: Failing tests** (append before final `console.log`):

```js
suite('buildSequencePayload', () => {
  const tasks=[
    {id:1, city:'א', time:'09:00', windowStart:'08:00', windowEnd:'11:00', locked:true,  catId:null},
    {id:2, city:'ב', time:'',      windowStart:'',      windowEnd:'',      locked:false, catId:null},
  ];
  const p = ctx.buildSequencePayload(tasks, t=>30);
  check('locked carries scheduled_time', p[0].locked===true && p[0].scheduled_time==='09:00');
  check('windows map to snake_case', p[0].window_start==='08:00' && p[0].window_end==='11:00');
  check('empty window → null', p[1].window_start===null && p[1].window_end===null);
  check('duration from resolver', p[0].duration_minutes===30);
});

suite('applySequenceResult (epoch guard)', () => {
  const tasks=[{id:'1',time:'07:00'},{id:'2',time:'08:00'}];
  const res={ordered_tasks:['2','1'],estimated_times:{'1':'10:00','2':'07:30'},dropped_tasks:[]};
  const out = ctx.applySequenceResult(tasks,res, /*sentEpoch*/3, /*currentEpoch*/3);
  check('applies times when epoch matches', out.applied===true && tasks[0].time==='10:00' && tasks[1].time==='07:30');
  const out2 = ctx.applySequenceResult(tasks,{...res,estimated_times:{'1':'12:00','2':'12:30'}}, 3, /*newer*/4);
  check('stale epoch discarded', out2.applied===false && tasks[0].time==='10:00');
  const out3 = ctx.applySequenceResult(tasks,{...res,dropped_tasks:['2']}, 5, 5);
  check('dropped ids surfaced', out3.dropped.length===1 && out3.dropped[0]==='2');
});
```

- [ ] **Step 2: Run `node tests/sched.test.js`** → FAIL (functions missing).

- [ ] **Step 3: Implement inside the `// <sched-logic>` block** (before closing marker):

```js
// Build the /optimize task payload from in-memory tasks. durationOf(task) → minutes.
function buildSequencePayload(dayTasks, durationOf){
  return (dayTasks||[]).map(t=>({
    id:String(t.id), city:t.city, address:t.street||null,
    lat:t.lat||null, lon:t.lon||null,
    duration_minutes:durationOf(t),
    scheduled_time:t.time||null,
    window_start:t.windowStart||null, window_end:t.windowEnd||null,
    locked:!!t.locked,
  }));
}
// Apply an /optimize result to in-memory tasks IF the epoch still matches.
// Returns {applied, dropped} — caller persists + renders; never applies stale results.
function applySequenceResult(dayTasks, result, sentEpoch, currentEpoch){
  if(sentEpoch!==currentEpoch) return {applied:false, dropped:[]};
  const times=(result&&result.estimated_times)||{};
  for(const t of dayTasks){
    const nt=times[String(t.id)];
    if(nt && !t.locked) t.time=nt;
  }
  return {applied:true, dropped:(result&&result.dropped_tasks)||[]};
}
```

- [ ] **Step 4: Run** → expected `31 passed` (24 + 7 new). Also `node tests/zones.test.js` unchanged.

- [ ] **Step 5: Commit**

```bash
git add index.html tests/sched.test.js
git commit -m "feat(seq): buildSequencePayload + applySequenceResult pure helpers (TDD)"
```

---

## Task 4: Frontend seam — markDayDirty / sequenceDay + call sites + UI

**Files:** `index.html`

- [ ] **Step 1: Add the seam** (after the `<sched-logic>` block's `appUsesZones` wrapper):

```js
// ═══ AUTO-SEQUENCING SEAM (features.auto_sequence) ═══════════════════════════
// markDayDirty(techId,date) is the ONLY entry point other code calls.
// Debounced per tech-day; epoch guard discards stale optimizer replies.
const _seqEpochs={}, _seqTimers={};
function _autoSeqOn(){ return !!(tenantConfig.features&&tenantConfig.features.auto_sequence) && !!CONFIG.OPTIMIZER_URL; }
function markDayDirty(techId,date){
  if(!_autoSeqOn()||!techId||!date) return;
  const k=`${techId}|${date}`;
  _seqEpochs[k]=(_seqEpochs[k]||0)+1;
  clearTimeout(_seqTimers[k]);
  _seqTimers[k]=setTimeout(()=>sequenceDay(techId,date),1000);
}
async function sequenceDay(techId,date){
  const k=`${techId}|${date}`, sentEpoch=_seqEpochs[k];
  const tech=technicians.find(t=>String(t.id)===String(techId)); if(!tech) return;
  const dayTasks=tasks.filter(t=>String(t.techId)===String(techId)&&t.date===date&&t.status!=='cancelled');
  if(dayTasks.length<2) return;
  const durationOf=(t)=>{const c=categories.find(c=>c.id===t.catId);return (tech.durationOverrides||{})[t.catId]||(c&&c.time)||settings.regularTime||30;};
  const sched=getTechDaySchedule(tech,date);
  const brk=getTechPartialBlocks(tech,date).map(b=>({from:minsToTime(b.from),to:minsToTime(b.to)}));
  try{
    const res=await fetch(`${CONFIG.OPTIMIZER_URL}/optimize`,{method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({date,technicians:[{id:String(tech.id),name:tech.name,
        base_city:(tech.address&&tech.base)?`${tech.address}, ${tech.base}`:(tech.base||''),
        return_city:tech.return_city||tech.base||'',
        start_time:sched.start||'07:00',end_time:sched.end||'18:00',breaks:brk,
        tasks:buildSequencePayload(dayTasks,durationOf)}]})});
    if(!res.ok) throw new Error('optimizer '+res.status);
    const data=await res.json(); const r=(data.optimized||[])[0]; if(!r) return;
    const {applied,dropped}=applySequenceResult(dayTasks,r,sentEpoch,_seqEpochs[k]);
    if(!applied) return; // a newer edit superseded this reply
    // Persist sequentially, awaited — partial failure leaves the day dirty for retry
    for(const t of dayTasks){ await saveTaskToSupabase(t); }
    _seqTraces[k]=r.trace||{};
    if(dropped.length) _markDroppedToTray(dropped,techId,date);
    if(r.conflict) showToast('⚠️ שתי קריאות נעולות מתנגשות — יש לשחרר אחת','error');
    _clearSeqBadge(techId,date);
    if(typeof renderPlanner==='function') renderPlanner();
  }catch(e){
    console.warn('[seq] optimizer unreachable, day stays heuristic:',e);
    _setSeqBadge(techId,date); // "טעון אופטימיזציה" — re-tries on next mutation
  }
}
const _seqTraces={};
function _markDroppedToTray(ids,techId,date){
  let n=0;
  for(const id of ids){const t=tasks.find(x=>String(x.id)===String(id));
    if(t){t.status='pending';t.techId=null;t.date='';t.time='';saveTaskToSupabase(t);n++;}}
  if(n)showToast(`היום מלא — ${n} קריאות הוחזרו לממתינות לשיבוץ`,'error');
}
function _setSeqBadge(techId,date){const el=document.getElementById(`seq-badge-${techId}-${date}`);if(el)el.style.display='inline';}
function _clearSeqBadge(techId,date){const el=document.getElementById(`seq-badge-${techId}-${date}`);if(el)el.style.display='none';}
```

- [ ] **Step 2: Hook the mutation call sites.** After each of these (match by quoted strings), add `markDayDirty(<techId>,<date>)`:
  - `confirmAssign` (≈5403): after the task is saved with its new tech/date → `markDayDirty(c.tech.id, c.date.str);`
  - Both cancel paths (≈5691 and ≈5714): after `saveTaskToSupabase(t)` → `markDayDirty(t.techId, t.date);`
  - `editTaskFromDetail` (≈7009): after save, if tech/date/time changed → `markDayDirty(t.techId, t.date);` and, when the task *moved* days, also `markDayDirty(oldTechId, oldDate);`

- [ ] **Step 3: Trace + badge in the day view.** In the daily-planner tech-day header add `<span id="seq-badge-${techId}-${date}" style="display:none;..." class="badge">טעון אופטימיזציה</span>`; in the task block tooltip/detail, when `_seqTraces[k]` has the task id, render: `נסיעה ${trace.drive_minutes} דק׳ מ-${trace.prev}`.

- [ ] **Step 4: Manual smoke (PureWater unchanged).** With `features.auto_sequence` ABSENT: dispatch/cancel/edit behave exactly as today (seam no-ops). Run `node tests/sched.test.js && node tests/zones.test.js` — green.

- [ ] **Step 5: Commit**

```bash
git add index.html
git commit -m "feat(seq): markDayDirty/sequenceDay seam + call-site hooks + tray/badge/trace (behind features.auto_sequence)"
```

---

## Task 5: Living-docs + enablement SQL

- [ ] **Step 1:** `context/scheduling-rules.md` — new section "Authoritative Auto-Sequencing (`features.auto_sequence`)": the seam, epoch guard, locked-pinned semantics, windows/breaks as hard constraints, dropped→tray (never silent), trace, fallback badge. Mark spec §6 implemented.
- [ ] **Step 2:** `context/architecture.md` — add `window_start/window_end/locked/breaks` to the optimizer API description + the quota-accounting change.
- [ ] **Step 3:** `context/clients/purewater.md` — note auto_sequence is OFF for PureWater pending the B3 shadow-compare.
- [ ] **Step 4:** Deliver enablement SQL (chat code block, test tenant first):

```sql
UPDATE tenants SET config = jsonb_set(config, '{features,auto_sequence}', 'true')
WHERE id = '<TEST_TENANT_ID>';
```

- [ ] **Step 5: Commit**

```bash
git add context/
git commit -m "docs(seq): auto-sequencing seam + constraints + rollout state"
```

---

## Verification (whole plan)

1. Backend: `pytest tests/ -q` → 42 passed. Frontend: `node tests/sched.test.js` → 31, zones → 18.
2. `features.auto_sequence` absent ⇒ zero behavior change anywhere (seam never fires).
3. On a test tenant with it enabled: assign 3 tasks to one day → after ~1s the day reorders with real drive times; cancel one → day re-tightens; a task with `locked=true` keeps its exact time; an over-full day returns tasks to the tray with the Hebrew toast (never silently lost).
4. Optimizer down ⇒ badge "טעון אופטימיזציה", day stays heuristic, nothing breaks.

## Deferred to B3 (next plan)
Weekly cross-tech balance term, reactive gap-fill (cheapest insertion), dry-run **shadow compare** UI + PureWater enablement, optimistic `updated_at` version check on persist (two-coordinator race), trace persistence (column), lock/unlock UI (drag-to-pin).
