# Round 2 → index.html Port Map — every button's backing, verified

> Eran (2026-07-12): "go through everything and make sure all fields communicate properly —
> no broken links, routes, flows." Method: every interactive element in the 8 approved
> mockups mapped to the live function/endpoint/knob behind it. **All EXISTS entries were
> grep-verified in index.html / backend on 2026-07-12** (29/29 functions present).
> Status: ✅ EXISTS (wire the new chrome to it) · 🟡 PARTIAL (exists, needs extension) ·
> 🆕 NEW (build in the port; engine door named).

## 1 · Home (artifact 46a022c1)
| Element | Backing | Status |
|---|---|---|
| Hero greeting + day summary numbers | derived from `tasks` queries already loaded for home KPIs | ✅ |
| + שיבוץ קריאה CTA | nav → dispatch page (`showPage('dispatch')` pattern) | ✅ |
| KPI cards (today/waiting/done/techs-out) | existing home dashboard counts (Slice 6 port `bb8c7d4`) | ✅ |
| KPI "so-what" delta lines (וותיקה 9 ימים, ‎+3 מאתמול) | 🆕 small compute over same data (JS-only, display) | 🆕 |
| Tech brick: load bar + next stop + window | `getTechDaySchedule`, tasks-per-tech query (tech cards exist on home) | ✅ |
| Tech brick: live status line (בדרך ל…) | **planned-route version only** — derived from current time vs scheduled stops; REAL events = E4 (post-pilot) | 🟡 |
| Tech brick: route-health chip | `healthChipHtml` + `_ensureDayHealth` (route_audits read) | ✅ |
| ממתינות rows + שבץ button | pending queue (dispatch data) + `queueAssign(id)` | ✅ |
| תובנת מסלול brick | 🆕 insights feed item (P2 recommendations / coverage calc) | 🆕 |

## 2 · שיבוץ קריאה (artifact 2bcb6ab4)
| Element | Backing | Status |
|---|---|---|
| Category chips + 📦 package builder (order rows, total time) | `cat-chips-container` + `pkg-section`/`total-time` — live form | ✅ |
| Client/phone/city+⊕/street/floor/apt/entry/notes | live fields `c-name…s-entrance` + `openAddCityModal` (B1 flow) | ✅ |
| חלונות זמן מועדפים chips | `addPrefWindow` + `pref-windows-list` | ✅ |
| אילוצי תאריך (3 dates) | `s-earliest/latest/fixed` → `dateCons` | ✅ |
| 🔁 קריאה חוזרת | `toggleRecurringMode` + recurring-config | ✅ |
| מצא שיבוץ אופטימלי | `findBestSlot` | ✅ |
| שמור ללא שיבוץ | `savePendingFromDispatch` | ✅ |
| Best card + "why" headline + chips | `showCandidateCards` + `explainCandidate`/`candidateSignals` | ✅ |
| 2 alternates בחר | same candidate flow (cards 2–3) | ✅ |
| Call-summary bar ✎ עריכת פרטים | form is on the same page — scroll/expand back (no new flow) | ✅ |
| Day preview w/ new call highlighted + drive times | `showCandidate` routeHtml (A11); drive-time labels between stops | 🟡 (labels new, data already in optTime calc) |
| Overrun popup (3 actions) | 🆕 NEXT ENGINE SLICE — spec in outputs/worklog.md (extend `guardManualPlacement` pattern; מצא חלון אחר = re-run `findBestSlot` excluding slot) | 🆕 |
| Crossing-call striped tail in calendar | 🆕 display-only render rule in `renderPlannerDaily` block builder (spec in worklog UI addendum) | 🆕 |

## 3 · יומן (artifact e7c04323)
| Element | Backing | Status |
|---|---|---|
| Daily: 3 tech columns, blocks by time, geometry | `renderPlannerDaily` (PX=1, 60px/hr — DO NOT change in restyle) | ✅ |
| Daily: drive-time gaps between blocks | 🆕 display row from leg data (route_audits/solver legs or optTime chain) | 🆕 |
| Daily: health chip per column + panel | `healthChipHtml` / `openHealthPanel` / `_ensureDayHealth` | ✅ |
| Weekly: per-tech cascading windows (lane algorithm) | 🟡 `_plannerWeekCell` exists; lane-cascade layout replaces its block layout (JS-only) | 🟡 |
| Weekly: tech picker chips (single + כל הצוות) | 🆕 UI state over same tasks query | 🆕 |
| Weekly: window click → detail card | task-detail modal exists (`mo-task-detail`); popover = new chrome, same data | 🟡 |
| Popover actions: פתח ביומי / שבץ מחדש / עריכה / בטל | day nav ✅ · `queueAssign` ✅ · task edit ✅ · cancel/status flow ✅ — ONE ENGINE DOOR rule | ✅ |
| Multi-call window count badge → breakdown list | 🆕 chrome; per-call times already computed (scheduled_time + effectiveDuration) | 🆕 |
| יומי/שבועי/חודשי seg + date nav | existing planner view switch | ✅ |

