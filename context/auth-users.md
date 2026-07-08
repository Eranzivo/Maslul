# Auth & Users Context — Maslul

## Mental Model: Two Separate Concepts

| Concept | Table | Purpose |
|---|---|---|
| Login account | `public.users` | Who can log in and what they see |
| Scheduling profile | `technicians` | How a field worker is configured for routing |

A technician needs **both**. An admin or coordinator needs only a `users` row.

---

## Roles

| Role | Where managed | What they see |
|---|---|---|
| `admin` | `users` | Everything in their tenant |
| `coordinator` | `users` | Ops pages only — controlled by `users.permissions.views[]` |
| `tech` | `users` + `technicians` | Tech view only (`page-techview`) — their own schedule |
| `super_admin` | `users.super_admin = true` | Cross-tenant admin (`page-admin`, wizard, impersonation) |

`super_admin` is a boolean flag on Eran's user row, separate from `role`. It bypasses RLS at the app level and unlocks the master admin panel.

---

## Page Ownership

| Page | Who uses it | What it manages |
|---|---|---|
| `🔐 הרשאות גישה` (`page-users`) | Tenant admin | Login accounts for **admins + coordinators only** |
| `👷 טכנאים` (`page-technicians`) | Tenant admin | Scheduling profiles for technicians |
| `🛡️ מנהל מאסטר` (`page-admin`) | Eran (super_admin) | Cross-tenant: create tenants, run wizard, impersonate |

Technician login accounts (`role='tech'`) are **intentionally excluded** from `הרשאות גישה` — they are managed from the `טכנאים` page. This keeps the mental model clean: `הרשאות גישה` = management staff, `טכנאים` = field staff.

---

## Users Table Schema

```
users.id          — matches auth.uid() (Supabase Auth UUID)
users.tenant_id   — multi-tenant isolation
users.role        — 'admin' | 'coordinator' | 'tech'
users.name        — display name
users.email       — login email (empty string if not set)
users.super_admin — boolean (Eran only)
users.permissions — JSONB: { views: ['home','dispatch','tasks',...] }
users.created_at  — timestamp
```

**`email` is currently stored as empty string `""` for both existing users** (Eran and Israel). The email is managed in Supabase Auth, not in this table.

---

## RLS Policies on `users`

```sql
users_self_read  — SELECT: id = auth.uid()  (everyone can read their own row)
users_all        — ALL:    tenant_id = get_tenant_id() OR is_super_admin()
```

`users_admin_all` was dropped (2026-06-08) — it was redundant with `users_all`.

All four helper functions (`get_tenant_id`, `is_super_admin`, `current_tenant_id`, `current_user_role`) are `SECURITY DEFINER` — they bypass RLS when called from within RLS policies to prevent recursion.

---

## Technician ↔ User Linkage

- `technicians` table has no FK to `users` by default
- The link is `technicians.user_id` (nullable UUID) → `users.id`
- A tech user without a linked `technicians` row shows "⚠️ לא מקושר לטכנאי" warning
- When a tech logs in: `routeTechLogin()` finds `technicians` row via `user_id` → loads their schedule

---

## How Impersonation Works (Eran → Israel)

1. Eran logs in to Maslul Admin tenant (`tenant_id = '642ad6e6-...'`)
2. In master admin, "כנס לסשן" button calls `enterTenantSession(tenantId)`
3. `currentTenantId` is changed to the target tenant in-memory
4. All Supabase queries now use the new `tenant_id`
5. RLS: `users_all` passes because `is_super_admin() = true` for Eran
6. Exiting impersonation restores `currentTenantId` to Eran's own tenant

---

## Adding a New User (Coordinator / Admin)

1. Go to `🔐 הרשאות גישה`
2. Click `+ משתמש חדש`
3. Fill in name, email, role (admin/coordinator), and for coordinators: which pages they can see
4. Supabase Auth `admin.createUser()` is called → email confirmation sent
5. A row is inserted into `public.users` with the new user's UUID

**Important:** Email confirmation must be disabled in Supabase Auth settings for users to log in immediately. Check: Supabase Dashboard → Auth → Settings → "Enable email confirmations" OFF.

---

## Coordinator Permissions (`users.permissions.views`)

Coordinators can only see pages listed in their `permissions.views` array:
```json
{ "views": ["home", "dispatch", "tasks", "planner", "clients"] }
```

Available pages (**extended 2026-07-07**, Phase 1 access control): operational `home`, `dispatch`, `tasks`, `planner`, `reports`, `clients` **+ settings areas** `zones`, `categories`, `technicians`, `settings`, `users`. The admin picks these per coordinator in the user modal (grouped תפעול / הגדרות). Constant `PERM_AREAS`.

`applyFeatureVisibility()` gates every nav item by the coordinator's `views`. **Settings areas are VIEW-ONLY for coordinators** (Phase 1): granting `zones` lets a coordinator *see* the zones page, but edit controls are hidden (`body[data-ro-settings]` + `.settings-edit-only` class + `.settings-ro-banner`) and the **RLS floor blocks any write regardless** (every settings-table write policy requires `admin`/`super_admin` — verified). **Phase 2** (admin grants a coordinator *edit* on a specific area) needs per-user RLS grants — deferred to client #2 (see outputs/worklog.md). This is INTRA-tenant delegation; cross-tenant access is the separate super_admin impersonation.

## RLS policy matrix — consolidated 2026-07-06 (single generation, advisor-clean)

Migration `rls_consolidation_role_scoped` (dry-run role-simulated first; outcome log:
`outputs/rls-consolidation-plan_2026-07-06.md`). Legacy `*_all` policies (any tenant member
= full write) are GONE. One permissive policy per action; helpers `current_tenant_id()` /
`current_user_role()` / `is_super_admin()` only (`get_tenant_id()` is now unreferenced).

| Table | SELECT | INSERT | UPDATE | DELETE |
|---|---|---|---|---|
| tasks | admin+coord (tenant) / tech **own rows** / SA | admin+coord / SA | admin+coord / tech **own** / SA | admin+coord / SA |
| day_offs | tenant / SA | admin+coord / tech **own** / SA | same as insert | same |
| clients, recurring_templates | tenant / SA | admin+coord / SA | same | same |
| technicians, users, zones, categories, packages | tenant / SA | **admin only** / SA | same | same |
| tenants | own tenant / SA | **SA only** (fixed: was impossible) | admin (own) / SA | SA only |
| audit_log | tenant / SA (unchanged) | — | — | — |

Rules of thumb: coordinator = day-to-day operations, never settings/tech/zone/category
management (Eran 2026-07-06); technicians see & update ONLY their own tasks and manage
their own vacations (policies ready — no tech logins exist yet); `is_super_admin()` clause
present on every policy (Eran's cross-tenant impersonation). Backend uses the service key
(bypasses RLS) — unaffected. Any policy change ⇒ re-run BOTH advisors + the DO-block role
simulation (technique documented in the plan outcome).
