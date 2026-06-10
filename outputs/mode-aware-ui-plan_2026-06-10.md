# Mode-Aware UI — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make dispatch & settings UI adapt to `scheduling.mode` so non-zone tenants (`open`/`radius`) never see zone concepts, while zone tenants (PureWater) stay byte-identical.

**Architecture:** One pure predicate `usesZones()`. Static DOM hidden via a body `data-zone-mode` attribute + `.zone-only` CSS class; behavior branched with `usesZones()` guards. A wizard mode-picker writes `config.scheduling.mode`.

**Tech Stack:** Single-file `index.html` (vanilla JS, no build); dependency-free Node harness in `tests/`.

**Source spec:** `outputs/mode-aware-ui-design_2026-06-10.md`.

**Conventions:** Never touch prod DB. Run tests with plain `node`. Living-docs task is mandatory. PureWater (`mode` absent or `'zone'`) MUST look identical to today — verify after every task.

**Spec deviation (intentional):** Spec surface #4 (tech-card "🔄 רוטציה" chip) lives only in the **admin cross-tenant panel** ([index.html:3889]) — an informational status chip for Eran across all tenants, not a per-tenant zone UI. Leaving it as-is. All other surfaces implemented.

---

## File Structure

| File | Change |
|---|---|
| `index.html` | `usesZones()` helper (sched-logic block); `.zone-only` CSS; `data-zone-mode` in `applyLabels`; tag nav/mobile/rotation DOM; guards in `saveTech`/`checkSpecificDate`/`showNoResult`/`findNextSlot`/batch-import; wizard mode-picker + config wiring | Modify |
| `tests/sched.test.js` | `usesZones()` unit tests | Modify |
| `context/architecture.md`, `context/scheduling-rules.md`, `context/zones-polygons.md` | living-docs | Modify |

---

## Task 1: `usesZones()` predicate + tests

**Files:** Modify `index.html` (inside existing `// <sched-logic>` block); `tests/sched.test.js`

- [ ] **Step 1: Write the failing test** — append to `tests/sched.test.js` before the final `console.log`:

```js
suite('usesZones', () => {
  check('absent config → true (zone default)', ctx.usesZones({}) === true);
  check('undefined → true', ctx.usesZones(undefined) === true);
  check('mode zone → true', ctx.usesZones({mode:'zone'}) === true);
  check('mode open → false', ctx.usesZones({mode:'open'}) === false);
  check('mode radius → false', ctx.usesZones({mode:'radius'}) === false);
});
```

- [ ] **Step 2: Run to verify it fails**

Run: `node tests/sched.test.js`
Expected: FAIL — `ctx.usesZones is not a function` (harness throws).

- [ ] **Step 3: Add the helper** inside the `// <sched-logic>` … `// </sched-logic>` block (before the closing marker). NOTE: the test passes `sc` (the scheduling object) directly, so the pure helper takes `sc`:

```js
// True when this tenant uses zones (mode 'zone' or absent). open/radius ⇒ no zones.
function usesZones(sc){ return ((sc && sc.mode) || 'zone') === 'zone'; }
```

- [ ] **Step 4: Run to verify it passes**

Run: `node tests/sched.test.js`
Expected: PASS — `24 passed, 0 failed`.

- [ ] **Step 5: Add the app-level wrapper** (the DOM/behavior code calls it with no args, reading the live config). Immediately AFTER the `// </sched-logic>` closing marker line, add:

```js
function appUsesZones(){ return usesZones(tenantConfig && tenantConfig.scheduling); }
```

- [ ] **Step 6: Commit**

```bash
git add index.html tests/sched.test.js
git commit -m "feat(mode-ui): usesZones() predicate + appUsesZones wrapper + tests"
```

---

## Task 2: Static-DOM gating (CSS + body attribute + tag elements)

**Files:** Modify `index.html` — `<style>` block, `applyLabels` (line ~1880), nav (678), mobile menu (7604), rotation block (1393)

- [ ] **Step 1: Add the CSS rule.** In the `<style>` block, after the `:root{…}` variables (right before the first non-`:root` rule), add:

```css
body[data-zone-mode="none"] .zone-only{ display:none !important; }
```

