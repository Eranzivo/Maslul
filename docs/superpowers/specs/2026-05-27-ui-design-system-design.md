# Maslul UI Design System — Spec
**Date:** 2026-05-27  
**Approach:** B — CSS token update + component class standardization  
**Inspiration:** Linear (light mode) + timing.tech UX  
**Status:** Approved for implementation

---

## 1. Design Principles

- **Light mode only** — white/off-white base throughout
- **Modern & friendly** — rounded corners, generous spacing, one strong accent
- **Linear-style precision** — every spacing value from the 4px scale, no magic numbers
- **RTL-first** — all layout decisions account for Hebrew right-to-left reading direction
- **Approach B scope** — update CSS tokens + standardize component classes; do not rewrite page logic or markup structure

---

## 2. Color Token System

Replace all current color variables at `:root` in `index.html`. The existing variable names are preserved where possible to minimize find/replace scope; new names added for indigo accent.

### Surfaces
```css
--surface-0: #FFFFFF;      /* main content, modals */
--surface-1: #F7F7F8;      /* sidebar, card fills, table alternates */
--surface-2: #EFEFEF;      /* hover states, subtle fills */
--border:    #E4E4E7;      /* all dividers, card edges, input borders */
```
> Replaces: `--bg: #F7F9FC`, `--line: #E5E7EB`, `--line-2: #F3F4F6`, `--white: #fff`

### Text Hierarchy
```css
--ink:   #111827;   /* primary — headings, nav labels, data */
--ink-2: #374151;   /* secondary — card subtitles, metadata */
--ink-3: #6B7280;   /* muted — timestamps, helper text, section labels */
--ink-4: #9CA3AF;   /* placeholder, disabled */
```
> These names already exist — values stay the same. No find/replace needed.

### Brand & Accent (replaces --blue system)
```css
--accent:       #6366F1;   /* indigo — primary CTAs, active nav, focus rings */
--accent-hover: #4F46E5;   /* pressed/hover */
--accent-light: #EEF2FF;   /* active nav background, tag fills, badge bg */
--accent-border:#C7D2FE;   /* indigo-tinted borders */
```
> `--blue: #2563EB` → `--accent: #6366F1`. All `--blue` references in JS/HTML updated to `--accent`.  
> `--blue-l` → `--accent-light`. `--blue-d` → `--accent-hover`. `--blue-m` → `--accent-border`.

### State Colors
```css
--green:    #10B981;   --green-l:  #ECFDF5;   /* completed, success */
--red:      #EF4444;   --red-l:    #FEF2F2;   /* error, cancelled */
--orange:   #F59E0B;   --orange-l: #FFFBEB;   /* pending, warning */
--purple:   #7C3AED;   --purple-l: #F5F3FF;   /* kept for tech color variety */
```
> `--amber` → renamed `--orange` for consistency. Values updated to match.

### Shape & Elevation
```css
--r:       6px;    /* inputs, buttons, small chips */
--r-lg:   10px;    /* cards, dropdowns */
--r-xl:   14px;    /* modals, large panels */

--sh:    0 1px 2px rgba(0,0,0,0.05);
--sh-md: 0 4px 12px rgba(0,0,0,0.08);
--sh-lg: 0 8px 32px rgba(0,0,0,0.14);
```
> Radius values tightened slightly (was 8/14/20px → 6/10/14px) for Linear-style precision.

---

## 3. Typography System

**Font:** Heebo — unchanged, correct for Hebrew RTL.

### Scale (6 sizes only — down from 20+)
```
xs:   12px / 400   → meta, timestamps, badge text, section labels
sm:   13px / 400   → secondary body, table metadata, helper text
base: 14px / 400   → primary body, nav items, form values
md:   15px / 500   → card titles, field labels, modal body
lg:   18px / 600   → page titles, modal headers
xl:   24px / 700   → major headings, KPI values
```

### Weights (4 only — down from 6)
```
400   regular — body text, secondary labels
500   medium  — field labels, toggle labels, nav items
600   semibold — card titles, page section headers, button text
700   bold     — page titles, modal titles, KPI values, client names
```
> Remove all `font-weight: 800` and `font-weight: 900` — replace with `700`.  
> Remove `font-weight: 500` where it duplicates `600` usage.

---

## 4. Component Class System

All ad-hoc styles consolidated into the following named classes. Existing class names migrated per the mapping below.

