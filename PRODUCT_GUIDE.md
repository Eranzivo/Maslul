# Maslul — Product Guide & Demo Script

_Use this as onboarding material, a support reference, or a live demo walkthrough._

---

## 🏠 דף הבית — Home

**What it is:** The daily command center. First screen after login.

**What you see:**
- 4 KPI cards: tasks today / completed / in-progress / unassigned
- One card per technician: their load (X/max tasks), zone for today, progress bar

**What you can do:**
- Click a tech card → opens their weekly calendar
- "🔀 מסלול מיטבי" button (appears when tech has 2+ tasks today) → AI route optimizer reorders tasks by shortest drive path
- Search bar → find any client by name across all tasks
- "📵 חופשות" → manage day-offs for any technician

**Demo talking point:** _"Every morning Israel opens this screen and sees exactly who's working, how loaded each tech is, and whether any calls are still waiting to be assigned."_

---

## 🎯 שיבוץ קריאה — Dispatch

**What it is:** The main flow for creating and assigning a new service call.

**Step-by-step flow:**
1. Pick a **category** (service type chip) or **package** (bundled service)
2. Select **city** → optionally add street address
3. Click **"מצא שיבוץ"** → system finds the best tech + date + time automatically
4. Review the suggestion (tech name, zone, date, time window)
5. Fill in client name, phone, notes
6. Click **Confirm** → call is scheduled and saved

**Additional options:**
- "מצא מועד אחר" → cycles through alternative slots
- Pick a specific date manually to check availability on that day
- After success: one-click WhatsApp message to client
- Option to turn into a **recurring series** (weekly / biweekly / monthly)

**Smart draft:** If you navigate away mid-form, all fields are saved and restored when you come back.

**Demo talking point:** _"From the moment a client calls to the moment the tech is assigned — about 15 seconds. The system checks zone rules, existing load, category limits, and picks the optimal slot automatically."_

---

## 📋 קריאות — Tasks

**What it is:** The complete call log — all statuses, all dates.

**What you can do:**
- Filter by: הכל / ממתינות / משובצות / הושלמו / בוטלו
- Click any task → full detail modal (client info, tech, time, status history)
- Update status through the flow: ממתין → שובץ → בדרך → הגיע → הושלם / תקלה
- Cancel a task → system offers to auto-replace with a pending call from the same zone
- "שבץ" button on pending tasks → quick-assign without going through full dispatch

**Demo talking point:** _"If a tech calls in sick mid-day, you cancel their tasks here. The system immediately finds pending calls from the same zone and offers to fill the freed slot."_

---

## 📅 לוח תכנון — Planner

**What it is:** Visual weekly calendar across all technicians simultaneously.

**Views:**
- **Weekly:** each tech = a column, each day = a row — full team at a glance
- **Daily:** one day, all techs, more detail per task

**What you can do:**
- Scan for gaps or overloaded days before they become a problem
- Click any task in the grid → opens task detail modal

**Demo talking point:** _"Management view. Before the week starts, you open this and see if Tuesday has 3 techs with 9 calls each while Wednesday is half-empty — and rebalance."_

---

## 👷 טכנאים — Technicians _(Settings)_

**What it is:** The technician roster and their scheduling rules.

**Per-technician settings:**
- Name, phone, base city, display color
- Work hours (start / end time)
- Min / max calls per day
- **Rotation:** which zone this tech covers each day of the week (Sun–Fri) — _this is the core of the scheduling engine_
- **Skills:** which service categories this tech is qualified for
- **Category limits:** max calls of a specific type per day (e.g. max 3 water system installs)
- **Blocked cities:** cities this tech never covers

**Demo talking point:** _"The rotation table is everything. You set 'Yossi covers Tel Aviv on Sundays and Wednesdays, Haifa on Tuesdays' — and the system enforces it automatically on every dispatch."_

---

## 🗺️ אזורים — Zones _(Settings)_

**What it is:** Geographic service areas.

**Structure:**
- Each zone = a name + list of cities
- Cities within a zone are ordered far-to-near (sets the route order within a day)
- Technician rotation maps each weekday → one zone

