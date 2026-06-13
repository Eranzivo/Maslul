# Style Reference — Maslul

**Font:** Heebo (Google Fonts) — Hebrew RTL-first throughout.  
**Architecture:** All CSS lives in a single `<style>` block inside `index.html`. No external stylesheet. Do not create separate CSS files.

---

## Color Tokens

```css
/* Surfaces */
--surface-0: #FFFFFF        /* main content, modals, cards */
--surface-1: #F7F7F8        /* sidebar, card fills, table alternates (alias: --bg) */
--surface-2: #EFEFEF        /* hover states, subtle fills */
--border:    #E4E4E7        /* all dividers, card edges, input borders (alias: --line) */
--line-2:    #F0F0F1        /* very subtle dividers, row backgrounds */

/* Text hierarchy */
--ink:   #111827            /* primary — headings, data values */
--ink-2: #374151            /* secondary — labels, card subtitles */
--ink-3: #6B7280            /* muted — timestamps, helper text */
--ink-4: #9CA3AF            /* placeholder, disabled, section labels */

/* Accent (indigo) */
--accent:        #6366F1    /* primary CTAs, active nav, focus rings */
--accent-hover:  #4F46E5    /* pressed/hover state */
--accent-light:  #EEF2FF   /* active nav bg, badge fills, selected bg */
--accent-border: #C7D2FE   /* indigo-tinted borders */
/* Legacy aliases still used in code: --blue, --blue-d, --blue-l, --blue-m */

/* State colors */
--green:    #10B981   --green-l:  #ECFDF5   /* completed, success */
--red:      #EF4444   --red-l:    #FEF2F2   /* error, cancelled */
--amber:    #F59E0B   --amber-l:  #FFFBEB   /* pending, warning */
--orange:   alias of --amber / --orange-l of --amber-l
--purple:   #7C3AED   --purple-l: #F5F3FF   /* tech color variety */

/* Shape */
--r:    6px     /* inputs, buttons, chips */
--r-lg: 10px    /* cards, dropdowns */
--r-xl: 14px    /* modals, large panels */

/* Shadows */
--sh:    0 1px 2px rgba(0,0,0,0.05)    /* card resting */
--sh-md: 0 4px 12px rgba(0,0,0,0.08)  /* elevated card, dropdown */
--sh-lg: 0 8px 32px rgba(0,0,0,0.14)  /* modal, drawer */
```

---

## Typography Scale

| Size | px | Weight | Use |
|---|---|---|---|
| xs | 12px | 400/600 | timestamps, badge text, section labels |
| sm | 13px | 400/600 | secondary body, table metadata, labels (`.fl`) |
| base | 14px | 400/500 | primary body, nav items, form values |
| md | 15px | 500/700 | card titles, field labels, modal body |
| lg | 18px | 600/700 | page titles, modal headers |
| xl | 24px+ | 700/900 | KPI values, major headings |

Weights in use: **400** (body), **500** (medium), **600** (semibold), **700** (bold), **800/900** (display only — KPI values, hero numbers).

---

## Buttons

```css
.btn              /* base — h36, px14, --r, 14px/600, flex center */
.btn-blue         /* --accent fill, white text — PRIMARY action */
.btn-outline      /* white fill, --border, --ink-2 — secondary */
.btn-ghost        /* transparent, --ink-3 — tertiary / icon actions */
.btn-red          /* --red fill, white — destructive */
.btn-green        /* --green fill, white */
.btn-sm           /* h30, px10, 13px */
.btn-lg           /* h44, px20, 15px */
.btn-full         /* width:100% */
```

> Note: spec names `.btn-primary` / `.btn-secondary` but code still uses `.btn-blue` / `.btn-outline`. Either works.

---

## Forms

