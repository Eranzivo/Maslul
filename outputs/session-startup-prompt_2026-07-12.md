# Session startup — continue the Round-2 PORT (paste this to the new session)

Run `/prime`, then read `context/design-system.md` (change log = port state) and
`outputs/round2-port-map_2026-07-12.md`. Memory `fable-review-session-state.md` has the queue.

State: **11 port slices LIVE+verified through `2024771`** (tokens, Home, brand/dispatch,
calendar sweep, קריאות revival, weekly wk2 rows, tech cards, zones coverage+demand,
weekly TIME-AXIS w/ cascading lanes, דוחות rebuild + `reports.cards` knob, קריאות
detail-panel + workweek pager). Logo at **iter 4** (Eran's annotated asset — clear gap
below wordmark, stub at ל edge, two mid-line carets) — awaiting his visual OK.
Suites 208 sched + 65 zones JS, 173 py. Deploy checklist per CLAUDE.md after every push.

## Next (in order)
1. **Eran visual QA** — logo iter 4, weekly time-axis (both lenses, drag/drop, ≤5 techs),
   דוחות (period toggle re-renders all sections, per-card ⬇/⤢), קריאות panel+pager.
   Fix-forward per feedback before starting new slices.
2. **Settings new-knob rows** — per mockup 75c61312: insights.* + reports.cards rows in
   #page-settings (knob rule: registry row + BOTH readers + test, same commit;
   reports.cards reader already exists — needs only the settings row + save wiring).
3. **Overrun popup engine slice** — spec in outputs/worklog.md incl. UI-tail addendum
   (extend guardManualPlacement; מצא חלון אחר = re-run findBestSlot excluding slot).
4. **Landing build** — assets in landing/assets/brand/, accessibility plan in
   design-system open threads; WAIT for Eran's example mockup sites first.

## Deferred polish (log, don't lose)
- Weekly popover detail card (block click currently: rows→detail modal, header→daily view).
- Manual archive action for הושלמו (new status value); archive date filter.
- Reports duration-accuracy insight — needs E4 completion timestamps (interim footnote shipped).
- Monthly view QA after calendar changes (port QA rule: daily+weekly+monthly all render).

## Standing rules
One engine door for every action · never regenerate approved mockups · commit per slice +
design-system change-log row · parse-check inline JS + run both suites before commit ·
Eran QAs overall appearance at the END.