### Buttons
```
.btn              base — flex, height 36px, radius --r, font-size sm, weight 600
.btn-primary      --accent fill, white text, hover --accent-hover         (replaces .btn-blue)
.btn-secondary    white fill, --accent border + text, hover --accent-light (replaces .btn-outline)
.btn-ghost        transparent, --ink-3 text, hover --surface-2             (replaces .btn-ghost)
.btn-danger       --red fill, white text                                    (replaces .btn-red)
.btn-sm           height 30px, font-size xs, padding 0 10px
.btn-lg           height 44px, font-size md, padding 0 20px
.btn-full         width: 100%
```

### Cards
```
.card             white bg, 1px --border, --sh, --r-lg, padding 20px
.card-header      flex between: title (md/600) + optional action (btn-ghost btn-sm)
.card-section     border-top --border, padding-top 16px, margin-top 16px
```
Consolidates: `.tech-card`, `.tech-home-card`, `.client-card`, `.zone-card`, `.kpi-card` → all use `.card` with content variants inside.

### Forms
```
.field            replaces .fg  — flex column, gap 6px
.field-2          replaces .fg-2 — 2-column grid
.field-3          replaces .fg-3 — 3-column grid
.label            replaces .fl  — 13px/500, --ink-2
.input            replaces .fc  — height 40px, padding 0 12px, --border, --r, full width
.input:focus      outline: 2px solid --accent-light, border-color --accent
.input.error      border-color --red
.field-error      replaces existing — 12px --red, margin-top 4px
```

### Badges
```
.badge            base — inline-flex, 12px/600, px 8px, py 2px, --r
.badge-green      --green-l bg, --green text
.badge-orange     --orange-l bg, --orange text
.badge-red        --red-l bg, --red text
.badge-indigo     --accent-light bg, --accent text              (replaces .badge-blue)
.badge-gray       --surface-2 bg, --ink-3 text
```

### Data Tables
```
.data-table         width 100%, border-collapse collapse
.data-table th      13px/600 uppercase --ink-3, 40px height, border-bottom --border, text-align right
.data-table td      14px --ink, 48px height, border-bottom --border
.data-table tr:hover  background --surface-1
.row-actions        hidden by default; visible on tr:hover — flex gap 4px, btn-ghost btn-sm
```

### Page Layout
```
.page-header        flex between, margin-bottom 24px, padding-bottom 16px, border-bottom --border
.page-title         18px/600 --ink
.page-content       padding 24px
.section-label      12px/600 uppercase --ink-3, letter-spacing 0.05em, margin-bottom 12px
```

### Modals
```
.mo                 fixed inset, backdrop blur(4px), rgba(0,0,0,0.4), z-index 1000
.mo-box             white, --r-xl, --sh-lg, padding 24px, max-width 480px, max-height 90vh scroll
.mo-title           18px/700, margin-bottom 20px
.mo-body            flex column, gap 16px
.mo-footer          flex end, gap 8px, margin-top 24px, padding-top 16px, border-top --border
```
Mobile: bottom sheet (align-items flex-end, border-radius --r-xl --r-xl 0 0, max-height 88vh)

### Toasts
```
fixed bottom-right, 320px, --r-lg, --sh-lg, padding 14px 16px
left border 3px: green (success) / red (error) / --accent (info)
auto-dismiss 4s — no raw backend strings shown (generic Hebrew only)
```

### Slide-in Drawer (new component)
```
.drawer             fixed right panel, width 360px, height 100%, --sh-lg
                    slides in from right (transform translateX), z-index 500
.drawer-header      flex between: title + close button
.drawer-body        padding 20px, scrollable
.drawer-footer      fixed bottom, padding 16px, border-top, btn-primary full width
```
Used for: add call flow, edit call flow. Replaces modal for primary dispatch actions.

---

## 5. Sidebar (Linear-style)

**Width:** 220px (down from 232px). Fixed right, full height, border-left 1px --border.  
**Background:** --surface-1.

### Structure
```
[Brand bar 56px]         logo mark + "מסלול" wordmark
[Divider]
[Navigation — scrollable, flex-col]
  Section: פעולות        (12px/600 uppercase --ink-4)
    בית / שיבוץ / קריאות / מתזמן / דוחות / לקוחות
  Section: הגדרות
    טכנאים / אזורים / קטגוריות / הגדרות
  Section: מערכת         (super_admin only)
    ניהול מערכת / אשף הקמה
[Divider]
[User profile bar — bottom]
  Avatar (28px circle, --accent bg, white initials)
  Name (14px/600) + Role (12px --ink-3)
  [Role chips for coordinator/admin]
  [↩ logout icon button]
```

### Nav Item Style
```
.ni-btn             flex right-align, height 36px, px 12px, --r 6px, 14px/500 --ink-2
.ni-btn:hover       background --surface-2
.ni-btn.active      background --accent-light, color --accent, font-weight 600
                    right border 2px solid --accent (RTL: border-right)
```

