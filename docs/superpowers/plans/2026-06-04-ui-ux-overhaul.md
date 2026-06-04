# UI/UX Overhaul — Home + Dispatch Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Modernize the Maslul coordinator home and dispatch pages — SVG sidebar icons, bold KPI cards with click-to-filter, rich tech cards showing status/capacity/next job, clean header, and a two-column dispatch layout.

**Architecture:** All changes are inline in `index.html` — the single-file HTML/CSS/JS app. CSS edits go in the `<style>` block (~lines 1–400). HTML edits go in page `<div>` blocks (~lines 650–850). JS edits go in the `<script>` block (~lines 2900+). No build step, no separate files.

**Tech Stack:** Vanilla JS, inline CSS, RTL Hebrew. No test framework — each task ends with a specific manual browser verification checklist.

---

### Task 1: SVG Icons — Sidebar Modernization

**Files:**
- Modify: `index.html` — CSS block (after `.ni-btn.active` rule, ~line 61), sidebar HTML (~lines 652–668)

- [ ] **Step 1: Add SVG sizing CSS**

Find `.ni-btn.active{background:var(--accent-light)...` and add these three lines immediately after it:

```css
.ni-btn svg{width:16px;height:16px;flex-shrink:0;opacity:0.7;}
.ni-btn.active svg,.ni-btn:hover svg{opacity:1;}
```

- [ ] **Step 2: Replace sidebar nav HTML**

Find the `<div class="sb-nav">` block (~line 652) and replace everything from `<div class="sb-nav">` through the closing `</div>` of that block (the one that contains all the `ni-btn` buttons) with:

```html
  <div class="sb-nav">
    <div class="sb-sec">תפעול</div>
    <button id="nav-home" class="ni-btn active" onclick="goPage('home')"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="m3 9 9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><polyline points="9 22 9 12 15 12 15 22"/></svg> דף הבית</button>
    <button id="nav-dispatch" class="ni-btn" onclick="goPage('dispatch')"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><circle cx="12" cy="12" r="6"/><circle cx="12" cy="12" r="2"/></svg> <span data-label="dispatch">שיבוץ קריאה</span></button>
    <button id="nav-tasks" class="ni-btn" onclick="goPage('tasks')"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="8" x2="21" y1="6" y2="6"/><line x1="8" x2="21" y1="12" y2="12"/><line x1="8" x2="21" y1="18" y2="18"/><line x1="3" x2="3.01" y1="6" y2="6"/><line x1="3" x2="3.01" y1="12" y2="12"/><line x1="3" x2="3.01" y1="18" y2="18"/></svg> <span data-label="tasks">קריאות</span></button>
    <button id="nav-planner" class="ni-btn" onclick="goPage('planner')"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect width="18" height="18" x="3" y="4" rx="2"/><line x1="16" x2="16" y1="2" y2="6"/><line x1="8" x2="8" y1="2" y2="6"/><line x1="3" x2="21" y1="10" y2="10"/></svg> יומן</button>
    <button id="nav-reports" class="ni-btn hidden" onclick="goPage('reports')"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="12" x2="12" y1="20" y2="10"/><line x1="18" x2="18" y1="20" y2="4"/><line x1="6" x2="6" y1="20" y2="16"/></svg> דוחות</button>
    <div id="nav-sec-crm" class="sb-sec hidden">CRM</div>
    <button id="nav-clients" class="ni-btn hidden" onclick="goPage('clients')"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M22 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg> לקוחות</button>
    <div id="nav-sec-settings" class="sb-sec">הגדרות</div>
    <button id="nav-technicians" class="ni-btn" onclick="goPage('technicians')"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z"/></svg> <span data-label="workers">טכנאים</span></button>
    <button id="nav-zones" class="ni-btn" onclick="goPage('zones')"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="2" x2="22" y1="12" y2="12"/><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/></svg> <span data-label="zones">אזורים</span></button>
    <button id="nav-categories" class="ni-btn" onclick="goPage('categories')"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 2H2v10l9.29 9.29c.94.94 2.48.94 3.42 0l6.58-6.58c.94-.94.94-2.48 0-3.42L12 2Z"/><path d="M7 7h.01"/></svg> <span data-label="categories">קטגוריות</span></button>
    <button id="nav-settings" class="ni-btn" onclick="goPage('settings')"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.39a2 2 0 0 0-.73-2.73l-.15-.08a2 2 0 0 1-1-1.74v-.5a2 2 0 0 1 1-1.74l.15-.09a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2z"/><circle cx="12" cy="12" r="3"/></svg> הגדרות</button>
    <button id="nav-users" class="ni-btn" onclick="goPage('users')"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg> משתמשים</button>
    <div id="nav-sec-admin" class="sb-sec hidden" style="color:var(--purple);">MASLUL ADMIN</div>
    <button id="nav-admin" class="ni-btn hidden" onclick="goPage('admin')" style="color:var(--purple);"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg> מנהל מאסטר</button>
  </div>
```

