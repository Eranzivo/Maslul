# Israel (PureWater) Feedback — Triage & Roadmap Mapping (2026-06-14)

Three feedback docs from Israel after the demo. Every item below is mapped to a status and a
roadmap bucket. **Status legend:** ✅ engine already does it (validate only) · 🔧 exists but needs
change · 🆕 new work · 🎯 already our north-star (no new work, reinforces direction).

> **Headline:** the feedback is one coherent message — *Maslul should behave like an experienced
> dispatcher and present a dead-simple coordinator flow* (Search → pick a recommended slot →
> confirm → back home). The optimization stays behind the scenes. This validates our
> AI-dispatch-cockpit north-star and sharpens the **back-office / coordinator flow** as the priority.

## ⛓️ Architecture guardrail (non-negotiable)

**This is ALL PureWater feedback, not product law.** Everything below lands in one of two layers:

1. **The brain (generic engine)** — the shared decision logic: zone/region assignment, fill-first
   vs balance scoring, route_strategy physics, category durations, skills filter, per-category
   caps, window math. The brain gains *generic, config-driven capabilities* — never PureWater
   constants. Every new dimension defaults to **absent/OFF** so a tenant that doesn't set it is
   unaffected.
2. **PureWater config** (`tenants.config` + `technicians.*` + `zones`) — PureWater's *choices*:
   `route_strategy:far_to_near`, `balance:OFF` (fill-first), 9/day, 30/45-min durations, its 9
   zones + rotation, its skills, its category limits.

**Test for every item:** Clients #2–5 may have completely different regions, durations, skills,
caps, route logic, even a different `mode` — and **nothing breaks**, because their behavior is
*their* config against the *same* brain. If implementing a feedback item would hardcode a
PureWater value into the engine, it's being done wrong — make it a config knob instead.
(See memories `product-philosophy`, `far-to-near-tenant-specific`, `living-docs-sync`.)

---

## 🔴 Affects the current re-calc (decide now)

| # | Item | Status | Action |
|---|---|---|---|
| 1.5 / 2.3 / 2.7 | **Fill-first / consolidate one tech's day before opening another** | 🔧 | PureWater live config has `balance.enabled:true` (even-spread = the *opposite*). **Re-calc with balance OFF (fill-first).** Flip live config. |
| 1.3 / 1.11 / 2.7-alt | **Strict daily-region enforcement** (tech only gets calls in that day's region) | ✅ batch engine | `batch_schedule.py:251` already hard-blocks cross-region. Complaint is about the **live dispatch UI** (our guard is fail-soft warn) → 🔧 make it a hard block (#1.3-UI below). |
| 1.2 / 2.11 | **Remove North/South boundary logic** | ✅ batch engine | Batch engine uses pure rotation, no N/S. Re-calc already clean. UI/tech-form cleanup is separate (🆕). |
| 1.1 | **Durations: 30 min standard / 45 min package** | ✅ data | Cats already 30 min; package 45 min already documented. Re-calc honors per-category duration. Need a real 45-min "package" category in DB (🆕 minor). |

**Re-calc verdict:** only one parameter changes — **balance ON → OFF (fill-first)**. Region
enforcement, N/S removal, and durations are already correct in the batch engine. Re-running now.

---

## 🟢 NOW — coordinator flow redesign (the dominant theme)

Feedback #3 + items 1.4/1.6/1.7/1.9/1.10/2.5/2.6/2.9 all describe **one simplified flow**. This
becomes the headline of the UI/UX pass.

| # | Item | Status | Bucket |
|---|---|---|---|
| #3 | **Search → 3 recommendation cards → confirm.** Card = Day · Date · Time-window only. Hide tech/route/scores until *after* a card is picked. | 🆕 | NOW — new "schedule" screen |
| 1.4 | Show **one** best recommendation by default (not many dates at once) | 🔧 | NOW (current `showCandidate` shows multiple slots) |
| 1.6 | **"Find Another Date"** → next-best optimized option, then 3rd, … | 🆕 | NOW |
| 1.7 / 2.5 | **"Check Specific Date"** → run the same engine against a coordinator-chosen date; show that day's open windows calendar-style | 🆕 | NOW |
| 2.6 | After a recommendation, show the day's **existing jobs** (cities + windows) so the route makes sense | 🆕 | NOW |
| 1.9 / 2.9 | **"Scheduled ✓" → auto-return to home/search** (no lingering on the schedule page) | 🆕 | NOW (small, high-value) |
| 1.10 | **Home = technician names only**; click a tech → structured weekly view (days · windows · cities · addresses · service types · status) | 🔧 | NOW (replaces current task/city dashboard) |
| 1.8 / 2.8 | **Chronological ordering everywhere** (never 10:00 before 07:00) | 🔧 | NOW — partially fixed (weekly sort window-first); audit all views |
| 2.8 | **Calendar shows only confirmed/completed** — never drafts/temp/pending candidates | 🔧 | NOW — ties to the "candidates behind the scenes" principle |
| 1.11 / #3 | **Dispatcher philosophy** (intelligent routes, max utilization, no fragmentation, regional rules, profitability) | 🎯 | already north-star — see `ai-dispatcher-northstar` memory |

---

## 🟠 NEXT — scheduling-engine capabilities (new config dimensions)

| # | Item | Status | Notes |
|---|---|---|---|
| 2.1 | **Technician skills / service categories** — required field; engine filters techs by skill (not every tech does every job type) | 🆕 | New `technicians.skills[]` + candidate filter. Schema + engine + tech form. |
| 2.4 | **Per-category daily limits** (e.g. ≤2 service calls, ≤5 complex installs/day) | 🆕 | New `technicians.category_limits` + assigner guard. |
| 2.2 | **Rotation engine** — up to 5 weekly regions/tech; ensure variety (not same region all week); balance regional spread | 🔧 | Rotation exists (5 weekday slots). Add: variety enforcement + a real fix for under-covered busy zones (see TLV bottleneck below). |
| 2.10 / 2.11 | **Mandatory tech config + real boundary engine** — can't create a tech without regions, skills, hours, durations, max daily, categories; recommendations never exceed the defined operating range | 🔧/🆕 | Tech form validation + region-based (not N/S) boundary. |
| 2.12 | **Bulk region creation** — paste a list of 100 city names into a region at once | 🆕 | Zone authoring UX. Pairs with `canonicalCity` guard + `zones-polygons`. |
| 1.1 | **45-min "package" category** in DB | 🆕 | Add category row; durations already flow through engine. |

---

## 🧱 Structural finding surfaced by the re-calc (feeds 2.2)

Israel's own feedback (#2.2 rotation, #1.5 fill-first) is the fix for a real bottleneck:
the **תל אביב zone has ~27 calls but only 2 covering tech-days** in the current rotation
(בני Sun + אלירן Wed = 18 slots at 9/day). 27 > 18 ⇒ ≥9 calls overflow no matter the algorithm.
That is *why* the 108-task re-calc leaves ~19 pending under 9/9/9. **Fix = rotation coverage**
(give busy regions a 3rd covering day), not a scheduler tweak. Logged under NEXT #2.2.

---

## Queue changes applied
- `context/backlog.md` — NOW bucket reframed around the coordinator flow; NEXT items added
  (skills, category limits, rotation variety, mandatory tech fields, bulk region, 45-min category).
- `context/clients/purewater.md` — `balance.enabled` flagged for flip to OFF (fill-first per #1.5);
  change-log entry.
- Pending docs (when implemented): `context/scheduling-rules.md` (remove N/S boundary language;
  state strict daily-region rule), tech-form validation spec.
