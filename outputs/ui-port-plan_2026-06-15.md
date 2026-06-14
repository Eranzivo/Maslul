# UI Port Plan — Claude Design mockups → index.html (2026-06-15)

**Goal:** port the 8 approved Claude Design screens (`mockups/claude-design/flow/*.html`) into our live
`index.html` (single-file, vanilla, no build), on our `style.md` tokens, **without breaking engine logic
or existing screens**. Design intent: `mockups/DESIGN-LOG.md`. Engine review: `outputs/israel-feedback-triage_2026-06-14.md`.

## Hard constraints
- **Namespace everything.** The mockups use generic classes (`.btn .card .page .nav .pill .status-pill
  .kpi-card .detail`) that already exist in `index.html` — pasting raw WILL clobber live styles. Each
  ported screen gets a scoped prefix (proposed: **`md-`** for "Maslul design", e.g. `.md-rc`, `.md-wblock`,
  `.md-nav-item`). Reuse existing tokens/vars; add only new component classes.
- **Additive first, rip-out last.** Build new screens alongside the working ones; switch over only after the
  new path is verified. Keep the old function until the new one is confirmed (feature-flag or A/B route).
- **Every slice leaves the app working & every button wired** (UI-testing rule). No half-screen commits.
- **No deploy** — local edits only; do not `git push` without explicit ask.

## Integration map (design file → index.html target → engine wiring)

| # | Screen (file) | index.html target | Wiring / notes |
|---|---|---|---|
| 1 | Step 1 - Search | `openCallDrawer()` ~L2328 (new-call entry) | Just a cleaner search form; feeds the same city/cat/dates into `_candidatesZone`. |
| 2 | Step 2 - Recommendations | **replaces** `showCandidate()` ~L5575 | Cards = top-3 of `_candidatesZone()` ranked list (already returns `{tech,date,optTime,fillScore}`). Card shows date+window only; hide `candidate.tech`. "מצא מועד אחר" = next slice of `allCandidates`. "בדוק תאריך מסוים" = call engine with one date. |
| 3 | Step 3 - Reveal & Confirm | post-selection state + `confirmAssign()` ~L5656 | Reveal `candidate.tech` + day route (reuse the route-preview block already in `showCandidate`). Keep `window._currentSlots`/`selectedTimeSlot` wiring intact. After confirm → success toast → return home (#1.9). |
| 4 | Weekly Calendar / Dispatch Board | `renderPlannerWeekly()` | **Pick one layout** (day-columns vs tech-rows×days). Requirements: full-size (not inner scroll), sticky day headers + sticky tech/time labels, render at 1/2/3+ techs. Group by window (already how `renderPlannerDaily` groups). |
| 5 | Daily Route Grid | `renderPlannerDaily()` ~L7182 | Already ~90% there (window blocks, drive-time traces, pending tray, now-line). Restyle to the mockup; keep `_onGridDrop`/`windowAtOffset`/`layoutColumns`. |
| 6 | Nav & Detail Panel | sidebar + `openTaskDetail()` / `toggleTaskLock()` | Nav = polish existing `.sidebar`/`.ni-btn`. Detail = enhance existing `.mo-panel` content rows; lock button already wired to `toggleTaskLock`. |
| 7 | Home Dashboard | home render + `tech-home-card` | KPI strip (pending/assigned/completed/today) + tech grid → click tech → weekly slide-in. Data already in `tasks`/`technicians`. |

## Slice order (safety-first, value-aware)
1. **Foundations** — add namespaced `md-*` component CSS (buttons, cards, pills, status, window-block,
   slide-in) into the `<style>` block. Pure addition, no selector collisions. Unblocks every screen.
2. **Detail side-panel (6)** — contained enhancement of `.mo-panel`; high value, low blast radius.
3. **Daily route grid (5)** — restyle `renderPlannerDaily` (closest to done) → proves the calendar look.
4. **Weekly calendar (4)** — the bigger calendar rebuild + sticky/responsive; decision on layout needed.
5. **Coordinator flow (1→2→3)** — the NOW priority, but engine-wired, so do it on a solid foundation with
   the old `showCandidate` retained as fallback until verified.
6. **Home dashboard (7)** — KPI strip + tech-first grid + weekly slide-in.
7. **Nav polish (6)** — align sidebar to the mockup.

> Rationale: 1–4 are additive/contained and let us validate the look on real data before touching the
> engine-wired booking flow (5). If you'd rather see the coordinator flow first (it's the headline), we
> can promote it — flag for the build session.

## Known fixes to apply during the port
- RTL time-range: keep `direction:ltr` + `tnum` on every window label (mockups already do this).
- Calendar: **not** an inner scroll box — full-height, page-level scroll; `position:sticky` headers (both axes).
- Responsive: test 1/2/3/4/5 techs + daily; columns must not collapse or overflow.
- Tech identity colors: drive from `technician.color` (already in schema), fallback palette
  [#6366F1,#7C3AED,#0D9488,#D97706,#E11D48].

## Decisions to confirm (defaults chosen so work can proceed)
1. **Weekly layout:** day-columns (`Weekly Calendar.html`) vs tech-rows×days (`Dispatch Board.html`).
   *Default:* day-columns for the weekly overview (cleaner, scales with tech count); keep tech-rows idea for
   a future "by technician" toggle.
2. **Cards count:** 3 best-first (resolves #1.4-vs-#3). *Default:* 3.
3. **Namespace prefix:** *Default:* `md-`.

## QA per slice (UI-testing rule)
After each slice: open the affected screen, click **every** button/nav/card, confirm it navigates or
triggers; verify the engine path (assign → persists; calendar → reads `tasks`); check 1/2/3-tech and mobile
widths. No console errors. Only then commit that slice.
