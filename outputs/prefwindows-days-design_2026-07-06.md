# Preferred Time Windows → Day-Aware + Enforced Both Doors (2026-07-06)

**Requirement (Eran, intake-form screenshot):** "חלונות זמן מועדפים" must support a DAY
option, not just hours — "רק ראשון/שלישי 10:00–13:00" — and the optimizer must direct the
call to the right tech+day accordingly. Israel's handover §8 lists customer availability as
a HARD constraint. Today: live gives a cosmetic ⭐ highlight only; **batch ignores
`preferred_windows` entirely** (one-door knob — exactly the class the registry exists for).

## Data shape (no migration — jsonb extension, back-compat)
`tasks.preferred_windows` item: `{from:"10:00", to:"13:00", days:[0,2]}`.
`days` = weekday ints **Sun=0…Sat=6** (JS `getDay()` convention; Python side converts via
existing `_dow`). `days` absent/empty ⇒ window applies every day (all existing rows keep
meaning). No windows at all ⇒ task unconstrained (unchanged).

## Semantics (per handover §8: HARD)
- **Day gate (hard, both doors):** if the task has windows and none allows weekday d,
  (tech, d) is not a candidate. Live: date filtered out of candidate generation; batch:
  `place_task` skips the day; new unassigned reason `no_preferred_window_day`.
- **Time gate:** live: slots that don't overlap an allowed window for the chosen date are
  rendered disabled (dispatcher override = pick another date or edit windows; manual
  calendar drag stays possible per §15F). Batch: the new call's solver window becomes the
  chosen day's earliest tenant-hours-overlapping preferred window (`window_start/end` are
  already hard in solve_route_v2). v1 limitation: one window per task passed to the solver
  (earliest overlapping); multiple disjoint windows on the same day = pick earliest.
- **Knob:** `scheduling.preferred_windows_mode: "hard" (default) | "soft"` — soft restores
  today's highlight-only behavior for tenants that treat windows as wishes.
  Readers: JS `resolvePrefWindowsMode` ↔ Py `resolve_pref_windows_mode`.

## Parity seam (golden fixture `tests/fixtures/prefwindow-cases.json`)
Pure helpers, identical logic both sides:
- `prefWindowAllowsDay(windows, dow)` ↔ `pref_allows_day(windows, dow)`
- `prefWindowAllowsRange(windows, dow, fromMin, toMin)` ↔ `pref_allows_range(...)` —
  true when any allowed window OVERLAPS [fromMin, toMin) (slot semantics).
Cases: empty/absent ⇒ allow; hour-only ⇒ any day; days-limited in/out; multi-window union;
overlap boundaries (touching ≠ overlap); malformed times ⇒ fail-open allow.

## UI (intake form, `renderPrefWindows`)
Each window row gets 7 day-chips (א ב ג ד ה ו ש) toggling `w.days`; none selected shows
"כל יום". Draft persistence + task save already pass the objects through untouched.

## Out of scope (next slice, backlog ⭐): earliest/latest date, fixed_date, priority,
forbidden windows — same pattern (structured field + both-door gate + fixture).
