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

suite('reassignTask', () => {
  const t = {id:'7', techId:'A', date:'2026-06-07', time:'09:30', windowStart:'07:00', windowEnd:'10:00', status:'assigned'};
  const r = ctx.reassignTask(t, 'B', '2026-06-09');
  check('moves to new tech', r.techId === 'B');
  check('moves to new day', r.date === '2026-06-09');
  check('keeps the customer window', r.windowStart === '07:00' && r.windowEnd === '10:00');
  check('clears exact time for re-sequencing', r.time === '');
  check('original task untouched (pure)', t.techId === 'A' && t.date === '2026-06-07');
  const p = ctx.reassignTask({id:'9', status:'pending'}, 'C', '2026-06-10');
  check('placing a pending task makes it assigned', p.status === 'assigned');
  check('no window → empty window kept', p.windowStart === '' && p.windowEnd === '');
});

suite('layoutColumns', () => {
  const a = ctx.layoutColumns([{start:0,end:60},{start:60,end:120}]);
  check('non-overlapping share one column', a[0].cols===1 && a[1].cols===1 && a[0].col===0 && a[1].col===0);
  const b = ctx.layoutColumns([{start:0,end:120},{start:60,end:180}]);
  check('two overlapping → 2 cols, distinct', b[0].cols===2 && b[1].cols===2 && b[0].col!==b[1].col);
  const c = ctx.layoutColumns([{start:0,end:180},{start:60,end:240},{start:120,end:300}]);
  check('three mutually overlapping → 3 distinct cols', c.every(x=>x.cols===3) && new Set(c.map(x=>x.col)).size===3);
  const e = ctx.layoutColumns([{start:0,end:60},{start:0,end:120},{start:60,end:120}]);
  check('a freed column is reused (max 2 cols)', Math.max(...e.map(x=>x.cols))===2);
  check('returns one entry per input, order preserved', e.length===3 && e.every(x=>typeof x.col==='number'));
});

suite('windowAtOffset (daily-grid drag snapping)', () => {
  // Day 07:00–18:00, 3h windows → bands 07-10, 10-13, 13-16, 16-18.
  const w = (y) => ctx.windowAtOffset(y, 7, 18, 3);
  check('top of grid → first band 07:00–10:00', w(0).ws==='07:00' && w(0).we==='10:00');
  check('mid first band stays 07:00', w(90).ws==='07:00');
  check('start of second band (180px=10:00) → 10:00–13:00', w(180).ws==='10:00' && w(180).we==='13:00');
  check('third band (13:00) at 360px', w(360).ws==='13:00' && w(360).we==='16:00');
  check('last partial band clamps to 16:00–18:00', w(540).ws==='16:00' && w(540).we==='18:00');
  check('overshoot past end clamps into last band', w(99999).ws==='16:00' && w(99999).we==='18:00');
  check('negative offset clamps to first band', w(-50).ws==='07:00');
  check('topMins/heightMins reflect the band', w(180).topMins===180 && w(180).heightMins===180);
});


suite('placement policy: golden fixture (parity with backend resolve_placement_policy)', () => {
  const fs2 = require('fs'), path2 = require('path');
  const fx = JSON.parse(fs2.readFileSync(path2.join(__dirname, 'fixtures', 'policy-cases.json'), 'utf8'));
  for (const c of fx.cases) {
    check(`sc=${JSON.stringify(c.sc)} → ${c.expect}`, ctx.resolvePlacementPolicy(c.sc) === c.expect);
  }
  // score semantics: consolidate packs, spread splits, same-city nudges apart under spread
  check('consolidate: active day beats empty', ctx.placementScore('consolidate',3,3,0,50) > ctx.placementScore('consolidate',0,0,0,50));
  check('spread: least-loaded wins', ctx.placementScore('spread',0,0,0,50) > ctx.placementScore('spread',3,3,0,50));
  check('spread: same-city penalized', ctx.placementScore('spread',1,1,0,50) > ctx.placementScore('spread',1,1,3,50));
});


