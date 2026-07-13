# QA Checklist — what shipped this session (2026-07-13)

> Focused, not exhaustive: for each changed area, the **normal flow** + the **edge case most likely to bite**.
> App: https://eranzivo.github.io/Maslul/ · Landing: https://eranzivo.github.io/Maslul/landing/
> Do it in **incognito** (clean session). If something looks cached, add `?v=1`.

---

## 1. One front door (login merge) — HIGH PRIORITY
**Normal:** Open the app URL in incognito → you should land on the **marketing page**, not a login form. Click **התחברות למערכת** → warm login card appears → sign in → lands **inside the app**, already loaded.
**Edges:**
- Wrong password → Hebrew error "האימייל או הסיסמה שגויים", button re-enables, no redirect.
- **Israel's normal login still works** — an already-logged-in session going to the app URL must go **straight in**, never bounce to the landing. (Log in, close tab, reopen app URL → should skip the landing.)
- **Logout** → should return to the marketing page (not the bare login form).
- Escape hatch: app URL + `?login=1` → shows the classic in-app login form directly (for you/support).
- Password reset from the landing ("שכחתי סיסמה" with an email filled) → "שלחנו קישור…" confirmation; the emailed link opens the app's reset screen.

## 2. Landing page
**Normal:** Scroll top→bottom on **desktop and phone**. Hero background motion (the route teaser) plays; copy reads clean; two image bands render; nothing overflows sideways on mobile.
**Edges:**
- **Lead form**: fill name+phone (+ optional) → שלחו → success state "הפרטים התקבלו". Then check it landed (see §3).
- Submit with an empty name or a 3-char phone → should not submit (focus jumps to the bad field).
- Accessibility page: footer **הצהרת נגישות** link opens and reads correctly.

## 3. Leads inbox (מנהל מאסטר) — verifies the whole lead pipeline
**Normal:** As Eran (super_admin) → **מנהל מאסטר** page → a "🌱 לידים מהאתר" card lists the test lead you just submitted, with clickable phone + WhatsApp. The **nav button shows an amber count badge**.
**Edges:**
- Click **✓ טופל** → row dims, badge count drops. Reload → stays handled. "החזר לחדשים" reverses it.
- Confirm a **non-super-admin** (e.g. impersonate a coordinator) does **not** see the leads card at all.

## 4. Window-overrun popup (שיבוץ קריאה) — HIGH PRIORITY (new engine behavior)
**Normal:** Book a normal call where the job fits the window → assigns silently, no popup (unchanged).
**Edges (the point of the feature):**
- Book a call into a slot where arrival is inside the window but the **job would finish after the window end** → the **"⚠️ הקריאה גולשת לחלון הבא"** popup appears with the facts (window / arrival / finish / overrun minutes).
  - **מצא חלון אחר** → that slot becomes disabled ("הוחרג — נבחר חלון אחר") and the search re-runs.
  - **שבץ בכל זאת** → books it; then open that day in the **daily calendar** and confirm the block shows the **striped tail past a dashed line** with "גולש X דק׳ · אושר ע״י המתאם", and the next call did **not** move.
  - **ביטול** → nothing booked.

## 5. Weekly calendar (יומן → שבועי) — HIGH PRIORITY (rebuilt)
**Normal:** Open weekly → **hour axis on the right**, day columns, each call is a block at its real time; overlapping windows sit **side-by-side (lanes), never stacked on top of each other**.
**Edges:**
- **Tech lens**: chips now **multi-select** — click אלירן then בני → both shown together; click one again to drop it; "כל הצוות" clears to all. With exactly **one** tech selected, drag a call between days and the 🔀 button both work.
- Switch to **יומי** and back → both views render correctly (no blank grid).
- A day-off day shows the יום חופש state.

## 6. דוחות (rebuilt) — HIGH PRIORITY
**Normal:** Open דוחות → 4 KPIs (calls / avg wait / utilization / route score), team + zone-demand bars, weekday load. Toggle the period (שבוע / חודש / **3 חודשים** / שנה / הכל) → **every section re-renders** and the compare stamp updates.
**Edges:**
- Each card's **⬇ export** downloads a CSV that matches the **currently selected period** (not all-time).
- **⤢ expand** on zones/categories reveals the rows beyond the top 5.
- Route-score KPI + per-tech score fill in a moment after load (they read route_audits async) — should show a number, not stay "…", if audits exist; "—" is acceptable if none.
- Settings → **📊 דוחות ותובנות**: untick a card (e.g. "עומס שבועי"), save, reopen דוחות → that card is gone. Re-tick to restore.

## 7. קריאות (detail panel + pager)
**Normal:** קריאות tab → click a row → **detail side-panel** opens (intake fields, constraint chips, current-assignment box with route position + health chip, status-aware actions). Click the same row → closes; click another → switches.
**Edges:**
- **ממתינות are timeless** — use the week pager ‹ › and confirm waiting calls always show regardless of week, while משובצות/הושלמו scope to the shown week.
- Panel actions run the real flow: on a pending call **שבץ עכשיו** → dispatch pre-filled; on an assigned call **פתח ביומן** → jumps to its day.
- Panel starts **empty** each time you enter the tab (no stale selection).

## 8. Categories & bundles (חבילות) — the bug you found
**Normal:** קטגוריות page → each bundle now has **✏️ ערוך**. Click it → modal prefilled with the bundle's rows → change name/qty, remove a row, add a row → שמור → the list updates and it persists on reload.
**Edges:**
- **+ חבילה חדשה** → add a bundle with 2 category rows → saves and appears (this was the broken path).
- The category dropdown in a bundle row only offers **existing categories** (no free text).
- Try to save a bundle with zero rows → blocked ("חייבת לכלול לפחות קטגוריה אחת").

## 9. Zones (polygon buttons)
**Normal:** אזורים → your 8 city-list zones show only **הסר** (no צייר button) — because they're manual, not polygon.
**Edges:**
- A brand-new empty zone offers **🗺️ צייר פוליגון**; once it has a polygon it shows **🗺️ ערוך פוליגון** and the editor titles itself "עריכת פוליגון".
- Zone cards still show coverage-day chips + demand line (respecting the insights window from settings).

## 10. Logo (visual only)
Sidebar (app) + landing header + login modal: the wordmark **מסלול** with the short arrow underneath (blue→teal, zigzag, arrowhead), centered, sitting cleanly below the letters — matches your final asset.

---

### Fastest high-value path if you're short on time
1 (front door) → 4 (overrun popup) → 5 (weekly) → 6 (דוחות) → 8 (bundles). Those are the biggest behavior changes; the rest are lower-risk restyles.

### Report back
For anything off: the section number + what you saw vs expected. I'll fix-forward.