```css
.fg               /* field group — flex col, gap0 */
.fg-2             /* 2-col grid, gap12 */
.fg-3             /* 3-col grid, gap12 */
.fl               /* label — 13px/600, --ink-2, mb5 */
.fc               /* input/select — h40, px12, --border, --r, full width */
.fc:focus         /* --accent border, --accent-light glow ring */
.fc.error         /* --red border */
.field-error      /* 12px --red, mt3 */
```

---

## Cards

```css
.card             /* white, 1px --border, --sh, --r-lg, p24 */
.card-title       /* 11px/800 uppercase --ink-4, letter-spacing 0.8px, mb16 */
.kpi-card         /* card variant — border-right:4px solid transparent; position:relative; cursor:pointer */
.kpi-card:hover   /* sh-md + translateY(-2px) */
.kpi-card.kpi-active  /* outline:2px solid --accent-border */
.kpi-icon         /* position:absolute; top:14px; left:14px; 18px; opacity:0.65 — decorative SVG */
.kpi-val          /* 30px/900, letter-spacing -1px */
.kpi-lbl          /* 12px --ink-4 */
```

## Tech Cards (Home page)

```css
.tech-home-card   /* white card, border-right:3px solid var(--border) — overridden inline with tech.color */
.tech-home-card:hover  /* sh-md + translateY(-2px) */
.tech-home-card.dimmed  /* opacity:0.4; pointer-events:none — KPI filter inactive state */
.th-color-bar     /* display:none (replaced by border-right) */
.th-body          /* padding:1.125rem 1.25rem; flex col gap:9px; text-align:right */
.th-top           /* flex between, avatar + name + status badge */
.th-avatar        /* 36px colored circle, initials, white 800 */
.th-name          /* 15px/700 --ink */
.th-status        /* pill badge, 11px/700 — color/bg set inline via getTechStatus() */
.th-capacity      /* flex row: count text + load-bar + percent */
.load-bar         /* flex:1; h5px; --line-2 bg; border-radius:3px */
.load-fill        /* h100%; color set inline (green<60%, amber<85%, red≥85%) */
.th-next          /* 13px --ink-3: "הבא: HH:MM — עיר" or "אין קריאות היום" */
.th-actions       /* flex end — optimizer btn + שבץ← btn */
```

## Dispatch Two-Column Layout

```css
.dispatch-cols       /* grid 1fr 320px; gap:1.5rem; align-items:start */
.dispatch-col-queue  /* white card, sticky top:1rem — pending queue sidebar */
.dispatch-col-queue .pq-title  /* 12px/800 uppercase --ink-3, letter-spacing:0.5px */
/* Mobile @media(max-width:900px): dispatch-cols → 1fr; dispatch-col-queue → static */
```

---

## Badges

```css
.badge            /* inline-flex, 12px/600, px8 py2, border-radius 20px */
.badge-blue       /* --blue-l bg, --blue text */
.badge-green      /* --green-l bg, --green text */
.badge-amber .badge-orange   /* --amber-l bg, --amber text */
.badge-red        /* --red-l bg, --red text */
.badge-gray       /* --surface-2 bg, --ink-3 text */
```

---

## Alerts (inline banners)

```css
.alert            /* --r, p10-14, 13px, flex gap8, mb12 */
.alert-amber      /* --amber-l bg, --amber text */
.alert-blue       /* --blue-l bg, --blue-d text */
.alert-green      /* --green-l bg, --green text */
.alert-red        /* --red-l bg, --red text */
```

---

## Modals

```css
.mo               /* fixed inset, rgba(15,23,42,0.5) backdrop, blur(3px), z1000 */
.mo-box           /* white, --r-xl, --sh-lg, p24, max-w480, max-h90vh scroll */
.mo-title         /* 17px/700, mb20 */
.mo-actions       /* flex end, gap8, mt24, pt16, border-top --border */
```

---

## Slide-in Drawer

