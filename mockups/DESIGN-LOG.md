# Maslul UI Redesign — Design Log

> Cross-session record of the UI/UX redesign directions approved from claude.ai/design mockups
> (prompts in `outputs/claude-design-prompts_2026-06-14.md`). Each screen: the approved layout, the
> elements to keep, and behavior requirements. Reference screenshots live in `mockups/references/`
> (drop the PNGs there + commit so future sessions can open them with Read). Built mockups on our
> real `style.md` tokens live alongside as `mockups/*.html`. Status: **design phase, started 2026-06-14.**

Principle for all screens: AI dispatch cockpit (not a calendar) · clean, visible, easy for a
non-technical coordinator · most relevant data per section, no repetition · everything flows · never
break engine logic. Tokens = `context/style.md` (Heebo, RTL, indigo #6366F1, etc.).

---

## 1 — Search screen (Step 1) ✅ approved
Centered single white card, generous whitespace. Title **"שיבוץ קריאה חדשה"** + helper subtext
("הזינו היכן ממוקמת הקריאה — והמערכת תמצא את המועד הטוב ביותר…"). Fields: **עיר**, **כתובת**,
**סוג שירות** dropdown. One primary indigo button **"חיפוש מועדים"**. Subtle loading hint
"המערכת מחשבת את המסלול האופטימלי עבורכם". 3-step progress dots at top. Nothing else competes.

## 2 — Recommendation cards (Step 2) ✅ approved
Slim summary bar: location pin + **city** (bold) + address (muted) + service-type chip ("התקנה") +
**"שינוי ✎"**. Section label **"המלצות שיבוץ · לפי המסלול האופטימלי"**. **3 cards, best-first**:
weekday (large bold) · date (muted) · **time-window chip** · **בחירה** button. Card 1 = engine's best:
indigo border + soft glow + **"מומלץ ★"** badge + filled indigo button. Two alt actions:
**"מצא מועד אחר"** (next-best) + **"בדוק תאריך מסוים"**. NO tech/route/score on cards.
- ⚠ **Fix on port:** window chip renders the range reversed in RTL ("10:00 — 07:00"). Force LTR/bidi
  isolation on time ranges so it reads start → end.

## 3 — Reveal + confirm (Step 3) ✅ approved
Top bar: **"המועד שנבחר"** + chosen slot ("יום א׳, 15 ביוני · 07:00–10:00") + clock icon + **"החלפת מועד"**.
Two columns (no repeated data):
- **Customer form** — שם מלא (חובה *), טלפון, הערות; primary **"אישור שיבוץ ✓"**.
- **Technician card** — colored avatar + initials, name, phone, **"אזור היום: …"**.
- **Day route timeline** — ordered stops (time · city · street), new job tagged **"חדש"**, plus the
  far→near reasoning line ("הקריאה שובצה בתחילת היום — הרחוקה ביותר — כך שהמסלול מתכנס פנימה").
After confirm → brief **"נקבע בהצלחה ✓"** → auto-return to search/home.

## 4 — Weekly calendar / dispatch board ✅ direction approved (needs the requirements below)
Header **"לוח שיבוצים"** + date range + counts ("31 קריאות · 9 ממתינות"). Controls: **יום/שבוע** toggle,
**היום** + prev/next arrows, filter pills (**"כל הצוות"** + one per tech, each with avatar + color).
Grid = **technician rows × day columns** (יום א׳…ה׳, Sunday-first on the right). Tech row label:
avatar + name + "N קריאות · region". Each cell = **window block**: count badge + **time range** +
stacked **client · city** rows + status dot. Empty = **"פנוי"**. Legend: משובץ (indigo) · ממתין
(amber) · הושלם (green). Bonus: full side-nav captured here (see screen 6).

**Requirements (must hold on the build):**
- **Sticky both axes:** day/week headers pinned on vertical scroll; technician/time labels (right side
  in RTL) pinned on horizontal scroll — they must always stay visible.
- **3-hour window with multiple blocks stacked inside** (PureWater model) — several jobs share one
  07:00–10:00 window block, shown stacked, exactly as Israel sent.
- **Not a cramped scroll box.** Current mockup is a small inner-scroll panel — the calendar must be
  **full-size and adjustable to our needs**, not a tiny scroller.
- **Important data up front; actions in visible parts; everything flows, clear and simple.**
- **Responsive integrity:** renders cleanly with **1, 2, 3+ technicians** and in **daily** view — no
  layout break at any count.

## 5 — Daily route grid (one tech) ✅ approved
Header: tech avatar + name + **"אזור … · 15 ביוני"** region/date + utilization ring **"9 / 9 קריאות מתוזמנות"**
+ indigo **"מסלול מיטבי"** (optimize) button. Vertical time grid **07:00–18:00**, hour labels on the edge,
thin lines + red **now-line** ("● 11:20"). **3-hour window blocks** positioned by time: each = count badge +
**time-range header** (e.g. 07:00–10:00) + stacked job rows (**time · status dot · client · "N דק׳ מ-origin"
drive-time hint**). Overlapping windows sit **side-by-side in columns** so nothing covers anything.
Below the grid: **"ממתין לשיבוץ N"** tray with **draggable** rows (drag handle + client + service-type chip
+ city chip) and hint "גררו אל הלוח כדי לשבץ". This is the canonical PureWater 3h-window + stacking view.

## 6 — Side panel nav + detail slide-in ✅ approved (`flow/Nav & Detail Panel.html`)
Fixed **right** nav (RTL), 220px: brand mark + "משׂלוּל", section label "ניווט", nav items (icon + label:
לוח בקרה, שיבוץ, יומן, טכנאים, אזורים, דוחות) — active = indigo fill + indigo text + bold + 3px edge bar.
Bottom: tenant card (gradient logo + company + role) + user row (avatar + name + logout). **Detail slide-in**:
left-anchored panel (420px, `translateX` in, scrim), header (eyebrow "קריאה #id" + close, client name + status
pill), body rows (מיקום, חלון הגעה [`direction:ltr`], טכנאי [avatar+name+region], סוג שירות chip, הערות),
footer (עריכה primary + lock-toggle icon + ביטול danger). Esc/scrim close. **Maps to our existing `.mo-panel`
+ `openTaskDetail` + `toggleTaskLock`.**

## 7 — Home dashboard (technician-first) ✅ approved (`flow/Home Dashboard.html`)
Nav + main. Header "לוח בקרה" + date/"מבט תפעולי" + רענון/שיבוץ קריאה buttons. **KPI strip** (4): ממתין לשיבוץ
(amber), משובץ (indigo), הושלם (green), היום (slate) — each icon + label + big number + sub. Section "צוות בשטח"
("לחצו על טכנאי לצפייה בלוח השבועי"). **Technician grid** of cards (demo has **5 techs** — proves it scales).
Click a tech → **weekly slide-in panel**: tech chip + summary (קריאות השבוע / היום / ימי פעילות) + week body +
footer "פתיחת מסלול יומי". Maps to our home dashboard + `tech-home-card` + the daily grid.

---

## Cross-cutting facts (verified in the source files)
- **RTL time-range is already fixed** — all window labels use `direction:ltr` + `font-feature-settings:"tnum"`.
  (My earlier screenshot note about "10:00 — 07:00" was the render before this; the HTML handles it.)
- **Two calendar variants exist:** `Weekly Calendar.html` = clean **day-columns** (window blocks stacked per
  day, `color-mix` tint). `Dispatch Board.html` = **tech-rows × day-columns** grid (the one with the sticky/
  responsive notes). Decide which becomes our weekly view — or support both.
- **Tech identity colors:** yossi #6366F1, dana #7C3AED, omer #0D9488, ran #D97706, maya #E11D48.
- **Token match is ~1:1** with `style.md` — minimal translation needed.

## Open items to resolve during the port
- ⚠ **Class-name collisions:** the mockups use generic names (`.btn .card .page .nav .pill .status-pill .kpi-*`)
  that ALSO exist in `index.html`. Port requires **namespacing** (e.g. prefix new screens) — do NOT paste raw.
- Calendar must be **full-size, not an inner scroll box**; sticky day headers (vertical) + sticky tech/time
  labels (horizontal); render cleanly at **1/2/3+ techs** and in daily view.
- Engine wiring: cards map 1:1 to `_candidatesZone()` ranked output; reveal pulls `candidate.tech` + day route;
  detail panel reuses `openTaskDetail`/`toggleTaskLock`. See `outputs/ui-port-plan_2026-06-15.md`.
