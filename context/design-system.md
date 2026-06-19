# Maslul — Living Design System & Design Playbook

> **Read this before ANY UI/design work** (restyle, move a block/page, new screen, redesign).
> It is the living entry point for design: the rules, the source-of-truth map, which
> skill/superpower to use, and a running change log. **Every design change appends a row to
> the Change Log at the bottom — including the skill/superpower used.** Keep it current.

Product north-star: an **AI dispatch cockpit** (not a calendar) — clean, friendly SaaS, operable
by a non-technical coordinator. Most relevant data per section, no repetition, everything flows,
**never break engine logic**. See [[ui-design-northstar]], [[ai-dispatcher-northstar]].

---

## Source-of-truth map (where design facts live)
| What | File |
|---|---|
| **Tokens** (Heebo, RTL, indigo `#6366F1`, surfaces, spacing) | `context/style.md` + the `:root` vars in `index.html` |
| **Namespaced component CSS** (the redesign foundation) | `md-*` classes in `index.html` `<style>` (`.md-btn .md-card .md-pill .md-status .md-seg .md-wblock .md-panel .md-kpi` …) |
| **Approved screens & directions** (8 Claude Design mockups) | `mockups/DESIGN-LOG.md` + `mockups/claude-design/flow/*.html` |
| **Port integration map** (mockup → index.html fn → engine wiring) | `outputs/ui-port-plan_2026-06-15.md` |
| **Reference inspirations** | Linear / Invo / Okd; shapes.co (warm gradient, confident type, soft cards). DESIGN-LOG "Reference inspirations". |

The app is a **single `index.html`** — all JS/CSS inline, vanilla JS, no build step. RTL Hebrew-first.

---

## Hard rules for any UI change (non-negotiable)
1. **Namespace new component CSS `md-*`.** The mockups use generic names (`.btn .card .nav .page
   .pill .status-pill .kpi`) that ALSO exist live — pasting raw clobbers existing styles.
2. **Never break existing handlers/IDs.** Restyle the chrome; keep every `onclick`, `id`, and the
   functions they call byte-for-byte. After editing, grep the handlers/IDs to confirm they survive.
3. **Daily-grid geometry is coupled.** `renderPlannerDaily` uses `PX=1` (px/min), `gridH=(endH-startH)*60*PX`,
   `labelW=42`; `_gridWindowAtY`/`windowAtOffset` assume 60px/hour. Do NOT change these in a restyle.
4. **RTL time ranges** use `direction:ltr` + `font-feature-settings:"tnum"` (`.md-num,.md-win`) so
   "07:00–10:00" reads start→end. Apply to every window/number label.
5. **Additive first.** Build the new path in front of the working one; switch only after verified.
6. **UI-testing rule** ([[ui-testing-rule]]): after the change, click EVERY button/link/card on the
   affected screen and confirm it navigates/triggers. Parse-check inline JS
   (`node -e` over `<script>` blocks). No console errors.
7. **Commit per slice** (one revertible commit per screen/change). UI is git-reversible; **live DB
   data is not** — schedule/config changes need SQL/re-run.
8. **Engine guardrail.** The engine is a generic *brain*; all per-tenant look/logic flows from
   `tenants.config`. A design change must not hardcode anything client-specific. [[product-philosophy]]

---

