# Claude Design prompts — Maslul UI/UX (2026-06-14)

Ready-to-paste prompts for **claude.ai/design** (the browser design tool). Generate visuals there,
then paste the screenshots back into our chat as references and I rebuild them on our real
`style.md` tokens inside `index.html`.

**How to use:**
1. Open claude.ai/design in your browser, start a new design.
2. Paste **Prompt 0 (Design language)** first — it sets the shared look for the whole session.
3. Then paste any screen prompt below *in the same conversation* (they reference the design language).
4. Screenshot what you like → paste here.

> Every screen obeys our north-star: **Maslul is an AI dispatch cockpit, not a calendar.** The engine
> already computes the optimal route — the UI surfaces that intelligence simply. Clean, visible, easy
> for a non-technical coordinator; each section shows only its most relevant data, never repeating.

---

## Prompt 0 — Design language (paste this FIRST)

```
You are designing screens for "Maslul" (משׂלוּל), a Hebrew, right-to-left (RTL) SaaS web app for
dispatching field-service technicians in Israel. It is an AI dispatch cockpit — a scheduling engine
already computes optimal technician routes, and the UI's only job is to surface that intelligence
simply. Visual principle: clean, minimalist, generous whitespace, modern professional SaaS (Linear /
Vercel feel), operable by a non-technical coordinator. Each section shows only its most relevant data,
never repeats information, never feels cluttered. Flat and modern — no heavy gradients, no skeuomorphism.

Use this exact design language on every screen:
- Font: Heebo. All text in Hebrew. Full RTL layout — right-aligned, controls and icons mirrored.
- Accent: indigo #6366F1 (hover #4F46E5, light fill #EEF2FF, soft border #C7D2FE).
- Page background #F7F7F8; cards/surfaces white #FFFFFF; all borders #E4E4E7.
- Text: #111827 primary, #374151 secondary, #6B7280 muted, #9CA3AF faint/placeholder.
- Status colors: green #10B981 = completed, amber #F59E0B = pending, indigo #6366F1 = assigned/
  scheduled, red #EF4444 = cancelled; purple #7C3AED, teal, etc. as per-technician identity colors.
- Corner radius: 6px buttons/inputs, 10px cards, 14px panels/modals. Soft low-opacity shadows.
- Spacing in 4px multiples, generous padding.
- Type scale: 12/13/14/15/18/24px+; weight 400 body, 600–700 emphasis, 800–900 only for big numbers/titles.

Acknowledge and wait — I'll describe each screen next.
```

---

## Prompt 1 — Coordinator flow: search screen (Step 1)

```
Using the Maslul design language, design the FIRST screen of the scheduling flow: a dead-simple search.
Nothing else competes for attention. Centered, lots of whitespace. A single clean card with: a city
field (עיר), an address field (כתובת), optional service-type dropdown (סוג שירות), and one primary
indigo button "חיפוש מועדים" (Find slots). Small Hebrew helper text under the title explaining the
coordinator just enters where the job is and the system finds the best route slot. No technician info,
no calendar, no options yet — the optimization happens behind the scenes after search. Title: "שיבוץ קריאה חדשה".
```

---

## Prompt 2 — Coordinator flow: 3 recommendation cards (Step 2)

```
Using the Maslul design language, design the recommendation screen shown AFTER search. At the top, a
slim summary bar of what's being booked: a location pin, city "תל אביב" (bold) + address "דיזנגוף 120"
(muted), and a small "שינוי" (edit) link — minimal, not a form.

Below, a section label "המלצות שיבוץ" and exactly THREE recommendation cards in a row, best-first. Each
card shows ONLY: weekday large and bold (e.g. "יום א׳"), the date muted ("15 ביוני 2026"), and a
prominent time-window chip with a clock ("07:00 — 10:00"), plus a "בחירה" select button. The first card
is the engine's best pick — give it an indigo border, a soft indigo glow, a small "מומלץ" badge, and a
filled indigo select button. Cards 2 and 3 are calmer (white, outline button).

Critically: NO technician name, NO route, NO scores, NO optimization details on these cards — those are
revealed only after a card is chosen. Below the cards, two equal outline buttons: "מצא מועד אחר"
(find the next-best option) and "בדוק תאריך מסוים" (check a specific date). Keep it calm and uncluttered.
```

---

## Prompt 3 — Coordinator flow: reveal after selection (Step 3 + confirm)