- [ ] **Step 2: Set the attribute on every tenant/config load.** In `applyLabels()` (line 1880), add a line at the end of the function, just before its closing `}`:

```js
function applyLabels(){
  document.querySelectorAll('[data-label]').forEach(el=>{
    const v=L(el.dataset.label);if(v)el.textContent=v;
  });
  document.body.dataset.zoneMode = appUsesZones() ? 'zone' : 'none';
}
```
(`applyLabels` already runs on tenant load + switch at lines 3137, 4013, 4034 — no new call sites needed.)

- [ ] **Step 3: Tag the desktop nav zones item.** Change line 678 — add `zone-only` to its class list:

```html
    <button id="nav-zones" class="ni-btn zone-only" onclick="goPage('zones')">
```
(keep the rest of the `<button>` line unchanged)

- [ ] **Step 4: Tag the mobile menu zones item.** Change line 7604 — add `zone-only`:

```html
  <button class="mob-sheet-item zone-only" onclick="closeMobMore();goPage('zones')"><span>🗺️</span><span data-label="zones">אזורים</span></button>
```

- [ ] **Step 5: Tag the tech-modal rotation block.** Change the rotation `<div class="fg">` (line 1393) to add `zone-only`:

```html
    <div class="fg zone-only">
      <label class="fl"><span class="req">*</span> רוטציה אזורים (ראשון–שישי)</label>
      <div class="field-error hidden" id="e-ti-rotation">יש להגדיר לפחות יום אחד</div>
      <div class="rotation-grid" id="ti-rotation"></div>
    </div>
```

- [ ] **Step 6: Manual verify.** Load the app as PureWater (zone) — nav "אזורים", mobile menu, and the tech-modal rotation grid all still show (identical to today). The tests don't cover DOM; this is a visual check.

- [ ] **Step 7: Commit**

```bash
git add index.html
git commit -m "feat(mode-ui): data-zone-mode body attr + .zone-only gating on nav/mobile/rotation"
```

---

## Task 3: Behavior guards — saveTech rotation requirement + checkSpecificDate

**Files:** Modify `index.html` — `saveTech` (line 6371), `checkSpecificDate` (line 5269)

- [ ] **Step 1: Guard the rotation requirement in `saveTech`.** Current (lines 6370–6372):

```js
  for(let i=0;i<6;i++){rotation[i]=document.getElementById('rot-'+i)?.value||'';if(rotation[i])hasRot=true;}
  if(!hasRot){document.getElementById('e-ti-rotation').classList.remove('hidden');valid=false;}
  else document.getElementById('e-ti-rotation').classList.add('hidden');
```

Replace the `if(!hasRot)` line so the requirement only applies in zone mode:

```js
  for(let i=0;i<6;i++){rotation[i]=document.getElementById('rot-'+i)?.value||'';if(rotation[i])hasRot=true;}
  if(appUsesZones() && !hasRot){document.getElementById('e-ti-rotation').classList.remove('hidden');valid=false;}
  else document.getElementById('e-ti-rotation').classList.add('hidden');
```

- [ ] **Step 2: Guard the zone gate in `checkSpecificDate`.** Current (line 5269):

```js
    if(!isCityInTechZone(tech,city,dateStr))continue;
```

Replace so the zone gate only filters in zone mode:

```js
    if(appUsesZones() && !isCityInTechZone(tech,city,dateStr))continue;
```

- [ ] **Step 3: Manual verify.** As PureWater: saving a tech with no rotation still shows the "יש להגדיר לפחות יום אחד" error (unchanged). (Non-zone path verified in Task 6 after a tenant can be created as `open`.)

- [ ] **Step 4: Commit**

```bash
git add index.html
git commit -m "feat(mode-ui): gate saveTech rotation requirement + checkSpecificDate zone filter on appUsesZones"
```

---

## Task 4: Mode-aware dispatch copy — showNoResult + findNextSlot

**Files:** Modify `index.html` — `showNoResult` (line 5296), `findNextSlot` (line 5261)

- [ ] **Step 1: Branch the no-result copy.** In `showNoResult`, the `else` branch (lines 5296–5299) is zone-specific. Replace it:

```js
  } else { // city_not_in_zone (or undefined → treat as city-not-in-zone)
    msg=`העיר "${h(city||'')}" אינה משויכת לאף אזור עם ${L('worker')} זמין.`;
    cta=`<button class="btn btn-blue btn-sm" onclick="goPage('zones')" style="margin-top:8px;">➕ שייך עיר לאזור</button>`;
  }
```

with:

```js
  } else if(!appUsesZones()){ // non-zone tenant — no zone concepts
    msg=`לא נמצא ${L('worker')} פנוי מתאים. בדוק זמינות ועומס של הצוות.`;
  } else { // city_not_in_zone (or undefined → treat as city-not-in-zone)
    msg=`העיר "${h(city||'')}" אינה משויכת לאף אזור עם ${L('worker')} זמין.`;
    cta=`<button class="btn btn-blue btn-sm" onclick="goPage('zones')" style="margin-top:8px;">➕ שייך עיר לאזור</button>`;
  }
```

- [ ] **Step 2: Branch the findNextSlot copy.** Current (line 5261):

```js
  if(currentCandidateIdx>=allCandidates.length){alert('אין עוד מועדים. בדוק הגדרות אזורים.');currentCandidateIdx=allCandidates.length-1;return;}
```

Replace:

```js
  if(currentCandidateIdx>=allCandidates.length){alert(appUsesZones()?'אין עוד מועדים. בדוק הגדרות אזורים.':'אין עוד מועדים זמינים.');currentCandidateIdx=allCandidates.length-1;return;}
```

- [ ] **Step 3: Manual verify.** As PureWater, a city not in any zone still shows "אינה משויכת לאף אזור" with the "שייך עיר לאזור" button (unchanged).

- [ ] **Step 4: Commit**

```bash
git add index.html
git commit -m "feat(mode-ui): mode-aware dispatch copy in showNoResult + findNextSlot"
```

---

## Task 5: Mode-aware batch-import unmatched CTA

**Files:** Modify `index.html` — `runBulkImport` result line (5801)

- [ ] **Step 1: Branch the unmatched CTA.** Current (line 5801):

```js
  out.innerHTML=`✅ נוצרו ${made} קריאות.`+(unmatched.length?`<div style="color:var(--amber);margin-top:6px;"><strong>${unmatched.length} לא שובצו:</strong><br>${unmatched.map(h).join('<br>')}<br><button class="btn btn-blue btn-sm" style="margin-top:6px;" onclick="goPage('zones')">תקן אזורים</button></div>`:'');
```

Replace (zone CTA only in zone mode):

```js
  const _unmCta = appUsesZones() ? `<br><button class="btn btn-blue btn-sm" style="margin-top:6px;" onclick="goPage('zones')">תקן אזורים</button>` : '';
  out.innerHTML=`✅ נוצרו ${made} קריאות.`+(unmatched.length?`<div style="color:var(--amber);margin-top:6px;"><strong>${unmatched.length} לא שובצו:</strong><br>${unmatched.map(h).join('<br>')}${_unmCta}</div>`:'');
```

- [ ] **Step 2: Manual verify.** As PureWater, batch import with unmatched cities still shows the "תקן אזורים" button (unchanged).

- [ ] **Step 3: Commit**

```bash
git add index.html
git commit -m "feat(mode-ui): mode-aware batch-import unmatched CTA"
```

---

## Task 6: Wizard mode-picker + config wiring

**Files:** Modify `index.html` — wizard config step (line 1289), config build (line 3484)

- [ ] **Step 1: Add the mode-picker radios** before the route-strategy field. Replace:

```html
    <div class="fg">
      <label class="fl">🗺️ אסטרטגיית ניתוב גיאוגרפי</label>
```

with:

```html
    <div class="fg">
      <label class="fl">⚙️ מודל שיבוץ</label>
      <div style="display:grid;gap:8px;margin-top:8px;">
        <label class="wiz-type-opt"><input type="radio" name="wc-mode" value="zone" checked><span>🗺️ אזורים לטכנאי לפי יום — חלוקת שטח (ברירת מחדל)</span></label>
        <label class="wiz-type-opt"><input type="radio" name="wc-mode" value="open"><span>🔓 ללא אזורים — שיבוץ לפי עומס וזמינות</span></label>
        <label class="wiz-type-opt"><input type="radio" name="wc-mode" value="radius"><span>📍 הקרוב ביותר — הטכנאי הפנוי הקרוב</span></label>
      </div>
    </div>
    <div class="fg">
      <label class="fl">🗺️ אסטרטגיית ניתוב גיאוגרפי</label>
```

- [ ] **Step 2: Read the chosen mode in the config build.** Current `scheduling` line (3484):

```js
    scheduling:{mode:'zone',zone_strict:true,fill_first:true,route_logic:routeStrategy==='far_to_near',route_strategy:routeStrategy}
```

Replace `mode:'zone'` with the picked value:

```js
    scheduling:{mode:document.querySelector('input[name="wc-mode"]:checked')?.value||'zone',zone_strict:true,fill_first:true,route_logic:routeStrategy==='far_to_near',route_strategy:routeStrategy}
```

- [ ] **Step 3: Manual verify.** Open the onboarding wizard — the "מודל שיבוץ" picker shows with "אזורים" pre-selected (so a wizard run with defaults still creates a `zone` tenant, unchanged). Selecting "ללא אזורים" and creating writes `scheduling.mode='open'`; that tenant then shows no zone UI (Tasks 2–5). Note: `open` mode ignores rotation, so collecting it in the wizard is harmless.

- [ ] **Step 4: Commit**

```bash
git add index.html
git commit -m "feat(mode-ui): wizard scheduling-mode picker (zone/open/radius) wired to config.scheduling.mode"
```

---

## Task 7: Living-docs sync

**Files:** Modify `context/architecture.md`, `context/scheduling-rules.md`, `context/zones-polygons.md`

- [ ] **Step 1: `context/architecture.md`** — add under the relevant UI/labels section:

> **Mode-aware UI:** `usesZones(sc)` (pure, in `// <sched-logic>`) + `appUsesZones()` wrapper. `applyLabels()` sets `document.body.dataset.zoneMode = 'zone'|'none'`; CSS `body[data-zone-mode="none"] .zone-only{display:none}` hides zone UI (nav, mobile menu, tech rotation grid). Behavior guards (`appUsesZones()`) in `saveTech` (rotation requirement), `checkSpecificDate`, `showNoResult`/`findNextSlot` copy, batch-import CTA. `open`/`radius` tenants see no zone concepts; absent/`zone` = unchanged.

- [ ] **Step 2: `context/scheduling-rules.md`** — under the two-axis zone model, add: "Zone UI (settings tab, rotation grid, city-in-zone gate, zone error copy) renders only when `mode='zone'` (`appUsesZones()`); `open`/`radius` tenants get address→auto-assign with no zone concepts. Wizard picks `mode` (zone/open/radius)."

- [ ] **Step 3: `context/zones-polygons.md`** — add a line: "The zones settings tab and tech rotation grid are gated by `appUsesZones()` — hidden for `open`/`radius` tenants."

- [ ] **Step 4: Commit**

```bash
git add context/architecture.md context/scheduling-rules.md context/zones-polygons.md
git commit -m "docs(mode-ui): document usesZones gating across UI + scheduling docs"
```

---

## Verification (whole plan)

1. `node tests/sched.test.js` → `24 passed, 0 failed`; `node tests/zones.test.js` → still passing.
2. **PureWater regression (most important):** load as PureWater — nav "אזורים", rotation grid, zone error copy, batch "תקן אזורים", saveTech rotation requirement all behave exactly as before (`data-zone-mode="zone"`).
3. **Non-zone path:** create a tenant via wizard with "ללא אזורים" → `scheduling.mode='open'`; load it → no "אזורים" nav, no rotation grid, tech saves without rotation, dispatch shows generic no-result copy, no zone CTAs (`data-zone-mode="none"`).

---

## Out of scope (logged in backlog)

Static-territory (zone-without-rotation), per-task constraints, variable windows, CRM structured fields. Plan B (auto-sequencing) is next.
