# Editable Calendar — Plan (Phase 3, Slice 1)

**Goal:** let the coordinator move and place calls on the planner — including the flagged
חרב (needs location) and overflow טבריה — directly, with no UI/UX mistakes.

## What already exists (don't rebuild)
- **Daily view** (`renderPlannerDaily`): absolute-positioned time grid, one tech at a time,
  calls grouped by 3-hour window into one block, **multiple calls stacked per window** ✅,
  with 🔒 lock marker, 🚗 drive-trace, 📝 notes, and an "ממתין לשיבוץ" tray below.
- **Weekly view** (`renderPlannerWeekly`): tech × day table of call chips.
- Persistence seam: `saveTaskToSupabase(t)` + `markDayDirty(techId,date)` (re-sequences when
  `auto_sequence` is on; harmless no-op otherwise).

## The gap
Nothing is movable. The coordinator can open a call but can't re-place it.

## Key constraint — mobile-first
HTML5 drag-and-drop does NOT fire on touch devices. So editing needs **two paths**:
- **Desktop:** drag a chip between cells (weekly) / between windows (daily).
- **Mobile + desktop fallback:** tap a call → "שבץ מחדש" → pick tech / day / window. Robust,
  no drag fragility. This is the *primary* path; drag is a desktop accelerator.

## Slices
1. **Weekly drag-to-reassign (desktop):** chips draggable; day/tech cells are drop targets;
   drop → keep the customer window, move tech/day, persist, mark both days dirty. Pure helper
   `reassignTask(task, techId, date)` (tested). *(this slice)*
2. **Tap-to-place (mobile + desktop):** task-detail modal gains tech/day/window editors +
   save → same `reassignTask` core. Covers placing חרב/טבריה. Works on touch.
3. **Daily within-window placement:** drag/tap a tray task into a 3-hour window band.
4. **Needs-attention surfacing:** flagged `needs_location` + overflow pending shown at top
   of the tray with one-tap actions.

## Verification
Slices 1–2 need browser QA (desktop drag + mobile tap) before deploy — drag interactions
can't be unit-tested; the `reassignTask` core is covered by `tests/sched.test.js`.
