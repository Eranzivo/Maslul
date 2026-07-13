# Session startup — continue the Round-2 PORT (paste this to the new session)

Run `/prime`, then read `context/design-system.md` (change log = port state) and
`outputs/round2-port-map_2026-07-12.md`. Memory `fable-review-session-state.md` has the queue.

State: **11 port slices LIVE+verified through `2024771`** (tokens, Home, brand/dispatch,
calendar sweep, קריאות revival, weekly wk2 rows, tech cards, zones coverage+demand,
weekly TIME-AXIS w/ cascading lanes, דוחות rebuild + `reports.cards` knob, קריאות
detail-panel + workweek pager). Logo at **iter 4** (Eran's annotated asset — clear gap
below wordmark, stub at ל edge, two mid-line carets) — awaiting his visual OK.
Suites 208 sched + 65 zones JS, 173 py. Deploy checklist per CLAUDE.md after every push.

## State update 2026-07-13 (all LIVE through `5365d31`)
Done since: slices 12–13 (weekly MULTI-select lens + zone-aware polygon buttons; settings
דוחות+תובנות section w/ `reports.cards` UI + `insights.window_days` knob) · logo iter 5
(Eran's final asset) · **overrun engine slice complete** (`auto_overrun_min` knob both doors,
live popup + slot exclusion + approved-tail; Eran's decision: auto ≤15 min books, beyond →
next window) · bundles editable + category-constrained (jsdom-verified) · **landing REBUILT**
(warm family, teaser-webp living hero, `leads` write-only table verified, accessibility page).
Suites: 241+65 JS · 195 py.

## Next (in order)
1. **Eran QA** — landing page (desktop+mobile), overrun popup flow (book a spilling slot),
   דוחות, weekly lens multi-select. Fix-forward per feedback.
2. **Lead NOTIFICATION** — leads are dashboard-read-only today; wire Supabase webhook→email
   (or daily check) so Eran hears about new leads. Candidates in design-system open threads.
3. **PureWater re-batch dry-run** (rebatch-dryrun skill) if Israel wants the calendar refreshed
   under the new overrun policy.

## Deferred polish (log, don't lose)
- Weekly popover detail card (block click currently: rows→detail modal, header→daily view).
- Weekly-view overrun tail (daily shipped); drag-path overrun popup (deliberate scope note in worklog).
- Manual archive action for הושלמו (new status value); archive date filter.
- Reports duration-accuracy insight — needs E4 completion timestamps (interim footnote shipped).
- Monthly view QA after calendar changes (port QA rule: daily+weekly+monthly all render).
- Landing: real video asset if teaser webp isn't enough; teaser webp compression (2.3MB); domain trigger.

## Standing rules
One engine door for every action · never regenerate approved mockups · commit per slice +
design-system change-log row · parse-check inline JS + run both suites before commit ·
Eran QAs overall appearance at the END.
