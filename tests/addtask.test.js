'use strict';
// Regression suite — creating NEW calls (2026-10-17).
// A new call is NOT WAL-covered, so it may enter local state only after the DB confirms the
// insert; never a success message for an unsaved call; one save in flight (no duplicate calls).
//  1. insertNewTaskConfirmed — the ONE create-call path (real source, stubbed DB).
//  2. confirmAddTask ("+ קריאה" modal) driven end-to-end with a stubbed DOM.
//  3. STRUCTURAL GUARD — every `tasks.push(` in index.html must live in an allow-listed
//     function, so a future door can't silently reintroduce the phantom-call bug.
// Usage: node tests/addtask.test.js [path/to/index.html]
const fs = require('fs');
const path = require('path');
const html = fs.readFileSync(process.argv[2] || path.join(__dirname, '..', 'index.html'), 'utf8');

// Return the source of `[async] function <name>(…){…}` by brace matching.
function extract(name) {
  const m = new RegExp(`(?:async\\s+)?function\\s+${name}\\s*\\(`).exec(html);
  if (!m) throw new Error(`function ${name} not found in index.html`);
  let i = html.indexOf('{', m.index), depth = 0;
  for (; i < html.length; i++) {
    if (html[i] === '{') depth++;
    else if (html[i] === '}' && --depth === 0) return html.slice(m.index, i + 1);
  }
  throw new Error(`unbalanced braces in ${name}`);
}
const SRC = ['insertNewTaskConfirmed', 'confirmAddTask', 'openAddTaskModal', 'cancelAddTask'].map(extract).join('\n');

function makeEnv({ saveResult = 'ok', geoOn = false, suggest = null, tenant = 't1', confirmAns = true, demo = false, saveDelay = 20 } = {}) {
  const el = {}; const mk = (id, v = '') => (el[id] = { value: v, textContent: '', disabled: false, innerHTML: '', classList: { remove() {}, add() {} } });
  mk('at-cat', 'cat1'); mk('at-name', 'דנה'); mk('at-phone', '0501234567'); mk('at-city', 'נתנייה');
  mk('at-street', 'הרצל 5'); mk('at-notes', ''); mk('at-error'); mk('at-save-btn'); mk('mo-add-task');
  el['at-save-btn'].textContent = 'שמור קריאה ←';
  const log = { toasts: [], closed: 0, saves: 0, sentry: 0, geoAsked: 0, rendered: 0 };
  const win = { Sentry: { captureException: () => log.sentry++ }, _atSession: 1 };
  const env = {
    document: { getElementById: id => el[id] || null },
    CONFIG: { DEMO_MODE: demo }, window: win,
    normalizeCity: s => (s || '').trim(), h: s => s, categories: [{ id: 'cat1', name: 'טוחן אשפה' }],
    currentTenantId: tenant, nextTaskId: 1, tasks: [], save: () => {}, closeMo: () => log.closed++,
    goPage: () => {}, filterTasks: () => {}, renderTasks: () => log.rendered++,
    showToast: (m, t) => log.toasts.push(t ? `${t}:${m}` : m),
    _geoSuggestOn: () => geoOn, geoSuggestCity: async () => { log.geoAsked++; return suggest; },
    geoCorrectionFor: (s, input) => (s && s.match && s.match !== input ? { value: s.match, auto: !!s.auto_ok } : null),
    confirm: () => confirmAns, console: { error: () => {} },
    saveTaskToSupabase: async t => {
      log.saves++; await new Promise(r => setTimeout(r, saveDelay));
      if (saveResult === 'throw') throw new Error('network');
      if (saveResult === 'fail') return false;
      t._dbId = 'uuid-' + log.saves; t.id = t._dbId; return true;
    },
  };
  const api = new Function(...Object.keys(env),
    `${SRC}; return {insertNewTaskConfirmed, confirmAddTask, openAddTaskModal, cancelAddTask, getTasks:()=>tasks};`)(...Object.values(env));
  return { api, el, log, env, win };
}
let pass = 0, fail = 0;
const ok = (c, m) => { c ? pass++ : fail++; console.log(`${c ? 'PASS' : 'FAIL'} | ${m}`); };
const toast = (log, s) => log.toasts.some(t => t.includes(s));

