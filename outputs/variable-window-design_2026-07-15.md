# Variable Window Length Per Task — Design (build-ready, HOLD build until after QA)

> **Status:** spec, 2026-07-15. Build deferred until Eran re-QAs the committed geo work.
> Israel's real cards show **1.5h / 3h / 4h** windows; today the service window is a fixed 3h
> (`config.defaults.arrival_window_hours`). Make the customer arrival-window length **per-task**,
> **back-compat** (absent ⇒ tenant default = today's exact behavior).

## Principle
The window is an **arrival commitment** (reserved insertion capacity), not a block on the tech.
A per-task length lets a customer get a tight 1.5h promise or a loose 4h one without changing the
tenant default. This is a per-TASK field (like `earliest_date`/`fixed_date`), **not a tenant knob**
→ no `knobs.md` row; it does need **JS↔Py parity** (both scheduling doors size the window).

## Data
- **`tasks.window_minutes`** INTEGER, nullable (additive migration). Absent/null ⇒ tenant default
  `arrival_window_hours*60`. Malformed/too-small ⇒ fail-open to default.
- Existing `scheduled_window_start`/`scheduled_window_end` continue to store the concrete window;
  `window_minutes` is the chosen LENGTH that sizes them.

## Parity helpers (one each, mirrored, golden fixture `tests/fixtures/window-cases.json`)
- JS `resolveWindowMinutes(task, config)` · Py `resolve_window_minutes(task, config)`:
  `task.window_minutes` if a positive int ≥ min-serviceable, else `arrival_window_hours*60`.
  min-serviceable = one job: `dur+buf` (else the window can't hold even one call).

## Live door — slot grid (the core rework, `showCandidate` ~index.html:7278–7302)
Today: integer-hour loop `for(h=sh; h<=eh-slotH; h++)`, `slotH=settings.window`. Rework to **minute-based**:
```js
const winMin = resolveWindowMinutes(task, tenantConfig);          // 90/180/240…
const step   = winMin % 60 === 0 ? 60 : 30;                       // 30-min starts only when needed
const dur = effectiveDuration(...), buf = 10;
const slotCapacity = Math.max(1, Math.floor((winMin-1)/(dur+buf))+1);
for(let m = sh*60; m <= eh*60 - winMin; m += step){
  const sStart = minToTime(m), sEnd = minToTime(m+winMin);        // minToTime handles :30
  // preferred/off-pref/full/excluded logic unchanged, computed from m / m+winMin
}
```
- **Back-compat:** integer window + `step=60` ⇒ **identical** slots to today (`h*60` starts, `slotH` hours).
- `minToTime(m)` must render `:30` (today `pad(h)+':00'` assumes whole hours) — small helper, tested.
- `prefWindowAllowsRange`, slot-capacity, exclusion, ⭐-preferred all read from `m`/`m+winMin` — no
  semantic change, just minute-sourced bounds.

## Batch door (`batch_schedule.py` ~557 window formula)
Today: `slot_num=(arr-start)//180; window_start=start+slot_num*180`. Replace the literal 180 with
`resolve_window_minutes(task, config)`; window sizing per-task. Existing overrun/pref-window gates
unchanged (they already work in minutes).

## Calendar display
Daily view is already **1px/min, 60px/hour** — a variable-length block is just `height = winMin px`
and the label shows the real span. `layoutColumns` already handles overlapping windows, so
1.5h/4h blocks lay out without change. Weekly chips show the stored window text.

## Intake UI
Window-length `<select>` in dispatch (near category) + add-task: options **1.5h / 2h / 3h / 4h**,
default = tenant window (shown as "ברירת מחדל"). Writes `window_minutes` on the task; empty ⇒ null
⇒ default. Draft-persisted like the other intake fields.

## Edge cases / guards
- `window_minutes < dur+buf` ⇒ ignore, use default (a window must hold ≥1 job). Surfaced in intake.
- Non-integer only where chosen (1.5h ⇒ `step=30`); everything else keeps hour-aligned starts.
- `eh*60 - winMin < sh*60` (window longer than the workday) ⇒ no slots ⇒ existing no-result path.

## Tests
- Golden `window-cases.json` in BOTH suites: default when absent; explicit 90/120/240; too-small→default; malformed→default.
- JS: `minToTime` half-hours; slot-grid back-compat (integer+step60 == today) + a 90-min grid case.
- Py: `resolve_window_minutes` + a batch e2e (a 90-min task lands a 90-min window; absent stays 180).
- Full suites + inline-JS parse before commit; deploy-verify.

## Rollout
Additive + back-compat ⇒ no flag needed (absent ⇒ today's behavior for every tenant). PureWater
starts using it the moment a coordinator picks a non-default length on a call.

## Build order when resumed
1. Migration + parity helpers + golden fixture (pure, tested).  2. `minToTime` + live slot-grid rework (back-compat proven).  3. Batch formula.  4. Calendar height.  5. Intake select.  6. Full suites + QA.