- [ ] **Step 3: Verify**

Open `index.html` locally. Check:
- All sidebar nav items show a small SVG icon + Hebrew label, no emoji anywhere
- Active item (Home) has icon at full opacity, indigo background, indigo text
- Hovering any nav item brings icon to full opacity
- Clicking each nav item still navigates to the correct page (test: Home, Dispatch, Tasks, Settings)

- [ ] **Step 4: Commit**

```bash
git add index.html
git commit -m "feat: replace emoji sidebar icons with inline Lucide SVGs"
```

---

### Task 2: KPI Cards — New Design + Click-to-Filter

**Files:**
- Modify: `index.html` — CSS (~line 182), JS `renderHomeTechCards()` (~line 4276)

- [ ] **Step 1: Update KPI card CSS**

Find `.kpi-card{background:var(--white);border:1px solid var(--line)...` and replace the entire `.kpi-card` rule with:

```css
.kpi-card{background:var(--white);border:1px solid var(--line);border-right:4px solid transparent;border-radius:var(--r-lg);padding:1rem 1.25rem 1rem 2.5rem;box-shadow:var(--sh);display:flex;flex-direction:column;gap:4px;position:relative;cursor:pointer;transition:box-shadow 0.15s,transform 0.15s;}
.kpi-card:hover{box-shadow:var(--sh-md);transform:translateY(-2px);}
.kpi-card.kpi-active{box-shadow:var(--sh-md);outline:2px solid var(--accent-border);}
.kpi-icon{position:absolute;top:14px;left:14px;width:18px;height:18px;opacity:0.65;}
```

- [ ] **Step 2: Add `kpiFilter` global variable**

In the JS block, find where global state variables are declared (search for `let selectedTechForCal`). Add on the line immediately before it:

```js
let kpiFilter=null;
```

- [ ] **Step 3: Add `filterByKpi()` function**

Find `function renderHomeTechCards(){` and add this function immediately before it:

```js
function filterByKpi(type){
  if(type==='pending'){goPage('dispatch');return;}
  kpiFilter=(kpiFilter===type)?null:type;
  renderHomeTechCards();
}
```

- [ ] **Step 4: Replace KPI card HTML generation in `renderHomeTechCards()`**

Find `kpiEl.innerHTML=\`` (the template literal starting at ~line 4287) and replace from that line through the closing backtick (ending at `};` on ~line 4291) with:

```js
    kpiEl.innerHTML=`
      <div class="kpi-card${kpiFilter==='today'?' kpi-active':''}" onclick="filterByKpi('today')" style="border-right-color:var(--accent);">
        <svg class="kpi-icon" viewBox="0 0 24 24" fill="none" stroke="var(--accent)" stroke-width="2"><rect width="18" height="18" x="3" y="4" rx="2"/><line x1="16" x2="16" y1="2" y2="6"/><line x1="8" x2="8" y1="2" y2="6"/><line x1="3" x2="21" y1="10" y2="10"/></svg>
        <div class="kpi-val">${todayTasks.length}</div><div class="kpi-lbl">${L('tasks')} היום</div>
      </div>
      <div class="kpi-card${kpiFilter==='active'?' kpi-active':''}" onclick="filterByKpi('active')" style="border-right-color:var(--amber);">
        <svg class="kpi-icon" viewBox="0 0 24 24" fill="none" stroke="var(--amber)" stroke-width="2"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>
        <div class="kpi-val">${active}</div><div class="kpi-lbl">בביצוע</div>
      </div>
      <div class="kpi-card${kpiFilter==='done'?' kpi-active':''}" onclick="filterByKpi('done')" style="border-right-color:var(--green);">
        <svg class="kpi-icon" viewBox="0 0 24 24" fill="none" stroke="var(--green)" stroke-width="2"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>
        <div class="kpi-val">${done}</div><div class="kpi-lbl">הושלמו</div>
      </div>
      <div class="kpi-card${kpiFilter==='pending'?' kpi-active':''}" onclick="filterByKpi('pending')" style="border-right-color:var(--red);">
        <svg class="kpi-icon" viewBox="0 0 24 24" fill="none" stroke="var(--red)" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="12" x2="12" y1="8" y2="12"/><line x1="12" x2="12.01" y1="16" y2="16"/></svg>
        <div class="kpi-val" style="color:${unassigned>0?'var(--red)':'var(--ink-4)'};">${unassigned}</div><div class="kpi-lbl">ממתינות לשיבוץ</div>
      </div>`;
```

- [ ] **Step 5: Verify**

Open in browser, go to Home. Check:
- 4 KPI cards show with a colored left border (indigo / amber / green / red, on the physical right side in RTL layout)
- Each card has a small icon at physical top-left
- Numbers are large and bold (30px/900)
- Clicking "בביצוע" card: card gets indigo outline (`kpi-active`), clicking again removes it
- Clicking "ממתינות לשיבוץ" navigates to Dispatch page
- Clicking "קריאות היום" toggles the `kpi-active` class on/off

- [ ] **Step 6: Commit**

```bash
git add index.html
git commit -m "feat: redesign KPI cards with colored borders, icons, and click-to-filter"
```

---

### Task 3: Tech Cards — New Design

**Files:**
- Modify: `index.html` — CSS (~lines 186–194), JS `renderHomeTechCards()` tech card section (~lines 4295–4313)

- [ ] **Step 1: Add helper functions**

Find `function getTechZoneForDate(tech,dateStr){` (~line 4315) and add these two functions immediately BEFORE it:

```js
function getTechStatus(tech,dateStr){
  const inProgress=tasks.filter(t=>t.techId===tech.id&&t.date===dateStr&&['en_route','arrived'].includes(t.status));
  if(inProgress.length)return{label:'בדרך',color:'var(--accent)',bg:'var(--accent-light)'};
  const assigned=tasks.filter(t=>t.techId===tech.id&&t.date===dateStr&&t.status==='assigned');
  if(assigned.length)return{label:'משובץ',color:'var(--amber)',bg:'var(--amber-l)'};
  const done=tasks.filter(t=>t.techId===tech.id&&t.date===dateStr&&t.status==='completed');
  if(done.length)return{label:'הסתיים',color:'var(--green)',bg:'var(--green-l)'};
  return{label:'פנוי',color:'var(--ink-3)',bg:'var(--surface-2)'};
}
function getNextJob(tech,dateStr){
  const now=new Date();
  const hhmm=String(now.getHours()).padStart(2,'0')+':'+String(now.getMinutes()).padStart(2,'0');
  return getTechDayTasks(tech,dateStr).find(t=>t.time&&t.time>=hhmm)||null;
}
```

- [ ] **Step 2: Update tech card CSS**

Find `.tech-home-card{background:var(--white)...` (~line 186) and replace the block of rules `.tech-home-card` through `.load-fill` with:

```css
.tech-home-card{background:var(--white);border:1px solid var(--line);border-right:3px solid var(--border);border-radius:var(--r-lg);box-shadow:var(--sh);cursor:pointer;transition:all 0.18s;overflow:hidden;}
.tech-home-card:hover{box-shadow:var(--sh-md);transform:translateY(-2px);}
.tech-home-card.dimmed{opacity:0.4;pointer-events:none;}
.th-color-bar{display:none;}
.th-body{padding:1rem 1.125rem;display:flex;flex-direction:column;gap:8px;text-align:right;}
.th-top{display:flex;align-items:center;justify-content:space-between;gap:8px;}
.th-avatar{width:36px;height:36px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:0.875rem;font-weight:800;color:white;flex-shrink:0;}
.th-name{font-size:0.9375rem;font-weight:700;color:var(--ink);}
.th-status{display:inline-flex;align-items:center;font-size:0.6875rem;font-weight:700;padding:3px 8px;border-radius:20px;}
.th-capacity{display:flex;align-items:center;gap:8px;font-size:0.8125rem;color:var(--ink-3);}
.load-bar{flex:1;height:5px;background:var(--line-2);border-radius:3px;overflow:hidden;}
.load-fill{height:100%;border-radius:3px;transition:width 0.4s ease;}
.th-next{font-size:0.8125rem;color:var(--ink-3);}
.th-next strong{color:var(--ink-2);font-weight:600;}
.th-actions{display:flex;justify-content:flex-end;margin-top:2px;}
```

Also update the mobile responsive rules for tech cards. Find `.tech-home-grid{grid-template-columns:repeat(2,1fr)...` in the `@media(max-width:900px)` block and update:

```css
  .tech-home-grid{grid-template-columns:repeat(2,1fr);gap:10px;}
  .th-body{padding:0.75rem;}
```

(Remove the old `.th-avatar`, `.th-name`, `.th-area`, `.th-body` mobile overrides that are no longer needed.)

- [ ] **Step 3: Update tech card HTML generation in `renderHomeTechCards()`**

Find `grid.innerHTML=technicians.map(tech=>{` through the closing `}).join('')||...` (~lines 4295–4313) and replace the entire map:

```js
  grid.innerHTML=technicians.map(tech=>{
    const cnt=getTechLoad(tech,today);
    const lp=Math.min(100,Math.round((cnt/Math.max(tech.max,1))*100));
    const fc=lp>=85?'var(--red)':lp>=60?'var(--amber)':'var(--green)';
    const st=getTechStatus(tech,today);
    const next=getNextJob(tech,today);
    const nextHtml=next
      ?`<div class="th-next">הבא: <strong>${next.time}</strong> — ${h(next.city)}</div>`
      :`<div class="th-next" style="color:var(--ink-4);">אין קריאות היום</div>`;
    const optBtn=CONFIG.OPTIMIZER_URL&&cnt>=2
      ?`<button class="btn btn-outline btn-sm" style="font-size:0.72rem;" onclick="event.stopPropagation();runOptimize('${tech.id}')"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="12" height="12"><polyline points="17 1 21 5 17 9"/><path d="M3 11V9a4 4 0 0 1 4-4h14"/><polyline points="7 23 3 19 7 15"/><path d="M21 13v2a4 4 0 0 1-4 4H3"/></svg> מסלול</button>`:'';
    // KPI filter dimming
    let dimmed='';
    if(kpiFilter==='active'){
      const hasActive=tasks.some(t=>t.techId===tech.id&&t.date===today&&['en_route','arrived'].includes(t.status));
      if(!hasActive)dimmed=' dimmed';
    } else if(kpiFilter==='done'){
      const hasDone=tasks.some(t=>t.techId===tech.id&&t.date===today&&t.status==='completed');
      if(!hasDone)dimmed=' dimmed';
    }
    return`<div class="tech-home-card${dimmed}" style="border-right-color:${tech.color};" onclick="openTechWeekly('${tech.id}')">
      <div class="th-color-bar"></div>
      <div class="th-body">
        <div class="th-top">
          <div class="th-avatar" style="background:${tech.color};">${h(initials(tech.name))}</div>
          <div style="flex:1;"><div class="th-name">${h(tech.name)}</div></div>
          <div class="th-status" style="background:${st.bg};color:${st.color};">${st.label}</div>
        </div>
        <div class="th-capacity">
          <span style="font-weight:700;color:${fc};">${cnt}</span><span style="color:var(--ink-4);">/ ${tech.max}</span>
          <div class="load-bar"><div class="load-fill" style="width:${lp}%;background:${fc};"></div></div>
          <span style="font-size:0.75rem;color:var(--ink-4);">${lp}%</span>
        </div>
        ${nextHtml}
        <div class="th-actions">
          ${optBtn}
          <button class="btn btn-outline btn-sm" onclick="event.stopPropagation();goPage('dispatch')" style="font-size:0.8rem;">שבץ ←</button>
        </div>
      </div>
    </div>`;
  }).join('')||`<div class="empty"><div class="empty-icon">👷</div><div>הוסף ${L('worker')} ראשון</div></div>`;
```

