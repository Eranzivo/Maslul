# Mode-Aware UI — Design Spec

> Date: 2026-06-10 · A slice between scheduling Plan A and Plan B.
> Status: design approved (scope + approach), pending spec review → implementation plan.

## Goal

Make the dispatch & settings UI **adapt to `scheduling.mode`** so a non-zone tenant (`open`/`radius`) never sees zone concepts — no zone dropdown, no "city must be in a zone" gate, no rotation grid, no zone-centric error copy — while zone tenants (PureWater) keep **today's exact behavior**. This is the first concrete step of the north star "the wizard is the per-tenant business-logic configurator" — the UI starts reading from config instead of being PureWater-shaped. (See [product-philosophy], [scheduling-engine-plan].)

**Scope (chosen):** support **no-zone** (`open`/`radius`: address → auto-assign) alongside today's **zone-rotation**. *Skip* static-territory (zone-without-rotation) for now. Includes a **wizard mode-picker** so a no-zone tenant can be created without SQL.

**Why now (before Plan B):** Plan B's auto-sequencing sits *on top of* assignment. The assignment UX must be coherent and mode-aware first, or we'd auto-sequence inside a UI that still assumes zones.

---

## 1. The mechanism — one predicate, two gating styles

**Single source of truth** (no new redundant config — derive from the mode already in `tenants.config`):
```js
function usesZones(){ return (tenantConfig.scheduling?.mode || 'zone') === 'zone'; }
```
`zone` ⇒ zones; `open`/`radius` ⇒ no zones; **absent ⇒ `zone` = today's behavior** (PureWater untouched).

**Two gating styles, by surface type:**
- **Static DOM** (nav item, mobile menu item, tech-card rotation chip, rotation grid) → on tenant load set a body attribute `document.body.dataset.zoneMode = usesZones() ? 'zone' : 'none'`, and tag those elements with class `zone-only`. One CSS rule hides them:
  ```css
  body[data-zone-mode="none"] .zone-only{ display:none !important; }
  ```
  Declarative, can't-miss, no per-render churn.
- **Behavior** (logic that must branch, not just hide) → explicit `usesZones()` guards.

`document.body.dataset.zoneMode` is (re)set wherever the tenant/config loads (e.g. after `loadTenantFromUser` / config apply) and on tenant switch (impersonation).

---

## 2. Surfaces & behavior changes

| # | Surface | Today (zone) | No-zone (`open`/`radius`) | Gating |
|---|---|---|---|---|
| 1 | Settings nav **אזורים** (`#nav-zones`) + mobile menu | shown | hidden | `.zone-only` |
| 2 | Tech modal **rotation grid** (`buildTechModalUI`, `rot-${i}`) | rendered | hidden | `.zone-only` |
| 3 | `saveTech` **requires rotation** (`hasRot` check) | blocks save w/o rotation | **skip requirement** | `if(usesZones())` guard ⚠️ *today this blocks creating a tech in non-zone mode* |
| 4 | Tech-card **🔄 רוטציה chip** (`renderTechs`) | shown | hidden | `.zone-only` (wrap chip) |
| 5 | Dispatch **no-result CTA** (`showNoResult`) | "שייך עיר לאזור" → zones page | generic: "לא נמצא טכנאי פנוי מתאים" — **no zone CTA** | `if(usesZones())` branch in copy |
| 6 | `findNextSlot` copy | "בדוק הגדרות אזורים" | "אין עוד מועדים זמינים" | `usesZones()` branch |
| 7 | `checkSpecificDate` (`isCityInTechZone` gate) | zone gate | **skip zone gate** when `!usesZones()` | `if(usesZones())` guard |
| 8 | Batch-import unmatched "תקן אזורים" CTA | zone CTA | generic unmatched copy | `usesZones()` branch |

The dispatch flow itself already works for `open`/`radius` — `buildCandidates` routes by mode to `_candidatesOpen`/`_candidatesRadius`. We are only making the *chrome* honest. The city input (`s-city`) is already free text + datalist (zone enforcement is engine-side, [index.html:3168]), so no change needed there for no-zone.

**No-zone dispatch result** reads naturally: address in → `buildCandidates` (open/radius) → `showCandidate` shows the assigned tech ("שובץ ל[הטכנאי הפנוי]"), with no zone language anywhere.

---

## 3. Wizard mode-picker

The onboarding wizard currently hardcodes `mode:'zone'` ([index.html:3481]). Add a small picker so a no-zone tenant is self-serve:

- A radio group `wc-mode`: **`zone`** (territories per tech per day — default, "מתאים לשירות שדה עם חלוקה לאזורים") · **`open`** (no zones, assign by availability/load — "כל טכנאי לכל אזור, שיבוץ לפי עומס") · **`radius`** (nearest available tech — "הטכנאי הפנוי הקרוב ביותר").
- On submit, write the chosen value to `config.scheduling.mode` (replacing the hardcoded `'zone'`).
- When `mode !== 'zone'`, the wizard **skips the rotation step** (no zones to rotate) — same `usesZones()` logic.

Framed as the first axis of the eventual full configurator; other axes (windows, route_strategy, durations, future CRM) remain config/onboarding for now.

---

## 4. Error handling

All mode-branched copy is generic + actionable Hebrew (no internal terms) per the principal error rule — e.g. no-zone no-result says what to do ("בדוק זמינות/עומס של הטכנאים") not "no zone". No raw errors. (See [error-messages-rule].)

---

## 5. Testing

- **Pure predicate** `usesZones()` → unit-tested in `tests/sched.test.js` (`// <sched-logic>`): `{}`/absent ⇒ true; `{mode:'zone'}` ⇒ true; `{mode:'open'}`/`{mode:'radius'}` ⇒ false.
- The DOM gating (CSS + `dataset.zoneMode`) and the per-surface guards are verified by **manual smoke**: load a `zone` tenant (PureWater) → everything identical to today; flip a test tenant to `open` → nav/rotation/chip hidden, tech saves without rotation, dispatch shows no zone copy.
- Regression guard: PureWater (`mode` absent or `zone`) must look byte-identical.

---

## 6. Backward compatibility & isolation

`mode` absent or `'zone'` ⇒ `usesZones()` true ⇒ **today's behavior exactly**. Every change is gated by the predicate; nothing else in the app is touched. PureWater is unaffected.

---

## 7. Documentation sync map

- `context/architecture.md` — `usesZones()` predicate + `data-zone-mode` gating convention.
- `context/scheduling-rules.md` — note that zone UI is mode-gated; `open`/`radius` skip zone concepts.
- `context/zones-polygons.md` — zone UI only renders in `mode='zone'`.
- `context/clients/purewater.md` — confirm `mode='zone'` (unchanged).
- Memory: links to [product-philosophy], [scheduling-engine-plan], [error-messages-rule].

---

## 8. Out of scope (logged elsewhere)

Static-territory (zone-without-rotation), per-task constraints, variable windows, CRM structured fields — all in `context/backlog.md`. Plan B (auto-sequencing) is the next workstream after this.
