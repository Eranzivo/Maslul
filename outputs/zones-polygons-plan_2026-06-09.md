# Zones & Polygons Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make zone definition and zone→tech matching reliable and per-tenant configurable (city-list now for PureWater, polygon as a config-ready seam), with a dev-only Node test harness as the safety net.

**Architecture:** Reuse the existing `scheduling.mode` axis (`zone`/`open`/`radius`) and add an orthogonal `scheduling.zone_match` (`city_list`/`polygon`). A single pure `resolveZone()` is the seam between zones and scheduling. Pure logic stays inline in `index.html` between `// <zone-logic>` markers; a zero-dependency Node harness extracts and tests it.

**Tech Stack:** Vanilla JS in single `index.html`, Supabase (PostgreSQL + RLS), Leaflet 1.9.4 + Leaflet.draw 1.0.4 (to be self-hosted), Node built-ins (`fs`, `vm`) for tests — no npm, no build step.

**Source docs:** Spec at `outputs/zones-polygons-design_2026-06-09.md`. Read it before starting.

---

## File Structure

| File | Responsibility | Action |
|---|---|---|
| `index.html` | App; pure zone logic inline between `// <zone-logic>` markers | Modify |
| `tests/zones.test.js` | Dev-only Node harness: extracts marked logic from `index.html`, runs assertions incl. tenant separation | Create |
| `outputs/migration-zones-polygons_2026-06-09.sql` | DB migration: `zones.polygons`, `technicians.blocked_zones` | Create |
| `.claude/commands/test-zones.md` | (Optional) command to run suite + review | Create |

**Convention note:** This repo keeps all JS inline in `index.html` (hard rule). The only new app-loaded change is comment markers + self-hosted Leaflet files in `vendor/`. `tests/` is dev-only and never loaded by the app.

---

## Task 0: Test harness scaffold + mark existing pure logic

