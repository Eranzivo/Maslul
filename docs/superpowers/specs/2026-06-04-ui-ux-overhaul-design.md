# UI/UX Overhaul — Home + Dispatch Pages
**Date:** 2026-06-04  
**Scope:** Coordinator app — Home page + Dispatch page  
**Goal:** Elevate Maslul from "prototype" to "real SaaS product" feel — clean structure with bold, data-rich KPI and tech status

---

## Visual Direction

**Mix: clean structure + bold KPIs**
- Overall layout: clean, minimal, generous white space (Linear-style)
- KPI cards and tech status: bold, colorful, data-rich (timing.tech-style)
- Sidebar: light background (keep current `--surface-1`), modernized with SVG icons (no emoji)
- Accent: existing `--accent` (#6366F1 indigo) — no new colors introduced

---

## Section 1 — Sidebar

### What changes
- Replace all emoji nav icons with clean SVG icons (inline, same size ~16px)
- Remove emoji from all nav item labels
- Keep structure: `--surface-1` bg, right border, 220px width, fixed position
- Active state unchanged: `--accent-light` bg, `--accent` text, 2px right border accent
- Section labels (`sb-sec`) stay
- Role chip (tenant switcher) stays — reduce visual prominence slightly (smaller font, less padding)

### What does NOT change
- Nav structure and order
- Sidebar width
- Background color (stays light)
- RTL positioning (right side)

### SVG icon set
Use **Lucide icons** — inline SVG only (no CDN). Copy the raw `<svg>` path for each icon directly into the HTML. One icon per nav item, ~16×16px, `stroke="currentColor"`, `fill="none"`, `stroke-width="2"`. Icons needed: home, target (dispatch), list (tasks), calendar, bar-chart, users, settings, map, shield (admin), phone (tech view).

---

## Section 2 — KPI Cards (Home page top row)

### Layout
4-column grid, full width. Each card: white background, `--r-lg` radius, `--sh` shadow, 4px left border in state color.

### Card anatomy
```
┌──[colored left border]──────────────────┐
│                              [icon]     │
│  30                                     │
│  קריאות היום                            │
└─────────────────────────────────────────┘
```
- **Number**: 30px/900, `--ink` color
- **Label**: 12px/400, `--ink-4`
- **Icon**: 20px, top-right, in the card's state color (opacity 0.7)
- **Left border**: 4px solid, state color

### Cards
| Card | Left border | Icon |
|---|---|---|
| קריאות היום | `--accent` | calendar |
| בביצוע | `--amber` | clock |
| הושלמו | `--green` | check-circle |
| ממתינות לשיבוץ | `--red` | alert-circle |

### Click-to-filter behavior
Clicking a KPI card filters the tech cards below:
- "בביצוע" → highlight techs with `status=assigned/driving/on-site` jobs
- "הושלמו" → highlight techs who completed jobs today
- "ממתינות לשיבוץ" → scroll to pending queue / pulse the pending badge
- "קריאות היום" → reset filter (show all)
- Active filter: card gets `--accent-border` outline + subtle `--accent-light` bg tint
- Unfiltered techs: reduce to 60% opacity (not hidden — coordinator still sees full picture)

---

## Section 3 — Tech Cards (Home page main content)

### Layout
Responsive grid below KPI row:
- Desktop (>1100px): 3 columns
- Tablet (700–1100px): 2 columns
- Mobile (<700px): 1 column

### Card anatomy
```
┌──[3px left border in tech color]────────┐
│  ● מיכאל כהן              [שובץ] badge  │
│                                          │
│  5 / 8 קריאות  ████████░░  63%          │
│  הבא: 10:30 — באר שבע                  │
│                             [שבץ →]     │
└─────────────────────────────────────────┘
```

### Elements
- **Avatar**: colored circle with Hebrew initials, 32px. Color = `tech.color`
- **Name**: 15px/600, `--ink`
- **Status badge**: right-aligned, pill shape
  - `פנוי` → gray
  - `שובץ` → amber  
  - `בדרך` / `הגיע` → indigo
  - `הסתיים` → green
  - Status derived from today's tasks (read from local `tasks` array, no new query):
    1. Any task with `status === 'בדרך'` or `'הגיע'` → badge = `בדרך`
    2. Else if any task with `status === 'שובץ'` → badge = `שובץ`
    3. Else if all tasks `status === 'הושלם'` and count > 0 → badge = `הסתיים`
    4. Else → badge = `פנוי`
- **Left border**: 3px solid, `tech.color` (replaces the current top-bar)
- **Capacity bar**: `X / max` label + progress bar
  - Bar color: green < 60%, amber 60–85%, red ≥ 85%
  - `max` = `tech.maxDaily` (from DB)
- **Next job line**: `הבא: HH:MM — עיר` — 13px, `--ink-3`. If no jobs: `אין קריאות היום` in `--ink-4`
- **Quick assign button**: `.btn-sm .btn-outline` — `שבץ →` — opens dispatch drawer pre-filled with this tech

### Filter integration (from KPI cards)
When a KPI filter is active, unmatched tech cards go to 60% opacity. Matched cards stay full opacity with a subtle `--accent-light` bg tint.

---

## Section 4 — Page Header & Action Buttons

### Layout
```
[page title + subtitle]        [מפה חיה]  [חופשות]  [+ שיבוץ קריאה]
```
- Right side: primary CTA + secondary ghost buttons
- Left side: title + dynamic subtitle

### Elements
- **Title**: "בית" or "לוח בקרה" — 26px/900, `--ink`, `.ph-title`
- **Subtitle**: dynamic text — "X טכנאים פעילים · היום, יום רביעי 4 ביוני" — 14px, `--ink-4`
- **Primary**: `+ שיבוץ קריאה` → `.btn .btn-blue`
- **Secondary**: `מפה חיה` → `.btn .btn-ghost` (SVG icon + label)
- **Tertiary**: `חופשות` → `.btn .btn-ghost` (SVG icon + label)
- **Removed**: `+ הוסף קריאה` button — merged into dispatch flow (same action, redundant entry point)

No emoji in any button. SVG icons only where needed.

---

## Section 5 — Dispatch Page

### Layout
Two-column layout replacing the current single-column form:

```
┌─────────────────────┬──────────────────────┐
│  פרטי הקריאה  [col1]│  שיבוץ        [col2] │
└─────────────────────┴──────────────────────┘
```

- **Col 1 (right, RTL = start)**: client details form
- **Col 2 (left, RTL = end)**: date/time + tech selector
- On mobile: stacks to single column, col1 first

### Col 1 — Client Details
- Fields (existing, kept as-is): client name, phone, city (autocomplete), street, category, notes
- Layout: `.fg-2` two-column grid for name+phone, city+street; notes full-width
- **Pending Queue** (existing panel): moved to bottom of col 1 as a compact collapsed list
  - Shows count badge: "15 ממתינות" 
  - Expandable — click to show list, click row to pre-fill form
  - Collapsed by default on desktop, expanded if `window._queueTask` is set

### Col 2 — Assignment
- **Date picker**: existing `s-date` input — `.fc`, full width
- **Time**: existing `s-time` — `.fc`, full width
- **Tech selector**: replaces the current `<select>` dropdown with a visual card list
  - Each tech shown as a compact row: avatar circle + name + capacity indicator (colored dot: green/amber/red) + job count for selected date
  - Click to select — selected row gets `--accent-light` bg + `--accent-border`
  - If no date selected: shows all techs with today's load
  - If date selected: shows load for that date (query from local `tasks` array)
- **Submit**: `.btn .btn-blue .btn-full` — `שבץ קריאה` — at bottom of col 2

### Preserved behavior
- `confirmAssign()` logic unchanged — detects `_queueTask`, updates vs creates
- Rollback on failure unchanged
- All existing validation unchanged
- Pending queue filter (`status==='pending'`) unchanged

---

## Implementation Constraints

- Single `index.html` — all changes inline in `<style>` and the relevant page `<div>`
- No new JS libraries
- RTL throughout — all layout decisions use start/end or explicit right/left as appropriate
- All new colors use existing CSS tokens — no hardcoded hex values
- SVG icons: inline in HTML (no external icon library CDN) — small set (~10 icons total)
- Mobile breakpoint: `max-width: 900px` (existing) — no new breakpoints

---

## Out of Scope (this spec)

- Tech view page redesign
- Dashboard analytics / charts
- Customer ETA portal
- Reports page
- Settings / admin pages
- Any new Supabase tables or columns
