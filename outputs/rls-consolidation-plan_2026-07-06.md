# RLS Policy Consolidation — Plan (2026-07-06, Fable → Opus handoff)

> Trigger: performance advisors show **135 `multiple_permissive_policies`** warnings.
> Root cause found: TWO policy generations coexist on every core table. Because permissive
> policies OR together, this is ALSO a **security finding** — the newer role restrictions
> never actually took effect. **Do NOT hot-fix; run as a focused session with the
> verification protocol below.** Zero-risk part already done: `idx_place_aliases_place_id`
> (advisor's unindexed FK) applied 2026-07-06.

## The two generations (live pg_policies dump, 2026-07-06)
- **Legacy `*_all` (ALL commands):** `tenant_id = get_tenant_id() OR is_super_admin()`
  — ANY tenant member (any role: technician, viewer) gets FULL WRITE on the table.
  Tables: `tasks_all`, `dayoffs_all`, `techs_all`, `users_all`, `zones_all`, `cats_all`,
  `pkgs_all`, `clients_all`, plus `tenant_select`/`tenant_update` on tenants.
- **Newer role-scoped (auth-users hardening):** `*_admin_coordinator`/`*_admin_write`
  (ALL, gated by `current_user_role()`), `*_read` (tenant SELECT),
  `*_technician_read`/`*_self_read` (own-rows SELECT via `auth.uid()`).

**Effective today:** legacy wins — role scoping is cosmetic. A technician CAN update any
task/zone/category in the tenant. Not exploited (3 trusted techs), but wrong at scale.

## Why you can't just DROP the legacy policies
Role-scoped write coverage is INCOMPLETE — dropping `*_all` breaks real flows:
1. **Technician completes a job** (tech view: status, checklist_done, photo_url,
   signature_url) → UPDATE on `tasks`; only `tasks_technician_read` (SELECT) exists.
2. **Technician saves a vacation** → INSERT into `day_offs`; only admin/coordinator ALL +
   tech SELECT exist.
3. **Batch/backend paths** use service key (bypasses RLS) — unaffected.
4. `is_super_admin()` (Eran's cross-tenant impersonation) appears ONLY in legacy quals —
   dropping them without re-adding super_admin clauses locks Eran out of tenant data.

## Target state (per table: ≤1 permissive policy per role×action)
For each table, ONE consolidated policy set, all using ONE helper generation
(`current_tenant_id()`/`current_user_role()` — keep `is_super_admin()` OR-clause):
- `SELECT`: `tenant_id = current_tenant_id() OR is_super_admin()` (single read policy;
  merge the narrow self/tech reads INTO it — they're subsets of tenant read for same-tenant
  users; verify users table: self-read may be INTENTIONALLY narrower than tenant-read —
  decide: do coordinators see all tenant users? App admin panel says yes ⇒ tenant read).
- `INSERT/UPDATE/DELETE` (per table):
  - tasks: admin+coordinator full; **new** `tasks_technician_update` — UPDATE where
    `technician_id IN (SELECT id FROM technicians WHERE user_id = (SELECT auth.uid()))`
    (row-level only; column limits need a trigger — defer, techs are trusted on own rows).
  - day_offs: admin+coordinator full; **new** `dayoffs_technician_write` — INSERT/UPDATE/
    DELETE own (`technician_id` self-join as above).
  - technicians/zones/categories/packages/tenants/users: admin (+coordinator where the
    app allows) only; plus `OR is_super_admin()` everywhere.
- Drop ALL legacy `*_all` policies + audit `clients_all`/`recurring_templates
  tenant_isolation`/`audit_log audit_read` (public SELECT on audit_log = every tenant
  member reads all tenant audit rows — decide if coordinator-only).

## Verification protocol (MUST run, in order)
1. Snapshot: `SELECT * FROM pg_policies WHERE schemaname='public'` → save to outputs/.
2. Apply per-table migration (one table per migration, tasks LAST).
3. After each table: `SET LOCAL ROLE authenticated; SET request.jwt.claims...` simulations
   for: admin (own tenant CRUD ✓, other tenant ✗), coordinator, technician (own-rows
   UPDATE ✓, others ✗, zone write ✗), super_admin (cross-tenant ✓).
4. App smoke test with Eran: login each role chip; technician job-complete + vacation-save
   (the flows with NEW policies); dispatch + zone edit as coordinator/admin.
5. Advisors re-run: multiple_permissive_policies → 0 (or explained); security advisors clean.
6. Update `context/auth-users.md` policy matrix + this file's outcome section.

## Also from the advisor run (INFO, no action yet)
Unused indexes (young DB — re-check after a month of pilot traffic before dropping):
idx_audit_tenant_table, idx_dayoffs_tech_date, idx_tasks_recurring_template,
idx_users_tenant, idx_packages_tenant, idx_rectemplates_pref_tech, idx_tasks_category.
No `auth_rls_initplan` warnings — auth.uid() wrapping is already clean everywhere.

## ✅ OUTCOME — EXECUTED 2026-07-06 (same day, Eran approved the role matrix in-session)
Eran confirmed the authorization matrix (admin = everything; coordinator = operations but
NOT settings/techs; technicians = own view + own-row writes) → executed immediately since
only 2 live users exist (Eran's admin + super_admin; no coordinator/tech logins yet —
zero real flows at risk, ideal timing).

1. **Dry-run**: full DDL + role sims in ONE rolled-back DO block (synthetic technician
   user created inside the txn incl. auth.users parent row). Report:
   `admin tasks_read=109 | admin tenant_update=1 | admin tech_update=1 | admin zones_update=8 |
   super crosstenant_tasks=109 | super tenant_update=1 | tech tasks_visible=39 (own=39) |
   tech own_update=39 | tech other_update=0 | tech zone_update=0 | tech tenant_update=0 |
   tech own_vacation_insert=1 | tech users_visible=2` — every gate exactly per the matrix.
2. **Applied** as migration `rls_consolidation_role_scoped`: all legacy `*_all` +
   two-generation policies dropped; one policy per action per table; helpers unified on
   `current_tenant_id()/current_user_role()` + `is_super_admin()`; NEW technician own-row
   policies (tasks UPDATE, day_offs INSERT/UPDATE/DELETE) so future tech logins work;
   tenants INSERT/DELETE = super_admin only (fixes the previously-broken tenant-creation
   RLS path). `audit_log` untouched (read-only, already single policy).
3. **Advisors after**: performance — 135 multiple_permissive_policies → **0**; unindexed
   FK → fixed. Security — only known intentional items (deny-all Layer-A tables INFO,
   4 helper-function WARNs required by RLS, leaked-password = Pro plan).
4. **Eran smoke test (pending, next login):** incognito login (admin) — home loads,
   dispatch works, zone edit saves, settings save; then 🔀 PureWater impersonation chip.
Dry-run technique worth reusing: DO block + SET LOCAL ROLE + set_config(jwt.claims) +
GET DIAGNOSTICS counts + RAISE EXCEPTION report = atomic RLS rehearsal with zero risk.
