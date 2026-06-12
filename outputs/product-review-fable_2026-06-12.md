# Full Product Review — Fresh-Eyes Audit (Fable 5)

> Date: 2026-06-12 · Scope: everything built/changed through the foundation brainstorm (zones & polygons, scheduling Plan A, mode-aware UI, bug fixes) + live DB audit + security/perf/data-integrity.
> Method: read all `context/` docs, key `index.html` paths, full `backend/`, ran Supabase security & performance advisors against the live project, and ran read-only data-integrity SQL probes.

## Verdict

**The foundations are sound and the brainstorm moved the product in the right direction.** The architecture decisions made — `resolveZone` as a single matching seam, the assignment/sequencing split with `route_strategy` as a soft bias, mode-aware UI driven by one predicate, per-tenant config over hardcoding — are the same patterns mature field-service/VRP products use. RLS posture is solid (every table enabled, tenant_id everywhere, no critical advisor findings). Test discipline (42 green assertions across two marker-extracted suites) and the living-docs rule are real assets.

Found: **1 genuine data-integrity bug** (WAL tenant stamping under impersonation), **1 modest backend cost-security gap** (`/geocode` unmetered), a batch of **cheap DB hardening wins**, and **4 doc-drift items**. Nothing critical; nothing that blocks the roadmap.

---

## 🔴 Important — fix soon

### 1. WAL replay can move a row across tenants under impersonation
`_replayWAL` (index.html ~2733) stamps **`tenant_id: currentTenantId`** onto every replayed row. For a normal user this is harmless (their tenant never changes). But for Eran: edit something while impersonating PureWater → save fails → lands in WAL → next session starts under Maslul Admin → replay rewrites that PureWater row with **Maslul Admin's tenant_id**. RLS won't block it (`is_super_admin()` bypasses), so the row silently migrates tenants. The backlog already suspected this ("WAL tenant isolation on replay") — confirmed real.
**Fix:** capture `tenant_id: currentTenantId` in `_walWrite` at write time; `_replayWAL` uses the stored value instead of the live one. ~4 lines.

### 2. `/geocode` is unauthenticated and outside the daily quota counter
`backend/main.py` `/geocode` calls Google Geocoding directly with no quota check and no auth. CORS does **not** protect server-to-server calls — anyone who finds the Railway URL can hammer it at ~$0.005/request against the Google key until the free credit drains. (`/optimize` is also unauthenticated, but it *is* bounded by the 1200-element/day counter, so exposure is capped.)
**Fix:** route `/geocode` through the same daily counter (e.g. count each geocode as N elements or its own `GEOCODE_DAILY_LIMIT`), and optionally a per-IP rate limit. Fold into Plan B1's backend work.

---

## 🟡 Worthwhile — one hardening migration before Client #2

All from the live advisors; invisible at 108 rows, real at scale. Bundle into a single SQL for Eran:

3. **RLS performance:**
   - 4 policies re-evaluate `auth.uid()` per row (`tasks_technician_read`, `technicians_self_read`, `users_self_read`, `dayoffs_technician_read`) — wrap as `(SELECT auth.uid())`.
   - 135 multiple-permissive-policy warnings — most tables have an `*_all` ALL policy *plus* per-operation policies, all evaluated per query. Consolidate to one policy per table/operation.
   - 9 unindexed FKs — notably the **`tenant_id` FKs** (zones, users, categories, packages, day_offs, recurring_templates) — these are the columns every RLS check filters on. Add indexes.
   - 3 unused indexes (`idx_audit_tenant_table`, `idx_dayoffs_tech_date`, `idx_tasks_recurring_template`) — keep for now (low traffic skews "unused"), re-check after Client #2.
4. **SECURITY DEFINER RPC exposure:** `get_tenant_id`, `is_super_admin`, `current_tenant_id`, `current_user_role`, `_maslul_audit_trigger`, `rls_auto_enable` are callable by `anon` via `/rest/v1/rpc/`. Low info-leak risk (they return NULL without a session) but unnecessary surface — `REVOKE EXECUTE FROM anon` on all six; also from `authenticated` for the trigger/util two.
5. **Leaked-password protection is off** — one click: Dashboard → Auth → enable HaveIBeenPwned check.
6. `pg_trgm` extension lives in `public` schema — cosmetic; move to `extensions` whenever convenient.

---

## 🟢 Cleanups & observations

7. **Zone leftovers (live data):** PureWater has 1 empty "אזור חדש" (QA artifact); Maslul Admin has 3 (one holds your polygon QA test). Harmless; delete from the zones page when convenient. *Everything else checked out: all 9 PureWater zones correctly linked in rotations (0 orphans — yesterday's fix verified at the DB level), 0 broken task→tech refs, 0 tenant-less rows.*
8. **All 108 tasks are `status='assigned'`** (batch-scheduled 06-08). The deferred re-calculation will need a reset-to-pending step first — already noted in the backlog prereqs.
9. **PureWater techs have `user_id = NULL`** — no tech login linkage yet. Fine today (coordinator-driven); becomes relevant when techs get the mobile view.
10. **Doc drift (fixed in this review's commit):** `context/architecture.md` still said `L('key')` after the `LBL` rename; `context/zones-polygons.md` carried the stale 6-zone rotation table; `context/business.md` said "4 technicians" (it's 3).

---

## Strengths to preserve (explicitly)

- **Safety stack layering:** WAL + `dbUpsert` single write-path + honest-toast rule + schema validator + audit-log triggers + connection monitor. This is more disciplined than most seed-stage products.
- **The seams:** `resolveZone`, `resolveRouteStrategy`/`isPairOrdered`, `splitLockedFlexible`, `usesZones` — small, pure, marker-tested functions that the whole app routes through. This is what makes per-tenant logic safe.
- **Process:** new-entity checklist, living-docs sync, dated migrations in `outputs/`, hard-learned auth rules documented. Secrets hygiene is clean (`.env` ignored, no keys tracked).
- **Quota guard already in place** (`GMAPS_DAILY_ELEMENT_LIMIT` + `/health` readout) — Plan B1's cache compounds it rather than replacing it.

## Architecture opinion (asked)

- **Single-file `index.html` (~7,600 lines) is past the comfort point** but the marker-block discipline compensates. The existing trigger (modularize at 2+ paying clients / 2nd developer) is the right call — don't restructure mid-roadmap.
- **Plan B1's "global cache" refinement is correct** (drive times are tenant-independent; service-role-only access).
- **One roadmap addition I recommend:** when B2's `sequenceDay` lands, emit a tiny **decision trace** per assignment ("נבחר בני, יום ג׳ — ממלא יום קיים (3 קריאות באזור), 12 דק׳ נסיעה מהמשימה הקודמת"). The expert-dispatcher pitch lives or dies on coordinator trust, and explainability is cheap if designed in now — and aligns with the no-internal-errors principle (explain *why*, in Hebrew).
- UI polish is a legitimate next workstream after the engine — agreed it comes after foundations; the mode-aware groundwork already removed the worst inconsistency (zone language for non-zone tenants).

## Where this leaves the roadmap

Unchanged, with two insertions:
1. **Plan B1 (cache)** — proceed; add the `/geocode` metering fix to its backend task.
2. **WAL tenant fix** — small standalone fix, do immediately (this review).
3. **Hardening migration** — SQL delivered to Eran (advisors batch), run anytime.
4. **Plan B2 (auto-sequencing)** — proceed after B1; include the decision trace.
