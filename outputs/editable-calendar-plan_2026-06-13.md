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
3. **Daily within-window placement:** ✅ done — drag a scheduled row or tray/needs-attention
   call onto the daily grid; `windowAtOffset` (pure, tested) snaps it to the 3-hour band under
   the pointer, with a dashed snap indicator. `_onGridDrop` assigns tech/day/window, clears time,
   persists, marks dirty. Mobile keeps tap-to-place. *(needs browser QA)*
4. **Needs-attention surfacing:** ✅ done — `_needsAttentionStrip()` renders every `status='pending'`
   call at the top of both planner views, tappable + draggable.

## Verification
Slices 1–2 need browser QA (desktop drag + mobile tap) before deploy — drag interactions
can't be unit-tested; the `reassignTask` core is covered by `tests/sched.test.js`.

## QA log / open items (2026-06-13, deferred to later QA pass)
- **Weekly drag works** (verified live: dragged a call into Wednesday). ✅
- **Order-after-move:** a dragged call cleared its exact time and floated to the top of the cell
  (empty time sorts first). **Fixed** — weekly cells now sort by service window first, then time
  (`renderPlannerWeekly`), so a 13:00–16:00 call stays below the 10:00–13:00 group on drop.
- **Open for later QA:**
  - Verify `auto_sequence` actually re-sequences the receiving day on drop (assigns correct
    intra-window times/order) for PureWater — the optimizer round-trip, not just the display sort.
  - Drag across **technicians** (tech-row → tech-row) and across the week edges.
  - Daily within-grid drag QA (snap indicator + band landing).
  - **Weekly view shows one chip per call, not grouped-by-window** — this is by design (the
    window-grouped *block* layout is the daily view). Revisit if Israel wants weekly grouping too.
