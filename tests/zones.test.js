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
  check('normalizeCity returns a string', typeof ctx.normalizeCity('תל אביב') === 'string');
  check('CITY_COORDS_JS block extracted', /CITY_COORDS_JS\s*=/.test(code));
  check('_pointInPolygon block extracted', typeof ctx._pointInPolygon === 'function');
});

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

suite('resolveZone', () => {
  const zonesA = [{id:'z1',cities:['קרית גת','אשקלון'],polygons:[]}];
  const confCity = {scheduling:{mode:'zone',zone_match:'city_list'}};
  check('city in list → matched', ctx.resolveZone('קרית גת',null,null,confCity,zonesA).zoneId === 'z1');
  check('city absent → reason', ctx.resolveZone('חיפה',null,null,confCity,zonesA).reason === 'city_not_in_zone');
  // hardening: zone stored a VARIANT spelling, canonical input still matches (both sides canonicalized)
  check('zone stored variant still matches', ctx.resolveZone('קרית גת',null,null,confCity,[{id:'zz',cities:['קריית גת'],polygons:[]}]).zoneId === 'zz');

  const sq=[{lat:32.00,lng:34.80},{lat:32.10,lng:34.80},{lat:32.10,lng:34.90},{lat:32.00,lng:34.90}];
  const zonesB=[{id:'p1',cities:[],polygons:[sq]}];
  const confPoly={scheduling:{mode:'zone',zone_match:'polygon'}};
  check('point inside → matched', ctx.resolveZone('x',32.05,34.85,confPoly,zonesB).zoneId === 'p1');
  check('point outside → reason', ctx.resolveZone('x',31.00,34.00,confPoly,zonesB).reason === 'outside_all_polygons');
  check('polygon no coords → reason', ctx.resolveZone('x',null,null,confPoly,zonesB).reason === 'not_geocoded');
});

suite('tenant separation', () => {
  const zones = [{id:'z1',cities:['חיפה'],polygons:[[{lat:32.0,lng:34.8},{lat:32.1,lng:34.8},{lat:32.1,lng:34.9},{lat:32.0,lng:34.9}]]}];
  const A = {scheduling:{mode:'zone',zone_match:'city_list'}};
  const B = {scheduling:{mode:'zone',zone_match:'polygon'}};
  check('Tenant A matches by city', ctx.resolveZone('חיפה',32.05,34.85,A,zones).matched === true);
  check('Tenant B matches by polygon', ctx.resolveZone('חיפה',32.05,34.85,B,zones).matched === true);
  check('Tenant B ignores city list', ctx.resolveZone('חיפה',31.0,34.0,B,zones).matched === false);
  check('Tenant A ignores coords', ctx.resolveZone('עיר אחרת',32.05,34.85,A,zones).matched === false);
});

suite('isTenantWorkDay', () => {
  // absent config ⇒ today's behavior: Saturday(6) off, every other day on (back-compat)
  check('absent config → Sat off', ctx.isTenantWorkDay(6, {}) === false);
  check('absent config → Sun on', ctx.isTenantWorkDay(0, {}) === true);
  check('null config → Thu on', ctx.isTenantWorkDay(4, null) === true);
  // explicit Sun–Thu (PureWater)
  const pw = { defaults: { work_days: [0, 1, 2, 3, 4] } };
  check('Sun-Thu → Sun on', ctx.isTenantWorkDay(0, pw) === true);
  check('Sun-Thu → Thu on', ctx.isTenantWorkDay(4, pw) === true);
  check('Sun-Thu → Fri off', ctx.isTenantWorkDay(5, pw) === false);
  check('Sun-Thu → Sat off', ctx.isTenantWorkDay(6, pw) === false);
  // empty/garbage list ⇒ fall back to default (never "no working days")
  check('empty work_days → default Sat off', ctx.isTenantWorkDay(6, { defaults: { work_days: [] } }) === false);
  check('empty work_days → default Sun on', ctx.isTenantWorkDay(0, { defaults: { work_days: [] } }) === true);
});

suite('zoneDropDecision', () => {
  const strict = { zone_strict: true };
  const relaxed = { zone_strict: false };
  const relaxedNoGuard = { zone_strict: false, zone_drop_guard: false };
  // no cross-zone mismatch ⇒ always allow the placement
  check('no mismatch → allow (strict)', ctx.zoneDropDecision(strict, false) === 'allow');
  check('no mismatch → allow (relaxed)', ctx.zoneDropDecision(relaxed, false) === 'allow');
  // mismatch under zone_strict ⇒ HARD block (no override) — matches batch + dispatch search
  check('mismatch + strict → block', ctx.zoneDropDecision(strict, true) === 'block');
  check('mismatch + default(undefined strict) → block', ctx.zoneDropDecision({}, true) === 'block');
  check('mismatch + null sc → block (default strict)', ctx.zoneDropDecision(null, true) === 'block');
  // mismatch under relaxed (zone_strict:false) ⇒ soft warn (today's behavior)
  check('mismatch + relaxed → warn', ctx.zoneDropDecision(relaxed, true) === 'warn');
  // relaxed + guard explicitly off ⇒ opted out → allow
  check('mismatch + relaxed + guard off → allow', ctx.zoneDropDecision(relaxedNoGuard, true) === 'allow');
  // zone_strict DOMINATES the soft guard — a strict tenant can't be downgraded by guard:false
  check('strict beats guard-off → block', ctx.zoneDropDecision({ zone_strict: true, zone_drop_guard: false }, true) === 'block');
});

console.log(`\n${passed} passed, ${failed} failed`);
process.exit(failed ? 1 : 0);