## 4 · קריאות (artifact 3a950879)
| Element | Backing | Status |
|---|---|---|
| **Separate tab returns** | `page-tasks`/`renderTasks` DORMANT since 07-08 retirement — re-enable nav + restyle (code kept) | 🟡 |
| KPI strip (4 numbers) | 🆕 counts over tasks by status/date (JS-only) | 🆕 |
| Status-grouped list, waiting first | `renderTasks` rewrite per new grouping (data exists) | 🟡 |
| Workweek pager א׳–ה׳ | `isTenantWorkDay`/`work_days` knob drives week shape; pager = new chrome | 🆕 |
| ממתינות timeless (never scoped by week) | grouping rule in render (waiting has no date — natural) | 🆕 rule |
| Row click → detail panel (fresh/toggle/switch) | task-detail data exists (`describeConstraintsHe`, assignment info); panel chrome new | 🟡 |
| Status-aware CTAs: שבץ עכשיו / פתח ביומן / שבץ מחדש / לארכיון / שחזר | `queueAssign` ✅ · planner nav ✅ · archive = `isPendingArchived` display logic (manual archive action 🆕 status value) | 🟡 |
| ייבוא CSV | `runBulkImport` (commented buttons — uncomment) | ✅ |

## 5 · טכנאים (artifact 41d2b7eb)
| Element | Backing | Status |
|---|---|---|
| Tech card fields (name/phone/base/hours) | technicians table + `saveTech`/`techCompleteness` (בסיס only shown; `return_city` stays engine-mandatory — auto-set = base at creation until UI resurfaces) | ✅ |
| חשבון משתמש row | technician↔user linkage (auth-users.md) | ✅ |
| Zone-rotation week strip | `rotation {dow: zone_id}` knob (read via `getTechZoneId`) | ✅ |
| Weekly stats (calls/health avg/utilization) | 🆕 aggregates: tasks count ✅ trivial · health avg over route_audits ✅ data exists · utilization = booked/capacity 🆕 compute | 🟡 |
| היומן שלו | planner nav filtered to tech | ✅ |
| 👁 צפה כטכנאי | `buildRoleSelect` impersonation + `renderTechView` exit | ✅ |
| ✎ עריכה / + הוסף טכנאי | `editTech`/`openAddTechModal`/`saveTech` | ✅ |
| ניהול חופשות + rows | `openDayoffModal` + day_offs table | ✅ |
| Dayoff impact line (זone uncovered, N calls) | 🆕 compute: rotation × day_offs × assigned tasks | 🆕 |

## 6 · אזורים (artifact c28050a9)
| Element | Backing | Status |
|---|---|---|
| Zones table (name/color/cities) | zones table + zone editor data | ✅ |
| Coverage-day chips per zone | derived from all techs' `rotation` | ✅ (invert existing data) |
| Demand column (calls/month) | 🆕 count tasks by zone by period (zone-demand-coverage habit — was manual SQL, becomes a query) | 🆕 |
| Status pill (מאוזן / חסר יום כיסוי) | 🆕 demand vs coverage-days threshold rule | 🆕 |
| Rotation matrix | same rotation data, matrix render | 🆕 chrome |
| 🗺 מפת אזורים | existing WYSIWYG polygon editor (zone-draw modal) | ✅ |
| + הוסף אזור | existing zone create flow | ✅ |
| Suggestions (max 2 + עוד הצעות toggle) | 🆕 insights: coverage calc + live-week overflow counter (batch results already report next-week placements) | 🆕 |
| Timeframe chip (3/6 חודשים) | 🆕 param of the demand query | 🆕 |