---

## 6. Core Coordinator Workflow — Add Call → Assign

### Trigger
Persistent **"+ קריאה חדשה"** button in sidebar footer area — always visible, `.btn-primary`, one click from any page.

### Step 1 — Slide-in Drawer (details)
Right drawer slides in. Fields:
- לקוח (search existing or type new) — autocomplete from clients table
- טלפון (auto-fills if existing client selected)
- עיר (dropdown, active cities only)
- קטגוריה (dropdown — sets duration automatically)
- הערות (single line, optional)

CTA: **"מצא חלונות פנויים ←"** (btn-primary, full width, bottom of drawer)

### Step 2 — Slot Suggestions (same drawer)
Drawer transitions to results view. Shows 2 ranked slots as selectable cards:
```
.slot-card          white, 1px --border, --r-lg, padding 16px, cursor pointer
.slot-card:hover    border-color --accent, --accent-light bg
.slot-card.selected border 2px --accent, --accent-light bg
```
Each card shows: tech name + avatar color · date · time range · city · existing load that day.  
Below cards: `[שנה תאריך]` (ghost btn) · `[שבץ ידנית]` (ghost btn)

CTA: **"אשר שיבוץ ←"** — activates only when a card is selected.

### Step 3 — Confirmation
Toast: "קריאה שובצה ✓ — דוד לוי · יום ג׳ 10:00"  
Drawer closes. Schedule view updates in place.

### Editing — Inline on Schedule
Every assigned slot in planner/home view shows on hover:
```
[✏️ ערוך]   → reopens drawer pre-filled
[⇄ העבר]   → reassign: picker for tech + time, re-runs optimizer on this call only  
[✕ בטל]    → cancel with confirmation (reason picker)
```
No full-page navigation for edit — always in-place drawer or inline.

---

## 7. Tech View UX

**Layout:** Vertical timeline — mobile-first, single column, ordered by scheduled time.

### Page Header
```
שלום [שם טכנאי] 👋
[יום בשבוע] · [N] קריאות היום
```

### Each Task Slot
```
● [זמן] – [זמן סיום]   [עיר]
  [שם לקוח]
  [קטגוריה] · [הערות אם יש]

  [📞 התקשר]   [📍 נווט]   [✓ סיים]

  ▼ פרטי לקוח                   (expandable, collapsed by default)
    📞 [מספר טלפון]  →  tel: link, opens dialer
    📍 [כתובת מלאה]
    📝 [הערות נוספות]
```

**Status dots:**
- ⚪ אפור — upcoming
- 🔵 כחול — in progress (current time window)
- 🟢 ירוק — completed
- 🔴 אדום — cancelled

**Actions:**
- 📞 התקשר — `tel:` link, one tap to dial
- 📍 נווט — deep link to Waze (`waze://`) with fallback to Google Maps URL
- ✓ סיים — opens completion flow (signature canvas + optional photo, already implemented)

**Tech cannot reorder** — schedule is set by coordinator. Tech can see all details, call client, navigate, complete.

---

## 8. Implementation Rules

1. **Approach B** — update CSS tokens + component classes in `index.html` only. No new files. No JS framework.
2. **Variable migration** — find/replace `--blue` → `--accent`, `--blue-l` → `--accent-light`, `--blue-d` → `--accent-hover`, `--blue-m` → `--accent-border` globally.
3. **Class migration** — `.btn-blue` → `.btn-primary`, `.btn-outline` → `.btn-secondary`, `.fg` → `.field`, `.fc` → `.input`, `.fl` → `.label`. All HTML updated.
4. **Button testing rule** — after any page change, verify every button/link on that page actually navigates or triggers correctly. No dead buttons shipped.
5. **Error messages** — never expose `error.message` / backend strings to users. Generic Hebrew only. `console.error()` + Sentry for Eran.
6. **Font sizes** — enforce 6-size scale. Any size outside the scale must be justified or collapsed to nearest scale value.
7. **Spacing** — all padding/margin/gap values must be multiples of 4px.
8. **Demo mode** — no Supabase calls when `CONFIG.DEMO_MODE` is true. All new UI must respect this.
9. **RTL** — all layout uses `dir="rtl"`. No `left/right` CSS values where `start/end` can be used.

---

## 9. Out of Scope (this spec)

- Dark mode
- New Supabase tables or schema changes
- WhatsApp template feature (separate backlog item)
- User management infrastructure (separate spec)
- Mobile app / PWA
- Any backend changes
