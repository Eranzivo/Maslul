# Recurring Jobs — Design Spec

> **For agentic workers:** Use `superpowers:subagent-driven-development` or `superpowers:executing-plans` to implement task-by-task from the plan.

**Goal:** Allow coordinators to define a recurring job (e.g. every Sunday at 09:00, weekly) when creating a call. The system auto-generates future task instances up to a configurable lookahead window. Technician assignment is optional — unassigned recurring tasks show a ⚠️ warning until handled.

**Architecture:** New `recurring_templates` table stores the definition. The `tasks` table gets a nullable `recurring_template_id` FK. On every `loadFromSupabase()`, a silent rolling-window generator creates missing future instances. Generated tasks are ordinary tasks — all existing dispatch, status, WhatsApp, and signature flows work unchanged.

**Tech Stack:** Vanilla JS, Supabase (PostgreSQL + RLS), single `index.html`. No backend changes. No cron — generation happens client-side on login/load.

---

## Data Model

### New table: `recurring_templates`

| Column | Type | Nullable | Notes |
|---|---|---|---|
| `id` | UUID | no | PK, gen_random_uuid() |
| `tenant_id` | UUID | no | RLS enforced |
| `client_name` | text | no | |
| `client_phone` | text | yes | |
| `city` | text | no | |
| `street` | text | yes | |
| `category_id` | UUID | yes | FK → categories.id |
| `category_name` | text | yes | Denormalized — avoids join on every load |
| `notes` | text | yes | |
| `day_of_week` | int | no | 0=ראשון … 6=שבת (JS Date.getDay() convention) |
| `scheduled_time` | text | no | HH:MM, e.g. `'09:00'` |
| `interval_weeks` | int | no | 1=שבועי, 2=דו-שבועי, 4=כל 4 שבועות |
| `preferred_technician_id` | UUID | yes | FK → technicians.id; null = no preference |
| `lookahead_weeks` | int | no | Default 6. How far ahead to generate instances. |
| `active` | boolean | no | Default true. Pause without deleting. |
| `last_generated_date` | date | yes | Tracks generation frontier. Null = never generated. |
| `created_at` | timestamptz | no | now() |

RLS: same pattern as all other tables — `(tenant_id = get_tenant_id()) OR is_super_admin()`.

### Change to `tasks` table

Add one nullable column:

```sql
ALTER TABLE tasks ADD COLUMN recurring_template_id UUID REFERENCES recurring_templates(id) ON DELETE SET NULL;
```

- `null` = regular one-time task (no change to existing tasks)
- non-null = generated instance of a recurring template

---

## UI/UX

### Creating a recurring job — call drawer (+ קריאה חדשה)

The drawer's Step 1 (client details) gets a toggle at the bottom of the form:

```
🔁 קריאה חוזרת?  [ toggle off/on ]
```

When toggled **on**, a panel expands:

| Field | Control | Default |
|---|---|---|
| יום בשבוע | 7-button segmented: א ב ג ד ה ו ש | ראשון |
| שעה | time input | `settings.work_start` or `'09:00'` |
| תדירות | 3 pills: שבועי / דו-שבועי / כל 4 שבועות | שבועי |
| טכנאי מועדף | dropdown: techs list + "אוטומטי (ללא העדפה)" at top | אוטומטי |
| צור קדימה | number input 1–12 labeled "שבועות" | 6 |

When recurring is on, Step 2 (scheduling candidates / slot picker) is **skipped**. Instead the drawer shows a read-only preview of dates that will be generated:

```
יוצרים 6 קריאות:
  ראשון 2.6.2026  09:00  —  ממתין לשיבוץ
  ראשון 9.6.2026  09:00  —  ממתין לשיבוץ
  ...
```

Confirm button: **צור קריאות חוזרות** → creates the template + all instances in one operation.

### Task list — visual indicators

- **🔄** small blue pill on any task where `recurring_template_id` is set — indicates it's part of a series
- **⚠️** orange triangle replaces 🔄 when `technician_id` is also null — action needed
- New filter pill in the task filter bar: **⚠️ ממתינות לשיבוץ** — filters to all unassigned recurring tasks across all dates
- Clicking a recurring task opens the normal task detail / edit modal. Coordinator can assign a tech, change time, etc. Changes affect only that instance.