suite('preferred windows: golden fixture (parity with backend pref_allows_day/range)', () => {
  const fsW = require('fs'), pathW = require('path');
  const fx = JSON.parse(fsW.readFileSync(pathW.join(__dirname, 'fixtures', 'prefwindow-cases.json'), 'utf8'));
  for (const c of fx.day_cases) {
    check(`day: ${c.why}`, ctx.prefWindowAllowsDay(c.windows, c.dow) === c.allow);
  }
  for (const c of fx.range_cases) {
    check(`range: ${c.why}`, ctx.prefWindowAllowsRange(c.windows, c.dow, c.from_min, c.to_min) === c.allow);
  }
  check('mode: absent -> hard (availability is hard per handover s8)', ctx.resolvePrefWindowsMode({}) === 'hard');
  check('mode: soft honored', ctx.resolvePrefWindowsMode({preferred_windows_mode:'soft'}) === 'soft');
  check('mode: unknown -> hard', ctx.resolvePrefWindowsMode({preferred_windows_mode:'x'}) === 'hard');
  check('mode: null sc -> hard', ctx.resolvePrefWindowsMode(null) === 'hard');
});


suite('date constraints: golden fixture (parity with backend date_constraint_allows)', () => {
  const fsD = require('fs'), pathD = require('path');
  const fx = JSON.parse(fsD.readFileSync(pathD.join(__dirname, 'fixtures', 'datecons-cases.json'), 'utf8'));
  for (const c of fx.cases) {
    check(`datecons: ${c.why}`, ctx.dateConstraintAllows(c.cons, c.date) === c.allow);
  }
  check('datecons: null cons allows', ctx.dateConstraintAllows(null, '2026-07-12') === true);
});


suite('explainCandidate (dispatch "why this recommendation" copy)', () => {
  // Consolidation is the dominant score driver → it must lead the headline.
  const merge = ctx.explainCandidate({existingInZone:2, load:2, max:6, zoneName:'דרום', techName:'אלירן', mode:'zone', isEarliest:true, routeStrategy:'far_to_near'});
  check('existing calls → merge headline (⚡)', merge.headline.icon === '⚡' && /מצטרף ל-2/.test(merge.headline.text));
  check('merge headline names the zone', /דרום/.test(merge.headline.text));
  check('merge → consolidation benefit chip present', merge.chips.some(c=>/ניצול מיטבי/.test(c.text)));

  const fresh = ctx.explainCandidate({existingInZone:0, load:0, max:5, zoneName:'שפלה', techName:'בני', mode:'zone'});
  check('empty day → new-day headline (📅)', fresh.headline.icon === '📅' && /פותח יום/.test(fresh.headline.text));
  check('new day → NO consolidation benefit chip', !fresh.chips.some(c=>/ניצול מיטבי/.test(c.text)));

  // Zone-rotation chip explains WHY this tech is eligible — zone mode only.
  check('zone mode → rotation chip names tech', merge.chips.some(c=>/אלירן/.test(c.text) && /דרום/.test(c.text)));
  const open = ctx.explainCandidate({existingInZone:1, load:1, max:4, zoneName:'', techName:'X', mode:'open'});
  check('open mode → no zone rotation chip', !open.chips.some(c=>/משובץ/.test(c.text)));

  // Day headroom reflects load vs cap.
  check('room left → headroom chip counts remaining', merge.chips.some(c=>/עומס 2\/6/.test(c.text) && /נותר מקום ל-4/.test(c.text)));
  const full = ctx.explainCandidate({existingInZone:5, load:6, max:6, zoneName:'ז', techName:'ט', mode:'zone'});
  check('day full → "מתמלא" not a negative count', full.chips.some(c=>/עומס 6\/6/.test(c.text) && /מתמלא/.test(c.text)) && !full.chips.some(c=>/נותר מקום/.test(c.text)));

  // Optional signals appear only when true.
  check('isEarliest → earliest chip', merge.chips.some(c=>/המוקדם ביותר/.test(c.text)));
  check('not earliest → no earliest chip', !fresh.chips.some(c=>/המוקדם ביותר/.test(c.text)));
  check('windowFit true → customer-window chip', ctx.explainCandidate({existingInZone:1,load:1,max:3,windowFit:true,mode:'zone',zoneName:'ז',techName:'ט'}).chips.some(c=>/חלון הזמינות/.test(c.text)));
  check('windowFit null → no customer-window chip', !merge.chips.some(c=>/חלון הזמינות/.test(c.text)));
  check('far_to_near → route-order chip (רחוק→קרוב)', merge.chips.some(c=>/רחוק→קרוב/.test(c.text)));
  check('nearest_first → route-order chip (קרוב→רחוק)', ctx.explainCandidate({existingInZone:1,load:1,max:3,routeStrategy:'nearest_first',mode:'zone',zoneName:'ז',techName:'ט'}).chips.some(c=>/קרוב→רחוק/.test(c.text)));
  check('flexible → no route-order chip', !ctx.explainCandidate({existingInZone:1,load:1,max:3,routeStrategy:'flexible',mode:'zone',zoneName:'ז',techName:'ט'}).chips.some(c=>/רחוק→קרוב|קרוב→רחוק/.test(c.text)));

  // Robustness — never throws on an empty/degenerate bag.
  const empty = ctx.explainCandidate();
  check('undefined sig → still returns a headline', !!empty.headline && typeof empty.headline.text === 'string');
  check('undefined sig → headroom chip with 0/0', empty.chips.some(c=>/עומס 0\/0/.test(c.text)));
});