(async () => {
  console.log('• insertNewTaskConfirmed (the one create-call path)');
  { const { api } = makeEnv(); const t = { client: 'x' };
    ok(await api.insertNewTaskConfirmed(t) === true && api.getTasks().length === 1 && t.id === 'uuid-1', 'confirmed insert → added locally with its DB uuid'); }
  { const { api } = makeEnv({ saveResult: 'fail' });
    ok(await api.insertNewTaskConfirmed({}) === false && api.getTasks().length === 0, 'DB error → false, nothing added locally'); }
  { const { api, log } = makeEnv({ saveResult: 'throw' });
    ok(await api.insertNewTaskConfirmed({}) === false && api.getTasks().length === 0 && log.sentry === 1, 'client throws → false (never rethrows), reported to Sentry'); }
  { const { api, log } = makeEnv({ demo: true, tenant: null }); const t = {};
    ok(await api.insertNewTaskConfirmed(t) === true && log.saves === 0 && api.getTasks().length === 1 && t.id === 1, 'demo mode → local only, ZERO Supabase calls'); }

  console.log('• confirmAddTask ("+ קריאה")');
  { const { api, el, log } = makeEnv(); await api.confirmAddTask();
    ok(api.getTasks().length === 1 && api.getTasks()[0].id === 'uuid-1', 'success: call added WITH its DB uuid');
    ok(log.closed === 1 && toast(log, 'הקריאה נרשמה ✓'), 'success: modal closed + success toast');
    ok(!el['at-save-btn'].disabled && el['at-save-btn'].textContent === 'שמור קריאה ←', 'success: button restored'); }
  { const { api, el, log } = makeEnv({ saveResult: 'fail' }); await api.confirmAddTask();
    ok(api.getTasks().length === 0, 'DB failure: NO phantom local call');
    ok(log.closed === 0 && !toast(log, 'הקריאה נרשמה ✓'), 'DB failure: modal stays open, NO success toast');
    ok(el['at-error'].textContent.includes('לא נשמרה'), 'DB failure: clear Hebrew error in the modal');
    ok(el['at-name'].value === 'דנה' && !el['at-save-btn'].disabled, 'DB failure: details kept + button re-enabled for retry'); }
  { const { api, el, log } = makeEnv({ saveResult: 'throw' }); await api.confirmAddTask();
    ok(api.getTasks().length === 0 && log.closed === 0 && el['at-error'].textContent.includes('לא נשמרה') && !el['at-save-btn'].disabled,
      'network throw: no phantom, modal open, error shown, button re-enabled'); }
  { const { api, log } = makeEnv(); await Promise.all([api.confirmAddTask(), api.confirmAddTask(), api.confirmAddTask()]);
    ok(log.saves === 1 && api.getTasks().length === 1, 'triple-click: exactly ONE save, ONE call (no duplicates)'); }
  { const { api, log } = makeEnv({ tenant: null }); await api.confirmAddTask();
    ok(log.saves === 0 && api.getTasks().length === 0, 'logged out (not demo): blocked before any write'); }
  { const { api, log } = makeEnv({ demo: true, tenant: null }); await api.confirmAddTask();
    ok(log.saves === 0 && api.getTasks().length === 1 && toast(log, 'הקריאה נרשמה ✓'), 'demo mode: call added locally, no Supabase (prospect demos work)'); }
  { const { api, el, log } = makeEnv({ geoOn: true }); el['at-street'].value = ''; await api.confirmAddTask();
    ok(log.geoAsked === 0 && log.saves === 0 && el['at-error'].textContent.includes('רחוב'), 'missing street: validated BEFORE any city prompt (geo never asked)'); }
  { const { api, el } = makeEnv({ geoOn: true, suggest: { status: 'suggest', match: 'נתניה', auto_ok: true }, saveResult: 'fail' }); await api.confirmAddTask();
    ok(el['at-city'].value === 'נתניה', 'geo auto-fix written back to the field (survives a failed save)'); }
  { const { api } = makeEnv({ geoOn: true, suggest: { status: 'suggest', match: 'נתניה', auto_ok: true } }); await api.confirmAddTask();
    ok(api.getTasks()[0] && api.getTasks()[0].city === 'נתניה', 'geo auto-fix applied to the saved call'); }
  { const { api } = makeEnv({ geoOn: true, suggest: { status: 'suggest', match: 'רחוב', auto_ok: false }, confirmAns: false }); await api.confirmAddTask();
    ok(api.getTasks()[0] && api.getTasks()[0].city === 'נתנייה', 'declined suggestion: original city kept'); }
  { // cancel while the insert is in flight: the insert can't be un-sent → honest toast, no navigation
    const { api, log } = makeEnv({ saveDelay: 60 }); const p = api.confirmAddTask(); api.cancelAddTask(); await p;
    ok(api.getTasks().length === 1 && toast(log, 'נשמרה ✓') && !toast(log, 'הקריאה נרשמה ✓') && log.closed === 1,
      'cancel during save: saved call reported honestly, no success-navigation'); }
  { // reopen during save: the late result must not close/lock the NEW modal
    const { api, el, log } = makeEnv({ saveDelay: 60 }); const p = api.confirmAddTask();
    api.openAddTaskModal(); el['at-name'].value = 'יוסי (חדש)'; await p;
    ok(log.closed === 0 && el['at-name'].value === 'יוסי (חדש)' && !el['at-save-btn'].disabled && el['at-save-btn'].textContent === 'שמור קריאה ←',
      'reopen during save: new modal NOT closed, its button NOT left on "שומר…"'); }

  console.log('• structural guard — every tasks.push( lives in an allow-listed function');
  const ALLOWED = new Set(['insertNewTaskConfirmed', '_generateRecurringInstances', 'runBulkImport']);
  const offenders = [];
  for (const m of html.matchAll(/tasks\.push\(/g)) {
    const before = html.slice(0, m.index);
    const fns = [...before.matchAll(/function\s+([A-Za-z_$][\w$]*)\s*\(/g)];
    const fn = fns.length ? fns[fns.length - 1][1] : '(top level)';
    if (!ALLOWED.has(fn)) offenders.push(`${fn} @ line ${before.split('\n').length}`);
  }
  ok(offenders.length === 0, offenders.length ? `NEW call added outside the confirmed path: ${offenders.join(', ')} — use insertNewTaskConfirmed()` : 'all new calls go through insertNewTaskConfirmed (or a confirmed dbInsert)');

  console.log(`\n${pass} passed, ${fail} failed`); process.exit(fail ? 1 : 0);
})();
