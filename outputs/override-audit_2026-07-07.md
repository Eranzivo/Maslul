# Override accountability + audit — migration & wiring record (2026-07-07)

Opus queue #4 (handover §15F). Coordinators can override the soft manual-placement
guards (out-of-zone / over-capacity / no route-fit). Until now that override left no
record of **why**. This adds a required, audited reason.

## Key finding (why this stayed small)
`public.tasks` already has an **`_audit_tasks` trigger** (`_maslul_audit_trigger`) that
writes every INSERT/UPDATE into `public.audit_log` (`old_data`/`new_data` jsonb,
`record_id` = tasks.id which is UUID). So stamping two columns on the task gives a full
audit trail **for free** — no new `audit_log` INSERT policy, no browser audit writes,
no new RLS surface. `audit_log` keeps its single `audit_read` SELECT policy
(`tenant_id = get_tenant_id() OR is_super_admin()`).

## Migration (applied, additive, reversible)
Name: `tasks_manual_override_audit`
```sql
alter table public.tasks
  add column if not exists manually_overridden boolean not null default false,
  add column if not exists override_reason text;
```
Readback-verified: both columns present (`manually_overridden` NOT NULL default false;
`override_reason` nullable text). Advisors (security + performance) run after — **no new
issues**; all remaining lints pre-existing/accepted (deny-all geo tables, SECURITY DEFINER
RLS helpers, unused indexes on young pilot DB, leaked-password = Pro/go-live).

### Rollback (if ever needed)
```sql
alter table public.tasks
  drop column if exists override_reason,
  drop column if exists manually_overridden;
```
(The audit_log rows already written stay — they're historical.)

## Frontend wiring (index.html)
- Pure `overrideStamp(reason)` (`<sched-logic>`, tested): `''`/whitespace/null ⇒ clean
  (flag cleared, reason null); non-empty ⇒ `{manuallyOverridden:true, overrideReason}`.
- Guards `confirmZoneDrop` / `confirmCapacityDrop` now return `{ok, override}`
  (override=true when the coordinator proceeds past a soft `confirm()` warn).
- `guardManualPlacement(techId,task,ds)` runs both guards; on override, calls
  `promptOverrideReason()` (required, loops until non-empty; cancel aborts placement).
  Returns `false` to abort, or the reason string (`''` when no override).
- Wired into all 3 manual paths: `_onCellDrop`, `_onGridDrop`, `placeTaskDetail`
  → `Object.assign(t, overrideStamp(_ovr))`.
- Recommended dispatch (`confirmAssign`) sets `manuallyOverridden:false` — an
  engine-computed slot is never an override (clears the flag on re-dispatch).
- Load/save mapping: `manually_overridden`⇄`manuallyOverridden`,
  `override_reason`⇄`overrideReason`.
- Task-detail modal shows «⚠ שיבוץ חריג (מחוץ להמלצה)» + the reason (transparency).

## Not forced
The **lock** action pins a call against the auto-sequencer — already captured by the
`_audit_tasks` trigger (locked column change). No reason prompt forced on lock (too
frequent; would annoy). Revisit if Israel wants lock reasons.

## Tests
`tests/sched.test.js` `overrideStamp` suite (6 checks). Full JS: 155 sched + 65 zones green.

## Eran smoke-test (after next deploy)
1. Weekly board → drag a call onto a tech/day that is out-of-zone or over max → accept
   the warn → a reason is REQUIRED (empty re-asks). Confirm the call saves.
2. Open that call → task-detail shows «⚠ שיבוץ חריג» + your reason.
3. (Optional, as Eran/super_admin) verify the audit row:
   ```sql
   select created_at, operation, new_data->>'override_reason' as reason
   from audit_log where table_name='tasks' and (new_data->>'manually_overridden')='true'
   order by created_at desc limit 5;
   ```
4. Drag the same call back to a valid in-zone slot → flag clears (no «חריג» row).
