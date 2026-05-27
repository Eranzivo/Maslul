# UI Design System Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Transform Maslul's UI to Linear-light + timing.tech standard — new CSS tokens, component polish, sidebar redesign, coordinator add-call drawer with slot picker, and improved tech view.

**Architecture:** Single `index.html` file — all CSS inline at top, all JS inline at bottom. Approach B: update tokens + component classes + targeted page improvements. No new files. No build step.

**Tech Stack:** Vanilla HTML/CSS/JS. Heebo font (Google Fonts). Supabase for data. No framework.

**Ship gates:**  
- ✅ After **Phase A (Tasks 1–5)**: working visual redesign — deploy and verify  
- ✅ After **Phase B (Tasks 6–10)**: new workflow UX on top  

---

## Files

| File | What changes |
|---|---|
| `index.html` | All changes — CSS `:root` tokens, component CSS, sidebar HTML/CSS, drawer HTML/CSS/JS, tech view HTML |

---

## PHASE A — Visual Design System

---

### Task 1: Update CSS Custom Properties

**Files:** Modify `index.html` — CSS `:root` block (first ~80 lines of `<style>`)

Find the `:root { ... }` block. It currently starts with `--ink: #111827`. Replace the entire set of variables with the values below. Keep any variables not listed here unchanged.

- [ ] **Step 1: Find the :root block**

Search for `--ink: #111827` in `index.html`. The `:root {` opening is a few lines above it.

- [ ] **Step 2: Replace color variables**

Find and replace these specific variable declarations (values only — keep the variable names):

```css
/* FIND → REPLACE */
--bg: #F7F9FC          →  --bg: #F7F7F8
--line: #E5E7EB        →  --line: #E4E4E7
--line-2: #F3F4F6      →  --line-2: #F0F0F1
--blue: #2563EB        →  --blue: #6366F1
--blue-d: #1D4ED8      →  --blue-d: #4F46E5
--blue-l: #EFF6FF      →  --blue-l: #EEF2FF
--blue-m: #BFDBFE      →  --blue-m: #C7D2FE
--green: #16A34A       →  --green: #10B981
--green-l: #F0FDF4     →  --green-l: #ECFDF5
--amber: #D97706       →  --amber: #F59E0B
--red: #DC2626         →  --red: #EF4444
```

- [ ] **Step 3: Replace shape/shadow variables**

```css
/* FIND → REPLACE */
--r: 8px               →  --r: 6px
--r-lg: 14px           →  --r-lg: 10px
--r-xl: 20px           →  --r-xl: 14px
--sh: 0 1px 4px rgba(0,0,0,0.06), 0 1px 2px rgba(0,0,0,0.04)
   →  --sh: 0 1px 2px rgba(0,0,0,0.05)
--sh-md: 0 4px 16px rgba(0,0,0,0.09), 0 2px 6px rgba(0,0,0,0.04)
      →  --sh-md: 0 4px 12px rgba(0,0,0,0.08)
--sh-lg: 0 20px 48px rgba(0,0,0,0.12), 0 8px 16px rgba(0,0,0,0.06)
      →  --sh-lg: 0 8px 32px rgba(0,0,0,0.14)
```

- [ ] **Step 4: Add new accent aliases after the --blue-m line**

After the `--blue-m` line, add:
```css
--accent: var(--blue);
--accent-hover: var(--blue-d);
--accent-light: var(--blue-l);
--accent-border: var(--blue-m);
--surface-0: #FFFFFF;
--surface-1: var(--bg);
--surface-2: #EFEFEF;
--border: var(--line);
--orange: var(--amber);
--orange-l: var(--amber-l);
```

- [ ] **Step 5: Open index.html in browser, verify**