### Managing templates — "חוזרות" tab in Tasks page

A second tab alongside the existing task list. Each template rendered as a card:

```
🔁  ניקוי מיכלים — תל אביב                    [● פעיל]
     ראשון · 09:00 · שבועי · 6 שבועות קדימה
     טכנאי מועדף: אוטומטי
     ⚠️ 3 קריאות ממתינות לשיבוץ

     [ערוך]   [השהה]   [מחק]
```

**Edit template:** Opens a modal with the same fields as creation. On save:
1. Delete future unassigned instances (`recurring_template_id = id AND status = 'pending' AND technician_id IS NULL AND date > today`)
2. Reset `last_generated_date` to yesterday
3. Next `loadFromSupabase()` re-generates from today with new settings
4. Already-assigned instances are never touched

**Pause (`active = false`):** Stops generating new instances. Existing pending ones remain — coordinator handles them individually.

**Delete template:** Sets `active = false`, nulls `recurring_template_id` on all future unassigned tasks (they become regular pending tasks — no orphan records), then deletes the template row.

---

## Generation Logic

### `_generateRecurringInstances()` — called inside `loadFromSupabase()`

Runs after templates and existing tasks are loaded. For each active template:

1. **Target end date:** `today + lookahead_weeks * 7` days
2. **Start date:** `last_generated_date + interval_weeks * 7`, or today if never generated
3. **Walk forward** stepping by `interval_weeks * 7` days, landing only on `day_of_week`
4. **Idempotency guard:** skip any date where a task already exists with `recurring_template_id = template.id AND date = targetDate` — no duplicates
5. **Insert** via `dbInsert('tasks', {...})`:
   - `client_name`, `client_phone`, `city`, `street`, `category_id`, `category_name`, `notes` — from template
   - `technician_id` — `preferred_technician_id` from template (may be null)
   - `status` — `'pending'`
   - `scheduled_time` — template's `scheduled_time`
   - `scheduled_date` — the computed date
   - `recurring_template_id` — template's `id`
   - `tenant_id` — `currentTenantId`
6. After all inserts for a template: `dbUpsert('recurring_templates', { id: template.id, last_generated_date: lastDateGenerated })`

**Silent, non-blocking:** Any error during generation is `console.warn`'d and skipped. The app loads normally with whatever tasks exist. Generation resumes on next login.

### Finding the first occurrence on or after a start date for a given `day_of_week`

```js
function _nextOccurrence(fromDate, dayOfWeek) {
  const d = new Date(fromDate);
  const diff = (dayOfWeek - d.getDay() + 7) % 7;
  d.setDate(d.getDate() + (diff === 0 ? 0 : diff));
  return d;
}
```

---

## Edge Cases

| Scenario | Behaviour |
|---|---|
| Template preferred tech is deleted | `preferred_technician_id` becomes null via FK cascade (SET NULL). New instances generate unassigned — ⚠️ shown. |
| App loaded offline | Generation skipped (Supabase calls fail silently). Existing local tasks still render. |
| Coordinator changes lookahead_weeks mid-run | Next load generates up to the new window from `last_generated_date`. |
| Two users load simultaneously | Idempotency guard prevents duplicate tasks. Second insert attempt hits the guard and skips. |
| Recurring task completed | Marks done like any task. Does not affect future instances (generation is template-driven, not completion-driven). |
| Template deleted while instances exist | `ON DELETE SET NULL` on the FK nulls `recurring_template_id` on all linked tasks (past and future). They lose the 🔄 badge but otherwise work normally. No orphan records. |

---

## Out of Scope (this version)

- Monthly patterns (1st/3rd Thursday of month) — add later when a client requests
- "Edit all future instances" bulk re-assign — coordinator edits each instance individually for now
- End date / stop after N occurrences — pause/delete the template manually
- Web Push notification when a recurring instance is auto-generated