```
Using the Maslul design language, design the screen shown AFTER the coordinator picks a recommended
slot — now we reveal the "why". A confirmation-style panel for the chosen date/window at the top
("יום א׳, 15 ביוני · 07:00–10:00"). Then, the details that were hidden before, each in its own clean
block, no repetition:
- Assigned technician: small colored avatar with initials, name, phone, and their region for that day
  (e.g. "אזור: תל אביב והסביבה").
- The planned day route as a simple ordered list of stops with times and cities (the new job marked
  "חדש"), conveying "far → near" sequence — this is the engine's reasoning made visible.
- A short customer-detail form (name חובה, phone, notes).
- A primary indigo button "אישור שיבוץ ✓".
Make it feel like a confident dispatcher explaining the plan. After confirm, show a brief success state
"נקבע בהצלחה ✓" that implies auto-return to the search/home screen.
```

---

## Prompt 4 — Weekly calendar (technician overview)

```
Using the Maslul design language, design a weekly dispatch calendar — the operations overview. Columns
are the work week RIGHT-TO-LEFT (יום א׳ … יום ה׳, Sunday first on the right). Rows/cells hold each
technician's jobs for that day. Color-code by technician identity color (indigo, purple, teal, amber).
Each job chip is compact: time-window + city + a tiny status dot (amber pending, indigo assigned, green
done). IMPORTANT behavior to show visually: multiple jobs that share the same 3-hour arrival window are
grouped/stacked inside ONE window block (e.g. a "07:00–10:00" block containing 2–3 stacked client rows),
not scattered. Always chronological top-to-bottom (never 10:00 above 07:00). Show only confirmed/completed
jobs — no drafts. A slim technician filter (colored pills) at the top. Clean, scannable, lots of breathing
room — this should read like a calm cockpit, not a cramped spreadsheet.
```

---

## Prompt 5 — Daily route grid (one technician)

```
Using the Maslul design language, design a single-technician daily schedule as a vertical time grid from
07:00 to 18:00 (hour lines with labels on the right edge for RTL, a thin red "now" line). Jobs are
positioned by time. The key idea: a 3-hour arrival window is one tall block (e.g. 07:00–10:00) that can
CONTAIN several stacked job rows (client name + exact time + a small "🚗 12 דק׳ מ-עיר" drive-time hint
from the previous stop). When two windows overlap they sit side-by-side in columns so nothing covers
anything. Below the grid, a small "ממתין לשיבוץ" tray listing unscheduled jobs as draggable rows. A
header line shows "9/9 קריאות" utilization and an indigo "מסלול מיטבי" (optimize route) button. Calm,
spacious, color = the technician's identity color at low opacity with a colored right edge.
```

---

## Prompt 6 — Left navigation side panel + detail slide-in

```
Using the Maslul design language, design two things together:
1) A fixed RIGHT-side navigation panel (RTL app, so nav sits on the right), 220px, light #F7F7F8 fill,
   border on its left edge. Small uppercase section labels ("ניווט"), then nav items as inset pills with
   an icon + Hebrew label (לוח בקרה, שיבוץ, יומן, טכנאים, אזורים, דוחות). The active item has an indigo
   light fill, indigo text, bold, and a 3px indigo edge bar. At the bottom: a tenant/role chip and user.
2) A right-side slide-in DETAIL panel (420px, full height, slides in from the side, soft shadow) for a
   single job: header with client name + status pill, then clean labeled rows — city/address, time
   window, technician, service type, notes — and footer actions (edit, lock 🔒, cancel). No data repeats
   between rows. Linear-style: quiet, precise, generous spacing.
```

---

## Prompt 7 — Home dashboard (technician-first)

```
Using the Maslul design language, design the home/dashboard as a dispatcher cockpit. Top: a compact KPI
strip — small cards for ממתין (pending, amber), משובץ (assigned, indigo), הושלם (completed, green),
היום (today). Below, the main content is a grid of TECHNICIAN cards (not a task list). Each tech card:
colored avatar + name, a status pill, a capacity bar showing "load / 9 קריאות" (green under 60%, amber
under 85%, red at/over), and "הבא: 08:30 — תל אביב". Clicking a technician opens their structured weekly
schedule (days · time windows · cities · addresses · service types · status). Emphasis: the home page
shows technicians and their utilization at a glance — clean, calm, no dense task/city lists. Title row:
"לוח בקרה" with the date.
```

---

## Notes for porting back
- These prompts intentionally over-specify color/RTL/Hebrew so the web tool stays on-brand.
- The web tool builds with generic React components — treat its output as **visual reference only**; I
  rebuild the chosen direction on our `style.md` tokens in `index.html` (no framework, no build).
- Engine logic is already verified against these flows (see `outputs/israel-feedback-triage_2026-06-14.md`):
  the cards map 1:1 to the ranked candidates the engine returns, tech-hidden-until-selected is display-only,
  and the calendar's window-stacking is already how `renderPlannerDaily` groups by window.
```