suite('describeConstraintsHe (per-call constraints read-out)', () => {
  // No constraints → both empty.
  const none = ctx.describeConstraintsHe({});
  check('empty task → no windows, no dates', none.windows === '' && none.dates === '');
  check('undefined task → safe empty', ctx.describeConstraintsHe().windows === '' && ctx.describeConstraintsHe().dates === '');

  // Windows: day-scoped and all-day.
  const w1 = ctx.describeConstraintsHe({preferredWindows:[{from:'09:00',to:'13:00',days:[0,2]}]});
  check('window with days → Hebrew day letters', w1.windows === '09:00–13:00 (א,ג)');
  const w2 = ctx.describeConstraintsHe({preferredWindows:[{from:'08:00',to:'11:00'}]});
  check('window without days → "כל יום"', w2.windows === '08:00–11:00 (כל יום)');
  const w3 = ctx.describeConstraintsHe({preferredWindows:[{from:'07:00',to:'10:00',days:[1]},{from:'15:00',to:'18:00',days:[4]}]});
  check('multiple windows joined with ·', w3.windows === '07:00–10:00 (ב) · 15:00–18:00 (ה)');
  check('window missing from/to is skipped', ctx.describeConstraintsHe({preferredWindows:[{days:[1]},{from:'09:00',to:'12:00'}]}).windows === '09:00–12:00 (כל יום)');
  check('days sorted before render', ctx.describeConstraintsHe({preferredWindows:[{from:'09:00',to:'13:00',days:[6,0,3]}]}).windows === '09:00–13:00 (א,ד,ש)');

  // Dates: fixed dominates; earliest/latest combine; TZ-safe formatting.
  check('fixed date → "בתאריך .. בלבד"', ctx.describeConstraintsHe({fixedDate:'2026-07-12'}).dates === 'בתאריך 12/07/2026 בלבד');
  check('fixed date ignores earliest/latest', ctx.describeConstraintsHe({fixedDate:'2026-07-12',earliestDate:'2026-07-01'}).dates === 'בתאריך 12/07/2026 בלבד');
  check('earliest only', ctx.describeConstraintsHe({earliestDate:'2026-07-05'}).dates === 'לא לפני 05/07/2026');
  check('latest only', ctx.describeConstraintsHe({latestDate:'2026-07-20'}).dates === 'לא אחרי 20/07/2026');
  check('earliest + latest joined', ctx.describeConstraintsHe({earliestDate:'2026-07-05',latestDate:'2026-07-20'}).dates === 'לא לפני 05/07/2026 · לא אחרי 20/07/2026');
  check('DMY formatting is TZ-safe (no Date parse, no day shift)', ctx._fmtDMY('2026-01-01') === '01/01/2026');
  check('malformed date passes through untouched', ctx._fmtDMY('soon') === 'soon');
});