**Rule:** A call in city X only goes to the tech whose zone includes X on that day. No exceptions.

**Demo talking point:** _"Zones prevent the classic chaos of sending two techs to the same city on the same day, or one tech driving from Haifa to Eilat and back."_

---

## 📦 קטגוריות — Categories _(Settings)_

**What it is:** Service types and bundles.

**Categories:** service name + duration in minutes (used to calculate available slots)

**Packages:** a bundle of multiple categories with a combined duration
_(e.g. "Full Installation" = installation 45 min + training 20 min + check 15 min = 80 min total)_

Categories appear as clickable chips in the Dispatch flow.

---

## ⚙️ הגדרות — Settings _(Settings)_

**What it is:** Company-wide defaults and feature controls.

**Configurable:**
- Company name, monthly volume target
- Global work hours (overridable per tech)
- Default call duration: regular / package
- Arrival window: 2h / 3h / 4h (the time bracket shown to clients)
- Lookahead days: how far ahead the scheduler searches for slots
- Export / import all settings as JSON (backup)

**Feature flags (admin only):**
CRM, Reports, WhatsApp, Google Maps, Odoo integration — toggle on per tenant.

---

## 👤 משתמשים — Users _(Settings, Admin only)_

**What it is:** Access management for the system.

**What you can do:**
- Create new users (email invite) — role: Admin or Coordinator
- Set which pages each coordinator can access (e.g. dispatch + tasks only, no settings)
- Link a tech-role user to a technician profile → they log in and see only their own day
- Reset any user's password
- Delete a user from the system

**Demo talking point:** _"You can give a call-center coordinator access to dispatch and tasks but not to technician settings or reports. Each user sees exactly what they need."_

---

## 📊 דוחות — Reports _(Feature flag — off by default)_

**What it is:** Business KPI dashboard.

**Shows:**
- Monthly/weekly task volume and completion rate
- Per-technician breakdown (how many calls, how many completed)
- Per-zone breakdown
- Per-category breakdown

**Enable:** Settings → תכונות מופעלות → Reports

---

## 👥 לקוחות — CRM _(Feature flag — off by default)_

**What it is:** Client address book with service history.

**What you can do:**
- Add/edit clients: name, phone, email, city, address, notes
- View a client's full call history
- Archive clients no longer active (restoreable)

**Enable:** Settings → תכונות מופעלות → CRM

---

## 📱 Tech Login — Field Worker View

**What it is:** Stripped-down mobile view for technicians in the field.

**What the tech sees:**
- Their tasks for today (ordered by time) and tomorrow
- Per task: category, client name, phone, address, notes, time slot

**Actions:**
- Status buttons: בדרך לך → הגעתי → הושלם (full-width, large tap targets)
- 🗺️ Waze → opens navigation directly to the job address
- 📞 התקשר → calls the client
- 💬 WhatsApp → sends the client a pre-written message

**What the tech cannot see:** other technicians, settings, dispatch, anything else.

---

## 🔧 מנהל מאסטר — Master Admin _(Eran only)_

**What it is:** Cross-tenant control panel for managing all Maslul clients.

**What you can do:**
- See all tenants (clients) and their feature flags
- Enter any client's session (view their data as if you're them)
- Enable / disable features per tenant
- Onboarding wizard: set up a new client in one flow (tenant → zones → techs → categories → rotation)

---

## Demo Flow (15-min script)

1. **Open Home** → show KPIs and tech cards. Point out the load bars.
2. **Go to Dispatch** → pick a category, pick a city, click "מצא שיבוץ". Show the result in under 3 seconds.
3. **Fill in a fake client** (name + phone) → confirm → show the success screen + WhatsApp button.
4. **Go to Tasks** → find the new task, click it, update status to "בדרך".
5. **Go to Planner** → show the weekly view, point to where the new task appears.
6. **Switch role selector to a tech** → show the simplified tech view. Tap the status button.
7. **Go to Technicians** → show the rotation table. Explain zone-strict scheduling.
8. **Go to Zones** → show one zone with its cities.
9. Close with: _"Everything you just saw — one URL, no app to install, works on any phone."_