- [ ] **Step 4: Verify**

Open in browser, go to Home. Check:
- Tech cards show: avatar circle with initials + name + status badge (פנוי/משובץ/בדרך/הסתיים) in correct color
- Capacity row: `X / max` text + progress bar (green/amber/red) + percentage
- "הבא: HH:MM — עיר" line appears if tech has upcoming tasks today; otherwise "אין קריאות היום" in gray
- "שבץ ←" button navigates to Dispatch without opening the tech weekly view
- Tech card left border (RTL physical right) is the tech's color
- In demo mode: tasks have statuses — verify at least one tech shows "משובץ" or "בדרך" badge
- Clicking the body of the card (not the button) opens the weekly calendar view as before
- Click KPI "בביצוע" → techs without en_route/arrived tasks dim to 40% opacity; click again → all full opacity

- [ ] **Step 5: Commit**

```bash
git add index.html
git commit -m "feat: redesign tech cards with status badge, capacity bar, and next job"
```

---

### Task 4: Home Page Header — Button Cleanup

**Files:**
- Modify: `index.html` — home page header HTML (~lines 690–697), `setDateLabel()` JS function

- [ ] **Step 1: Replace the home page header buttons**

Find the `<div id="page-home" class="page">` block header section (~lines 690–697):

```html
  <div class="ph ph-row">
    <div><div class="ph-title">דף הבית</div><div class="ph-sub" id="home-date"></div></div>
    <div class="flex-gap">
      <button class="btn btn-outline btn-sm" id="live-map-btn" onclick="toggleCoordinatorMap()" title="מפה חיה — מיקום טכנאים בשטח">🗺️ מפה חיה</button>
      <button class="btn btn-outline btn-sm" onclick="openDayoffModal()">📵 חופשות</button>
      <button class="btn btn-outline" onclick="openAddTaskModal()">+ הוסף קריאה</button>
      <button class="btn btn-blue" onclick="goPage('dispatch')">+ שיבוץ קריאה</button>
    </div>
  </div>
```

Replace it with:

```html
  <div class="ph ph-row">
    <div><div class="ph-title">דף הבית</div><div class="ph-sub" id="home-date"></div></div>
    <div class="flex-gap">
      <button class="btn btn-ghost btn-sm" id="live-map-btn" onclick="toggleCoordinatorMap()" title="מפה חיה — מיקום טכנאים בשטח"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14"><polygon points="3 6 9 3 15 6 21 3 21 18 15 21 9 18 3 21"/></svg> מפה חיה</button>
      <button class="btn btn-ghost btn-sm" onclick="openDayoffModal()"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14"><rect x="3" y="4" width="18" height="18" rx="2"/><line x1="16" x2="16" y1="2" y2="6"/><line x1="8" x2="8" y1="2" y2="6"/><line x1="3" x2="21" y1="10" y2="10"/><path d="m9 16 2 2 4-4"/></svg> חופשות</button>
      <button class="btn btn-blue" onclick="goPage('dispatch')">+ שיבוץ קריאה</button>
    </div>
  </div>
```