**Files:**
- Create: `tests/zones.test.js`
- Modify: `index.html` — wrap existing `CITY_ALIASES`+`normalizeCity` ([:4515-4526](../index.html#L4515)), `CITY_COORDS_JS` ([:4852](../index.html#L4852)), `_pointInPolygon` ([:7260](../index.html#L7260)) in markers

- [ ] **Step 1: Add markers around existing pure logic in `index.html`**

Wrap each existing block. Before `const CITY_ALIASES={` add a line `// <zone-logic>` and after `function normalizeCity(...){...}` add `// </zone-logic>`. Do the same around `const CITY_COORDS_JS={...};` and around `function _pointInPolygon(lat, lon, polygon){...}`. Example for the aliases block:

```js
// <zone-logic>
const CITY_ALIASES={ /* …existing entries unchanged… */ };
function normalizeCity(city){if(!city)return city;return CITY_ALIASES[city.trim()]||city.trim();}
// </zone-logic>
```

- [ ] **Step 2: Write the harness with one trivial assertion**

Create `tests/zones.test.js`:

```js
'use strict';
const fs = require('fs');
const vm = require('vm');
const path = require('path');

// ── Extract all // <zone-logic> … // </zone-logic> blocks from index.html ──
const html = fs.readFileSync(path.join(__dirname, '..', 'index.html'), 'utf8');
const re = /\/\/ <zone-logic>([\s\S]*?)\/\/ <\/zone-logic>/g;
let code = '', m;
while ((m = re.exec(html)) !== null) code += m[1] + '\n';
if (!code.trim()) { console.error('FAIL: no <zone-logic> blocks found'); process.exit(1); }

const ctx = {};
vm.createContext(ctx);
vm.runInContext(code, ctx);

// ── Minimal assert runner ──
let passed = 0, failed = 0;
function check(name, cond) {
  if (cond) { passed++; }
  else { failed++; console.error('  ✗ ' + name); }
}
function suite(name, fn){ console.log('• ' + name); fn(); }

// ── Smoke test ──
suite('harness', () => {
  check('normalizeCity is extracted', typeof ctx.normalizeCity === 'function');
  check('normalizeCity collapses alias', ctx.normalizeCity('קריית גת') === 'קרית גת');
});

console.log(`\n${passed} passed, ${failed} failed`);
process.exit(failed ? 1 : 0);
```

- [ ] **Step 3: Run to verify the harness works**

Run: `node tests/zones.test.js`
Expected: `2 passed, 0 failed` (exit 0). If "no <zone-logic> blocks found", the markers in Step 1 are missing/mismatched.

- [ ] **Step 4: Commit**

```bash
git add tests/zones.test.js index.html
git commit -m "test: add dependency-free zone-logic harness + markers"
```

---

## Task 1: DB migration + `zone_match` config plumbing

**Files:**
- Create: `outputs/migration-zones-polygons_2026-06-09.sql`
- Modify: `index.html` — zone load mapper ([:2456](../index.html#L2456)), `saveZoneToSupabase` ([:2910](../index.html#L2910)), settings wiring ([:3534](../index.html#L3534))

- [ ] **Step 1: Write the migration SQL**

Create `outputs/migration-zones-polygons_2026-06-09.sql`:

```sql
-- Zones & Polygons foundation (additive, reversible)
-- Apply via Supabase SQL editor.

ALTER TABLE public.zones
  ADD COLUMN IF NOT EXISTS polygons JSONB;            -- array of [{lat,lng}, …] rings

-- Migrate existing single polygon → polygons[0]
UPDATE public.zones
  SET polygons = jsonb_build_array(polygon)
  WHERE polygon IS NOT NULL AND polygons IS NULL;

ALTER TABLE public.technicians
  ADD COLUMN IF NOT EXISTS blocked_zones TEXT[] NOT NULL DEFAULT '{}';

-- Verify
SELECT 'zones.polygons' AS col, count(*) FILTER (WHERE polygons IS NOT NULL) AS populated FROM public.zones
UNION ALL
SELECT 'tech.blocked_zones', count(*) FROM public.technicians WHERE array_length(blocked_zones,1) > 0;
```

Apply it in Supabase, confirm the verify query runs without error. **Do not drop `zones.polygon` yet** — kept one release as fallback.

- [ ] **Step 2: Load `polygons` + `blocked_zones` into memory**

In the zone load mapper ([:2456](../index.html#L2456)), change:

```js
id: z.id, name: z.name, cities: z.cities || [], polygons: z.polygons || (z.polygon ? [z.polygon] : []), polygon: z.polygon || null, _dbId: z.id
```

In the technician load mapper near `blocked:` ([:2427](../index.html#L2427)) add:

```js
blockedZones: t.blocked_zones || [],
```

- [ ] **Step 3: Persist `polygons` + `blocked_zones`**

In `saveZoneToSupabase` ([:2910](../index.html#L2910)) change the `dbUpsert` row to include polygons:

```js
const data = await dbUpsert('zones', { id: zone.id, name: zone.name, cities: zone.cities, polygons: zone.polygons || [], polygon: zone.polygon || null });
```

In the technician save row ([:2871](../index.html#L2871)) add alongside `blocked_cities`:

```js
blocked_zones: tech.blockedZones || [],
```

- [ ] **Step 4: Add the `zone_match` setting (super_admin)**

In the `#sec-scheduling` settings markup (the block containing `<select id="sched-mode">`), add directly after the mode row:

```html
<div class="fg" id="sched-row-zone-match">
  <label class="fl">הגדרת אזור (כשמצב = אזורים)</label>
  <select class="fc" id="sched-zone-match" onchange="saveSchedulingConfig()">
    <option value="city_list">רשימת ערים (ברירת מחדל)</option>
    <option value="polygon">פוליגון על המפה</option>
  </select>
</div>
```

In the settings-apply JS ([:3536](../index.html#L3536)) add after the mode line:

```js
const zm=document.getElementById('sched-zone-match');
if(zm)zm.value=sc.zone_match||'city_list';
```

And in the row-visibility list ([:3545](../index.html#L3545)) add `'sched-row-zone-match'` so it hides when `mode==='open'`:

```js
const zoneRows=['sched-row-zone-strict','sched-row-route-logic','sched-row-zone-match'];
```

Ensure `saveSchedulingConfig()` writes `tenantConfig.scheduling.zone_match` from `#sched-zone-match` (mirror how it persists `mode`). If `saveSchedulingConfig` doesn't exist, locate the existing scheduling-save handler and add the field there.

- [ ] **Step 5: Manual verify**

Open settings as super_admin → the new dropdown shows, defaults to "רשימת ערים", toggling mode to "פתוח" hides it. Reload → value persists.

- [ ] **Step 6: Commit**

```bash
git add index.html "outputs/migration-zones-polygons_2026-06-09.sql"
git commit -m "feat: zones.polygons + technicians.blocked_zones + zone_match config"
```

---

## Task 2: `canonicalCity()` — duplicate-spelling guard

**Files:**
- Modify: `index.html` — new logic inside a `// <zone-logic>` block near `normalizeCity`
- Test: `tests/zones.test.js`

- [ ] **Step 1: Write failing tests**

Add to `tests/zones.test.js` before the final summary:

```js
suite('canonicalCity', () => {
  // exact known city passes through
  check('known city unchanged', ctx.canonicalCity('קרית גת').city === 'קרית גת');
  // variant spelling collapses (rule-based)
  check('double-yud variant collapses', ctx.canonicalCity('קריית גת').city === 'קרית גת');
  // near-duplicate not in dict → suggestion offered
  const r = ctx.canonicalCity('קריית שמונהh');
  check('typo yields suggestion', r.suggestion === 'קרית שמונה' || r.suggestion === 'קריית שמונה');
  // unknown city → no suggestion, kept as typed (trimmed)
  check('unknown kept as-is', ctx.canonicalCity('  כפר דמיוני ').city === 'כפר דמיוני');
});
```

(Requires `קרית שמונה` to exist in `CITY_COORDS_JS`; if absent, add it in Step 3.)

- [ ] **Step 2: Run to verify failure**

Run: `node tests/zones.test.js`
Expected: FAIL — `✗ known city unchanged` etc. (`ctx.canonicalCity` is undefined).

- [ ] **Step 3: Implement `canonicalCity` + `levenshtein`**

Inside a `// <zone-logic>` block (place right after the `normalizeCity` block), add:

```js
// <zone-logic>
function levenshtein(a,b){
  const m=a.length,n=b.length;if(!m)return n;if(!n)return m;
  const d=Array.from({length:m+1},(_,i)=>[i,...Array(n).fill(0)]);
  for(let j=0;j<=n;j++)d[0][j]=j;
  for(let i=1;i<=m;i++)for(let j=1;j<=n;j++)
    d[i][j]=Math.min(d[i-1][j]+1,d[i][j-1]+1,d[i-1][j-1]+(a[i-1]===b[j-1]?0:1));
  return d[m][n];
}
// Returns {city, suggestion|null}. city = canonical/trimmed form to store.
// suggestion = a close known city when input isn't an exact match (caller prompts "did you mean").
function canonicalCity(input){
  if(!input)return{city:input,suggestion:null};
  let c=normalizeCity(input);                 // alias + trim
  c=c.replace(/קריית/g,'קרית').replace(/\s+/g,' ').trim(); // rule-based variant collapse
  if(CITY_COORDS_JS[c])return{city:c,suggestion:null};      // exact known
  let best=null,bestD=99;
  for(const known of Object.keys(CITY_COORDS_JS)){
    const dd=levenshtein(c,known);
    if(dd<bestD){bestD=dd;best=known;}
  }
  const thresh=c.length<=4?1:2;
  return{city:c,suggestion:(best&&bestD<=thresh&&bestD>0)?best:null};
}
// </zone-logic>
```

If `קרית שמונה` is missing from `CITY_COORDS_JS`, add `'קרית שמונה':[33.2074,35.5695],` inside that object (within its existing markers).

- [ ] **Step 4: Run to verify pass**

Run: `node tests/zones.test.js`
Expected: all `canonicalCity` checks pass.

- [ ] **Step 5: Commit**

```bash
git add index.html tests/zones.test.js
git commit -m "feat: canonicalCity guard against duplicate city spellings"
```

---

## Task 3: `resolveZone()` seam + tenant-separation tests

**Files:**
- Modify: `index.html` — new `// <zone-logic>` block; refactor `isCityInTechZone` ([:4579](../index.html#L4579)), `getCityZone` ([:4527](../index.html#L4527))
- Test: `tests/zones.test.js`

- [ ] **Step 1: Write failing tests (incl. tenant separation)**

Add to `tests/zones.test.js`:

```js
suite('resolveZone', () => {
  const zonesA = [{id:'z1',cities:['קרית גת','אשקלון'],polygons:[]}];
  const confCity = {scheduling:{mode:'zone',zone_match:'city_list'}};
  check('city in list → matched', ctx.resolveZone('קרית גת',null,null,confCity,zonesA).zoneId === 'z1');
  check('city absent → reason', ctx.resolveZone('חיפה',null,null,confCity,zonesA).reason === 'city_not_in_zone');

  // square polygon around (32.00..32.10 lat, 34.80..34.90 lng)
  const sq=[{lat:32.00,lng:34.80},{lat:32.10,lng:34.80},{lat:32.10,lng:34.90},{lat:32.00,lng:34.90}];
  const zonesB=[{id:'p1',cities:[],polygons:[sq]}];
  const confPoly={scheduling:{mode:'zone',zone_match:'polygon'}};
  check('point inside → matched', ctx.resolveZone('x',32.05,34.85,confPoly,zonesB).zoneId === 'p1');
  check('point outside → reason', ctx.resolveZone('x',31.00,34.00,confPoly,zonesB).reason === 'outside_all_polygons');
  check('polygon no coords → reason', ctx.resolveZone('x',null,null,confPoly,zonesB).reason === 'not_geocoded');
});

suite('tenant separation', () => {
  // Same input, two tenants with different configs, no shared state.
  const zones = [{id:'z1',cities:['חיפה'],polygons:[[{lat:32.0,lng:34.8},{lat:32.1,lng:34.8},{lat:32.1,lng:34.9},{lat:32.0,lng:34.9}]]}];
  const A = {scheduling:{mode:'zone',zone_match:'city_list'}};
  const B = {scheduling:{mode:'zone',zone_match:'polygon'}};
  check('Tenant A matches by city', ctx.resolveZone('חיפה',32.05,34.85,A,zones).matched === true);
  check('Tenant B matches by polygon', ctx.resolveZone('חיפה',32.05,34.85,B,zones).matched === true);
  check('Tenant B ignores city list', ctx.resolveZone('חיפה',31.0,34.0,B,zones).matched === false);
  check('Tenant A ignores coords', ctx.resolveZone('עיר אחרת',32.05,34.85,A,zones).matched === false);
});
```

- [ ] **Step 2: Run to verify failure**

Run: `node tests/zones.test.js`
Expected: FAIL — `ctx.resolveZone` undefined.

- [ ] **Step 3: Implement `resolveZone`**

Add a new `// <zone-logic>` block (place after `_pointInPolygon`'s block so it's defined; function hoisting makes order safe regardless):

```js
// <zone-logic>
// Single seam: which zone does a task belong to, given a tenant's config.
// zonesList passed explicitly for testability; app callers pass the global `zones`.
function resolveZone(city, lat, lon, conf, zonesList){
  const match=(conf&&conf.scheduling&&conf.scheduling.zone_match)||'city_list';
  const list=zonesList||[];
  if(match==='polygon'){
    if(lat==null||lon==null)return{zoneId:null,matched:false,reason:'not_geocoded'};
    const z=list.find(zz=>(zz.polygons||[]).some(p=>_pointInPolygon(lat,lon,p)));
    return z?{zoneId:z.id,matched:true,reason:null}
            :{zoneId:null,matched:false,reason:'outside_all_polygons'};
  }
  // city_list (default)
  const c=canonicalCity(city).city;
  const z=list.find(zz=>(zz.cities||[]).includes(c));
  return z?{zoneId:z.id,matched:true,reason:null}
          :{zoneId:null,matched:false,reason:'city_not_in_zone'};
}
// </zone-logic>
```

- [ ] **Step 4: Run to verify pass**

Run: `node tests/zones.test.js`
Expected: all `resolveZone` + `tenant separation` checks pass.

- [ ] **Step 5: Route existing matchers through `resolveZone`**

Rewrite `getCityZone` ([:4527](../index.html#L4527)) and `isCityInTechZone` ([:4579](../index.html#L4579)) to use the seam (app passes globals `tenantConfig`, `zones`):

```js
function getCityZone(city){const r=resolveZone(city,null,null,tenantConfig,zones);return r.zoneId?zones.find(z=>z.id===r.zoneId):null;}
function isCityInTechZone(tech,city,dateStr){
  const zid=getTechZoneId(tech,dateStr);if(!zid)return false;
  const r=resolveZone(city,null,null,tenantConfig,zones);
  return r.matched && r.zoneId===zid;
}
```

(City-list behavior is unchanged for PureWater; polygon mode will pass coords from callers in later tasks. For now coords are null → polygon tenants would return `not_geocoded`, which is correct until geocoding is wired.)

- [ ] **Step 6: Manual smoke**

Load app as PureWater (city_list). Dispatch a known in-zone city → still finds candidates. Dispatch an out-of-zone city → no candidates (unchanged behavior).

- [ ] **Step 7: Commit**

```bash
git add index.html tests/zones.test.js
git commit -m "feat: resolveZone seam (city_list + polygon) + tenant-separation tests"
```

---

## Task 4: Map reliability — self-host Leaflet + lazy fallback

**Files:**
- Create: `vendor/leaflet/*`, `vendor/leaflet-draw/*`
- Modify: `index.html` — head tags ([:18-22](../index.html#L18)), `_initZoneDrawMap` guard ([:7186](../index.html#L7186))

- [ ] **Step 1: Vendor the library files**

From the repo root (PowerShell), download pinned files:

```powershell
New-Item -ItemType Directory -Force vendor/leaflet, vendor/leaflet/images, vendor/leaflet-draw, vendor/leaflet-draw/images | Out-Null
$L='https://cdn.jsdelivr.net/npm/leaflet@1.9.4/dist'; $D='https://cdn.jsdelivr.net/npm/leaflet-draw@1.0.4/dist'
Invoke-WebRequest "$L/leaflet.js" -OutFile vendor/leaflet/leaflet.js
Invoke-WebRequest "$L/leaflet.css" -OutFile vendor/leaflet/leaflet.css
'layers.png','layers-2x.png','marker-icon.png','marker-icon-2x.png','marker-shadow.png' | % { Invoke-WebRequest "$L/images/$_" -OutFile "vendor/leaflet/images/$_" }
Invoke-WebRequest "$D/leaflet.draw.js" -OutFile vendor/leaflet-draw/leaflet.draw.js
Invoke-WebRequest "$D/leaflet.draw.css" -OutFile vendor/leaflet-draw/leaflet.draw.css
'spritesheet.png','spritesheet-2x.png','spritesheet.svg' | % { Invoke-WebRequest "$D/images/$_" -OutFile "vendor/leaflet-draw/images/$_" }
```

- [ ] **Step 2: Point the app at the vendored files**

Replace the four head tags ([:18-22](../index.html#L18)) with relative paths:

```html
<link rel="stylesheet" href="vendor/leaflet/leaflet.css"/>
<script src="vendor/leaflet/leaflet.js"></script>
<link rel="stylesheet" href="vendor/leaflet-draw/leaflet.draw.css"/>
<script src="vendor/leaflet-draw/leaflet.draw.js"></script>
```

Leaflet.css references `images/` relative to the CSS file → already satisfied by `vendor/leaflet/images/`. Same for leaflet.draw.css.

- [ ] **Step 3: Add lazy fallback so a missing lib self-heals instead of dead-ending**

Replace the guard in `_initZoneDrawMap` ([:7186-7190](../index.html#L7186)) with a loader:

```js
if (typeof window.L === 'undefined' || typeof L.map !== 'function') {
  const st = document.getElementById('zone-draw-status');
  if (st) st.textContent = 'טוען מפה…';
  return _lazyLoadLeaflet().then(ok => {
    if (ok) _initZoneDrawMap();
    else if (st) st.textContent = 'שגיאה בטעינת המפה — בדוק חיבור לרשת ונסה שוב.';
  });
}
```

Add the loader near the polygon section (not inside markers — it's not pure logic):

```js
let _leafletLoading=null;
function _lazyLoadLeaflet(){
  if(typeof L!=='undefined'&&L.map)return Promise.resolve(true);
  if(_leafletLoading)return _leafletLoading;
  _leafletLoading=new Promise(res=>{
    const s=document.createElement('script');
    s.src='vendor/leaflet/leaflet.js';
    s.onload=()=>{const d=document.createElement('script');d.src='vendor/leaflet-draw/leaflet.draw.js';d.onload=()=>res(true);d.onerror=()=>res(false);document.head.appendChild(d);};
    s.onerror=()=>res(false);
    document.head.appendChild(s);
  });
  return _leafletLoading;
}
```

- [ ] **Step 4: Manual verify (incl. forced failure)**

Push, load the app, open a zone's "🗺️ צייר" → map renders. Then in DevTools, block `vendor/leaflet/leaflet.js` (Network → block request URL), hard reload, open draw → status shows "טוען מפה…" then the lazy path (will still fail if truly blocked, but no permanent dead-end on a transient miss). Unblock → works.

- [ ] **Step 5: Commit**

```bash
git add vendor index.html
git commit -m "fix: self-host Leaflet + lazy fallback — kills the recurring map-load failure"
```

---

## Task 5: Zone authoring — canonical guard + bigger, redraw-safe map

**Files:**
- Modify: `index.html` — `addCities` ([:6324](../index.html#L6324)), draw modal markup ([:1722-1733](../index.html#L1722)), `confirmZoneDraw` ([:7280](../index.html#L7280))

- [ ] **Step 1: Run city adds through the canonical guard**

Replace `addCities` ([:6324](../index.html#L6324)):

```js
function addCities(zoneId){
  const inp=document.getElementById('new-city-'+zoneId);const text=inp.value.trim();if(!text)return;
  const z=zones.find(x=>x.id===zoneId);if(!z)return;
  text.split(/[\n,]+/).map(c=>c.trim()).filter(Boolean).forEach(raw=>{
    const {city,suggestion}=canonicalCity(raw);
    let toAdd=city;
    if(suggestion&&suggestion!==city){
      toAdd=confirm(`"${raw}" אינה מזוהה. האם התכוונת ל"${suggestion}"?`)?suggestion:city;
    }
    if(!z.cities.includes(toAdd))z.cities.push(toAdd);
  });
  inp.value='';save();renderZones();populateCitySelect();saveZoneToSupabase(z);
}
```

- [ ] **Step 2: Enlarge the draw map + add fullscreen**

In the modal markup ([:1723](../index.html#L1723)) widen the box and map:

```html
<div class="mo-box" style="max-width:min(96vw,1000px);">
```
and ([:1726](../index.html#L1726)):
```html
<div id="zone-draw-map" style="height:min(70vh,620px);border-radius:var(--r-lg);overflow:hidden;border:1px solid var(--line);"></div>
```

After opening, `invalidateSize` already runs ([:7237](../index.html#L7237)) so the larger container lays out correctly.

- [ ] **Step 3: Persist `polygons[]` on confirm (multi-disjoint ready)**

In `confirmZoneDraw` ([:7280](../index.html#L7280)), where it currently sets `z.polygon`, also write the array form and keep the single for fallback:

```js
const ring = _drawnPolygon.map(p => ({ lat: p.lat, lng: p.lng }));
z.polygon = ring;
z.polygons = [ring];   // exclusive zones: one drawn area replaces; multi-disjoint editing is a later enhancement
```

Ensure the following `saveZoneToSupabase(z)` is `await`ed and shows a toast on completion (it routes through WAL-backed `dbUpsert`).

- [ ] **Step 4: Manual verify**

Add a city typed as "קריית גת" → prompt offers "קרית גת" → accept → stored canonical. Draw a polygon → cities captured → reload → `zone.polygons` persisted and map redraw replaces cleanly.

- [ ] **Step 5: Commit**

```bash
git add index.html
git commit -m "feat: canonical guard on city add + larger redraw-safe zone map + polygons[]"
```

---

## Task 6: Technician zone exclusions (`blocked_zones`)

**Files:**
- Modify: `index.html` — tech edit markup ([:1400](../index.html#L1400)), tech load/save mappers ([:2427](../index.html#L2427),[:2871](../index.html#L2871)) (load/save done in Task 1), candidate filter ([:4750](../index.html#L4750))

- [ ] **Step 1: Filter excluded techs in zone strategy**

In `_candidatesZone` ([:4750](../index.html#L4750)), right after the `isCityInTechZone` check, add:

```js
const _zid=getTechZoneId(tech,date.str);
if((tech.blockedZones||[]).includes(_zid))continue;
```

- [ ] **Step 2: Add the exclusions UI in the tech drawer**

After the blocked-cities field ([:1400](../index.html#L1400)) add a zone multi-select:

```html
<div class="fg"><label class="fl">אזורים חסומים</label>
  <select class="fc" id="ti-blocked-zones" multiple size="4"></select>
</div>
```

Where the tech drawer is populated (where `ti-blocked` is set from `tech.blocked`), populate options + selection:

```js
const bz=document.getElementById('ti-blocked-zones');
if(bz){bz.innerHTML=zones.map(z=>`<option value="${z.id}">${h(z.name)}</option>`).join('');
  Array.from(bz.options).forEach(o=>o.selected=(tech.blockedZones||[]).includes(o.value));}
```

Where the tech form is read on save (where `blocked` is read from `ti-blocked`), add:

```js
const bzEl=document.getElementById('ti-blocked-zones');
tech.blockedZones=bzEl?Array.from(bzEl.selectedOptions).map(o=>o.value):[];
```

- [ ] **Step 3: Manual verify**

Edit a tech, block their rotation zone for a given day, save, reload. Dispatch a city in that zone on that day → that tech is not offered; others still are.

- [ ] **Step 4: Commit**

```bash
git add index.html
git commit -m "feat: per-tech blocked_zones excludes wrong-zone calls"
```

---

## Task 7: No-match UX — mode-aware block + fix-it CTA

**Files:**
- Modify: `index.html` — `findBestSlot` ([:5124](../index.html#L5124)), `showNoResult` ([:5166](../index.html#L5166))

- [ ] **Step 1: Pass the resolve reason into the no-result view**

In `findBestSlot` ([:5131-5133](../index.html#L5131)), compute the reason when there are no candidates:

```js
allCandidates=buildCandidates(city,catId);
currentCandidateIdx=0;selectedTimeSlot=null;
if(!allCandidates.length){
  const r=resolveZone(city,_pendingGeocode?.lat??null,_pendingGeocode?.lon??null,tenantConfig,zones);
  showNoResult(city,r.reason);return;
}
```

- [ ] **Step 2: Make `showNoResult` mode-aware with a CTA**

Replace `showNoResult` ([:5166](../index.html#L5166)):

```js
function showNoResult(city,reason){
  document.getElementById('dispatch-search-card').style.opacity='0.5';
  document.getElementById('dispatch-search-card').style.pointerEvents='none';
  document.getElementById('dispatch-result').classList.remove('hidden');
  const a=document.getElementById('d-alert');a.className='alert alert-amber';
  let msg,cta;
  if(reason==='outside_all_polygons'){msg=`הכתובת מחוץ לאזור השירות.`;cta=`<button class="btn btn-blue btn-sm" onclick="goPage('zones')" style="margin-top:8px;">🗺️ ערוך אזור על המפה</button>`;}
  else if(reason==='not_geocoded'){msg=`לא ניתן לאתר את הכתובת — בדוק רחוב ועיר.`;cta='';}
  else{msg=`העיר "${h(city)}" אינה משויכת לאף אזור.`;cta=`<button class="btn btn-blue btn-sm" onclick="goPage('zones')" style="margin-top:8px;">➕ שייך עיר לאזור</button>`;}
  a.innerHTML=`⚠️ ${msg} ${cta}`;a.classList.remove('hidden');
  document.getElementById('suggestion-card').innerHTML='';
}
```

- [ ] **Step 3: Manual verify**

PureWater: dispatch a city not in any zone → amber message names the city + "שייך עיר לאזור" button jumps to zones page. (Polygon-mode messages verified when a polygon tenant exists.)

- [ ] **Step 4: Commit**

```bash
git add index.html
git commit -m "feat: mode-aware no-match block with one-click fix-it CTA"
```

---

## Task 8: Bulk task import

**Files:**
- Modify: `index.html` — add a modal + `openBulkImport`/`runBulkImport`; reuse `resolveZone`, `canonicalCity`, `dbInsert`

- [ ] **Step 1: Add the bulk-import modal markup**

Near the other modals (after `mo-zone-draw`, [:1733](../index.html#L1733)) add:

```html
<div class="mo hidden" id="mo-bulk-import">
  <div class="mo-box" style="max-width:min(92vw,760px);">
    <div class="mo-title">ייבוא קריאות מרובה</div>
    <div style="font-size:0.8rem;color:var(--ink-3);margin-bottom:8px;">שורה לכל קריאה: <strong>רחוב, עיר</strong> (קטגוריה אופציונלית בעמודה שלישית).</div>
    <textarea class="fc" id="bulk-rows" style="width:100%;height:200px;font-size:0.85rem;" placeholder="הרצל 10, קרית גת&#10;ויצמן 5, אשקלון"></textarea>
    <div id="bulk-result" style="margin-top:10px;font-size:0.85rem;"></div>
    <div class="mo-actions">
      <button class="btn btn-blue" style="flex:1;" onclick="runBulkImport()">ייבא</button>
      <button class="btn btn-outline" style="flex:1;" onclick="closeMo('mo-bulk-import')">סגור</button>
    </div>
  </div>
</div>
```

Add a trigger button on the tasks page (next to the existing add-task control): `<button class="btn btn-outline btn-sm" onclick="document.getElementById('mo-bulk-import').classList.remove('hidden')">⇪ ייבוא מרובה</button>`.

- [ ] **Step 2: Implement `runBulkImport`**

```js
async function runBulkImport(){
  const rows=document.getElementById('bulk-rows').value.split('\n').map(r=>r.trim()).filter(Boolean);
  const out=document.getElementById('bulk-result');
  let made=0;const unmatched=[];
  for(const row of rows){
    const parts=row.split(',').map(s=>s.trim());
    const street=parts[0]||'';const rawCity=parts[1]||parts[0]||'';
    const {city}=canonicalCity(rawCity);
    const r=resolveZone(city,null,null,tenantConfig,zones); // polygon tenants: geocode step added when that mode ships
    if(!r.matched){unmatched.push(`${row} — ${r.reason==='city_not_in_zone'?'עיר לא משויכת':'מחוץ לאזור'}`);continue;}
    const t={id:genClientId(),client:'',city,street,status:'pending'};
    const saved=await dbInsert('tasks',{tenant_id:currentTenantId,city,street,status:'pending'});
    if(saved){t._dbId=saved.id;tasks.push(t);made++;}else{unmatched.push(`${row} — שמירה נכשלה`);}
  }
  save();renderTasks();
  out.innerHTML=`✅ נוצרו ${made} קריאות.`+(unmatched.length?`<div style="color:var(--amber);margin-top:6px;"><strong>${unmatched.length} לא שובצו:</strong><br>${unmatched.map(h).join('<br>')}<br><button class="btn btn-blue btn-sm" style="margin-top:6px;" onclick="goPage('zones')">תקן אזורים</button></div>`:'');
}
```

- [ ] **Step 3: Manual verify**

Paste 3 rows where one city is outside all zones → 2 created, 1 listed under "לא שובצו" with a "תקן אזורים" button. Reload → the 2 tasks persist.

- [ ] **Step 4: Commit**

```bash
git add index.html
git commit -m "feat: bulk task import with zone resolution + unmatched tray"
```

---

## Task 9 (optional): `/test-zones` command

**Files:**
- Create: `.claude/commands/test-zones.md`

- [ ] **Step 1: Add the command**

```markdown
---
description: Run the zone-logic test suite and suggest improvements
---
Run `node tests/zones.test.js` and report pass/fail. Then review `tests/zones.test.js` against `outputs/zones-polygons-design_2026-06-09.md` section 10 and list any coverage gaps (missing tenant-separation cases, untested resolveZone reasons, canonicalCity edge cases) as concrete suggestions. Do not change code unless asked.
```

- [ ] **Step 2: Verify**

Run `/test-zones` → suite runs, suggestions printed. Commit:

```bash
git add .claude/commands/test-zones.md
git commit -m "chore: /test-zones command to run suite + suggest improvements"
```

---

## Self-Review Notes (verify before execution)

- **Spec coverage:** match modes (Task 1,3) · resolveZone seam (3) · no-overlap exclusive (3, single-ring write in 5) · canonical guard (2,5) · map reliability (4) · authoring (5) · tech exclusions (6) · no-match CTA (7) · bulk import (8) · tenant-separation tests (3) · living-docs harness (0) · migration (1). All spec sections mapped.
- **Polygon runtime (seam, light build):** `resolveZone` polygon branch is built + tested (Task 3); callers pass `null` coords until geocoding is wired for a polygon tenant — correct per spec §11.
- **Naming consistency:** `polygons` (array), `blockedZones` (in-memory) ↔ `blocked_zones` (DB), `canonicalCity().city/.suggestion`, `resolveZone(city,lat,lon,conf,zonesList)` used identically across tasks.
- **Deferred:** drop `zones.polygon` column — a later release after `polygons` is proven.
