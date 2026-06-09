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

console.log(`\n${passed} passed, ${failed} failed`);
process.exit(failed ? 1 : 0);