## 7 · דוחות (artifact 4164c874)
| Element | Backing | Status |
|---|---|---|
| Period seg + compare stamp | 🆕 page (current דוחות page is minimal) — all queries over tasks/route_audits | 🆕 |
| 4 KPIs | counts + avg wait (created→scheduled delta) + utilization + health avg | 🆕 compute, data exists |
| Weekly bars / zone demand hbars | same queries, CSS bars (no chart lib needed) | 🆕 |
| ⬇ ייצוא per active filters | 🆕 CSV export of the filtered query (client-side blob) | 🆕 |
| Insights feed (3 types) | coverage 🆕 · live-week 🆕 · duration-accuracy 🆕 (actual times need completion timestamps — TODAY only status flips exist; full accuracy arrives with E4 events; interim = scheduled vs configured spread) | 🆕/🟡 |
| Team month table | tasks per tech + route_audits avg | 🆕 compute |
| Per-tenant card visibility | 🆕 knob `reports.cards` (registry row when built) | 🆕 knob |

## 8 · הגדרות (artifact 75c61312) — every row ↔ registry knob
| Mockup row | Knob | Both doors today? |
|---|---|---|
| ימי עבודה | `defaults.work_days` | ✅ |
| שעות פעילות | `defaults.work_start/end` | ✅ |
| אורך חלון ללקוח | `defaults.arrival_window_hours` | ✅ |
| מקס׳ קריאות ליום | `defaults.max_daily_jobs` | ✅ |
| הפסקת צהריים | `defaults.break {enabled,start,end}` | ✅ |
| אופק חיפוש | `defaults.lookahead_days` | ✅ (JS; batch n/a by design) |
| אסטרטגיית מסלול 🔒 | `scheduling.route_strategy` | ✅ |
| חלון מבטיח הגעה 🔒 | `scheduling.window_semantics` | ✅ |
| שמירת בוקר לרחוקות | `scheduling.slot_release` | ✅ (JS; batch n/a by design) |
| חסימת שיבוץ ידני | `scheduling.route_strict` | ✅ |
| פילוסופיית שיבוץ 🔒 | `scheduling.placement_policy` | ✅ |
| זמינות לקוח קשיח | `scheduling.preferred_windows_mode` | ✅ |
| הצעות מילוי בביטול | `scheduling.gap_fill` | ✅ |
| ציוני מסלול | `audit.enabled` | ✅ |
| שיטת שיוך 🔒 | `scheduling.mode` | ✅ (⚠ open/radius batch unsupported — registry caveat) |
| גבולות אזור 🔒 | `scheduling.zone_match` | ✅ |
| חסימת חציית אזורים | `scheduling.zone_strict` | ✅ |
| אזהרת גרירה חוצת־אזור | `scheduling.zone_drop_guard` | ✅ |
| סוגים+משכים / ברירת מחדל | categories + `defaults.regular_job_minutes` (`effectiveDuration` chain) | ✅ |
| הצעות כיסוי / טווח / התראת משך / כרטיסי דוחות | 🆕 knobs (insights.*, reports.cards) — registry rows at build | 🆕 |
| לשונית CRM | `crm_enabled` | ✅ |
| שמור שינויים | `saveSettings` (+ view-only coordinator gate `data-ro-settings`) | ✅ |

**Per-tech knobs NOT on settings (by design — they live in the tech edit modal):** skills[],
cat_limits, blocked_cities/zones, duration_overrides, weekly_schedule (+_break), min/max_daily,
rotation. All ✅ in the modal today; the port restyles, never moves them.

## Cross-cutting rules the port must honor (from this round)
1. **ONE ENGINE DOOR** — every שבץ/עריכה/בטל, from any surface, enters the same flow.
2. Daily/weekly (and month) views re-render correctly after ANY calendar change; reports re-render on period toggle.
3. ממתינות are timeless; week pagers scope only date-anchored statuses.
4. Insights: timeframe stamp + הצעה-בלבד + max-2-visible; suggestions never change config.
5. Approved-overrun tail = display layer; next call never moves.
6. Hard rule #3 (design-system): daily-grid geometry (PX=1, 60px/hr, labelW=42) untouched.

## NEW-build inventory for the port (rolled up)
JS-display only: KPI deltas/strips, grouping+pager, lane-cascade weekly, drive-gap labels,
breakdown popover, rotation matrix, dayoff impact, demand column, reports page, CSV export.
Engine slices: overrun popup (spec'd), insights computations (coverage query, live-week
overflow counter, duration spread), new knobs (insights.*, reports.cards) — each = registry
row + both readers + test, same commit, per the knob rule.
