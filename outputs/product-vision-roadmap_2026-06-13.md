# Product Vision & Reprioritized Roadmap (2026-06-13)

> Source: Eran's UI/UX brief + 4 product-vision prompts + Okd/Odoo reference screenshots.
> Reprioritized through the pilot POV: ship value now, log the rest, iterate with PureWater
> feedback. Canonical backlog stays `context/backlog.md`; this doc holds the *why* + buckets.

## North star (the organizing idea)
**Maslul is an AI dispatch cockpit, not a calendar.** Every screen answers an operational
question: who's available, who's overloaded, where are the gaps, who gets the next job, is this
route efficient. Most of this intelligence **already exists** in the engine (drive-time cache,
far→near, balance, fill-first, zone guard, shadow-compare) — much of the roadmap is *surfacing*
it, not building new brains.

## UI direction (from references)
Linear sidebar (muted, grouped, generous spacing) · Linear right-side properties panel for detail
(replace modals) · Invo dashboard (KPI cards + whitespace). Principle: **minimalist white space,
ample padding, clear hierarchy, professional.** Grab the idea, not the colors. Keep `style.md`
tokens (RTL, Hebrew-first), extend don't replace.

## Buckets

### ✅ Already have — surface, don't rebuild
Drive-time cache · far→near physics · weekly balance · fill-first · slot-release · zone-drop guard ·
shadow-compare (current vs proposed) · KPI cards + per-tech load bars · auto-sequence · zone polygons.

### 🟢 NOW (this iteration)
1. **Design system + shell / side-panel redesign (Pass 1).** Tokens (spacing/whitespace, status→colour,
   typography, buttons); side panel refined (Linear feel); dashboard reframed as a cockpit
   (pending/in-progress/completed/today + per-tech utilization). Extract reusable components
   (`statusDot`/`callCard`/`kpiCard`/`loadBar`/nav/buttons). Current shell is ~75% there → refine, don't teardown.
2. **Explainability v1 (Prompt 1).** On the assignment recommendation, a "why this tech" panel from
   signals the engine already computes: same zone/cluster · km saved · uses an active day · avoids a
   new route · load impact. + hover tooltips on key terms. Fastest path to "intelligent & trustworthy".

### 🟡 NEXT (near-term)
3. **Planner redesign (Pass 2)** on the new system, dispatch-framed (availability/overload/gaps).
4. **Detail-as-side-panel** — replace the task modal with a Linear-style right panel.
5. **Schedule Health Score v1 (Prompt 4, lightweight)** — 0–100 from utilization %, drive efficiency,
   out-of-zone count, gaps + 1–2 obvious suggestions. (Recommendation engine = LATER.)
6. **Done-call detail in the coordinator view** — photos + signature + status + notes the tech uploaded;
   **first verify the tech photo-upload flow end-to-end.**
7. **AI call summary** — concise summary of a completed call from whatever data exists (correct when
   data is sparse). Small, reuses Claude API.
8. **Adjustable / many-shape zone polygons** — edit vertices, more shapes, on the existing zones map.

### 🔵 LATER (logged; revisit with PureWater feedback)
9. **Route Intelligence map dashboard (Prompt 3)** — route flow, tech start, active/future jobs, drive
   times, gaps, traffic; map-as-primary. Higher value at multi-tech scale.
10. **Full explainability everywhere (Prompt 1 complete).**
11. **Health-Score recommendation engine (Prompt 4 complete)** — auto-suggest moves w/ quantified
    savings, leveraging shadow-compare.
12. **Per-tech utilization table (Okd img 4)** — dense ops table w/ over-capacity flags (many-tech).
13. **Analytics dashboard (Okd img 5)** — charts, closure rate, by-location.
14. **Tech-view redesign (Okd img 7–9)** — mobile call cards + detail + route map.
15. Smart lists / global search in side panel; remaining screens onto the system.

### 🟣 DREAMS (long-run)
Fully autonomous auto-assign + auto-rebalance · predictive traffic/delay learning (`route_observations`
Phase 2) · customer ETA portal · multi-tenant scale features.

## Sequencing note
NOW first (cockpit shell + explainability v1) delivers the "intelligent, transparent, professional"
feel using mostly what we already have. Big builds (route map dashboard, recommendation engine,
analytics) wait for real PureWater usage so we build them right.
