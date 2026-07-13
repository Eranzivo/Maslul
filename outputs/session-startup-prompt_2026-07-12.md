# Session startup — Maslul (paste to a new session)

Run `/prime`, then read `context/design-system.md` (change log = the running state) and
`outputs/round2-port-map_2026-07-12.md`. Memories `ui-redesign-port`, `fable-review-session-state`.

## Where things stand (2026-07-13, all LIVE + verified through `53eee38`)
The Round-2 warm redesign port is **done and live**, plus several engine/product slices on top.
Suites: **244 sched + 65 zones JS · 195 py** (all green). Deploy = GitHub Pages (app + /landing/),
backend = Railway. Verify every push by grepping the live page for a marker (per CLAUDE.md).

**Shipped this stretch (newest first):**
- Landing **hero fit** (controlled min-height ~2:1 so the teaser isn't hard-cropped) + **technicians
  cards restyle** (wider grid, warm card: avatar tile + load chip + meta band + labeled sections).
- **Overrun tolerance UNIFIED** — live popup now fires only when spill > `auto_overrun_min` (same
  tolerance the batch absorbs); small spills book silently on both doors. Shared fn + fixture.
- **Weekly-view overrun tail** (parity with daily).
- **ONE FRONT DOOR** — app with no session → `/landing/`; landing hosts the login modal
  (same-origin session → app opens signed-in); logout → landing; `?login=1` escape hatch.
  All cross-links RELATIVE; domain move = 2 code lines + platform config (design-system open threads).
- **Landing rebuilt** (warm, low-noise, teaser-webp hero, accessibility.html) + **leads** write-only
  table + **leads inbox** on מנהל מאסטר (super_admin-only RLS, 🌱 card + nav badge).
- **Overrun engine** (`auto_overrun_min` knob, both doors, popup + slot-exclusion + approved tail).
- Bundles editable + category-constrained (jsdom-verified). Slices 12–13 (weekly multi-lens,
  zone-aware polygon buttons, settings דוחות+תובנות rows w/ `reports.cards` + `insights.window_days`).
- Logo at **iter 5** (Eran's final asset).

## Open with Eran
- **QA in progress** — checklist at `outputs/qa-checklist_2026-07-13.md` (front door, overrun,
  weekly, דוחות, bundles are the high-value path). Fix-forward on his findings.
- Re-batch of Israel's 108 tasks was run offline (95/109 place cleanly under today's rules;
  14 flagged = tiny settlements not in any zone + junk חרב). Eran: **old schedule, dropped** —
  don't re-run unless he asks.

## Next / deferred (log, don't lose)
- **PureWater re-batch dry-run** (rebatch-dryrun skill) only if Israel wants the live calendar
  refreshed — backup → dry-run → diff → explicit approval before any write.
- Weekly block → popover detail card (currently: rows→modal, header→daily).
- Manual archive action for הושלמו (new status value) + archive date filter.
- Reports duration-accuracy insight — needs E4 completion timestamps (interim footnote shipped).
- Monthly view QA after calendar changes (both views must render).
- Landing: teaser-webp compression (2.3MB — no local image tooling this session); real video; domain trigger.
- Lead email/push notification (in-app badge exists; email deferred to the domain move).

## Standing rules
One engine door for every action · never regenerate approved mockups · a per-tenant rule =
knobs.md row + BOTH readers + test (or a golden fixture when runtimes can't share code), same
commit · commit per slice + design-system change-log row · parse-check inline JS + run both
suites before commit · verify deploys by observing the live page · answer Eran in English.