suite('techCompleteness (mandatory tech gate #7)', () => {
  const full = {name:'אלירן',phone:'050',base:'אשקלון',return_city:'אשקלון',skills:['c1'],hasWorkDay:true,max:9,hasRotation:true};
  check('complete zone tech → ok, nothing missing', (()=>{const r=ctx.techCompleteness(full,true);return r.complete===true && r.missing.length===0;})());
  check('complete non-zone tech (rotation not required)', ctx.techCompleteness({...full,hasRotation:false},false).complete===true);
  // Each engine-critical field, individually missing, blocks:
  check('missing name blocks', ctx.techCompleteness({...full,name:''},true).missing.includes('name'));
  check('missing phone blocks', ctx.techCompleteness({...full,phone:'  '},true).missing.includes('phone'));
  check('missing base blocks', ctx.techCompleteness({...full,base:''},true).missing.includes('base'));
  check('missing return blocks', ctx.techCompleteness({...full,return_city:''},true).missing.includes('return'));
  check('no skills blocks', ctx.techCompleteness({...full,skills:[]},true).missing.includes('skills'));
  check('no work day blocks', ctx.techCompleteness({...full,hasWorkDay:false},true).missing.includes('hours'));
  check('max<1 blocks', ctx.techCompleteness({...full,max:0},true).missing.includes('max'));
  check('max NaN blocks', ctx.techCompleteness({...full,max:NaN},true).missing.includes('max'));
  check('max=1 is allowed', !ctx.techCompleteness({...full,max:1},true).missing.includes('max'));
  // Rotation is required ONLY for zone tenants:
  check('zone tenant missing rotation blocks', ctx.techCompleteness({...full,hasRotation:false},true).missing.includes('rotation'));
  check('non-zone tenant ignores rotation', !ctx.techCompleteness({...full,hasRotation:false},false).missing.includes('rotation'));
  // Robustness + ordering (missing[0] is the field the UI focuses first):
  check('empty bag → many missing, safe', ctx.techCompleteness({},true).complete===false);
  check('missing preserves field order (name first)', ctx.techCompleteness({},true).missing[0]==='name');
  check('undefined arg → not complete, no throw', ctx.techCompleteness().complete===false);
});

suite('overrideStamp (#4 manual-override audit fields)', () => {
  check('reason → overridden + reason set', (()=>{const s=ctx.overrideStamp('אין טכנאי אחר זמין');return s.manuallyOverridden===true && s.overrideReason==='אין טכנאי אחר זמין';})());
  check('reason trimmed', ctx.overrideStamp('  דחוף  ').overrideReason==='דחוף');
  check('empty reason → clean (flag cleared, null reason)', (()=>{const s=ctx.overrideStamp('');return s.manuallyOverridden===false && s.overrideReason===null;})());
  check('whitespace-only → clean', (()=>{const s=ctx.overrideStamp('   ');return s.manuallyOverridden===false && s.overrideReason===null;})());
  check('null → clean', (()=>{const s=ctx.overrideStamp(null);return s.manuallyOverridden===false && s.overrideReason===null;})());
  check('undefined → clean (no throw)', (()=>{const s=ctx.overrideStamp();return s.manuallyOverridden===false && s.overrideReason===null;})());
});

suite('effectiveDuration: golden fixture (parity with backend _effective_duration)', () => {
  const fx = JSON.parse(fs.readFileSync(path.join(__dirname, 'fixtures', 'duration-cases.json'), 'utf8'));
  for (const c of fx.cases) {
    const tech = { durationOverrides: c.techOverrides };
    const cats = Object.entries(c.catTimes).map(([id, time]) => ({ id, time }));
    const settings = { regularTime: c.regular };
    check(`dur: ${c.why}`, ctx.effectiveDuration(c.catId, tech, cats, settings) === c.expect);
  }
  // Robustness — the resolver must never throw on degenerate inputs (it runs in hot render loops).
  check('null tech → uses category', ctx.effectiveDuration('c1', null, [{ id: 'c1', time: 45 }], { regularTime: 30 }) === 45);
  check('undefined settings → floor 30', ctx.effectiveDuration('c1', {}, [{ id: 'c1' }], undefined) === 30);
  check('undefined categories → floor 30', ctx.effectiveDuration('c1', {}, undefined, {}) === 30);
});

