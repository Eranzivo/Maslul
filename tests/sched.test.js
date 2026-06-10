'use strict';
const fs = require('fs');
const vm = require('vm');
const path = require('path');

// ── Extract all // <sched-logic> … // </sched-logic> blocks from index.html ──
const html = fs.readFileSync(path.join(__dirname, '..', 'index.html'), 'utf8');
const re = /\/\/ <sched-logic>([\s\S]*?)\/\/ <\/sched-logic>/g;
let code = '', m;
while ((m = re.exec(html)) !== null) code += m[1] + '\n';
if (!code.trim()) { console.error('FAIL: no <sched-logic> blocks found'); process.exit(1); }

const ctx = {};
vm.createContext(ctx);
vm.runInContext(code, ctx);

let passed = 0, failed = 0;
function check(name, cond) { if (cond) { passed++; } else { failed++; console.error('  ✗ ' + name); } }
function suite(name, fn){ console.log('• ' + name); fn(); }

suite('resolveRouteStrategy', () => {
  check('absent config → flexible (safe default)', ctx.resolveRouteStrategy(undefined) === 'flexible');
  check('empty scheduling → flexible', ctx.resolveRouteStrategy({}) === 'flexible');
  check('explicit far_to_near honored', ctx.resolveRouteStrategy({route_strategy:'far_to_near'}) === 'far_to_near');
  check('explicit nearest_first honored', ctx.resolveRouteStrategy({route_strategy:'nearest_first'}) === 'nearest_first');
  check('legacy route_logic:true → far_to_near', ctx.resolveRouteStrategy({route_logic:true}) === 'far_to_near');
  check('legacy route_logic:false → flexible', ctx.resolveRouteStrategy({route_logic:false}) === 'flexible');
});

suite('isPairOrdered', () => {
  // index 0 = farthest from depot, higher index = nearer
  check('far_to_near: far(0) before near(2) OK', ctx.isPairOrdered('far_to_near',0,2) === true);
  check('far_to_near: near(2) before far(0) violates', ctx.isPairOrdered('far_to_near',2,0) === false);
  check('far_to_near: equal index OK', ctx.isPairOrdered('far_to_near',1,1) === true);
  check('nearest_first: near(2) before far(0) OK', ctx.isPairOrdered('nearest_first',2,0) === true);
  check('nearest_first: far(0) before near(2) violates', ctx.isPairOrdered('nearest_first',0,2) === false);
  check('flexible: any order OK', ctx.isPairOrdered('flexible',2,0) === true && ctx.isPairOrdered('flexible',0,2) === true);
});

console.log(`\n${passed} passed, ${failed} failed`);
process.exit(failed ? 1 : 0);
