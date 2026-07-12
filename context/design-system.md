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
| **CRM / client-card pattern** (Eran reference 2026-07-11 — "build like this if we'll ever need") | Warm cream page; header = page title + count ("147 לקוחות פעילים") + global search; toolbar = segmented filter tabs (הכל / VIP / חדשות) + local search + primary "+ לקוח חדש". Card anatomy: big rounded initial-avatar (right), name + tier tag pill top-inline (VIP filled / רגילה outline / חדשה sun), phone + email rows with trailing icons (LTR numbers), dashed divider, footer stats row (⭐ N ביקורים · ביקור אחרון: X). Keep OUR warm tokens (teal primary; the reference's orange maps to our sun-amber for tier/avatar accents). Future WhatsApp integration hangs off these cards (message action per client) — design for a toggleable action slot. |

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
| 2026-07-12 | **Calendar iter 2 — weekly combined view added** (Eran: daily is great; weekly must show 1→all techs in one calendar, per-tech color/tag, clean overlay). Interactive tech-picker chips (כל הצוות/אלירן/בני/מיכאל; click-to-filter works in the mockup), 6 day columns, compact time·city·tag rows sorted by hour, live per-day counts; 58 demo calls following the real zone rotation. Script parse-checked + picker exercised in node. Open threads added: 10–20-tech grid concept + "both views render properly everywhere" port-QA rule. Artifact: e7c04323 iter 2 | artifact-design (live mockup, no app change) | — |
| 2026-07-11 | **Round 2, screen 3 — daily יומן in the warm language** + form fidelity pass. Dispatch form board rebuilt 1:1 vs live `index.html` intake (category chips incl. 📦 package builder w/ order rows + total time — duration derives from category, NOT a manual field; client/phone; city+⊕/street; floor/apt; entry code; notes; pref-window chips; date constraints לא לפני/לא אחרי/קבוע; 🔁 recurring) after Eran: "make sure the relevant details are there, not a general idea". New calendar artifact: 3 tech columns on an hour axis showing far-to-near visibly (אלירן דימונה→שדרות), per-tech color accents matching Home avatars, drive-time gaps between blocks, health chip per column header, crossing-call tail on מיכאל/רעננה. Heebo embedded as data-URI in ALL mockups (Eran disliked Segoe fallback; CSP blocks font CDNs). Artifacts: dispatch 2bcb6ab4 (iter 4) · calendar e7c04323 · sources in scratchpad. | artifact-design (live mockup, no app change) | — |
| 2026-07-11 | **Round 2, screen 2 — שיבוץ קריאה in the warm language** (Home ג approved: "looking better lets continue"). Board 1 = post-search recommendations: call summary bar w/ quick-edit, best card w/ crown + Hebrew "why" headline + explain chips (maps to `explainCandidate`/`showCandidateCards`), 2 alternates, day-preview with the new call highlighted in-route + drive times (maps to `showCandidate` routeHtml). Board 2 = **window-overrun popup design** (the next engine slice): facts table (window/arrival/finish overrun) + 3 actions שבץ בכל זאת / מצא חלון אחר / ביטול. Artifact: claude.ai/code/artifact/2bcb6ab4 · source: scratchpad maslul-dispatch-round2.html. **Iter 2 (Eran: day-preview approved; wants crossing calls clean + better intake form):** added board 0 = intake form restyle (same fields, one card, availability day-chips, collapsible optional section) and board 3 = **approved-overrun calendar treatment** — ONE block, striped tail past a dashed window-end line + tag "גולש 20 דק׳ · אושר ע״י המתאם", next call unmoved; display-only, tenant-agnostic (spec addendum in outputs/worklog.md). | artifact-design (live mockup, no app change) | — |
| 2026-07-11 | **Redesign Round 2 — Home direction ג (חם וידידותי) chosen & refined.** Eran picked ג from Round 1 ("the long brick with בוקר טוב ישראל + assign CTA is great"), asked for better internal bricks + page flow. Round 2 keeps the hero (adds summary line, day chips, secondary ליומן action) and upgrades: team rows → tech bricks (load bar, next stop+window, live Route-Health chip, mini day-strip), KPI cards get "so-what" delta lines, pending queue sorted oldest-first with age badges + per-row שבץ, warm תובנת-מסלול insight card. Palette locked: cream `#FBF8F3` / teal `#0E7A6E` / sun `#E9A23B`. Artifact: claude.ai/code/artifact/46a022c1 · source: scratchpad maslul-home-round2.html. **Iter 2 (same day, Eran feedback):** removed ליומן secondary button + the mini day-strips ("colored bricks make it messy") — tech brick is now 2 clean lines; current live status (בדרך ל…/בהתקנה ב…) kept and emphasized in teal per his explicit ask. | artifact-design (live mockup, no app change) | — |
| 2026-07-09 | **Redesign Round 1 — three live Home directions** published as an Artifact for Eran to react to (א שקט-ומדויק/Linear · ב קוקפיט/timing.tech · ג חם-וידידותי/shapes.co; same real PureWater data in all three). Chosen direction will seed the token/component pass, then screen-by-screen port. Artifact: claude.ai/code/artifact/37c69681 · source: scratchpad maslul-home-directions.html | artifact-design (live mockup, no app change) | — |
| 2026-07-05 | **Zone-draw modal rebuilt as WYSIWYG multi-polygon editor** (Eran feedback: "Edited" flow unfriendly, must be adjustable + capture every city). Saved rings load INTO the Leaflet.draw edit group (vertex-editable + deletable); drawing ADDS rings (no more clear-on-create); ALL brain places render as small grey dots (zone cities indigo) and turn GREEN live when captured; status recounts on every draw/edit/delete; confirm saves exactly what's on the map (append/replace prompts removed); empty map ⇒ offered polygon removal; sub-city ring with no city-centers allowed with confirm. Detection scans `GEO_BRAIN` (500+) not the static 255. | Inline (contained rebuild of one modal flow; UI-testing pass = Eran browser QA) | (geo-one-source) |
| 2026-06-16 | **Phase-2 IA: re-surfaced technician impersonation** — added `#role-chips` ("צפייה כטכנאי") to the Technicians page (`buildRoleSelect()` already fired on nav) + a "↩ חזרה לתצוגת מנהל" exit in `renderTechView` (manager-only) so the impersonate→return round-trip works after the sidebar chips were removed. Clears the QA `role-chips` finding; `.role-chip*` CSS live again. Verified it was a parked feature, not dead code, before acting. | Inline (verify-first) | `724907e` |
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
- **Weekly view = per-tech week with CASCADING WINDOWS (Eran 2026-07-12, supersedes the compact overlay same day):** Eran showed PureWater's current Google-Calendar weekly — overlapping 3h windows hiding each other = the failure mode to beat. Rule: staggered windows render חופפים side-by-side in lanes (greedy interval-coloring; a block NEVER covers a block), full window height on the hour axis, click → detail card with עריכה + פתח ביומי. Tech picker single-select (אלירן/בני/מיכאל) + "כל הצוות" mode (same lane algorithm, per-tech colors; gets thin at 13 windows/day → per-tech is the primary lens). Daily view keeps travel-time gaps (also feeds the find-booking day preview). Mockup: calendar artifact e7c04323 iter 3, lane algorithm no-overlap-verified in node. **Port QA rule: every screen with daily/weekly views must render BOTH properly after any calendar change.**
- **10–20 technician calendars need a different grid** (Eran): overlay works for ~3; at 10+ think row-per-tech timeline / zone-grouped lanes / paginated picker. Design when a bigger client approaches.
From `mockups/DESIGN-LOG.md` "Phase 2": ~~move **חופשות → Technicians view**~~ ✅ done 2026-06-15; **compact top-nav**
reference; **re-order/distribute pages by area** (תפעול / CRM / הגדרות); ~~re-surface technician-view
impersonation inside the Technicians page~~ ✅ done 2026-06-16. The remaining items (compact top-nav,
page re-order) to be designed as a proposal (brainstorming) before building.

---
> 🧠 [[maslul-brain.canvas|Brain map]] · Related: [[business]] · [[architecture]]