suite('isPendingArchived (pending-queue 3-week split)', () => {
  const today='2026-07-08'; // cutoff = 2026-06-17
  check('date 30 days ago → archived', ctx.isPendingArchived({date:'2026-06-08'}, today) === true);
  check('date 10 days ago → active', ctx.isPendingArchived({date:'2026-06-28'}, today) === false);
  check('exactly at cutoff (21d) → active (strictly older only)', ctx.isPendingArchived({date:'2026-06-17'}, today) === false);
  check('no date, old createdAt → archived', ctx.isPendingArchived({createdAt:'2026-06-08T10:00:00Z'}, today) === true);
  check('no date, fresh createdAt → active', ctx.isPendingArchived({createdAt:'2026-07-01T10:00:00Z'}, today) === false);
  check('date wins over createdAt', ctx.isPendingArchived({date:'2026-07-01',createdAt:'2026-01-01T00:00:00Z'}, today) === false);
  check('neither date nor createdAt → active (fresh)', ctx.isPendingArchived({}, today) === false);
  check('null task → safe false', ctx.isPendingArchived(null, today) === false);
});

suite('resolveWindowSemantics (what the customer window promises)', () => {
  check('absent config → finish (conservative default)', ctx.resolveWindowSemantics(undefined) === 'finish');
  check('empty scheduling → finish', ctx.resolveWindowSemantics({}) === 'finish');
  check('arrive honored (PureWater / Israel operation)', ctx.resolveWindowSemantics({window_semantics:'arrive'}) === 'arrive');
  check('finish honored explicitly', ctx.resolveWindowSemantics({window_semantics:'finish'}) === 'finish');
  check('unknown value → finish, never crashes', ctx.resolveWindowSemantics({window_semantics:'banana'}) === 'finish');
});

suite('route-health display templates (P1 — render-only, Python computes)', () => {
  check('band he: healthy', ctx.healthBandHe('healthy') === 'מסלול תקין');
  check('band he: review', ctx.healthBandHe('review') === 'כדאי לבדוק');
  check('band he: issues', ctx.healthBandHe('issues') === 'נמצאו בעיות');
  check('band he: unknown/null → empty', ctx.healthBandHe(null) === '' && ctx.healthBandHe('x') === '');

  check('finding: backtrack', ctx.describeHealthFindingHe({type:'backtrack'}).includes('זיגזג'));
  check('finding: better_order carries saving', ctx.describeHealthFindingHe({type:'better_order_exists',data:{saving_min:34}}).includes('34'));
  check('finding: lateness carries minutes', ctx.describeHealthFindingHe({type:'lateness_risk',data:{late_by_min:15}}).includes('15'));
  check('finding: idle carries minutes', ctx.describeHealthFindingHe({type:'idle_gap',data:{idle_min:40}}).includes('40'));
  check('finding: overtime carries minutes', ctx.describeHealthFindingHe({type:'overtime',data:{overtime_min:25}}).includes('25'));
  check('finding: window violation', ctx.describeHealthFindingHe({type:'window_violation'}).includes('חלון'));
  check('finding: unknown type → raw name, never throws', ctx.describeHealthFindingHe({type:'weird_new_type'}) === 'weird_new_type');
  check('finding: null → safe', typeof ctx.describeHealthFindingHe(null) === 'string');
  check('finding: missing data → 0 not NaN', ctx.describeHealthFindingHe({type:'idle_gap'}).includes('0'));

  check('chip: null → hidden', ctx.healthChipHtml(null) === '');
  check('chip: score null → hidden (no fake 100)', ctx.healthChipHtml({score:null,band:null}) === '');
  const chip = ctx.healthChipHtml({score:62,band:'issues',partial:false,findings:[{type:'backtrack'},{type:'better_order_exists'}]});
  check('chip: shows score', chip.includes('62'));
  check('chip: issues palette (red bg)', chip.includes('#FEE2E2'));
  check('chip: findings count', chip.includes('2 ממצאים'));
  const partial = ctx.healthChipHtml({score:100,band:'healthy',partial:true,findings:[]});
  check('chip: partial marker *', partial.includes('100*'));
  check('chip: healthy palette (green bg)', partial.includes('#DCFCE7'));
  check('chip: no findings → no count', !partial.includes('ממצאים'));
});

