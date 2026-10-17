'use strict';
// Regression suite for confirmAddTask (the "+ קריאה" pending-call door) — 2026-10-17.
// A NEW call is not WAL-covered, so it must enter local state only after the DB confirms the
// insert; never a success toast for an unsaved call; one save in flight (no duplicate calls).
// Extracts the REAL function from index.html and drives it with stubbed DOM/DB.
// Usage: node tests/addtask.test.js [path/to/index.html]
const fs=require('fs');
const html=fs.readFileSync(process.argv[2]||require('path').join(__dirname,'..','index.html'),'utf8');
const start=html.indexOf('async function confirmAddTask(){');
let i=html.indexOf('{',start),depth=0,end=-1;
for(;i<html.length;i++){if(html[i]==='{')depth++;else if(html[i]==='}'){depth--;if(depth===0){end=i+1;break;}}}
const src=html.slice(start,end);

function makeEnv({saveResult='ok',geoOn=false,suggest=null,tenant='t1',confirmAns=true}){
  const el={};const mk=(id,v='')=>el[id]={value:v,textContent:'',disabled:false};
  mk('at-cat','cat1');mk('at-name','דנה');mk('at-phone','0501234567');mk('at-city','נתנייה');
  mk('at-street','הרצל 5');mk('at-notes','');mk('at-error');mk('at-save-btn');el['at-save-btn'].textContent='שמור קריאה ←';
  const log={toasts:[],closed:0,saves:0,pushedLocal:0,sentry:0};
  const env={
    document:{getElementById:id=>el[id]||null},
    normalizeCity:s=>(s||'').trim(), categories:[{id:'cat1',name:'טוחן אשפה'}],
    currentTenantId:tenant, nextTaskId:1, tasks:[], save:()=>{}, closeMo:()=>log.closed++,
    goPage:()=>{}, filterTasks:()=>{}, showToast:(m,t)=>log.toasts.push(t?`${t}:${m}`:m),
    _geoSuggestOn:()=>geoOn, geoSuggestCity:async()=>suggest,
    geoCorrectionFor:(s,input)=>s&&s.match&&s.match!==input?{value:s.match,auto:!!s.auto_ok}:null,
    confirm:()=>confirmAns, console:{error:()=>{}}, window:{Sentry:{captureException:()=>log.sentry++}},
    saveTaskToSupabase:async(t)=>{log.saves++;await new Promise(r=>setTimeout(r,20));
      if(saveResult==='throw')throw new Error('network');
      if(saveResult==='fail')return false; t._dbId='uuid-1';t.id='uuid-1';return true;},
  };
  const fn=new Function(...Object.keys(env),`${src}; return confirmAddTask;`)(...Object.values(env));
  return {fn,el,log,env};
}
let pass=0,fail=0;const ok=(c,m)=>{c?pass++:fail++;console.log(`${c?'PASS':'FAIL'} | ${m}`);};
(async()=>{
  { const {fn,el,log,env}=makeEnv({}); await fn();
    ok(env.tasks.length===1&&env.tasks[0].id==='uuid-1','success: call added locally WITH its DB uuid');
    ok(log.closed===1&&log.toasts.includes('הקריאה נרשמה ✓'),'success: modal closed + success toast');
    ok(!el['at-save-btn'].disabled&&el['at-save-btn'].textContent==='שמור קריאה ←','success: button restored'); }
  { const {fn,el,log,env}=makeEnv({saveResult:'fail'}); await fn();
    ok(env.tasks.length===0,'DB failure: NO phantom local call');
    ok(log.closed===0&&!log.toasts.includes('הקריאה נרשמה ✓'),'DB failure: modal stays open, NO success toast');
    ok(el['at-error'].textContent.includes('לא נשמרה'),'DB failure: clear Hebrew error in modal');
    ok(el['at-name'].value==='דנה','DB failure: typed details kept for retry');
    ok(!el['at-save-btn'].disabled,'DB failure: button re-enabled for retry'); }
  { const {fn,el,log,env}=makeEnv({saveResult:'throw'}); await fn();
    ok(env.tasks.length===0&&log.closed===0,'network throw: no phantom call, modal open');
    ok(log.sentry===1&&el['at-error'].textContent.includes('לא נשמרה'),'network throw: reported to Sentry + error shown');
    ok(!el['at-save-btn'].disabled,'network throw: button re-enabled (finally)'); }
  { const {fn,log,env}=makeEnv({}); await Promise.all([fn(),fn(),fn()]);
    ok(log.saves===1&&env.tasks.length===1,'triple-click: exactly ONE save, ONE call (no duplicates)'); }
  { const {fn,log,env}=makeEnv({tenant:null}); await fn();
    ok(log.saves===0&&env.tasks.length===0,'no tenant: blocked before any write'); }
  { const {fn,el,log,env}=makeEnv({}); el['at-street'].value=''; let asked=0;
    env.geoSuggestCity=async()=>{asked++;return null;}; await fn();
    ok(log.saves===0&&el['at-error'].textContent.includes('רחוב'),'missing street: validated BEFORE any city prompt'); }
  { const {fn,el,env}=makeEnv({geoOn:true,suggest:{status:'suggest',match:'נתניה',auto_ok:true},saveResult:'fail'}); await fn();
    ok(el['at-city'].value==='נתניה','geo auto-fix written back to the field (survives a failed save)'); }
  { const {fn,env}=makeEnv({geoOn:true,suggest:{status:'suggest',match:'נתניה',auto_ok:true}}); await fn();
    ok(env.tasks[0]&&env.tasks[0].city==='נתניה','geo auto-fix applied to the saved call'); }
  { const {fn,env}=makeEnv({geoOn:true,suggest:{status:'suggest',match:'רחוב',auto_ok:false},confirmAns:false}); await fn();
    ok(env.tasks[0]&&env.tasks[0].city==='נתנייה','declined suggestion: original city kept'); }
  console.log(`\n${pass} passed, ${fail} failed`); process.exit(fail?1:0);
})();