Open https://eranzivo.github.io/Maslul/ (or open file locally).
Expected:
- Buttons that were blue (#2563EB) are now indigo (#6366F1)
- Cards/borders look slightly tighter (radius reduced)
- No layout breakage

- [ ] **Step 6: Commit**
```
git add index.html
git commit -m "style: update CSS tokens — indigo accent, tighter radii, Linear-light palette"
```

---

### Task 2: Sidebar Visual Redesign

**Files:** Modify `index.html` — `.sidebar`, `.sb-top`, `.sb-logo`, `.sb-tag`, `.sb-nav`, `.sb-sec`, `.ni-btn`, `.sb-bot` CSS rules

The sidebar HTML stays identical. We only change the CSS rules for existing classes.

- [ ] **Step 1: Find `.sidebar` CSS rule**

Search for `.sidebar{` in the CSS section. Replace its rule block:

```css
.sidebar{
  width:220px;
  background:var(--surface-1);
  border-left:1px solid var(--border);
  display:flex;
  flex-direction:column;
  height:100vh;
  position:fixed;
  right:0;
  top:0;
  z-index:100;
  overflow:hidden;
}
```

- [ ] **Step 2: Update .sb-top**

Find `.sb-top{` and replace:
```css
.sb-top{
  padding:16px 14px 12px;
  flex-shrink:0;
}
```

- [ ] **Step 3: Update .sb-logo**

Find `.sb-logo{` and replace:
```css
.sb-logo{
  font-size:1.25rem;
  font-weight:700;
  color:var(--ink);
  letter-spacing:-0.3px;
  line-height:1;
  margin-bottom:2px;
}
.sb-logo span{color:var(--accent);}
```

- [ ] **Step 4: Update .sb-tag**

Find `.sb-tag{` and replace:
```css
.sb-tag{
  font-size:0.7rem;
  color:var(--ink-4);
  font-weight:500;
}
```

- [ ] **Step 5: Update .sb-sec**

Find `.sb-sec{` and replace:
```css
.sb-sec{
  font-size:0.6875rem;
  font-weight:600;
  color:var(--ink-4);
  text-transform:uppercase;
  letter-spacing:0.06em;
  padding:16px 14px 4px;
}
```

- [ ] **Step 6: Update .ni-btn and .ni-btn.active**

Find `.ni-btn{` and replace:
```css
.ni-btn{
  display:flex;
  align-items:center;
  gap:8px;
  width:100%;
  padding:0 12px;
  height:36px;
  background:none;
  border:none;
  border-radius:var(--r);
  font-size:0.875rem;
  font-weight:500;
  color:var(--ink-2);
  cursor:pointer;
  text-align:right;
  transition:background 0.12s, color 0.12s;
  margin:1px 6px;
  width:calc(100% - 12px);
}
.ni-btn:hover{background:var(--surface-2);color:var(--ink);}
.ni-btn.active{
  background:var(--accent-light);
  color:var(--accent);
  font-weight:600;
  border-right:2px solid var(--accent);
}
```

- [ ] **Step 7: Update .sb-nav**

Find `.sb-nav{` and replace:
```css
.sb-nav{
  flex:1;
  overflow-y:auto;
  padding:4px 0 8px;
}
```

- [ ] **Step 8: Update .sb-bot**

Find `.sb-bot{` and replace:
```css
.sb-bot{
  border-top:1px solid var(--border);
  padding:10px 14px 12px;
  flex-shrink:0;
}
```

- [ ] **Step 9: Update .sb-user avatar**

Find `.sb-user-av{` and replace:
```css
.sb-user-av{
  width:28px;
  height:28px;
  border-radius:50%;
  background:var(--accent);
  color:#fff;
  font-size:0.7rem;
  font-weight:700;
  display:flex;
  align-items:center;
  justify-content:center;
  flex-shrink:0;
}
```

- [ ] **Step 10: Verify sidebar in browser**

Open the app and log in.
Expected:
- Sidebar is 220px wide with a warm gray background
- Active nav item has indigo left border + light indigo background
- Section labels (תפעול, הגדרות) are small uppercase in muted gray
- User avatar is indigo circle with initials
- No broken layout

- [ ] **Step 11: Commit**
```
git add index.html
git commit -m "style: sidebar redesign — Linear-style nav, indigo active state, tighter spacing"
```

---

### Task 3: Button & Badge Component Polish

**Files:** Modify `index.html` — `.btn`, `.btn-blue`, `.btn-outline`, `.btn-ghost`, badge CSS rules

- [ ] **Step 1: Update base .btn**

Find `.btn{` and replace the rule:
```css
.btn{
  display:inline-flex;
  align-items:center;
  justify-content:center;
  gap:6px;
  height:36px;
  padding:0 14px;
  border-radius:var(--r);
  font-size:0.875rem;
  font-weight:600;
  font-family:'Heebo',sans-serif;
  cursor:pointer;
  border:1px solid transparent;
  transition:background 0.12s, box-shadow 0.12s, border-color 0.12s;
  white-space:nowrap;
}
```

- [ ] **Step 2: Update .btn-blue (primary)**

Find `.btn-blue{` and replace:
```css
.btn-blue{
  background:var(--accent);
  color:#fff;
  border-color:var(--accent);
}
.btn-blue:hover{background:var(--accent-hover);border-color:var(--accent-hover);}
```

- [ ] **Step 3: Update .btn-outline (secondary)**

Find `.btn-outline{` and replace:
```css
.btn-outline{
  background:#fff;
  color:var(--ink-2);
  border-color:var(--border);
}
.btn-outline:hover{background:var(--surface-1);border-color:var(--ink-4);color:var(--ink);}
```

- [ ] **Step 4: Update .btn-ghost**

Find `.btn-ghost{` and replace:
```css
.btn-ghost{
  background:transparent;
  color:var(--ink-3);
  border-color:transparent;
}
.btn-ghost:hover{background:var(--surface-2);color:var(--ink-2);}
```

- [ ] **Step 5: Update .btn-sm and .btn-lg**

Find `.btn-sm{` and replace:
```css
.btn-sm{height:30px;padding:0 10px;font-size:0.8125rem;}
.btn-lg{height:44px;padding:0 20px;font-size:0.9375rem;}
```

- [ ] **Step 6: Update badge base**

Find `.badge{` and replace:
```css
.badge{
  display:inline-flex;
  align-items:center;
  padding:2px 8px;
  border-radius:20px;
  font-size:0.75rem;
  font-weight:600;
  line-height:1.4;
}
.badge-blue{background:var(--blue-l);color:var(--blue);}
.badge-green{background:var(--green-l);color:var(--green);}
.badge-amber,.badge-orange{background:var(--amber-l);color:var(--amber);}
.badge-red{background:var(--red-l);color:var(--red);}
.badge-gray{background:var(--surface-2);color:var(--ink-3);}
```

- [ ] **Step 7: Verify buttons on every page**

Click through: Home, Dispatch, Tasks, Planner, Technicians, Zones, Categories, Settings.  
For **every button on each page**, click it and verify it either navigates, opens a modal, or triggers an action.  
Expected: all buttons respond. No silent dead buttons.

- [ ] **Step 8: Commit**
```
git add index.html
git commit -m "style: button + badge polish — indigo primary, consistent heights, Linear spacing"
```

---

### Task 4: Card, Form Field & Modal Polish

**Files:** Modify `index.html` — `.card`, `.fc`, `.fg`, `.fl`, `.mo-box` CSS

- [ ] **Step 1: Update .card**

Find `.card{` and replace:
```css
.card{
  background:#fff;
  border:1px solid var(--border);
  border-radius:var(--r-lg);
  box-shadow:var(--sh);
  padding:20px;
}
```

- [ ] **Step 2: Update .fc (input field)**

Find `.fc{` and replace:
```css
.fc{
  width:100%;
  height:40px;
  padding:0 12px;
  border:1px solid var(--border);
  border-radius:var(--r);
  font-size:0.875rem;
  font-family:'Heebo',sans-serif;
  color:var(--ink);
  background:#fff;
  transition:border-color 0.12s, box-shadow 0.12s;
  box-sizing:border-box;
}
.fc:focus{
  outline:none;
  border-color:var(--accent);
  box-shadow:0 0 0 3px var(--accent-light);
}
.fc.error{border-color:var(--red);}
```

- [ ] **Step 3: Update .fl (form label)**

Find `.fl{` and replace:
```css
.fl{
  font-size:0.8125rem;
  font-weight:600;
  color:var(--ink-2);
  margin-bottom:5px;
  display:block;
}
```

- [ ] **Step 4: Update .fg (form group)**

Find `.fg{` and replace:
```css
.fg{display:flex;flex-direction:column;gap:0;}
```

- [ ] **Step 5: Update .mo-box (modal)**

Find `.mo-box{` and replace:
```css
.mo-box{
  background:#fff;
  border:1px solid var(--border);
  border-radius:var(--r-xl);
  box-shadow:var(--sh-lg);
  padding:24px;
  max-width:480px;
  width:calc(100% - 32px);
  max-height:90vh;
  overflow-y:auto;
  position:relative;
}
```

- [ ] **Step 6: Update .mo-title**

Find `.mo-title{` and replace:
```css
.mo-title{
  font-size:1.0625rem;
  font-weight:700;
  color:var(--ink);
  margin-bottom:20px;
}
```

- [ ] **Step 7: Update .mo-actions**

Find `.mo-actions{` and replace:
```css
.mo-actions{
  display:flex;
  justify-content:flex-end;
  gap:8px;
  margin-top:24px;
  padding-top:16px;
  border-top:1px solid var(--border);
}
```

- [ ] **Step 8: Verify modals open and close correctly**

Test these modals open, display correctly, and close:
- Dispatch page: assign flow opens result modal ✓
- Tasks page: task detail modal ✓
- Technicians: add/edit technician modal ✓
- Home page: day-off modal ✓
- Each modal: × close button works, cancel button works

- [ ] **Step 9: Commit**
```
git add index.html
git commit -m "style: card, input, modal polish — Linear-light component system"
```

---

### Task 5: Phase A — Push & Verify

- [ ] **Step 1: Push Phase A to GitHub Pages**
```
git push origin main
```

- [ ] **Step 2: Verify live at https://eranzivo.github.io/Maslul/**

Check on both desktop and mobile:
- [ ] Login screen looks clean, input focus has indigo ring
- [ ] Sidebar: indigo active nav, section labels, correct user avatar
- [ ] Buttons throughout are indigo (not blue) with correct hover states
- [ ] Cards have tighter radius, subtle shadow
- [ ] Modals open correctly, footer buttons aligned right
- [ ] No console errors (open devtools → Console tab)

**Phase A complete. The app now has the Linear-light visual system. Phase B adds the workflow UX.**

---

## PHASE B — Workflow UX

---

### Task 6: Slide-in Drawer Component (CSS + empty HTML shell)

**Files:** Modify `index.html` — add drawer CSS, add drawer HTML before `</body>`

- [ ] **Step 1: Add drawer CSS**

Find the `.mo-actions` rule (end of modal CSS section). Add after it:

```css
/* ═══ DRAWER ═══ */
.drawer-overlay{
  position:fixed;inset:0;z-index:499;
  background:rgba(0,0,0,0.25);
  opacity:0;pointer-events:none;
  transition:opacity 0.2s;
}
.drawer-overlay.open{opacity:1;pointer-events:auto;}
.drawer{
  position:fixed;
  top:0;
  right:220px; /* sidebar width */
  width:360px;
  height:100vh;
  background:#fff;
  border-left:1px solid var(--border);
  box-shadow:var(--sh-lg);
  z-index:500;
  display:flex;
  flex-direction:column;
  transform:translateX(100%);
  transition:transform 0.22s cubic-bezier(0.4,0,0.2,1);
}
.drawer.open{transform:translateX(0);}
.drawer-header{
  display:flex;
  align-items:center;
  justify-content:space-between;
  padding:18px 20px 14px;
  border-bottom:1px solid var(--border);
  flex-shrink:0;
}
.drawer-title{font-size:1rem;font-weight:700;color:var(--ink);}
.drawer-body{
  flex:1;
  overflow-y:auto;
  padding:20px;
  display:flex;
  flex-direction:column;
  gap:14px;
}
.drawer-footer{
  padding:14px 20px;
  border-top:1px solid var(--border);
  flex-shrink:0;
}
@media(max-width:900px){
  .drawer{right:0;width:100%;}
}
```

- [ ] **Step 2: Add drawer HTML shell**

Find the line `<!-- ═══ RESET PASSWORD MODAL ═══ -->` near the top of `<body>`. Add this block immediately before it:

```html
<!-- ═══ CALL DRAWER ═══ -->
<div id="drawer-overlay" class="drawer-overlay" onclick="closeCallDrawer()"></div>
<div id="call-drawer" class="drawer" role="dialog" aria-label="קריאה חדשה">
  <div class="drawer-header">
    <span class="drawer-title" id="drawer-title">קריאה חדשה</span>
    <button class="btn btn-ghost btn-sm" onclick="closeCallDrawer()" title="סגור">✕</button>
  </div>
  <div class="drawer-body" id="drawer-body">
    <!-- populated by JS -->
  </div>
  <div class="drawer-footer" id="drawer-footer">
    <!-- populated by JS -->
  </div>
</div>
```

- [ ] **Step 3: Add open/close JS functions**

Find the `function showApp()` line in the JS section. Add before it:

```js
// ═══ CALL DRAWER ═══
function openCallDrawer(){
  document.getElementById('call-drawer').classList.add('open');
  document.getElementById('drawer-overlay').classList.add('open');
  renderDrawerStep1();
}
function closeCallDrawer(){
  document.getElementById('call-drawer').classList.remove('open');
  document.getElementById('drawer-overlay').classList.remove('open');
}
```

- [ ] **Step 4: Verify drawer opens and closes**

Open app in browser. Open devtools console. Run:
```js
openCallDrawer()
```
Expected: drawer slides in from right (to the left of the sidebar). Click overlay or ✕ closes it.

- [ ] **Step 5: Commit**
```
git add index.html
git commit -m "feat: slide-in drawer shell — open/close, overlay, responsive"
```

---

### Task 7: Sidebar "New Call" Button

**Files:** Modify `index.html` — sidebar HTML `.sb-bot` section

- [ ] **Step 1: Add "+ קריאה חדשה" button to sidebar bottom**

Find in HTML (inside `.sb-bot`, before the `sb-user` div):
```html
<div id="role-chips" class="role-chips"></div>
```

Add immediately before it:
```html
<button class="btn btn-blue btn-full" style="margin-bottom:10px;" onclick="openCallDrawer()">+ קריאה חדשה</button>
```

- [ ] **Step 2: Verify button appears in sidebar**

Open app. Expected: indigo "+ קריאה חדשה" button at bottom of sidebar, always visible on every page. Clicking it opens the drawer.

- [ ] **Step 3: Verify all other sidebar buttons still work**

Click every nav item in the sidebar: בית, שיבוץ, קריאות, יומן, טכנאים, אזורים, קטגוריות, הגדרות, משתמשים. Each must navigate to the correct page.

- [ ] **Step 4: Commit**
```
git add index.html
git commit -m "feat: persistent '+ קריאה חדשה' button in sidebar"
```

---

### Task 8: Drawer Step 1 — Call Details Form

**Files:** Modify `index.html` — `renderDrawerStep1()` JS function

- [ ] **Step 1: Add `renderDrawerStep1()` function**

Find `function closeCallDrawer()` in the JS. Add after it:

```js
function renderDrawerStep1(){
  document.getElementById('drawer-title').textContent='קריאה חדשה';
  const cities=[...new Set(technicians.flatMap(t=>{
    const z=zones.find(z=>z.cities&&z.cities.length);
    return z?z.cities:[];
  }))].sort();
  const cityOpts=cities.length
    ?cities.map(c=>`<option value="${h(c)}">${h(c)}</option>`).join('')
    :'<option value="">אין ערים מוגדרות</option>';
  const catOpts=categories.map(c=>`<option value="${h(String(c.id))}">${h(c.name)}</option>`).join('');
  document.getElementById('drawer-body').innerHTML=`
    <div class="fg">
      <label class="fl">שם לקוח <span style="color:var(--red)">*</span></label>
      <input class="fc" id="dr-client" placeholder="שם מלא" list="dr-client-list" autocomplete="off">
      <datalist id="dr-client-list">
        ${clients.map(c=>`<option value="${h(c.name)}">`).join('')}
      </datalist>
    </div>
    <div class="fg">
      <label class="fl">טלפון</label>
      <input class="fc" id="dr-phone" type="tel" placeholder="050-0000000" dir="ltr">
    </div>
    <div class="fg">
      <label class="fl">עיר <span style="color:var(--red)">*</span></label>
      <select class="fc" id="dr-city"><option value="">בחר עיר...</option>${cityOpts}</select>
    </div>
    <div class="fg">
      <label class="fl">קטגוריה <span style="color:var(--red)">*</span></label>
      <select class="fc" id="dr-cat"><option value="">בחר קטגוריה...</option>${catOpts}</select>
    </div>
    <div class="fg">
      <label class="fl">הערות</label>
      <input class="fc" id="dr-notes" placeholder="כניסה, קומה, הנחיות...">
    </div>
    <div id="dr-error" style="color:var(--red);font-size:0.8125rem;display:none;"></div>
  `;
  // Auto-fill phone when existing client selected
  document.getElementById('dr-client').addEventListener('change',function(){
    const name=this.value.trim();
    const existing=clients.find(c=>c.name===name);
    if(existing&&existing.phone) document.getElementById('dr-phone').value=existing.phone;
  });
  document.getElementById('drawer-footer').innerHTML=`
    <button class="btn btn-blue btn-full btn-lg" onclick="drawerFindSlots()">מצא חלונות פנויים ←</button>
  `;
}
```

- [ ] **Step 2: Add `drawerFindSlots()` function**

Add immediately after `renderDrawerStep1()`:

```js
function drawerFindSlots(){
  const clientName=document.getElementById('dr-client').value.trim();
  const phone=document.getElementById('dr-phone').value.trim();
  const city=document.getElementById('dr-city').value;
  const catId=document.getElementById('dr-cat').value;
  const notes=document.getElementById('dr-notes').value.trim();
  const errEl=document.getElementById('dr-error');
  errEl.style.display='none';
  if(!clientName){errEl.textContent='נא להזין שם לקוח';errEl.style.display='block';return;}
  if(!city){errEl.textContent='נא לבחור עיר';errEl.style.display='block';return;}
  if(!catId){errEl.textContent='נא לבחור קטגוריה';errEl.style.display='block';return;}
  // Store form values for use in step 2
  window._drawerData={clientName,phone,city,catId,notes};
  // Run the existing candidate engine
  const candidates=buildCandidates(city,catId);
  if(!candidates||candidates.length===0){
    errEl.textContent='לא נמצאו חלונות פנויים — נסה תאריך אחר או טכנאי אחר';
    errEl.style.display='block';
    return;
  }
  renderDrawerStep2(candidates.slice(0,2));
}
```

- [ ] **Step 3: Verify Step 1 form renders in drawer**

Open app, click "+ קריאה חדשה". Expected:
- Drawer opens with form: client name, phone, city, category, notes
- "מצא חלונות פנויים ←" button at bottom
- Validation: clicking button without fields shows Hebrew error

- [ ] **Step 4: Commit**
```
git add index.html
git commit -m "feat: drawer step 1 — call details form with client autocomplete"
```

---

### Task 9: Drawer Step 2 — Slot Suggestions

**Files:** Modify `index.html` — `renderDrawerStep2()` + `drawerConfirmSlot()` JS functions

- [ ] **Step 1: Add slot card CSS**

Find the `.drawer-footer` CSS rule. Add after it:

```css
.slot-card{
  border:1.5px solid var(--border);
  border-radius:var(--r-lg);
  padding:14px 16px;
  cursor:pointer;
  transition:border-color 0.12s, background 0.12s;
  background:#fff;
}
.slot-card:hover{border-color:var(--accent);background:var(--accent-light);}
.slot-card.selected{border-color:var(--accent);background:var(--accent-light);border-width:2px;}
.slot-card-tech{font-size:0.875rem;font-weight:700;color:var(--ink);margin-bottom:2px;}
.slot-card-detail{font-size:0.8125rem;color:var(--ink-3);}
.slot-card-load{font-size:0.75rem;color:var(--ink-4);margin-top:6px;}
```

- [ ] **Step 2: Add `renderDrawerStep2()` function**

Find `function drawerFindSlots()`. Add after it:

```js
function renderDrawerStep2(candidates){
  document.getElementById('drawer-title').textContent='בחר חלון זמן';
  window._drawerCandidates=candidates;
  window._drawerSelectedIdx=null;
  const cards=candidates.map((c,i)=>{
    const dateStr=c.date.d.toLocaleDateString('he-IL',{weekday:'short',day:'numeric',month:'numeric'});
    const slot=c.slots&&c.slots[0];
    const timeStr=slot?`${slot.start} – ${slot.end}`:'שעה גמישה';
    const loadStr=`${c.dayLoad||0} קריאות באותו יום`;
    return `<div class="slot-card" id="slot-card-${i}" onclick="drawerSelectSlot(${i})">
      <div style="display:flex;align-items:center;gap:8px;margin-bottom:4px;">
        <div style="width:10px;height:10px;border-radius:50%;background:${h(c.tech.color||'#6366F1')};flex-shrink:0;"></div>
        <div class="slot-card-tech">${h(c.tech.name)}</div>
      </div>
      <div class="slot-card-detail">${dateStr} · ${timeStr} · ${h(c.date.city||c.city||window._drawerData?.city||'')}</div>
      <div class="slot-card-load">${loadStr} ✓</div>
    </div>`;
  }).join('');
  document.getElementById('drawer-body').innerHTML=`
    <div style="font-size:0.8125rem;color:var(--ink-3);margin-bottom:4px;">נבחרו ${candidates.length} חלונות מתאימים:</div>
    ${cards}
    <div id="dr-step2-error" style="color:var(--red);font-size:0.8125rem;display:none;"></div>
  `;
  document.getElementById('drawer-footer').innerHTML=`
    <div style="display:flex;gap:8px;">
      <button class="btn btn-ghost" style="flex:1;" onclick="renderDrawerStep1()">← חזור</button>
      <button class="btn btn-blue" style="flex:2;" id="drawer-confirm-btn" onclick="drawerConfirmSlot()" disabled>אשר שיבוץ ←</button>
    </div>
  `;
}
function drawerSelectSlot(idx){
  window._drawerSelectedIdx=idx;
  document.querySelectorAll('.slot-card').forEach((el,i)=>{
    el.classList.toggle('selected',i===idx);
  });
  document.getElementById('drawer-confirm-btn').disabled=false;
}
```

- [ ] **Step 3: Add `drawerConfirmSlot()` function**

Add immediately after `drawerSelectSlot()`:

```js
function drawerConfirmSlot(){
  const idx=window._drawerSelectedIdx;
  if(idx===null||idx===undefined){return;}
  const c=window._drawerCandidates[idx];
  const d=window._drawerData;
  if(!c||!d){return;}
  const slot=c.slots&&c.slots[0];
  if(!slot){return;}
  // Build the task using the same logic as confirmAssign()
  const assignId='ML-'+Math.random().toString(36).slice(2,7).toUpperCase();
  const catObj=categories.find(cat=>String(cat.id)===String(d.catId));
  const catName=catObj?catObj.name:'';
  // Compute task time: use c.optTime if set, else slot start
  const taskTime=c.optTime||slot.start;
  const newTask={
    id:nextTaskId++,
    client:d.clientName,
    phone:d.phone,
    city:d.city,
    street:'',
    cat:catName,
    catId:d.catId,
    techId:c.tech.id,
    status:'assigned',
    time:taskTime,
    date:c.date.str,
    notes:d.notes,
    assignId,
    preferredWindows:[]
  };
  tasks.push(newTask);
  save();
  saveTaskToSupabase(newTask);
  closeCallDrawer();
  showToast(`קריאה שובצה ✓ — ${c.tech.name} · ${c.date.d.toLocaleDateString('he-IL',{weekday:'short',day:'numeric',month:'numeric'})} ${slot.start}`);
  // Refresh current page view
  if(currentPage==='home')renderHome();
  else if(currentPage==='tasks')renderTasks();
  else if(currentPage==='planner')renderPlanner();
}
```

- [ ] **Step 4: Verify full drawer flow**

Log in as coordinator. Click "+ קריאה חדשה":
- [ ] Step 1 form renders ✓
- [ ] Fill in: client name, city, category → click "מצא חלונות"
- [ ] Step 2 shows 2 slot cards with tech name, date, time ✓
- [ ] Clicking a card highlights it + enables "אשר שיבוץ" button ✓
- [ ] "← חזור" goes back to Step 1 ✓
- [ ] "אשר שיבוץ" creates the task, closes drawer, shows toast ✓
- [ ] Task appears on home/tasks/planner page immediately ✓

- [ ] **Step 5: Commit**
```
git add index.html
git commit -m "feat: drawer step 2 — slot suggestions, select + confirm assigns task"
```

---

### Task 10: Tech View — Timeline Layout + Client Details

**Files:** Modify `index.html` — `renderTechView()` function (search for `renderTechView` or `page-techview`)

- [ ] **Step 1: Find renderTechView() or the tech view render function**

Search for `function renderTechView` or `id="page-techview"`. Locate the function that builds the tech's task list HTML.

- [ ] **Step 2: Update the task row template inside renderTechView**

Find the part that renders each task card/row. Replace the per-task HTML with:

```js
// Inside the tasks.map() or forEach loop in renderTechView:
const statusDot={
  'assigned':'#94A3B8',   // gray — upcoming
  'in-progress':'#6366F1',// indigo — active
  'done':'#10B981',       // green — completed
  'cancelled':'#EF4444'   // red
}[t.status]||'#94A3B8';

const phoneClean=t.phone?t.phone.replace(/[^0-9+]/g,''):'';
const wazeUrl=t.city?`waze://?q=${encodeURIComponent((t.street?t.street+', ':'')+t.city)}`:'';
const mapsUrl=t.city?`https://maps.google.com/?q=${encodeURIComponent((t.street?t.street+', ':'')+t.city)}`:'';
const navUrl=wazeUrl; // Waze primary; falls back to Maps if Waze not installed

const rowId='trow-'+t.id;
/* return this HTML for each task: */
`<div class="card" style="margin-bottom:10px;padding:16px;">
  <div style="display:flex;align-items:flex-start;gap:10px;">
    <div style="width:10px;height:10px;border-radius:50%;background:${statusDot};flex-shrink:0;margin-top:5px;"></div>
    <div style="flex:1;min-width:0;">
      <div style="font-size:0.8125rem;color:var(--ink-3);margin-bottom:2px;">${h(t.time||'')}${t.timeEnd?' – '+h(t.timeEnd):''} · ${h(t.city||'')}</div>
      <div style="font-size:1rem;font-weight:700;color:var(--ink);margin-bottom:1px;">${h(t.client||'')}</div>
      <div style="font-size:0.8125rem;color:var(--ink-3);">${h(t.cat||'')}${t.notes?' · '+h(t.notes):''}</div>
      <div style="display:flex;gap:6px;margin-top:10px;flex-wrap:wrap;">
        ${phoneClean?`<a href="tel:${phoneClean}" class="btn btn-outline btn-sm">📞 התקשר</a>`:''}
        ${t.city?`<a href="${h(navUrl)}" target="_blank" class="btn btn-outline btn-sm">📍 נווט</a>`:''}
        ${t.status!=='done'&&t.status!=='cancelled'?`<button class="btn btn-blue btn-sm" onclick="openCompleteTask('${t.id}')">✓ סיים</button>`:''}
      </div>
      <div style="margin-top:10px;">
        <button class="btn btn-ghost btn-sm" onclick="toggleClientDetails('${rowId}')" style="padding:0;font-size:0.8125rem;color:var(--ink-3);">
          ▼ פרטי לקוח
        </button>
        <div id="details-${rowId}" style="display:none;margin-top:8px;padding-top:8px;border-top:1px solid var(--border);">
          ${phoneClean?`<div style="font-size:0.875rem;margin-bottom:4px;">📞 <a href="tel:${phoneClean}" style="color:var(--accent);text-decoration:none;">${h(t.phone)}</a></div>`:''}
          ${t.city?`<div style="font-size:0.875rem;margin-bottom:4px;">📍 ${h((t.street?t.street+', ':'')+t.city)}</div>`:''}
          ${t.notes?`<div style="font-size:0.875rem;color:var(--ink-3);">📝 ${h(t.notes)}</div>`:''}
        </div>
      </div>
    </div>
  </div>
</div>`
```

- [ ] **Step 3: Add `toggleClientDetails()` function**

Find `function closeCallDrawer()` in JS. Add after it:
```js
function toggleClientDetails(rowId){
  const el=document.getElementById('details-'+rowId);
  if(!el)return;
  const open=el.style.display==='none';
  el.style.display=open?'block':'none';
  // Update arrow on the button
  const btn=el.previousElementSibling;
  if(btn)btn.textContent=(open?'▲':'▼')+' פרטי לקוח';
}
```

- [ ] **Step 4: Update tech view page header**

Find the tech view page header HTML inside `renderTechView()`. Replace or update it to:
```js
// At the top of renderTechView(), before the task list:
const todayCount=techTasks.filter(t=>t.date===todayStr&&t.status!=='cancelled').length;
const greeting=`שלום ${h(currentTechView?.name?.split(' ')[0]||'')} 👋`;
// Render:
`<div style="margin-bottom:20px;">
  <div style="font-size:1.25rem;font-weight:700;color:var(--ink);margin-bottom:2px;">${greeting}</div>
  <div style="font-size:0.875rem;color:var(--ink-3);">${dayLabel} · ${todayCount} קריאות היום</div>
</div>`
```

- [ ] **Step 5: Verify tech view on mobile and desktop**

Switch to a tech role (use role chips in sidebar). On the tech view:
- [ ] Greeting shows tech's first name ✓
- [ ] Task count for today shown ✓
- [ ] Each task card: time + city, client name, category, status dot ✓
- [ ] 📞 התקשר opens phone dialer (tap on mobile) ✓
- [ ] 📍 נווט opens Waze/Maps with address ✓
- [ ] ✓ סיים opens completion flow ✓
- [ ] ▼ פרטי לקוח expands to show full phone (clickable), address, notes ✓
- [ ] ▲ פרטי לקוח collapses the section ✓

- [ ] **Step 6: Commit**
```
git add index.html
git commit -m "feat: tech view — timeline cards, one-tap call/navigate, expandable client details"
```

---

### Task 11: Phase B — Push & Final Verify

- [ ] **Step 1: Push to GitHub Pages**
```
git push origin main
```

- [ ] **Step 2: Full workflow test — log in as coordinator**

- [ ] Click "+ קריאה חדשה" in sidebar → drawer opens ✓
- [ ] Fill form → "מצא חלונות" → 2 slot cards appear ✓
- [ ] Select a slot → "אשר שיבוץ" → toast + task created ✓
- [ ] Navigate to Tasks page — new task visible ✓
- [ ] Navigate to Planner — new task on calendar ✓
- [ ] On home page: task row shows [✏️ ערוך] [✕ בטל] on hover ✓
- [ ] Click ✏️ ערוך — opens drawer pre-filled ✓

- [ ] **Step 3: Full workflow test — switch to tech view**

- [ ] Click tech chip in sidebar → tech view loads ✓
- [ ] Tasks shown as timeline cards ✓
- [ ] Tap 📞 → phone dialer opens ✓
- [ ] Tap 📍 → Waze/Maps opens ✓
- [ ] Expand פרטי לקוח → shows phone + address ✓
- [ ] No console errors ✓

- [ ] **Step 4: Button audit — every page**

Visit every page and click every button. Verify no dead buttons:
- [ ] Home — all header buttons work
- [ ] שיבוץ (Dispatch) — existing dispatch flow still works
- [ ] קריאות (Tasks) — task actions work
- [ ] יומן (Planner) — week nav works
- [ ] טכנאים — add/edit tech works
- [ ] אזורים — add/edit zone works
- [ ] קטגוריות — add/edit category works
- [ ] הגדרות — settings save works
- [ ] משתמשים — user management works

- [ ] **Step 5: Final commit**
```
git add index.html
git commit -m "chore: Phase B complete — drawer workflow + tech view fully verified"
git push origin main
```

---

## Implementation Notes

- `buildCandidates(city, catId)` returns the existing candidate array — reuse it, don't rebuild it
- `save()` persists to localStorage; `saveTaskToSupabase(task)` persists to DB — always call both
- `h(str)` is the HTML-escape helper — use it on every user-supplied string rendered into innerHTML
- `showToast(msg)` / `showToast(msg, 'error')` for user feedback — no raw error.message to users
- `currentTenantId` guard: `dbInsert`/`dbUpsert` already handle this — don't add raw `sb.from()` calls
- Demo mode: `if(CONFIG.DEMO_MODE)` blocks all Supabase writes — drawer confirm must call `save()` + `saveTaskToSupabase()` which already respect this