suite('resolveReportCards (reports.cards knob — display-only, batch n/a by design)', () => {
  const all = ctx.resolveReportCards(undefined);
  check('absent config → every card visible', ctx.REPORT_CARDS.every(k => all[k] === true));
  check('empty reports → every card visible', ctx.REPORT_CARDS.every(k => ctx.resolveReportCards({})[k] === true));
  const trimmed = ctx.resolveReportCards({cards:{zones:false, insights:false}});
  check('explicit false hides the card', trimmed.zones === false && trimmed.insights === false);
  check('unmentioned cards stay visible', trimmed.kpis === true && trimmed.team === true && trimmed.weekday === true && trimmed.categories === true);
  const truthy = ctx.resolveReportCards({cards:{zones:true, team:1}});
  check('only explicit false hides — truthy/other values keep visible', truthy.zones === true && truthy.team === true);
  check('unknown card keys ignored (no crash, not added)', !('bogus' in ctx.resolveReportCards({cards:{bogus:false}})));
  check('card set is the 6 known cards', ctx.REPORT_CARDS.length === 6 && Object.keys(all).length === 6);
});

suite('window overrun: golden fixture (parity with backend resolve_auto_overrun_min/overrun_decision)', () => {
  const fsO = require('fs'), pathO = require('path');
  const fx = JSON.parse(fsO.readFileSync(pathO.join(__dirname, 'fixtures', 'overrun-cases.json'), 'utf8'));
  for (const c of fx.resolver_cases) {
    check(`resolver sc=${JSON.stringify(c.sc)} → ${c.expect}`, ctx.resolveAutoOverrunMin(c.sc) === c.expect);
  }
  for (const c of fx.decision_cases) {
    check(`decision ${c.semantics}/over=${c.overrun}/auto=${c.auto}/tol=${c.tol} → ${c.expect}`,
      ctx.overrunDecision(c.semantics, c.overrun, c.auto, c.tol) === c.expect);
  }
  // overrunMinutes math
  check('fits exactly → 0', ctx.overrunMinutes(570, 30, 600) === 0);
  check('spills 20 → 20', ctx.overrunMinutes(590, 30, 600) === 20);
  check('no window → 0 (fail-open)', ctx.overrunMinutes(590, 30, null) === 0);
  check('null start → 0 (fail-open)', ctx.overrunMinutes(null, 30, 600) === 0);
});

suite('resolveInsightsWindow (insights.window_days knob — display-only, batch n/a by design)', () => {
  check('absent config → 90', ctx.resolveInsightsWindow(undefined) === 90);
  check('empty insights → 90', ctx.resolveInsightsWindow({}) === 90);
  check('explicit 30 honored', ctx.resolveInsightsWindow({window_days:30}) === 30);
  check('explicit 365 honored', ctx.resolveInsightsWindow({window_days:365}) === 365);
  check('string number coerced', ctx.resolveInsightsWindow({window_days:'180'}) === 180);
  check('zero/negative → 90 (never a dead window)', ctx.resolveInsightsWindow({window_days:0}) === 90 && ctx.resolveInsightsWindow({window_days:-5}) === 90);
  check('junk → 90', ctx.resolveInsightsWindow({window_days:'abc'}) === 90 && ctx.resolveInsightsWindow({window_days:Infinity}) === 90);
  check('fractional rounded', ctx.resolveInsightsWindow({window_days:90.6}) === 91);
});