Key changes: removed `+ הוסף קריאה` button; changed `btn-outline` to `btn-ghost` for secondary buttons; replaced emoji with SVG icons; kept only one primary CTA.

- [ ] **Step 2: Update home subtitle to show dynamic tech count**

Find `function setDateLabel()` or wherever `document.getElementById('home-date')` is set. (Search for `home-date` in the JS block.) Find the line that sets `#home-date` text and update it to include the active tech count:

```js
// Before (something like):
document.getElementById('home-date').textContent = formatDate(today);

// After:
const activeTechCount = technicians.filter(t => getTechLoad(t, todayStr()) > 0).length;
document.getElementById('home-date').textContent = `${activeTechCount} טכנאים פעילים · ${formatDate(todayStr())}`;
```

Note: if `formatDate` doesn't exist by that name, find the actual function used and keep using it. The key addition is prepending the tech count string.

- [ ] **Step 3: Verify**

Open in browser, go to Home. Check:
- Header shows: "דף הבית" title + subtitle with tech count + "מפה חיה" ghost button + "חופשות" ghost button + "+ שיבוץ קריאה" blue button
- No emoji in any button
- "+ הוסף קריאה" button is gone
- "מפה חיה" button still toggles the coordinator map correctly
- "חופשות" button still opens the day-off modal
- Subtitle shows "X טכנאים פעילים · [date]"

- [ ] **Step 4: Commit**

```bash
git add index.html
git commit -m "feat: clean up home header — remove duplicate button, SVG icons, dynamic subtitle"
```

---

### Task 5: Dispatch Page — Two-Column Layout

**Files:**
- Modify: `index.html` — CSS block, dispatch page HTML (~lines 739–850)

- [ ] **Step 1: Add two-column layout CSS**

Find `.dispatch-search{background:var(--white)...` (~line 115) and add these rules immediately before it:

```css
.dispatch-cols{display:grid;grid-template-columns:1fr 320px;gap:1.5rem;align-items:start;}
.dispatch-col-queue{background:var(--white);border:1px solid var(--line);border-radius:var(--r-lg);padding:1.125rem 1.25rem;box-shadow:var(--sh);position:sticky;top:1rem;}
.dispatch-col-queue .pq-title{font-size:0.75rem;font-weight:800;color:var(--ink-3);text-transform:uppercase;letter-spacing:0.5px;margin-bottom:10px;}
```

Also add in `@media(max-width:900px)`:

```css
  .dispatch-cols{grid-template-columns:1fr;}
  .dispatch-col-queue{position:static;}
```

- [ ] **Step 2: Restructure dispatch page HTML**

Find the `<div id="page-dispatch" class="page hidden">` block. The current structure after the `ph-row` header is:

```html
  <div id="dispatch-search-card" class="dispatch-search">...</div>
  <div id="dispatch-result" class="hidden">...</div>
  <!-- PENDING QUEUE -->
  <div id="pending-queue" style="margin-top:1rem;">
    <div style="...">📋 קריאות ממתינות לשיבוץ ... <button>+ הוסף קריאה</button></div>
    <div id="pending-queue-list"></div>
  </div>
  <div id="dispatch-success" class="hidden">...</div>
```

Replace everything from `<div id="dispatch-search-card"` through `</div>` of `dispatch-success` with:

```html
  <div class="dispatch-cols">
    <div class="dispatch-col-main">
      <div id="dispatch-search-card" class="dispatch-search">
        <!-- ALL EXISTING FORM CONTENT STAYS HERE — do not change any inner HTML -->
      </div>
      <div id="dispatch-result" class="hidden">
        <!-- ALL EXISTING RESULT CONTENT STAYS HERE — do not change any inner HTML -->
      </div>
      <div id="dispatch-success" class="hidden">
        <!-- ALL EXISTING SUCCESS CONTENT STAYS HERE — do not change any inner HTML -->
      </div>
    </div>
    <div class="dispatch-col-queue">
      <div class="pq-title">קריאות ממתינות</div>
      <div id="pending-queue">
        <div id="pending-queue-list"></div>
      </div>
    </div>
  </div>
```

Important: the inner HTML of `dispatch-search-card`, `dispatch-result`, and `dispatch-success` must remain exactly as-is — only the wrapping structure changes. Copy the exact inner content from the current file.

Also: remove the old `<div style="display:flex;justify-content:space-between...">📋 קריאות ממתינות לשיבוץ</div>` header row from pending-queue — it's replaced by `.pq-title` above.

Remove the `style="margin-top:1rem;"` from `#pending-queue` since it's now inside its own column container.

The `+ הוסף קריאה` button inside the old pending-queue header row is removed (it was duplicating the home page button). Users can still add tasks via the home page.

- [ ] **Step 3: Verify**

Open in browser, go to Dispatch. Check:
- Page shows two columns: left = the full dispatch form; right = pending queue list
- Pending queue (right column) stays visible while filling in the form
- Clicking "שבץ →" in pending queue still pre-fills the form and sets `window._queueTask` correctly (test: click a pending task, verify city/street/category are pre-filled in the form)
- "מצא שיבוץ" button still works — results appear in left column below the form
- "אשר שיבוץ" flow still works end-to-end (select a time slot, fill client name, confirm)
- On mobile (resize to <900px): columns stack vertically, form first

- [ ] **Step 4: Commit**

```bash
git add index.html
git commit -m "feat: dispatch page two-column layout — form left, pending queue right"
```

---

## Self-Review Checklist (run before handing off)

- [ ] **Spec coverage:** All 5 spec sections accounted for — sidebar ✓, KPI cards ✓, tech cards ✓, home header ✓, dispatch layout ✓
- [ ] **Type consistency:** `getTechStatus()` returns `{label,color,bg}` — used as `st.label`, `st.color`, `st.bg` in Task 3 ✓. `getNextJob()` returns a task object or null — checked with ternary ✓. `kpiFilter` is `null | 'today' | 'active' | 'done' | 'pending'` — all branches handled ✓
- [ ] **RTL check:** `border-right` in CSS = physical right = reading-direction START in Hebrew ✓. KPI icons at `left:14px` = physical left = visual end of card ✓. `text-align:right` on `.th-body` ✓
- [ ] **No regressions:** `openTechWeekly()`, `runOptimize()`, `toggleCoordinatorMap()`, `openDayoffModal()`, `confirmAssign()`, `queueAssign()`, `renderPendingQueue()` all called with same signatures ✓
- [ ] **Demo mode safe:** `kpiFilter` defaults to null → no filter applied → all tech cards full opacity ✓. No new Supabase calls added ✓
- [ ] **`+ הוסף קריאה` removal safe:** `openAddTaskModal()` is still accessible from other pages (Tasks page) — only removed from Home header ✓

---

## Notes for Implementer

- **Line numbers shift** as earlier tasks are applied — use function names and unique CSS selectors to locate code, not raw line numbers.
- **Task 4 Step 2** (`setDateLabel`): search for `getElementById('home-date')` in the JS to find the exact location. The function may be named differently. Preserve the existing date format — only prepend the tech count.
- **Task 5 Step 2** (dispatch restructure): the safest approach is to cut the entire `#pending-queue` block from its current location and paste it into the new `dispatch-col-queue` div, rather than retyping it.
- **Demo mode**: to test with real task statuses, append `?demo=1` to the URL (or check `CONFIG.DEMO_MODE` isn't blocking).
