# Session startup — continue the Round-2 PORT (paste this to the new session)

Run `/prime`, then read `context/design-system.md` (change log = port state) and
`outputs/round2-port-map_2026-07-12.md`. Memory `fable-review-session-state.md` has the queue.

State: 8 port slices LIVE+verified through `7854a98` (tokens, Home, brand/dispatch,
calendar sweep, קריאות revival, weekly wk2 rows, tech cards, zones coverage+demand).
Suites 201 sched + 65 zones JS, 173 py. Deploy checklist per CLAUDE.md after every push.

## Do FIRST (Eran feedback, in order)
1. **Logo iter 3** — VIEW `landing/assets/brand/maslul-logo-hebrew-v2.png` (Read tool), then fix
   the sidebar SVG (index.html ~line 898): arrow starts from the MIDDLE of the ל, add a second
   zigzag in the opposite direction, flow/end exactly like the asset. Logo is centered; parked
   after this fix.
2. **Weekly calendar time axis** — Eran: wk2 chip rows ≠ what he asked. Wants the mockup's fuller
   treatment + a TIME AXIS on weekly for orientation, sized for ≤5 techs in parallel. Re-read his
   Google-Calendar-blocks message (in compact summary) + `_plannerWeekCell`/`renderPlannerWeekly`
   (~line 8360) before building. Hard rule: daily-grid geometry untouched; both views QA'd.
3. **דוחות page** — build per mockup 4164c874 + port map (period seg re-renders ALL sections,
   per-card export honoring filters, per-tenant card visibility = future knob).

## Then: קריאות polish (detail panel + workweek pager) → settings new-knob rows (knob rule:
registry row + BOTH readers + test, same commit) → overrun popup engine slice (spec in
outputs/worklog.md incl. UI-tail addendum) → landing build (assets in landing/assets/brand/,
accessibility plan in design-system open threads).

## Standing rules
One engine door for every action · never regenerate approved mockups · commit per slice +
design-system change-log row · parse-check inline JS + run both suites before commit ·
Eran QAs overall appearance at the END.