suite('durationAccuracyInsights (E4-lite)', () => {
  const cats=[{id:'c1',name:'טוחן',time:30},{id:'c2',name:'מים',time:60}];
  const st={regularTime:30};
  const a='2026-06-09T08:00:00Z';
  const mkT=(catId,mins)=>({catId,arrivedAt:a,completedAt:new Date(new Date(a).getTime()+mins*60000).toISOString()});
  check('exact ~30 on c1 (3 jobs) → no insight', ctx.durationAccuracyInsights([mkT('c1',30),mkT('c1',30),mkT('c1',30)],cats,st).length===0);
  const over=ctx.durationAccuracyInsights([mkT('c1',48),mkT('c1',48),mkT('c1',48)],cats,st);
  check('c1 ~48 vs 30 → one insight for c1', over.length===1 && over[0].catId==='c1');
  check('  actualMedian rounded to 50, n=3, configured 30', over.length===1 && over[0].actualMedian===50 && over[0].n===3 && over[0].configured===30);
  check('  deltaPct positive (over-run) ≥ 0.25', over.length===1 && over[0].deltaPct>0.25);
  check('n<3 suppressed', ctx.durationAccuracyInsights([mkT('c1',48),mkT('c1',48)],cats,st).length===0);
  check('outlier >8h dropped → median unchanged → no insight', ctx.durationAccuracyInsights([mkT('c1',30),mkT('c1',30),mkT('c1',30),mkT('c1',600)],cats,st).length===0);
  check('sub-3-min glitch dropped', ctx.durationAccuracyInsights([mkT('c1',48),mkT('c1',48),mkT('c1',48),mkT('c1',1)],cats,st)[0].n===3);
  const miss=ctx.durationAccuracyInsights([{catId:'c1',completedAt:a},mkT('c1',48),mkT('c1',48),mkT('c1',48)],cats,st);
  check('missing arrived_at excluded (n stays 3)', miss.length===1 && miss[0].n===3);
  const under=ctx.durationAccuracyInsights([mkT('c2',20),mkT('c2',20),mkT('c2',20)],cats,st);
  check('c2 ~20 vs 60 → insight with negative delta (faster than configured)', under.length===1 && under[0].deltaPct<0 && under[0].actualMedian===20);
});

suite('traffic mode/bucket: golden fixture (parity with backend resolve_traffic_mode/traffic_bucket)', () => {
  const fx = JSON.parse(fs.readFileSync(path.join(__dirname, 'fixtures', 'traffic-cases.json'), 'utf8'));
  fx.mode_cases.forEach((c, i) => check(`mode[${i}] → ${c.expect}`, ctx.resolveTrafficMode(c.config) === c.expect));
  fx.bucket_cases.forEach((c, i) => check(`bucket[${i}] ${c.mode}@${c.hhmm} → ${c.expect}`, ctx.trafficBucket(c.mode, c.hhmm) === c.expect));
});

suite('deriveLegObservation + obsLocKey (cross-tenant brain P1)', () => {
  check('obsLocKey rounds coords to 4dp', ctx.obsLocKey('32.1234567,34.7654321') === '32.1235,34.7654');
  check('obsLocKey trims city name', ctx.obsLocKey('  חיפה ') === 'חיפה');
  // local-time (no-Z) timestamps → deterministic getHours() regardless of machine tz
  const mk = (er, ar, city) => ({ enRouteAt: er, arrivedAt: ar, city, _dbId: 't1' });
  const o = ctx.deriveLegObservation(mk('2026-06-09T08:00:00', '2026-06-09T08:30:00', 'חיפה'), 'עכו', null);
  check('valid 30-min leg → observation (off ⇒ static)', !!o && o.from_key === 'עכו' && o.to_key === 'חיפה' && o.observed_min === 30 && o.time_bucket === 'static' && o.source === 'timestamps' && o.task_id === 't1');
  check('missing en_route_at → null', ctx.deriveLegObservation({ arrivedAt: '2026-06-09T08:30:00', city: 'חיפה' }, 'עכו', null) === null);
  check('missing arrived_at → null', ctx.deriveLegObservation({ enRouteAt: '2026-06-09T08:00:00', city: 'חיפה' }, 'עכו', null) === null);
  check('same from/to → null', ctx.deriveLegObservation(mk('2026-06-09T08:00:00', '2026-06-09T08:30:00', 'חיפה'), 'חיפה', null) === null);
  check('zero/negative delta → null', ctx.deriveLegObservation(mk('2026-06-09T08:30:00', '2026-06-09T08:30:00', 'חיפה'), 'עכו', null) === null);
  check('overnight/huge delta (>600m) → null', ctx.deriveLegObservation(mk('2026-06-09T08:00:00', '2026-06-09T20:00:00', 'חיפה'), 'עכו', null) === null);
  const rush = ctx.deriveLegObservation(mk('2026-06-09T08:00:00', '2026-06-09T08:30:00', 'חיפה'), 'עכו', { routing: { traffic_mode: 'rush_hour' } });
  check('rush_hour config + 08:00 departure → rush bucket', !!rush && rush.time_bucket === 'rush');
});

console.log(`\n${passed} passed, ${failed} failed`);
process.exit(failed ? 1 : 0);