```css
.drawer-overlay   /* fixed inset, z499, dark bg, opacity 0 → 1 when open */
.drawer           /* fixed top-0 right-220px, w360, h100vh, white, --sh-lg, z500 */
                  /* starts off-screen (translateX), slides in on .open */
.drawer.open      /* transform: translateX(0) */
.drawer-header    /* flex between, p18-20, border-bottom --border */
.drawer-title     /* 16px/700 */
.drawer-body      /* flex-1 scroll, p20, flex col gap14 */
.drawer-footer    /* p14-20, border-top --border */

/* Slot cards inside drawer */
.slot-card        /* border 1.5px --border, --r-lg, p14-16, cursor pointer */
.slot-card:hover  /* --accent border, --accent-light bg */
.slot-card.selected /* --accent border 2px, --accent-light bg */
```

Mobile (`max-width:900px`): drawer takes `right:0; width:100%`.

---

## Sidebar

```css
.sidebar          /* fixed right-0, w220, h100vh, --surface-1, border-left --border */
.sb-nav           /* scrollable nav area */
.sb-sec           /* section label — 11px/600 uppercase --ink-4, letter-spacing 0.06em */
.ni-btn           /* nav item — h40, px12, gap10, r8, 14px/500 --ink-2; inset pill (margin 2px 8px) */
.ni-btn:hover     /* --surface-2 bg */
.ni-btn.active    /* --accent-light bg, --accent-hover text, 700, inset 3px --accent edge bar */
.role-chip        /* tenant switcher chip in sidebar bottom */
.role-chip.active /* --blue-l bg, --blue border/text */
```

---

## Layout Utilities

```css
.page             /* p: 2rem 2.75rem, max-w 1240px, fade-in animation */
.ph               /* page header block, mb 1.75rem */
.ph-row           /* flex between, wrap */
.ph-title         /* 26px/900, letter-spacing -0.8px */
.ph-sub           /* 14px --ink-4 */
.hidden           /* display:none !important */
.flex-between     /* flex, justify-content space-between, align center */
.flex-gap         /* flex, gap8, align center, flex-wrap */
.empty            /* text-center, p3rem, --ink-4 — empty state container */
.empty-icon       /* 40px, mb10 */
```

---

## Status Pills (tasks)

```css
.status-pill      /* px12 py4, border-radius 20px, 11px/700, uppercase */
                  /* color set inline via JS (pending=amber, assigned=blue, etc.) */
```

Task status → color mapping (applied by JS, not CSS class):
- `ממתין` → amber (`--amber-l` / `--amber`)
- `שובץ` → blue (`--blue-l` / `--blue`)
- `בדרך` / `הגיע` → indigo
- `הושלם` → green
- `בוטל` → red

---

## Wizard

```css
.wiz-steps        /* flex, --r-lg, overflow hidden, white, border --line */
.wiz-step         /* flex-1, col, center, p12-6, 11px/700, border-right --line */
.wiz-step.active  /* --blue-l bg, --blue-d text; number circle: --blue bg white */
.wiz-step.done    /* --green text; number circle: --green-l bg --green */
.wiz-type-opt     /* radio option card — border 1.5px --line, --r, p8-14, 14px/600 */
.wiz-type-opt:has(input:checked) /* --blue border, --blue-l bg, --blue-d text */
```

---

## Key Rules

1. **RTL always** — `dir="rtl"` on `<html>`. Use `right/left` in CSS only where truly directional; prefer `start/end` where possible.
2. **Spacing = 4px multiples** — all padding, margin, gap values are 4, 8, 12, 16, 20, 24px etc.
3. **No new files** — CSS additions go inside the `<style>` block in `index.html` only.
4. **Font sizes** — stick to the 6-size scale above. Any new size needs justification.
5. **Accent color = `--accent` / `--blue`** — never hardcode `#6366F1`.
6. **Error messages to users** — generic Hebrew only. Never expose raw `error.message`.
7. **Page animations** — use `animation: fi 0.2s ease` (defined as `@keyframes fi` — fade + 6px slide up). All `.page` divs already have this.
