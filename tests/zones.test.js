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

console.log(`\n${passed} passed, ${failed} failed`);
process.exit(failed ? 1 : 0);
