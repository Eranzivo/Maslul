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

suite('strategy truth table (locks refactor intent)', () => {
  // far_to_near: a "before" task that is nearer (higher idx) than the new one is illegal
  check('FTN before-nearer illegal', ctx.isPairOrdered('far_to_near', /*earlier*/2, /*later=new*/1) === false);
  // far_to_near: an "after" task that is farther (lower idx) than the new one is illegal
  check('FTN after-farther illegal', ctx.isPairOrdered('far_to_near', /*earlier=new*/1, /*later*/0) === false);
  // nearest_first mirrors
  check('NF before-farther illegal', ctx.isPairOrdered('nearest_first', 0, 1) === false);
  check('NF after-nearer illegal', ctx.isPairOrdered('nearest_first', 1, 2) === false);
});

suite('splitLockedFlexible', () => {
  const day = [
    {id:1, city:'a', locked:true},
    {id:2, city:'b'},
    {id:3, city:'c', locked:false},
    {id:4, city:'d', locked:true},
  ];
  const r = ctx.splitLockedFlexible(day);
  check('locked picks only truthy locked', r.locked.map(t=>t.id).join(',') === '1,4');
  check('flexible is the rest', r.flexible.map(t=>t.id).join(',') === '2,3');
  check('empty input → empty arrays', JSON.stringify(ctx.splitLockedFlexible([])) === '{"locked":[],"flexible":[]}');
});

suite('usesZones', () => {
  check('absent config → true (zone default)', ctx.usesZones({}) === true);
  check('undefined → true', ctx.usesZones(undefined) === true);
  check('mode zone → true', ctx.usesZones({mode:'zone'}) === true);
  check('mode open → false', ctx.usesZones({mode:'open'}) === false);
  check('mode radius → false', ctx.usesZones({mode:'radius'}) === false);
});

suite('buildSequencePayload', () => {
  const tasks=[
    {id:1, city:'א', street:'הרצל 1', time:'09:00', windowStart:'08:00', windowEnd:'11:00', locked:true,  catId:null, lat:32.1, lon:34.8},
    {id:2, city:'ב', time:'',      windowStart:'',      windowEnd:'',      locked:false, catId:null},
  ];
  const p = ctx.buildSequencePayload(tasks, t=>30);
  check('locked carries scheduled_time', p[0].locked===true && p[0].scheduled_time==='09:00');
  check('windows map to snake_case', p[0].window_start==='08:00' && p[0].window_end==='11:00');
  check('empty window → null', p[1].window_start===null && p[1].window_end===null);
  check('duration from resolver', p[0].duration_minutes===30);
  check('ids stringified + coords carried', p[0].id==='1' && p[0].lat===32.1);
});

suite('applySequenceResult (epoch guard)', () => {
  const tasks=[{id:'1',time:'07:00',locked:false},{id:'2',time:'08:00',locked:false}];
  const res={ordered_tasks:['2','1'],estimated_times:{'1':'10:00','2':'07:30'},dropped_tasks:[]};
  const out = ctx.applySequenceResult(tasks,res, /*sentEpoch*/3, /*currentEpoch*/3);
  check('applies times when epoch matches', out.applied===true && tasks[0].time==='10:00' && tasks[1].time==='07:30');
  const out2 = ctx.applySequenceResult(tasks,{...res,estimated_times:{'1':'12:00','2':'12:30'}}, 3, /*newer*/4);
  check('stale epoch discarded', out2.applied===false && tasks[0].time==='10:00');
  const out3 = ctx.applySequenceResult(tasks,{...res,dropped_tasks:['2']}, 5, 5);
  check('dropped ids surfaced', out3.dropped.length===1 && out3.dropped[0]==='2');
  const lockedTasks=[{id:'9',time:'09:00',locked:true}];
  ctx.applySequenceResult(lockedTasks,{estimated_times:{'9':'11:00'},dropped_tasks:[]},1,1);
  check('locked task time never moved', lockedTasks[0].time==='09:00');
});

suite('balanceAdjust', () => {
  // candidate A: day already has 3 tasks (partial) → bonus; candidate B: empty day later → penalty
  check('partial day beats empty later day',
    ctx.balanceAdjust({enabled:true,weight:50}, {dayLoad:3, dateOffset:0}) >
    ctx.balanceAdjust({enabled:true,weight:50}, {dayLoad:0, dateOffset:4}));
  check('disabled → 0', ctx.balanceAdjust({enabled:false,weight:50}, {dayLoad:3, dateOffset:0}) === 0);
  check('absent config → 0', ctx.balanceAdjust(undefined, {dayLoad:3, dateOffset:0}) === 0);
  check('empty today is neutral-ish vs empty far future',
    ctx.balanceAdjust({enabled:true,weight:50}, {dayLoad:0, dateOffset:0}) >
    ctx.balanceAdjust({enabled:true,weight:50}, {dayLoad:0, dateOffset:6}));
});

suite('rankGapFill', () => {
  const freed={techId:'T',date:'2026-06-15',time:'09:00',city:'באר שבע'};
  const pending=[
    {id:'a',status:'pending',city:'באר שבע'},
    {id:'b',status:'pending',city:'קריית שמונה'},
    {id:'c',status:'assigned',city:'באר שבע'},
    {id:'d',status:'pending',city:'דימונה'},
  ];
  const dist=(c1,c2)=>c1===c2?0:(c1==='דימונה'||c2==='דימונה')?40:300;
  const ranked=ctx.rankGapFill(freed,pending,dist);
  check('same-city pending ranks first', ranked[0]&&ranked[0].id==='a');
  check('nearby city second', ranked[1]&&ranked[1].id==='d');
  check('non-pending excluded', !ranked.some(t=>t.id==='c'));
  check('caps at 5', ctx.rankGapFill(freed,Array.from({length:9},(_,i)=>({id:i,status:'pending',city:'x'})),()=>1).length===5);
});

console.log(`\n${passed} passed, ${failed} failed`);
process.exit(failed ? 1 : 0);