## Which skill / superpower to use (design work)
| Situation | Use |
|---|---|
| Small contained restyle (one block/row/card; move an existing element) | **Do it inline.** Apply the hard rules + UI-testing rule. One commit. |
| New screen, or a multi-screen redesign / big layout rethink | **brainstorming** → **writing-plans** → **subagent-driven-development** (fresh subagent per slice, spec-review then code-quality-review). This is how the 7-slice port was done. |
| Generating fresh visual mockups | **claude.ai/design** (the web tool — not the `/design-sync` skill, which needs a compiled component lib we don't have). Hand off HTML → port onto `md-*` + tokens. |
| Polished, accessible component build from a spec | **frontend-design** skill (if the change is substantial UI implementation). |
| Risky change touching engine-wired UI (dispatch cards, calendar, batch) | TDD on the engine side; flag-gate; dry-run preview before any live write. [[feedback_engine-work-process]] |

> Rule of thumb: **contained restyle = inline; new/large = brainstorm → plan → subagent slices.**

---

## QA gate per design slice
Open the screen → click every button/nav/card → verify engine path still fires (assign persists,
calendar reads `tasks`) → check 1/2/3+ techs + narrow widths → parse-check inline JS → commit.

---

## Design Change Log
> Append newest on top. Columns: date · what & where · skill/superpower · commit.

| Date | Change | Skill/superpower | Commit |
|---|---|---|---|
| 2026-06-16 | **Dispatch results auto-scroll** — `findBestSlot` scrolls `#dispatch-result` into view after מצא שיבוץ אופטימלי so the 3 recommendation cards aren't below the fold (QA: coordinator thought it failed, had to scroll). Auto-scroll = the "minimum direct-to-location" fix; true popup is a heavier separate slice. | Inline (contained fix) | `65e405a` |
| 2026-06-15 | **Phase-2 IA: moved חופשות → Technicians** — relocated the `openDayoffModal()` button from the home header to the Technicians page header (keeps the operational home lean). Button + handler + `mo-dayoff` modal unchanged. | Inline (contained move) | `f5a2444` |
| 2026-06-15 | **Settings "ימי עבודה" row** — 7 day toggles (א׳–ש׳) writing `config.defaults.work_days`, in `#page-settings` after שעות עבודה. Inline-styled (no new CSS class, per hard-rule #1). Wired in `renderSettings`/`saveSettings`. | brainstorming → TDD (engine helpers) + inline UI | `79dd2fb` |
| 2026-06-15 | **קריאות action-row declutter** — actions in header (+ הוסף קריאה primary; ייבא CSV/מרובה secondary), 7 filters moved to their own wrap bar with a divider. `tf-*` ids + handlers preserved. | Inline (contained restyle) | `40629f9` |
| 2026-06-15 | **Bulk-import → batch engine** UI: ⚡ שבץ אוטומטית → dry-run preview → commit (in `runBulkImport` result). Backend user-JWT auth. | Inline + TDD (backend `batch_auth` 8 tests) | `5acf4cd` |
| 2026-06-15 | **Slice 3** daily-grid visual polish (`renderPlannerDaily` blocks/rows; geometry untouched). | subagent-driven-development | `25214e3` |
| 2026-06-15 | **Side panel** — removed technician impersonation chips (relocate to Technicians page in Phase 2). | Inline | `c154f91` |
| 2026-06-15 | **Slice 7** sidebar polish (`.md-brand`, active edge bar, `.md-tenant-card`, `renderSidebarTenant`). | subagent-driven-development | `f7b7b78` |
| 2026-06-15 | **Slice 6** home dashboard (KPI top-border cards + tech cards). | subagent-driven-development | `bb8c7d4` |
| 2026-06-15 | **Slice 5** coordinator 3-card chooser (`showCandidateCards` additive in front of `showCandidate`). | subagent-driven-development | `16b51ba` |
| 2026-06-15 | **Slice 4** weekly board 3h window blocks (`_plannerWeekCell`). | Inline | `e785ec8` |
| 2026-06-15 | **Slice 2** detail side-panel restyle (`#mo-task-detail`; wiring preserved). | Inline | `db2a49d` |
| 2026-06-15 | **Slice 1** `md-*` foundation CSS (buttons/cards/pills/status/avatar/window-block/panel/KPI). | Inline | `dc897ce` |

---

## Open design threads (Phase 2 — IA / page organization)
From `mockups/DESIGN-LOG.md` "Phase 2": ~~move **חופשות → Technicians view**~~ ✅ done 2026-06-15; **compact top-nav**
reference; **re-order/distribute pages by area** (תפעול / CRM / הגדרות); re-surface technician-view
impersonation inside the Technicians page. To be designed as a proposal (brainstorming) before building.
